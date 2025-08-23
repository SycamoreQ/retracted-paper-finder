import pymongo
import datetime
from bson.son import SON
from pymongo import MongoClient
import random
import numpy as np
import pinecone as pc 
from sentence_transformers import SentenceTransformer


client = MongoClient("mongodb://localhost:27017/")
db = client["retraction-paper-db"]


class Entities: 
    def get_entities_by_cat(db : MongoClient) -> MongoClient : 
        pipeline = [
                    {"$group": {"_id": "$Category", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}}
                    ]               

        result = db.entities.aggregate(pipeline)
        return result
    
    def get_entities_by_id(db : MongoClient , entity_id: int) -> MongoClient:
        return db.entities.find_one({"EntityID" : entity_id})
    
    def get_text_only(db: MongoClient , entity_id : int ) -> MongoClient:
            entity = db.entities.find_one({"EntityID": entity_id}, 
                                          {"TextContent": 1, "_id": 0})

            return entity.get("TextContent")
    
    def get_entities_by_relevance(db: MongoClient, relevance_score: int) -> MongoClient:
        return db.entities.find({"Relevance_score": relevance_score})
    
    def get_entities_by_potential_rank(db: MongoClient, potential_rank: int) -> MongoClient:
        return db.entities.find({"Potential_rank": potential_rank})
    
    def get_entities_by_context(db: MongoClient, context: str) -> MongoClient:
        return db.entities.find({"Context": context})
    
    def get_top_entities_by_relevance(db, top_n=10):
        return db.entities.find().sort("Relevance_score", -1).limit(top_n)
    
    def avg_relevance_by_category(db):
        pipeline = [
            {"$group": {"_id": "$Category", "avg_relevance": {"$avg": "$Relevance_score"}}},
            {"$sort": {"avg_relevance": -1}}
        ]
        return db.entities.aggregate(pipeline)


    

class Chains: 
    def get_chain_by_id(db : MongoClient , chain_id: int) -> int:
        return db.entities.find_one({"chain_ id" : chain_id})
    
    def get_no_entities(db : MongoClient , chain_id: int) -> MongoClient : 

        chain = db.chains.find_one({"chain_id" : chain_id} , {"entity_id" : 1} , {"_id" : 0})

        if chain and entity_id in chain : 
            return len(chain["entity_ids"])
        else :
            return 0
        
    def chains_with_most_entities(db, limit=5):
        pipeline = [
            {"$project": {"chain_id": 1, "num_entities": {"$size": "$entity_ids"}}},
            {"$sort": {"num_entities": -1}},
            {"$limit": limit}
        ]
        return db.chains.aggregate(pipeline)
    
    def avg_confidence_by_retraction_reason(db):
        pipeline = [
            {"$group": {"_id": "$retraction_reason", "avg_confidence": {"$avg": "$confidence_score"}}},
            {"$sort": {"avg_confidence": -1}}
        ]
        return db.chains.aggregate(pipeline)
    
    def chains_with_shared_entities(db, entity_id):
        return db.chains.find({"entity_ids": entity_id})
    
    def combined_reasoning_steps(db, chain_id):
        chain = db.chains.find_one({"chain_id": chain_id}, {"reasoning_steps": 1, "_id": 0})
        if chain and "reasoning_steps" in chain:
            return " ".join(chain["reasoning_steps"])
        return None
    

class Cluster: 
    def get_cluster_by_id(db: MongoClient, cluster_id: int) -> MongoClient:
        return db.clusters.find_one({"cluster_id": cluster_id})
    
    def get_clusters_by_size(db: MongoClient, min_size: int) -> MongoClient:
        return db.clusters.find({"cluster_size": {"$gte": min_size}})
    
    def avg_severity_by_cluster(db: MongoClient):
        pipeline = [
            {"$group": {"_id": "$cluster_id", "avg_severity": {"$avg": "$avg_severity"}}},
            {"$sort": {"avg_severity": -1}}
        ]
        return db.clusters.aggregate(pipeline)
    
    def clusters_with_common_reason(db: MongoClient, reason: str) -> MongoClient:
        return db.clusters.find({"common_reason": reason})
    
    def find_cluster_similarity(db : MongoClient, cluster_id: int) -> MongoClient:
        cluster = db.clusters.find_one({"cluster_id": cluster_id})
        if not cluster:
            return None
        
        pipeline = [
            {"$match": {"cluster_id": {"$ne": cluster_id}}},
            {"$project": {
                "cluster_id": 1,
                "similarity_score": {
                    "$size": {
                        "$setIntersection": ["$cluster_relations", cluster["cluster_relations"]]
                    }
                }
            }},
            {"$sort": {"similarity_score": -1}}
        ]
        
        return db.clusters.aggregate(pipeline)
    
    def clusters_with_high_avg_confidence(db: MongoClient, threshold: float) -> MongoClient:
        return db.clusters.find({"avg_confidence_score": {"$gte": threshold}})
    
    def clusters_with_high_avg_severity(db: MongoClient, threshold: float) -> MongoClient:
        return db.clusters.find({"avg_severity_level": {"$gte": threshold}})
    
    def community_detection(db : MongoClient , min_size = 3 ): 

        pipeline = [
            {"$project": {"entity_ids": 1, "chain_id": 1, "_id": 0}},
            {"$match": {"$expr": {"$gte": [{"$size": "$entity_ids"}, min_size]}}},
            {"$group": {
                "_id": "$entity_ids", 
                "chains": {"$addToSet": "$chain_id"},
                "community_size": {"$first": {"$size": "$entity_ids"}},
                "chain_count": {"$sum": 1},
                "similarity_score" : {"$sort":SON([{"similarity_score.value" , -1}])}
            }},
            {"$sort": SON([("community_size", -1), ("chain_count", -1)])}
            ]
        
        return db.clusters.aggregate(pipeline)
    

class Search : 
    
    # Add to requirements: pinecone-client, sentence-transformers
    def generate_embeddings(self, text):
        model = SentenceTransformer('all-MiniLM-L6-v2')
        return model.encode(text)

    def find_similar_papers(self, query_embedding, top_k=10):

    





 