from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List, Mapping, Optional

from ner.schemas import NerResult


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _select_provider(provider: Optional[str] = None) -> str:
    raw = (provider or _env("NER_PROVIDER", "openmed")).strip().lower()
    return raw or "openmed"


def extract_from_text(
    text: str,
    *,
    entity_types: Optional[Iterable[str]] = None,
    custom_labels: Optional[Iterable[str]] = None,
    enable_assertion: bool = False,
    provider: Optional[str] = None,
) -> NerResult:
    """
    Extract entities from text.
    
    Args:
        text: Input text
        entity_types: Standard entity types (DISEASE, DRUG, GENE, etc.)
        custom_labels: Custom zero-shot labels (BRAIN_REGION, BIOMARKER, etc.)
        enable_assertion: Whether to compute assertion status (F2c)
        provider: NER backend to use (openmed, gliner, pubtator3)
    
    Returns:
        NerResult with extracted entities
    """
    p = _select_provider(provider)
    
    # F2b: Zero-shot mode if custom labels provided
    if custom_labels:
        custom_labels_list = list(custom_labels)
        
        if p == "openmed":
            # Use OpenMed zero-shot backend
            from ner.backends import openmed_zeroshot
            
            return openmed_zeroshot.extract(
                text,
                custom_labels=custom_labels_list,
                enable_assertion=enable_assertion,
            )
        
        elif p == "gliner":
            # Use GLiNER backend for zero-shot
            from ner.backends import gliner_backend
            
            return gliner_backend.extract(
                text,
                entity_types=None,
                enable_assertion=enable_assertion,
                custom_labels=custom_labels_list,
            )
    
    # F2a: Standard NER mode
    if p == "openmed":
        from ner.backends import openmed_backend

        return openmed_backend.extract(
            text, 
            entity_types=entity_types,
            enable_assertion=enable_assertion,
            is_custom=False,
        )

    if p == "gliner":
        from ner.backends import gliner_backend

        return gliner_backend.extract(
            text, 
            entity_types=entity_types,
            enable_assertion=enable_assertion,
            custom_labels=None,
        )

    return NerResult(
        entities={str(t).strip().upper(): [] for t in (entity_types or []) if str(t).strip()},
        provider=p,
        error=f"ValueError: Unknown NER provider '{p}'",
        custom_labels=list(custom_labels) if custom_labels else None,
        assertion_enabled=enable_assertion,
    )


def extract_from_article(
    article: Mapping[str, Any],
    *,
    entity_types: Optional[Iterable[str]] = None,
    provider: Optional[str] = None,
) -> Dict[str, Any]:
    title = _safe_text(article.get("title"))
    abstract = _safe_text(article.get("abstract"))
    pmid = _safe_text(article.get("pmid"))

    p = _select_provider(provider)

    # PubTator3: use PMID-based lookup (no local ML)
    if p == "pubtator3" and pmid:
        from ner.backends import pubtator3_backend

        by_pmid = pubtator3_backend.extract_by_pmids([pmid], entity_types=entity_types)
        out = by_pmid.get(pmid)
        if out is None:
            out = extract_from_text(
                (title + "\n\n" + abstract).strip(),
                entity_types=entity_types,
                provider="openmed",
            )
        result: Dict[str, Any] = {
            "pmid": pmid,
            "title": title,
            "entities": out.to_dict().get("entities", {}),
            "provider": out.provider,
        }
        if out.error:
            result["error"] = out.error
        return result

    text = (title + "\n\n" + abstract).strip()
    out = extract_from_text(text, entity_types=entity_types, provider=provider)

    result: Dict[str, Any] = {
        "pmid": pmid,
        "title": title,
        "entities": out.to_dict().get("entities", {}),
        "provider": out.provider,
    }
    if out.error:
        result["error"] = out.error
    return result


def extract_batch(
    articles: List[Mapping[str, Any]],
    *,
    entity_types: Optional[Iterable[str]] = None,
    provider: Optional[str] = None,
) -> List[Dict[str, Any]]:
    p = _select_provider(provider)

    # PubTator3 fast path: single HTTP call for all PMIDs
    if p == "pubtator3":
        from ner.backends import pubtator3_backend

        results = pubtator3_backend.extract_batch_from_articles(
            articles, entity_types=entity_types
        )
    else:
        texts: List[str] = []
        for a in articles:
            title = _safe_text(a.get("title"))
            abstract = _safe_text(a.get("abstract"))
            texts.append((title + "\n\n" + abstract).strip())

        if p == "openmed":
            from ner.backends import openmed_backend

            results = openmed_backend.extract_batch(texts, entity_types=entity_types)
        elif p == "gliner":
            from ner.backends import gliner_backend

            results = gliner_backend.extract_batch(texts, entity_types=entity_types)
        else:
            results = [extract_from_text(t, entity_types=entity_types, provider=p) for t in texts]

    out: List[Dict[str, Any]] = []
    for idx, article in enumerate(articles):
        pmid = _safe_text(article.get("pmid"))
        title = _safe_text(article.get("title"))
        r = results[idx] if idx < len(results) else None
        if r is None:
            out.append({"pmid": pmid, "title": title, "entities": {}, "provider": p, "error": "IndexError: missing batch result"})
            continue

        payload = r.to_dict()
        item: Dict[str, Any] = {
            "pmid": pmid,
            "title": title,
            "entities": payload.get("entities", {}),
            "provider": payload.get("provider", p),
        }
        if payload.get("error"):
            item["error"] = payload["error"]
        out.append(item)

    return out
