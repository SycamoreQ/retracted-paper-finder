from langchain_community.graphs import Neo4jGraph
from langchain.chains import create_history_aware_retriever
from langchain_core.prompts import PromptTemplate,MessagesPlaceholder,ChatPromptTemplate
import json 

class Graph:
    DOI: str
    source: str 
    abstract: str
    subjects: str
    
    def set_entity(self , DOI):
        self.graph.query(
            f"""
                MATCH(n:`__Entity__`)
                REMOVE n:`__Entity__`
                SET n: `__Entity__{DOI}`
            """
        )

    def set_document(self,DOI):
        self.graph.query(
            f"""
                MATCH (n:`Document`)
                REMOVE n:`Document`
                SET n:`Document{uuid}`
            """
        )
        

    def 
    