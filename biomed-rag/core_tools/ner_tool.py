from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional
from ner import router

def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _entity_to_dict(entity: Any) -> Dict[str, Any]:
    if isinstance(entity, dict):
        text = entity.get("text") or entity.get("entity") or entity.get("label") or ""
        out: Dict[str, Any] = {
            "text": _safe_text(text).strip(),
            "confidence": entity.get("confidence") or entity.get("score"),
        }
        if "start" in entity:
            out["start"] = entity["start"]
        if "end" in entity:
            out["end"] = entity["end"]
        return out

    text = getattr(entity, "text", None) or getattr(entity, "entity", None) or getattr(entity, "label", None)
    score = getattr(entity, "confidence", None)
    if score is None:
        score = getattr(entity, "score", None)

    out = {
        "text": _safe_text(text).strip(),
        "confidence": score,
    }
    start = getattr(entity, "start", None)
    end = getattr(entity, "end", None)
    if start is not None:
        out["start"] = start
    if end is not None:
        out["end"] = end
    return out


def _normalize_extraction_result(result: Any) -> Dict[str, Any]:
    """Normalize router extraction result to a stable dict shape.

    Returns:
      {
        "entities": {"DISEASE": [...], ...},
        "provider": str | None,
        "error": str | None
      }
    """
    payload = result.to_dict() if hasattr(result, "to_dict") else (result or {})

    entities = payload.get("entities") or {}
    if isinstance(entities, dict):
        entities = {
            entity_type: [_entity_to_dict(entity) for entity in (items or [])]
            for entity_type, items in entities.items()
        }
    else:
        entities = {}

    provider = payload.get("provider")
    if provider is None:
        provider = getattr(result, "provider", None)

    error = payload.get("error")
    if error is None:
        error = getattr(result, "error", None)

    return {
        "entities": entities,
        "provider": provider,
        "error": error,
    }


def extract_medical_entities_from_text(
    text: str,
    *,
    entity_types: Optional[Iterable[str]] = None,
    provider: Optional[str] = None,
) -> Dict[str, Any]:
    """Extract medical entities from a free text.

    Returns a dict:
      {"entities": {"DISEASE": [...], ...}, "provider": str, "error": str|None}
    """
    text = _safe_text(text).strip()
    if not text:
    return {
        "entities": {},
        "provider": provider,
        "error": "Text cannot be empty",
    }
    
    out = router.extract_from_text(text, entity_types=entity_types, provider=provider)
    return _normalize_extraction_result(out)


def extract_medical_entities_from_article(
    article: Mapping[str, Any],
    *,
    entity_types: Optional[Iterable[str]] = None,
    provider: Optional[str] = None,
) -> Dict[str, Any]:
    """Extract entities from an article dict (expects title/abstract/pmid keys)."""

    out = router.extract_from_article(article, entity_types=entity_types, provider=provider)
    return _normalize_extraction_result(out)

def extract_medical_entities_batch(
    articles: List[Mapping[str, Any]],
    *,
    entity_types: Optional[Iterable[str]] = None,
    provider: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Batch extraction.

    Tries OpenMed batch API first; if not available, falls back to per-article extraction.
    """

    results = router.extract_batch(articles, entity_types=entity_types, provider=provider)  


    normalized_results: List[Dict[str, Any]] = []
    for idx, result in enumerate(results or []):
        normalized = _normalize_extraction_result(result)

        article = articles[idx] if idx < len(articles) else {}
        normalized["article"] = {
            "pmid": article.get("pmid"),
            "title": article.get("title"),
        }

        normalized_results.append(normalized)

    return normalized_results