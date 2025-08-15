import json 
from utils import query_chat_openai
import redis
from redis.commands.search.field import TagField
from redis.commands.search.index_definition import IndexType , IndexDefinition
from redis.commands.search import Search 
from redis.commands.search.aggregation import AggregateRequest
from typing import List, Dict, Optional, Any


redis_client = redis.Redis(host="localclient" , port="9000" , db = 0)

def schema_match(agg_func: str) -> TagField: 
    if agg_func == "entities":
        match agg_func : 
            case 1: 
                schema = TagField("$entities[*].entityId" , as_name = "entityId")

    if agg_func == "chain": 
        match agg_func : 
            case 1: 
                schema = TagField("$entities[*].confidence_score" , as_name = "confidence_score")


    return schema 
            



COT_BREAKDOWN_PROBLEM_SYSTEM_MESSAGE = """You are an expert in breaking down a big problem into smaller problems. The reason you break down big problems into smaller ones, is that the system can then search for solutions for each one of the small problems individually, thus increasing the chance of success.

If two or more of the small problems are related, please merge them into just one small problem. Your problem is to detect the reason for the retraction of academic papers. There can be 10 reasons why for now

1. Factual/methodological/other critical errors in manuscript
2. Incomplete exposition or more work in progress
3. Typos in manuscript
4. Self-identified as "not novel"
5. Administrative or legal issues
6. ArXiv policy violation
7. Subsumed by another publication
8. Plagiarism
9. Personal reasons
10. Reason not specified

Let me work through this systematically:

1. Given a paper, you recognise the author, DOI or the Digital object Identifier, date of publication. You should also recognise the topic of the paper i.e what the paper tries to explain.
2. You then scrape the document for important entities that might be a clue as to why the paper has been retracted based on the given reasons above. All these entities need to be collected and be considered as nodes
3. All these entities can be chunks of text, mathematical formulae which can be direct statements/explicit reasons but also look deep into the paper and find implicit hidden patterns by linking the entities with each other as a chain of events and return the chain based reasoning as a total reason as to why that paper is retracted based on the above 10 possibilities.
4. In this way you are breaking down bigger problems into smaller ones by considering each entity as a key to understanding why that paper is retracted. The key could also be the complex and the causal patterns of entities you might have computed.
"""

ENTITY_IDENTIFICATION_SYSTEM_MESSAGE = """You are an expert in identifying key entities from academic papers that could indicate reasons for retraction. 

Your task is to extract and categorize entities that might provide clues about paper retraction. Look for:

1. **Metadata Entities**: Authors, DOI, publication date, journal, title, research topic
2. **Content Entities**: Key methodologies, data sources, statistical methods, experimental procedures
3. **Quality Indicators**: Error statements, correction notices, duplicate content markers
4. **Administrative Markers**: Policy violations, ethical concerns, plagiarism indicators
5. **Textual Clues**: Specific phrases or statements that might indicate problems

For each entity, provide:
- Entity text/content
- Category (metadata, content, quality_indicator, administrative, textual_clue)
- Relevance score (1-10) for retraction analysis
- Potential retraction reason it relates to (1-10 from the list)
"""

CHAIN_OF_THOUGHT_SYSTEM_MESSAGE = """You are an expert in creating logical chains of reasoning to determine why academic papers are retracted.

Given a list of entities extracted from a paper, your task is to:

1. **Connect Related Entities**: Group entities that are logically connected
2. **Build Causal Chains**: Create sequences showing how entities lead to potential retraction reasons
3. **Identify Patterns**: Look for implicit patterns that might not be obvious from individual entities
4. **Synthesize Reasoning**: Provide a comprehensive explanation of the most likely retraction reason(s)

For each chain, provide:
- Chain of entities (in logical order)
- Reasoning steps connecting the entities
- Confidence score (1-10)
- Final retraction reason classification (1-10)
"""

