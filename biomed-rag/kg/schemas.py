from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass
class KgNode:
    """A node in the knowledge graph (one unique entity)."""

    id: str
    label: str
    entity_type: str
    frequency: int = 1
    sources: List[str] = field(default_factory=list)
    confidence_max: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "entity_type": self.entity_type,
            "frequency": self.frequency,
            "sources": self.sources,
            "confidence_max": self.confidence_max,
            "metadata": self.metadata,
        }


@dataclass
class KgEdge:
    """An edge between two co-occurring entities."""

    source_id: str
    target_id: str
    weight: int = 1
    relation_type: str = "co_occurrence"
    sources: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "weight": self.weight,
            "relation_type": self.relation_type,
            "sources": self.sources,
            "metadata": self.metadata,
        }


@dataclass
class KgSnapshot:
    """Serialisable snapshot of a knowledge graph."""

    nodes: List[KgNode] = field(default_factory=list)
    edges: List[KgEdge] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
        }
