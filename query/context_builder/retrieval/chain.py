"""base class for subgraph related context building . This can be applied to local
and global context building 
"""


from database.community import Chain
from typing import List , Dict , Any , cast
import uuid 
import re 
import pandas as pd 
import collections.abc 
from collections.abc import Iterable
import datetime 
import numpy as np 
import networkx as nx 
from retrieval.entity import * 

from .entity import ( 
    find_seminal_papers,
    find_trending_papers,
    get_entities_by_citations
)



def get_chain_by_id(chains: dict[str , Chain] , value: str) -> Chain | None : 
    """Get chain by id"""

    chain =  chains.get(value)
    if community is None and is_valid_uuid(value):
        community = chains.get(value.replace("-" , ""))
    return community

def get_chains_by_key(
    chains: Iterable[Chain], key: str, value: str | int
) -> Chain | None:
    """Get chains by key."""
    if isinstance(value, str) and is_valid_uuid(value):
        value_no_dashes = value.replace("-", "")
        for community in chains:
            community_value = getattr(community, key)
            if community_value in (value, value_no_dashes):
                return community
    else:
        for community in chains:
            if getattr(community, key) == value:
                return community
    return None



def get_chains_by_attribute(
    chains: Iterable[Chain], attribute_name: str, attribute_value: Any
) -> list[Chain]:
    """Get chains by attribute."""
    return [
        community
        for community in chains
        if community.attributes
        and community.attributes.get(attribute_name) == attribute_value
    ]


def get_reasoning_steps(chains: Iterable[Chain] , key: str | Any , value: str) -> list[str]:
    """get reasoning steps for particular chain"""
    
    if isinstance(value , str ) and is_valid_uuid(value): 
        value_no_dashes = value.replace("-" , "")
        
        for chain in chains:
            chain_reasoning_value = getattr(chain , key)

            if chain_reasoning_value in (value , value_no_dashes):
                return chain.reasoning_steps
        
        else:
            for chain in chains: 
                if getattr(chain, key) == value: 
                    return chain.reasoning_steps
                
        return None 
    

def confidence_score_calculation(
    chains: Iterable[Chain], 
    key: str | Any, 
    value: str,
    weight_factors: Dict[str, float] = None
) -> Dict[str, Any]:
    """
    Calculate comprehensive confidence score for paper retraction reasoning chains.
    
    Args:
        chains: Iterable of Chain objects
        key: Attribute key to match against
        value: Value to search for
        weight_factors: Optional weights for different confidence factors
    
    Returns:
        Dict containing confidence scores and detailed breakdown
    """
    if weight_factors is None:
        weight_factors = {
            'frequency_weight': 0.3,
            'reasoning_consistency': 0.25,
            'citation_strength': 0.2,
            'temporal_relevance': 0.15,
            'source_credibility': 0.1
        }
    
    target_chain = None
    if isinstance(value, str) and is_valid_uuid(value):
        value_no_dashes = value.replace("-", "")
        for chain in chains:
            chain_value = getattr(chain, key, None)
            if chain_value in (value, value_no_dashes):
                target_chain = chain
                break
    else:
        for chain in chains:
            if getattr(chain, key, None) == value:
                target_chain = chain
                break
    
    if not target_chain:
        return {
            'overall_confidence': 0.0,
            'confidence_breakdown': {},
            'reasoning': "No matching chain found"
        }
    
    confidence_components = {}
    
    confidence_components['frequency_score'] = calculate_frequency_confidence(
        target_chain, chains
    )
    
    overall_confidence = max(0.0, min(1.0, overall_confidence))
    
    return {
        'overall_confidence': overall_confidence,
        'confidence_breakdown': confidence_components,
        'reasoning_steps_count': len(target_chain.reasoning_steps) if hasattr(target_chain, 'reasoning_steps') else 0,
        'chain_frequency': target_chain.frequency if hasattr(target_chain, 'frequency') else 0,
        'confidence_level': get_confidence_level(overall_confidence)
    }

def calculate_frequency_confidence(target_chain: Chain, all_chains: Iterable[Chain]) -> float:
    """
    Calculate confidence based on how frequently this chain/reasoning appears
    across the dataset relative to other chains.
    """
    if not hasattr(target_chain, 'frequency'):
        return 0.5 
    
    frequencies = [
        chain.frequency for chain in all_chains 
        if hasattr(chain, 'frequency') and chain.frequency is not None
    ]
    
    if not frequencies:
        return 0.5
    
    target_freq = target_chain.frequency
    max_freq = max(frequencies)
    mean_freq = np.mean(frequencies)
    
    if max_freq == 0:
        return 0.5
    
    freq_percentile = np.percentile(frequencies, 
                                   100 * sum(1 for f in frequencies if f <= target_freq) / len(frequencies))
    
    return min(1.0, freq_percentile / 100.0)

            
def get_confidence_level(confidence_score: float) -> str:
    """Convert numerical confidence to descriptive level."""
    if confidence_score >= 0.8:
        return "Very High"
    elif confidence_score >= 0.6:
        return "High" 
    elif confidence_score >= 0.4:
        return "Moderate"
    elif confidence_score >= 0.2:
        return "Low"
    else:
        return "Very Low"


def is_valid_uuid(value: str) -> bool:
    """Determine if a string is a valid UUID."""
    try:
        uuid.UUID(str(value))
    except ValueError:
        return False
    else:
        return True
        
            

    
    