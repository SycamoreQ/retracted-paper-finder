import pymongo 
import datetime


paper_schema = [

    {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["title", "author", "DOI", "Date", "Journal", "Subject"],
        "properties": {
            "title": {
                "bsonType": "string",
                "description": "Paper title"
            },

            "author": {
                "bsonType": "string",
                "description": "Author name"
                },

            "DOI": {
                "bsonType": "string",
                "description": "Document Object ID"
            },

            "Date": {
                "bsonType": "date",
                "description": "Publication date"
            },

            "Journal": {
                "bsonType": "string",
                "description": "Journal name"
            },

            "Subject": {
                "bsonType": "string",
                "description": "Paper subject category"
            }
        }
    }
    }
]


entities_schema = [
    {
  "$jsonSchema": {
        "bsonType": "object",
        "required": ["EntityID", "TextContent", "Category", "Relevance_score", "Potential_rank", "Context"],

        "properties": {
            "EntityID": {"bsonType": "int"},
            "TextContent": {"bsonType": "string"},
            "Category": {"bsonType": "string"},
            "Relevance_score": {"bsonType": "int"},
            "Potential_rank": {"bsonType": "int"},
            "Context": {"bsonType": "string"}
            }
        }
    }
]

chain_schema = [
    {
  "$jsonSchema": {
        "bsonType": "object",
        "required": ["chain_id", "entity_ids", "reasoning_steps", "confidence_score", "Frequency", "Severity_level", "OverallExplanation"],

        "properties": {
            "chain_id": {"bsonType": "int"},
            "entity_ids": {
                "bsonType": "array",
                "items": {"bsonType": "int"}
            },

            "reasoning_steps": {
                "bsonType": "array",
                "items": {"bsonType": "string"}
            },

            "confidence_score": {"bsonType": "int"},
            "Frequency": {"bsonType": "int"},
            "Severity_level": {"bsonType": "int"},
            "OverallExplanation": {"bsonType": "string"}
            }
        }
    }
]

filtered_schema = [
    {
        "$jsonSchema":{
            "bsonType" : "object",
            "required" : ["chain_id" , "summary" , "confidence_score"],

            "properties": {
                "chain_id" : {"bsonType" : "int"},
                "summary":   {"bsonType" : "string"},
                "confidence_score" : {"bsonType" : "int"}
            }
        }
    }
]

cluster_schema = [
    {
        "$jsonSchema" : {
            "bsonType" : "object",
            "required" : ["cluster_id" , "cluster_size" , "cluster_intra_relations" , "avg_severity" , "avg_confidence" , "common_reason "],
            

            "properties": {
                "cluster_id" : {"bsonType" : "int"},
                "cluster_size" : {"bsonType" : "int"},
                "cluster_relations" : {"bsonType" : "string"},
                "avg_confidence_score" : {"bsonType" : "float"},
                "avg_severity_level" : {"bsonType" : "float"}
            }
        }
    }
]




