# Dataclasses NER (NerEntity, NerResult)

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple


@dataclass(frozen=True)
class NerEntity:
    text: str
    confidence: Optional[float] = None
    start: Optional[int] = None
    end: Optional[int] = None
    assertion_status: Optional[str] = None  # PRESENT, NEGATED, HYPOTHETICAL, HISTORICAL
    label: Optional[str] = None  # Entity type label
    concept_id: Optional[str] = None  # Canonical ID, e.g. "MESH:D009369", "NCBIGene:673"
    concept_source: Optional[str] = None  # Vocabulary, e.g. "MeSH", "NCBIGene", "NCBITaxon"

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "text": self.text,
            "confidence": self.confidence,
        }
        if self.start is not None:
            out["start"] = self.start
        if self.end is not None:
            out["end"] = self.end
        if self.assertion_status is not None:
            out["assertion_status"] = self.assertion_status
        if self.label is not None:
            out["label"] = self.label
        if self.concept_id is not None:
            out["concept_id"] = self.concept_id
        if self.concept_source is not None:
            out["concept_source"] = self.concept_source
        return out


@dataclass(frozen=True)
class NerResult:
    entities: Dict[str, List[NerEntity]]
    provider: str
    error: Optional[str] = None
    custom_labels: Optional[List[str]] = None  # Zero-shot custom labels used
    assertion_enabled: bool = False  # Whether assertion status was computed
    relations: List[Tuple[str, str, str]] = field(default_factory=list)  # (subj_text, relation_type, obj_text)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "entities": {k: [e.to_dict() for e in v] for k, v in self.entities.items()},
            "provider": self.provider,
            "error": self.error,
            "assertion_enabled": self.assertion_enabled,
            "relations": list(self.relations),
        }
        if self.custom_labels:
            result["custom_labels"] = self.custom_labels
        return result


TextLike = Any
ArticleLike = Mapping[str, Any]
EntityTypes = Optional[Iterable[str]]
