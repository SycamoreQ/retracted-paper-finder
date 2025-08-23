import redis 
import pymongo
from pymongo import MongoClient
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import pickle
import hashlib
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import logging
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RedisCache:
    def __init__(self , host = 'localhost' , port = 6379 , db = 0  , ttl = 3600):
        self.client = redis.StrictRedis(host=host, port=port, db=db)
        self.default_ttl = ttl

    def _generate_key(self , prefix: str , identifier: str) -> str:
        return f"{prefix}:{hashlib.md5(identifier.encode()).hexdigest()}"
    
    def get_paper_analysis(self, paper_id: str) -> Optional[Dict]:
        """Get cached paper analysis results"""
        key = self._generate_key("paper_analysis", paper_id)
        cached_data = self.redis_client.get(key)
        if cached_data:
            logger.info(f"Cache hit for paper analysis: {paper_id}")
            return json.loads(cached_data)
        return None
    
    def cache_paper_analysis(self, paper_id: str, analysis_data: Dict, ttl: int = None) -> bool:
        """Cache paper analysis results"""
        key = self._generate_key("paper_analysis", paper_id)
        ttl = ttl or self.default_ttl
        try:
            self.redis_client.setex(key, ttl, json.dumps(analysis_data))
            logger.info(f"Cached paper analysis: {paper_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cache paper analysis {paper_id}: {e}")
            return False
        
    def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get cached text embedding"""
        key = self._generate_key("embedding", text[:100])  # Use first 100 chars for key
        cached_embedding = self.redis_client.get(key)
        if cached_embedding:
            logger.info("Cache hit for embedding")
            return np.frombuffer(eval(cached_embedding), dtype=np.float32)
        return None
    
    def cache_embedding(self, text: str, embedding: np.ndarray, ttl: int = None) -> bool:
        """Cache text embedding"""
        key = self._generate_key("embedding", text[:100])
        ttl = ttl or self.default_ttl
        try:
            embedding_bytes = embedding.astype(np.float32).tobytes()
            self.redis_client.setex(key, ttl, str(embedding_bytes))
            return True
        except Exception as e:
            logger.error(f"Failed to cache embedding: {e}")
            return False
    
    def get_similar_papers(self, query_hash: str) -> Optional[List[Dict]]:
        """Get cached similarity search results"""
        key = self._generate_key("similar_papers", query_hash)
        cached_results = self.redis_client.get(key)
        if cached_results:
            logger.info("Cache hit for similarity search")
            return json.loads(cached_results)
        return None
    
    def cache_similar_papers(self, query_hash: str, similar_papers: List[Dict], ttl: int = None) -> bool:
        """Cache similarity search results"""
        key = self._generate_key("similar_papers", query_hash)
        ttl = ttl or self.default_ttl
        try:
            self.redis_client.setex(key, ttl, json.dumps(similar_papers))
            return True
        except Exception as e:
            logger.error(f"Failed to cache similar papers: {e}")
            return False
    
    def invalidate_paper_cache(self, paper_id: str) -> bool:
        """Invalidate all cache entries for a specific paper"""
        try:
            keys_to_delete = []
            keys_to_delete.append(self._generate_key("paper_analysis", paper_id))
            
            # Delete the keys
            if keys_to_delete:
                self.redis_client.delete(*keys_to_delete)
                logger.info(f"Invalidated cache for paper: {paper_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to invalidate cache for paper {paper_id}: {e}")
            return False
        

class SimilaritySearch:
    """Semantic similarity search for retracted papers"""
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2', cache: RedisCache = None):
        self.model = SentenceTransformer(model_name)
        self.cache = cache
        
    def generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for text with caching support"""
        if self.cache:
            cached_embedding = self.cache.get_embedding(text)
            if cached_embedding is not None:
                return cached_embedding
        
        # Generate new embedding
        embedding = self.model.encode([text])[0]
        
        # Cache the embedding
        if self.cache:
            self.cache.cache_embedding(text, embedding)
        
        return embedding
    
    def find_similar_papers(self, db: MongoClient, query_text: str, top_k: int = 10, 
                          similarity_threshold: float = 0.5) -> List[Dict]:
        """Find papers similar to the query text"""
        
        query_hash = hashlib.md5(f"{query_text}_{top_k}_{similarity_threshold}".encode()).hexdigest()
        
        if self.cache:
            cached_results = self.cache.get_similar_papers(query_hash)
            if cached_results:
                return cached_results
        
        query_embedding = self.generate_embedding(query_text)
        
        papers_cursor = db.papers.find({"embedding": {"$exists": True}})
        
        similarities = []
        for paper in papers_cursor:
            if 'embedding' in paper and paper['embedding']:
                paper_embedding = np.array(paper['embedding'])
                similarity = cosine_similarity([query_embedding], [paper_embedding])[0][0]
                
                if similarity >= similarity_threshold:
                    similarities.append({
                        'paper_id': paper.get('paper_id'),
                        'title': paper.get('title'),
                        'authors': paper.get('authors'),
                        'similarity_score': float(similarity),
                        'retraction_reason': paper.get('retraction_reason'),
                        'doi': paper.get('DOI')
                    })
        
        similarities.sort(key=lambda x: x['similarity_score'], reverse=True)
        results = similarities[:top_k]
        
        if self.cache:
            self.cache.cache_similar_papers(query_hash, results)
        
        return results
    
    def find_similar_entities(self, db: MongoClient, entity_text: str, top_k: int = 5) -> List[Dict]:
        """Find similar entities based on text content"""
        entity_embedding = self.generate_embedding(entity_text)
        
        # Get entities with embeddings
        entities_cursor = db.entities.find({"embedding": {"$exists": True}})
        
        similarities = []
        for entity in entities_cursor:
            if 'embedding' in entity and entity['embedding']:
                entity_emb = np.array(entity['embedding'])
                similarity = cosine_similarity([entity_embedding], [entity_emb])[0][0]
                
                similarities.append({
                    'entity_id': entity.get('EntityID'),
                    'text_content': entity.get('TextContent'),
                    'category': entity.get('Category'),
                    'similarity_score': float(similarity),
                    'relevance_score': entity.get('Relevance_score')
                })
        
        similarities.sort(key=lambda x: x['similarity_score'], reverse=True)
        return similarities[:top_k]
    
    