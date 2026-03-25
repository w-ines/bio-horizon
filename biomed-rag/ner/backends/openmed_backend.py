"""OpenMed NER Backend - Standard biomedical entity extraction.

Supports:
- F2a: Standard NER (DISEASE, DRUG, GENE, PROTEIN, ANATOMY, CHEMICAL, ONCOLOGY)
- F2c: Assertion Status via OpenMed Assertion models
- Batch processing for efficiency

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


@dataclass(frozen=True)
class OpenMedNerConfig:
    """Configuration for OpenMed NER extraction."""
    confidence_threshold: float = 0.7
    group_entities: bool = True
    use_medical_tokenizer: bool = True
    enable_assertion: bool = False  # F2c: Assertion Status
    assertion_model: str = "assertion_detection_superclinical"  # OpenMed assertion model


def load_openmed_config_from_env() -> OpenMedNerConfig:
    return OpenMedNerConfig(
        confidence_threshold=_env_float("OPENMED_CONFIDENCE_THRESHOLD", 0.7),
        group_entities=_env_bool("OPENMED_GROUP_ENTITIES", True),
        use_medical_tokenizer=_env_bool("OPENMED_USE_MEDICAL_TOKENIZER", True),
        enable_assertion=_env_bool("OPENMED_ENABLE_ASSERTION", False),
        assertion_model=_env("OPENMED_ASSERTION_MODEL", "assertion_detection_superclinical"),
    )


# OpenMed model registry - F2a Standard NER
# Full catalog: https://openmed.life/docs/model-registry
DEFAULT_OPENMED_MODELS: Dict[str, str] = {
    "DISEASE": "disease_detection_superclinical",
    "DRUG": "pharma_detection_superclinical",
    "GENE": "gene_detection_genecorpus",
    "PROTEIN": "protein_detection_bc5cdr",  # Added for spec compliance
    "ANATOMY": "anatomy_detection_electramed",
    "CHEMICAL": "chemical_detection_bc5cdr",  # Added for spec compliance
    "ONCOLOGY": "disease_detection_superclinical",  # Reuse disease model for oncology
}


def models_from_env() -> Dict[str, str]:
    models = dict(DEFAULT_OPENMED_MODELS)
    for k in list(models.keys()):
        override = _env(f"OPENMED_MODEL_{k}", "").strip()
        if override:
            models[k] = override
    return models


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _to_entity(obj: Any, label: Optional[str] = None, assertion_status: Optional[str] = None) -> NerEntity:
    """Convert OpenMed result object to NerEntity.
    
    Args:
        obj: OpenMed entity result (dict or object)
        label: Entity type label
        assertion_status: F2c assertion status (PRESENT/NEGATED/HYPOTHETICAL/HISTORICAL)
    """
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


def _build_openmed_config(cfg: OpenMedNerConfig):
    from openmed import OpenMedConfig

    return OpenMedConfig(
        use_medical_tokenizer=cfg.use_medical_tokenizer,
        confidence_threshold=cfg.confidence_threshold,
        group_entities=cfg.group_entities,
    )


def _detect_assertion_status(text: str, entity_text: str, config: OpenMedNerConfig) -> Optional[str]:
    """Detect assertion status using OpenMed Assertion model.
    
    Returns: PRESENT, NEGATED, HYPOTHETICAL, or HISTORICAL
    """
    if not config.enable_assertion:
        return None
    
    try:
        from openmed import analyze_text
        
        # Use OpenMed assertion detection model
        result = analyze_text(
            text,
            model_name=config.assertion_model,
            confidence_threshold=config.confidence_threshold,
        )
        
        if not result or not hasattr(result, 'entities'):
            return "PRESENT"  # Default
        
        # Find assertion for this entity
        for entity in result.entities:
            entity_label = getattr(entity, 'label', '').upper()
            if entity_label in ['NEGATED', 'ABSENT']:
                return "NEGATED"
            elif entity_label in ['HYPOTHETICAL', 'POSSIBLE']:
                return "HYPOTHETICAL"
            elif entity_label in ['HISTORICAL', 'PAST']:
                return "HISTORICAL"
        
        return "PRESENT"
    except Exception:
        return "PRESENT"  # Fallback


def extract(
    text: str,
    *,
    entity_types: Optional[Iterable[str]] = None,
    enable_assertion: bool = False,
    is_custom: bool = False,
    config: Optional[OpenMedNerConfig] = None,
) -> NerResult:
    """Extract biomedical entities using OpenMed.
    
    Args:
        text: Input text
        entity_types: Entity types to extract (DISEASE, DRUG, GENE, etc.)
        enable_assertion: Whether to compute assertion status (F2c)
        is_custom: Whether these are custom entity types (not used for OpenMed standard)
        config: OpenMed configuration
    
    Returns:
        NerResult with extracted entities
    """
    config = config or load_openmed_config_from_env()
    if enable_assertion:
        config = OpenMedNerConfig(
            confidence_threshold=config.confidence_threshold,
            group_entities=config.group_entities,
            use_medical_tokenizer=config.use_medical_tokenizer,
            enable_assertion=True,
            assertion_model=config.assertion_model,
        )
    
    models = models_from_env()
    requested = [t.strip().upper() for t in (entity_types or models.keys()) if str(t).strip()]
    requested = [t for t in requested if t in models]
    if not requested:
        requested = list(models.keys())

    text = _safe_text(text).strip()
    if not text:
        return NerResult(
            entities={t: [] for t in requested}, 
            provider="openmed", 
            error=None,
            assertion_enabled=enable_assertion,
        )

    try:
        from openmed import analyze_text

        om_cfg = _build_openmed_config(config)

        entities: Dict[str, List[NerEntity]] = {t: [] for t in requested}
        for entity_type in requested:
            model_name = models[entity_type]
            result = analyze_text(text, model_name=model_name, config=om_cfg)
            
            if result is None or not hasattr(result, 'entities'):
                continue
            
            entity_list = []
            for e in result.entities:
                entity_text = _safe_text(getattr(e, 'text', '') or getattr(e, 'word', '')).strip()
                if not entity_text:
                    continue
                
                # F2c: Detect assertion status if enabled
                assertion = None
                if enable_assertion:
                    assertion = _detect_assertion_status(text, entity_text, config)
                
                entity_list.append(_to_entity(e, label=entity_type, assertion_status=assertion))
            
            entities[entity_type] = entity_list

        return NerResult(
            entities=entities, 
            provider="openmed", 
            error=None,
            assertion_enabled=enable_assertion,
        )
    except ImportError:
        return NerResult(
            entities={t: [] for t in requested},
            provider="openmed",
            error="ImportError: openmed is not installed. Install with: pip install 'openmed[hf]'",
            assertion_enabled=enable_assertion,
        )
    except Exception as e:
        return NerResult(
            entities={t: [] for t in requested},
            provider="openmed",
            error=f"{type(e).__name__}: {e}",
            assertion_enabled=enable_assertion,
        )


def extract_batch(
    texts: List[str],
    *,
    entity_types: Optional[Iterable[str]] = None,
    config: Optional[OpenMedNerConfig] = None,
) -> List[NerResult]:
    config = config or load_openmed_config_from_env()
    models = models_from_env()

    requested = [t.strip().upper() for t in (entity_types or models.keys()) if str(t).strip()]
    requested = [t for t in requested if t in models]
    if not requested:
        requested = list(models.keys())

    try:
        from openmed import batch_process

        om_cfg = _build_openmed_config(config)

        per_type_results: Dict[str, List[Any]] = {}
        for t in requested:
            model_name = models[t]
            per_type_results[t] = batch_process(texts, model_name=model_name, config=om_cfg)

        out: List[NerResult] = []
        for idx in range(len(texts)):
            entities_by_type: Dict[str, List[NerEntity]] = {}
            for t in requested:
                batch_res = per_type_results.get(t) or []
                entities = batch_res[idx] if idx < len(batch_res) else []
                entities_by_type[t] = [_to_entity(e) for e in (entities or [])]
            out.append(NerResult(entities=entities_by_type, provider="openmed", error=None))
        return out
    except Exception as e:
        return [extract(t, entity_types=requested, config=config) for t in texts]
