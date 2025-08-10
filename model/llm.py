import json 
from utils import query_chat_openai


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


class CoTPaper:
    def __init__(self , problem , str):

        self.problem = problem 
        self.small_problem = list()
        self.solutions = list()
        self.index = None
        self.all_snippets = list()

    
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
                                "text": "entity content",
                                "category": "metadata/content/quality_indicator/administrative/textual_clue",
                                "relevance_score": 8,
                                "potential_retraction_reason": 1,
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
            
        return self.entities
        
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

        return self.chains_of_thought
        

    


        




