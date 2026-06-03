"""OpenMed Zero-shot NER Backend - Custom entity extraction.

Supports:
- F2b: Zero-shot NER with custom labels (BRAIN_REGION, BIOMARKER, etc.)
- GLiNER integration via OpenMed
- User-defined entity types without model retraining

Docs: https://openmed.life/docs/
GitHub: https://github.com/maziyarpanahi/openmed
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from ner.schemas import NerEntity, NerResult


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def _env_bool(name: str, default: bool) -> bool:
    raw = _env(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "y", "on"}


def _env_float(name: str, default: float) -> float:
    raw = _env(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except Exception:
        return default


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


@dataclass(frozen=True)
class OpenMedZeroShotConfig:
    """Configuration for OpenMed Zero-shot NER."""
    confidence_threshold: float = 0.5  # Lower threshold for zero-shot
    gliner_model: str = "gliner_medium"  # OpenMed GLiNER model
    enable_assertion: bool = False


def load_zeroshot_config_from_env() -> OpenMedZeroShotConfig:
    return OpenMedZeroShotConfig(
        confidence_threshold=_env_float("OPENMED_ZEROSHOT_THRESHOLD", 0.5),
        gliner_model=_env("OPENMED_GLINER_MODEL", "gliner_medium"),
        enable_assertion=_env_bool("OPENMED_ENABLE_ASSERTION", False),
    )


def _to_entity(obj: Any, label: Optional[str] = None, assertion_status: Optional[str] = None) -> NerEntity:
    """Convert OpenMed GLiNER result to NerEntity."""
    if isinstance(obj, dict):
        text = obj.get("text") or obj.get("entity") or obj.get("word") or ""
        return NerEntity(
            text=_safe_text(text).strip(),
            confidence=obj.get("confidence") or obj.get("score"),
            start=obj.get("start"),
            end=obj.get("end"),
            label=label,
            assertion_status=assertion_status,
        )

    text = getattr(obj, "text", None) or getattr(obj, "entity", None) or getattr(obj, "word", None)
    score = getattr(obj, "confidence", None)
    if score is None:
        score = getattr(obj, "score", None)

    return NerEntity(
        text=_safe_text(text).strip(),
        confidence=score,
        start=getattr(obj, "start", None),
        end=getattr(obj, "end", None),
        label=label,
        assertion_status=assertion_status,
    )


def _detect_assertion_status(text: str, entity_text: str, config: OpenMedZeroShotConfig) -> Optional[str]:
    """Detect assertion status using heuristics (OpenMed Assertion model would be better)."""
    if not config.enable_assertion:
        return None
    
    # Simple heuristic-based detection
    # TODO: Use OpenMed Assertion model when available
    text_lower = text.lower()
    entity_lower = entity_text.lower()
    
    # Find context
    sentences = text.split('.')
    context = ""
    for sent in sentences:
        if entity_lower in sent.lower():
            context = sent.lower()
            break
    
    if not context:
        return "PRESENT"
    
    # Negation patterns
    negation_patterns = ["no ", "not ", "without ", "absence of", "lack of", "negative for", "ruled out"]
    for pattern in negation_patterns:
        if pattern in context:
            return "NEGATED"
    
    # Hypothetical patterns
    hypothetical_patterns = ["may ", "might ", "could ", "would ", "possible", "hypothesis", "suggest"]
    for pattern in hypothetical_patterns:
        if pattern in context:
            return "HYPOTHETICAL"
    
    # Historical patterns
    historical_patterns = ["history of", "previous", "prior", "past", "had been"]
    for pattern in historical_patterns:
        if pattern in context:
            return "HISTORICAL"
    
    return "PRESENT"


def extract(
    text: str,
    *,
    custom_labels: List[str],
    enable_assertion: bool = False,
    config: Optional[OpenMedZeroShotConfig] = None,
) -> NerResult:
    """Extract custom entities using OpenMed Zero-shot (GLiNER).
    
    Args:
        text: Input text
        custom_labels: Custom entity types (e.g., ["BRAIN_REGION", "BIOMARKER"])
        enable_assertion: Whether to compute assertion status
        config: Zero-shot configuration
    
    Returns:
        NerResult with extracted custom entities
    
    Examples:
        >>> result = extract(
        ...     "The hippocampus shows elevated tau levels.",
        ...     custom_labels=["BRAIN_REGION", "BIOMARKER"]
        ... )
        >>> result.entities["BRAIN_REGION"]  # ["hippocampus"]
        >>> result.entities["BIOMARKER"]     # ["tau"]
    """
    config = config or load_zeroshot_config_from_env()
    
    if not custom_labels:
        return NerResult(
            entities={},
            provider="openmed-zeroshot",
            error="No custom labels provided",
            custom_labels=[],
            assertion_enabled=enable_assertion,
        )
    
    # Normalize labels
    labels = [str(l).strip().upper() for l in custom_labels if str(l).strip()]
    
    text = _safe_text(text).strip()
    if not text:
        return NerResult(
            entities={l: [] for l in labels},
            provider="openmed-zeroshot",
            error=None,
            custom_labels=labels,
            assertion_enabled=enable_assertion,
        )
    
    try:
        from openmed import analyze_text
        
        # Use OpenMed GLiNER for zero-shot extraction
        # Note: OpenMed may wrap GLiNER or provide its own zero-shot model
        result = analyze_text(
            text,
            model_name=config.gliner_model,
            labels=labels,  # Pass custom labels to GLiNER
            confidence_threshold=config.confidence_threshold,
        )
        
        if result is None or not hasattr(result, 'entities'):
            return NerResult(
                entities={l: [] for l in labels},
                provider="openmed-zeroshot",
                error=None,
                custom_labels=labels,
                assertion_enabled=enable_assertion,
            )
        
        # Group entities by label
        entities: Dict[str, List[NerEntity]] = {l: [] for l in labels}
        for e in result.entities:
            entity_text = _safe_text(getattr(e, 'text', '') or getattr(e, 'word', '')).strip()
            if not entity_text:
                continue
            
            entity_label = getattr(e, 'label', '').upper()
            if entity_label not in entities:
                continue
            
            # Detect assertion status if enabled
            assertion = None
            if enable_assertion:
                assertion = _detect_assertion_status(text, entity_text, config)
            
            entities[entity_label].append(_to_entity(e, label=entity_label, assertion_status=assertion))
        
        return NerResult(
            entities=entities,
            provider="openmed-zeroshot",
            error=None,
            custom_labels=labels,
            assertion_enabled=enable_assertion,
        )
    
    except ImportError:
        # Fallback to local GLiNER if OpenMed not available
        try:
            from gliner2 import GLiNER2
            
            model = GLiNER2.from_pretrained("fastino/gliner2-base-v1")
            raw_entities = model.extract_entities(text, labels)
            
            entities: Dict[str, List[NerEntity]] = {l: [] for l in labels}
            if raw_entities and isinstance(raw_entities, dict):
                for label, entity_list in raw_entities.get("entities", {}).items():
                    label_upper = label.upper()
                    if label_upper in entities:
                        for entity_text in entity_list:
                            assertion = None
                            if enable_assertion:
                                assertion = _detect_assertion_status(text, entity_text, config)
                            
                            entities[label_upper].append(NerEntity(
                                text=_safe_text(entity_text).strip(),
                                confidence=None,
                                label=label_upper,
                                assertion_status=assertion,
                            ))
            
            return NerResult(
                entities=entities,
                provider="gliner-fallback",
                error=None,
                custom_labels=labels,
                assertion_enabled=enable_assertion,
            )
        
        except ImportError:
            return NerResult(
                entities={l: [] for l in labels},
                provider="openmed-zeroshot",
                error="ImportError: Neither openmed nor gliner2 is installed. Install with: pip install 'openmed[hf]' or pip install gliner2",
                custom_labels=labels,
                assertion_enabled=enable_assertion,
            )
    
    except Exception as e:
        return NerResult(
            entities={l: [] for l in labels},
            provider="openmed-zeroshot",
            error=f"{type(e).__name__}: {e}",
            custom_labels=labels,
            assertion_enabled=enable_assertion,
        )


def extract_batch(
    texts: List[str],
    *,
    custom_labels: List[str],
    enable_assertion: bool = False,
    config: Optional[OpenMedZeroShotConfig] = None,
) -> List[NerResult]:
    """Batch extract custom entities using OpenMed Zero-shot.
    
    Args:
        texts: List of input texts
        custom_labels: Custom entity types
        enable_assertion: Whether to compute assertion status
        config: Zero-shot configuration
    
    Returns:
        List of NerResult objects
    """
    config = config or load_zeroshot_config_from_env()
    
    # For now, process sequentially
    # TODO: Implement true batch processing with OpenMed batch API
    return [extract(t, custom_labels=custom_labels, enable_assertion=enable_assertion, config=config) for t in texts]
