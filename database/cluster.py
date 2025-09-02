from dataclasses import dataclass
from typing import Any 
import datetime 
import community
import entity 

@dataclass
class Cluster: 
    cluster_id: str 
    
    cluster_size: int 

    cluster_cot: community.Chain

    cluster_entity: entity.Paper

    avg_confidence_score : float 

    avg_severity_level : float

    attributes: dict[str , Any]

    def from_dict(
        cls,
        d: dict[str, Any],
        cluster_id_key: str = "cluster_id",
        cluster_size_key: str = "cluster_size",
        cluster_cot_key: str = "cluster_cot",
        cluster_entity_key: str = "cluster_entity",
        avg_confidence_score_key: str = "avg_confidence_score",
        avg_severity_level_key: str = "avg_severity_level",
        attributes_key: str = "attributes",
    ) -> "Cluster":
        """Create a new Cluster from dict data."""

        return Cluster(
            cluster_id=d[cluster_id_key],
            cluster_size=int(d[cluster_size_key]),
            cluster_cot=d[cluster_cot_key],
            cluster_entity=d[cluster_entity_key],
            avg_confidence_score=float(d[avg_confidence_score_key]),
            avg_severity_level=float(d[avg_severity_level_key]),
        )
         

    