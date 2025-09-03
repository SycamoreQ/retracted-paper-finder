from dataclasses import dataclass
from typing import Any
from entity import Paper

@dataclass
class Chain:
    type: str
    chain_id: str
    entity_ids: list[str]
    entities: list[Paper]
    relationship_id: list[str]
    attributes: dict[str, Any]
    reasoning_steps: dict[Any, str]
    confidence_score: float
    frequency: float
    severity_level: int
    overall_explanation: dict[Any, str]

    @classmethod
    def from_dict(
        cls,
        d: dict[str, Any],
        type_key: str = "type",
        chain_id_key: str = "chain_id",
        entity_ids_key: str = "entity_ids",
        entities_key: str = "entities",
        relationship_id_key: str = "relationship_id",
        attributes_key: str = "attributes",
        reasoning_steps_key: str = "reasoning_steps",
        confidence_score_key: str = "confidence_score",
        frequency_key: str = "frequency",
        severity_level_key: str = "severity_level",
        overall_explanation_key: str = "overall_explanation",
    ) -> "Chain":
        """Create a new Chain from dict data."""
        
        # Handle entities field - assuming it might be a dict that needs conversion
        entities_data = d[entities_key]
        if isinstance(entities_data, dict):
            entities_value = entity.Entity.from_dict(entities_data)
        elif isinstance(entities_data, entity.Entity):
            entities_value = entities_data
        else:
            raise ValueError(f"Invalid entities data type: {type(entities_data)}")
        
        return cls(
            type=d[type_key],
            chain_id=d[chain_id_key],
            entity_ids=d[entity_ids_key],
            entities=entities_value,
            relationship_id=d[relationship_id_key],
            attributes=d.get(attributes_key, {}),
            reasoning_steps=d.get(reasoning_steps_key, {}),
            confidence_score=float(d[confidence_score_key]),
            frequency=float(d[frequency_key]),
            severity_level=int(d[severity_level_key]),
            overall_explanation=d.get(overall_explanation_key, {}),
        )
        

        