import os
import glob
from typing import List, Dict, Any, Tuple
from pathlib import Path
from langchain_community.graphs import Neo4jGraph
from langchain.chains import create_history_aware_retriever
from langchain_core.prompts import PromptTemplate,MessagesPlaceholder,ChatPromptTemplate
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import pandas as pd
from neo4j import GraphDatabase
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter, CharacterTextSplitter
from langchain.schema import Document
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

graph = Neo4jGraph(
    url=os.getenv("NEO4J_URI"),
    username=os.getenv("NEO4J_USER"),
    password=os.getenv("NEO4J_PASSWORD"),
)

gen_kwargs = {
    "max_length": 256,
    "length_penalty": 0,
    "num_beams": 3,
    "num_return_sequences": 1,
}

triples = []

driver = GraphDatabase.driver(URI, auth=AUTH)

class PDFProcessor:
    def __init__(self, 
                 chunk_size: int = 1000, 
                 chunk_overlap: int = 200,
                 splitter_type: str = "recursive"):
        """
        Initialize PDF processor with text splitting parameters
        
        Args:
            chunk_size: Size of each text chunk
            chunk_overlap: Overlap between chunks
            splitter_type: Type of splitter ('recursive' or 'character')
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        if splitter_type == "recursive":
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len,
                separators=["\n\n", "\n", " ", ""]
            )
        else:
            self.text_splitter = CharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separator="\n"
            )
    
    
    def load_all_pdfs(self, directory_path: str) -> Dict[str, List[Document]]:
        """
        Load and split all PDFs from a directory
        
        Args:
            directory_path: Path to directory containing PDFs
            
        Returns:
            Dictionary mapping filename to list of document chunks
        """
        pdf_files = self.find_pdf_files(directory_path)
        
        if not pdf_files:
            print("No PDF files found in the directory")
            return {}
        
        results = {}
        total_chunks = 0
        
        for pdf_path in pdf_files:
            filename = os.path.basename(pdf_path)
            print(f"\nProcessing: {filename}")
            
            chunks = self.load_single_pdf(pdf_path)
            if chunks:
                results[filename] = chunks
                total_chunks += len(chunks)
        
        print(f"\n=== Summary ===")
        print(f"Processed {len(results)} PDF files")
        print(f"Total chunks created: {total_chunks}")
        print(f"Average chunks per file: {total_chunks/len(results) if results else 0:.1f}")
        
        return results
    

def extract_triplets(text):
    triplets = []
    relation, subject, relation, object_ = '', '', '', ''
    text = text.strip()
    current = 'x'
    for token in text.replace("<s>", "").replace("<pad>", "").replace("</s>", "").split():
        if token == "<triplet>":
            current = 't'
            if relation != '':
                triplets.append({'head': subject.strip(), 'type': relation.strip(),'tail': object_.strip()})
                relation = ''
            subject = ''
        elif token == "<subj>":
            current = 's'
            if relation != '':
                triplets.append({'head': subject.strip(), 'type': relation.strip(),'tail': object_.strip()})
            object_ = ''
        elif token == "<obj>":
            current = 'o'
            relation = ''
        else:
            if current == 't':
                subject += ' ' + token
            elif current == 's':
                object_ += ' ' + token
            elif current == 'o':
                relation += ' ' + token
    if subject != '' and relation != '' and object_ != '':
        triplets.append({'head': subject.strip(), 'type': relation.strip(),'tail': object_.strip()})
    return triplets


def generate_triples(texts):
    tokenizer = AutoTokenizer.from_pretrained("Babelscape/rebel-large")
    model = AutoModelForSeq2SeqLM.from_pretrained("Babelscape/rebel-large")


    model_inputs = tokenizer(texts, max_length=512, padding=True, truncation=True, return_tensors='pt')
    generated_tokens = model.generate(
        model_inputs["input_ids"].to(model.device),
        attention_mask=model_inputs["attention_mask"].to(model.device),
        **gen_kwargs
    )
    decoded_preds = tokenizer.batch_decode(generated_tokens, skip_special_tokens=False)
    for idx, sentence in enumerate(decoded_preds):
        et = extract_triplets(sentence)
        for t in et:
            triples.append((t['head'], t['type'], t['tail']))

def clean_node_name(self, name: str) -> str:
    """Clean node names for Neo4j storage"""
    if not name:
        return ""
    # Remove special characters and normalize
    cleaned = name.strip().replace('"', '').replace("'", "").replace('\\', '')
    return cleaned[:100]  # Limit length

def clean_relation_name(self, relation: str) -> str:
    """Clean relationship names for Neo4j storage"""
    if not relation:
        return ""
    # Replace spaces and special characters with underscores
    cleaned = relation.strip().upper().replace(' ', '_').replace('-', '_')
    cleaned = ''.join(c if c.isalnum() or c == '_' else '_' for c in cleaned)
    return cleaned[:50]  # Limit length


def load_triplets_to_neo4j(self, 
                        triples: List[Tuple[str, str, str]], 
                        source_info: Dict[str, Any] = None,
                        batch_size: int = 1000) -> Dict[str, int]:
    """
    Load triplets into Neo4j database
    
    Args:
        triplets: List of (head, relation, tail) tuples
        source_info: Dictionary with source document information
        batch_size: Number of triplets to process in each batch
        
    Returns:
        Dictionary with statistics about loaded data
    """
    if not triples:
        logger.warning("No triplets to load")
        return {"nodes": 0, "relationships": 0, "errors": 0}
    self.create_neo4j_indexes()
    
    stats = {"nodes": 0, "relationships": 0, "errors": 0}
    
    for i in range(0, len(triples), batch_size):
        batch = triples[i:i + batch_size]
        logger.info(f"Loading batch {i//batch_size + 1}/{(len(triples)-1)//batch_size + 1}")
        
        try:
            with self.driver.session() as session:
                batch_data = []
                for head, relation, tail in batch:
                    cleaned_head = self.clean_node_name(head)
                    cleaned_tail = self.clean_node_name(tail)
                    cleaned_relation = self.clean_relation_name(relation)
                    
                    if cleaned_head and cleaned_tail and cleaned_relation:
                        batch_data.append({
                            'head': cleaned_head,
                            'tail': cleaned_tail,
                            'relation': cleaned_relation,
                            'source': source_info.get('source', 'unknown') if source_info else 'unknown',
                            'source_file': source_info.get('file', 'unknown') if source_info else 'unknown'
                        })
                
                if not batch_data:
                    continue
                
                cypher_query = """
                UNWIND $batch AS row
                
                // Create or merge head entity
                MERGE (head:Entity {name: row.head})
                ON CREATE SET head.created_at = datetime(),
                            head.source = row.source
                ON MATCH SET head.last_seen = datetime()
                
                // Create or merge tail entity  
                MERGE (tail:Entity {name: row.tail})
                ON CREATE SET tail.created_at = datetime(),
                            tail.source = row.source
                ON MATCH SET tail.last_seen = datetime()
                
                // Create relationship with dynamic type
                WITH head, tail, row
                CALL apoc.create.relationship(head, row.relation, {
                    created_at: datetime(),
                    source: row.source,
                    source_file: row.source_file
                }, tail) YIELD rel
                
                RETURN count(rel) as relationships_created
                """
                
                simple_query = """
                UNWIND $batch AS row
                
                // Create or merge entities and relationship
                MERGE (head:Entity {name: row.head})
                ON CREATE SET head.created_at = datetime(),
                            head.source = row.source
                
                MERGE (tail:Entity {name: row.tail})
                ON CREATE SET tail.created_at = datetime(),
                            tail.source = row.source
                
                MERGE (head)-[r:RELATED_TO]->(tail)
                ON CREATE SET r.relation_type = row.relation,
                            r.created_at = datetime(),
                            r.source = row.source,
                            r.source_file = row.source_file
                
                RETURN count(r) as relationships_created
                """
                
                # Try APOC query first, fall back to simple query
                try:
                    result = session.run(cypher_query, batch=batch_data)
                    summary = result.consume()
                except:
                    logger.info("APOC not available, using simple relationships")
                    result = session.run(simple_query, batch=batch_data)
                    summary = result.consume()
                
                # Update statistics
                stats["nodes"] += summary.counters.nodes_created
                stats["relationships"] += summary.counters.relationships_created
                
        except Exception as e:
            logger.error(f"Error loading batch: {e}")
            stats["errors"] += len(batch)
    
    logger.info(f"Loading complete. Stats: {stats}")
    return stats
    
    
