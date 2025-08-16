import pymongo
import datetime
from bson.son import SON
from pymongo import MongoClient


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
    
    def 

 