CLUSTER_PAPER_SYSTEM_MESSAGE = """You are an expert in clustering entities of similar nature. Your task is supposed to cluster academic papers which have the same reason as to why
they are retracted based on entities given to you 

Given a list of entities called entity chains that are retrieved from the paper , your task is to: 

1. **Determine similar entities**: Identify entities that might be similar
2. **Cluster Entities**: Cluster entites based on a few reasons like 
- Same DOI but different retraction reasons 
- Similar retraction reasons
- Similar plagiarism content 
- Similar subject 
- Same author (or any metadata match)
- Similar confidence score , severity level 

Give a reason as to why you had to cluster these chains and also you are allowed to find relationships between these chains based on the reason given by you .

"""


class CoTPaper:
    def __init__(self , problem , str):

        self.problem = problem 
        self.small_problem = list()
        self.solutions = list()
        self.index = None
        self.all_snippets = list()

    def extract_metadata(self, paper_content: str) -> dict[str, Any]:
        system_message = """You are an expert at extracting metadata from academic papers. 
        Extract the following information and return it in JSON format:
        - title
        - authors (with affiliations if available)
        - publication_date
        - doi
        - journal
        - abstract
        - keywords
        - subject_categories"""
        
        prompt = f"""Extract metadata from this paper:

        {paper_content[:3000]}  # First 3000 chars for metadata

        Return in this JSON format:
        {{
            "title": "paper title",
            "authors": [
                {{"name": "Author Name", "affiliation": "Institution", "email": "email@domain.com"}}
            ],
            "publication_date": "YYYY-MM-DD",
            "doi": "10.xxxx/xxxxx",
            "journal": "Journal Name",
            "abstract": "Abstract text",
            "keywords": ["keyword1", "keyword2"],
            "subject_categories": ["cs.AI", "stat.ML"]
        }}
        """
        
        response = query_chat_openai(system_message, prompt)
        
        try:
            metadata = json.loads(response)
            # Generate paper_id if not present
            metadata['paper_id'] = self._generate_paper_id(metadata.get('title', ''), 
                                                        metadata.get('publication_date', ''))
            
            self.analysis_data["paper_analysis"]["metadata"] = metadata
            return metadata
        except json.JSONDecodeError:
            print("⚠️ Could not extract metadata, using defaults")
            return self._get_default_metadata()

    
    def break_down_problem(self) -> list[str]:
        system_message = COT_BREAKDOWN_PROBLEM_SYSTEM_MESSAGE
        
        prompt = f"""Problem to be broken down:
                    {self.problem}

                    <End of problem>
                    
                    Please return your results in a JSON object in this format:

                    {{\"results\": [\"problem_1\", \"problem_2\", ...]}}
                    """
        
        response = query_chat_openai(system_message , prompt)

        try:
            response = json.loads(response)
        except json.decoder.JSONDecodeError:
            if '{"results"' in response:
                split_response = response.split('{')[1]
                response = json.loads(f"{{{split_response}")
            else:
                raise Exception('Error breaking down problem: Response from LLM is not JSON compliant')

        self.small_problems = response['results']
        return self.small_problems
    

    def identify_entities(self , paper_content: str) -> list[dict]:
        system_message = ENTITY_IDENTIFICATION_SYSTEM_MESSAGE
        
        prompt = f"""Paper content to analyse for entities:

                    {paper_content}

                    <End of paper content>

                    Please identify the key entities that could indicate the retraction reasons . Return results in JSON format:

                    {{
                        "entities": [
                            {{
                                "entityId":"1"
                                "text": "entity content",
                                "category": "metadata/content/quality_indicator/administrative/textual_clue",
                                "relevance_score": 8,
                                "potential_retraction_reason": 1,
                                "page_number": 7,
                                "context": "surrounding context or explanation"
                            }}
                        ]
                    }}
                """
        
        response = query_chat_openai(system_message , prompt)
        
        try: 
            response = json.load(response)
            self.entities = response['entities']
            
        except json.JSONDecodeError: 
            if '{"entities"' in response:
                split_response = response.split('{}')[1]
                response = json.load(f"{{{split_response}")
                self.entities = response['entities']

            else:
                raise Exception('error identifying entities: Response from LLM is not json compliant')
            

        unique_key = (entities["entityId"] for entities in response["entitiyId"])
        redis_client.set(unique_key , response)

             
        return self.entities , redis_client
        
    def build_chains_of_thought(self, entities: list[dict] = None) -> list[dict]:
        """Build logical chains of reasoning from the identified entities"""
        if entities is None:
            entities = self.entities

        if not entities:
            raise ValueError("No entities available. Run identify_entities() first.")

        system_message = CHAIN_OF_THOUGHT_SYSTEM_MESSAGE

        entities_text = json.dumps(entities, indent=2)

        prompt = f"""Entities identified from the paper:

        {entities_text}

        <End of entities>

        Based on these entities, create logical chains of reasoning to determine the most likely retraction reason(s).

        Return results in JSON format:
        {{
            "chains": [
                {{
                    "chain_id": 1,
                    "entity_sequence": ["entity1", "entity2", "entity3"],
                    "reasoning_steps": [
                        "Step 1: Entity1 indicates...",
                        "Step 2: This connects to Entity2 because...",
                        "Step 3: Together they suggest..."
                    ],
                    "confidence_score": 8,
                    "retraction_reason": 1,
                    "frequency": 1,
                    "severity_level": {self.severity_level_calculator(response["frequency"])},
                    "explanation": "Overall explanation of this chain's conclusion"
                }}
            ],
            "final_assessment": {{
                "most_likely_reason": 1,
                "confidence": 9,
                "supporting_chains": [1, 2],
                "summary": "Comprehensive explanation of the retraction reason"
            }}
        }}
        """

        response = query_chat_openai(system_message, prompt)

        try:
            response = json.loads(response)
            self.chains_of_thought = response
        except json.JSONDecodeError:
            if '{"chains"' in response:
                split_response = response.split('{')[1]
                response = json.loads(f"{{{split_response}")
                self.chains_of_thought = response
            else:
                raise Exception('Error building chains of thought: Response from LLM is not JSON compliant')
            
        
        unique_key = [entities["chain_id"] for entities in response["chain_id"]]
        redis_client.set(unique_key , response)

        return self.chains_of_thought
    
    def cluster_papers(self  , paper_content: str , entities : List[dict] , cluster_threshold: int = 10 ) -> json : 
        system_message = CLUSTER_PAPER_SYSTEM_MESSAGE
        entities = self.identify_entities(paper_content) 
        chain_of_thought = self.build_chains_of_thought(entities)
        
        chains = (chains["chains"] for chains in json.loads(chain_of_thought))

        prompt = f"""Chains identified from the paper :
        {chains}

        <End of chains> 
        
        Based on these entities ,create logical clusters create and return the most possible clusters 
        
        Return results in json format: 
        {{
            "clusters":[
                {{
                    "cluster_id": 1 ,
                    "common_reason" : "Chains are clustered because they all violate the arxiv policy", 
                    "possible_connection" : "Chains 1 and 2 might be closely connected because of the same author and the same reaosns for retraction" ,
                    "average_severity_level" : "6.5" ,
                    "average_confidence_score" : 5.4 
                }}
                ],

            "final_analysis": {{
                    "summary" : "Clusters 1 seems most connected due to the fact that the papers in that cluster have a lot in common considering the similarity score
                    of he two clusters which might suggest that the same author or different authors in the same subject of interest is prone to higher retraction rates 
                    which can be mitigated"
            
                }}
            }}
        """
        
        
    
    def severity_level_calculator(frequency: float):
        sum += frequency if frequency != 0 else 0 
        return sum 

    
        

    


        




