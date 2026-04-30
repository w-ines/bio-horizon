"""LLM-based semantic relation extractor for the Knowledge Graph.

Uses OpenRouter (OpenAI-compatible API) to classify semantic relations
between entity pairs found in biomedical article abstracts.

Strategy:
  - One LLM call per article (not per entity pair) to keep cost low.
  - Abstract text + entity list → JSON triplets.
  - Returns a structured dict with status/reason for full debuggability.

Supported relation types:
  treats, inhibits, activates, causes, associated_with,
  expressed_in, binds, predisposes, cotreatment, converts
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

RELATION_TYPES = {
    "treats",
    "inhibits",
    "activates",
    "causes",
    "associated_with",
    "expressed_in",
    "binds",
    "predisposes",
    "cotreatment",
    "converts",
}

# Timeout for the LLM HTTP call (seconds).
# 30 s is safer than 15 s for real biomedical abstracts on shared endpoints.
_LLM_TIMEOUT = int(os.getenv("RELATION_LLM_TIMEOUT", "30"))

_SYSTEM_PROMPT = """You are a biomedical relation extraction expert.
Given a PubMed abstract and a list of named entities, extract semantic relations between entity pairs.

Output ONLY a JSON array of triplets, each with the format:
{"subject": "<entity text>", "relation": "<relation_type>", "object": "<entity text>"}

Allowed relation types: treats, inhibits, activates, causes, associated_with, expressed_in, binds, predisposes, cotreatment, converts

Rules:
- Only output relations explicitly supported by the abstract text.
- Use the entity text exactly as it appears in the entities list.
- Do not invent relations not grounded in the text.
- Output [] if no clear relations exist.
- Maximum 20 triplets per article."""


# ─────────────────────────────────────────────────────────────
# Structured result
# ─────────────────────────────────────────────────────────────

class RelationExtractionResult:
    """Structured result from extract_relations_llm for debuggability."""

    __slots__ = ("triplets", "backend", "status", "reason", "rejected_labels", "raw_content")

    def __init__(
        self,
        triplets: List[Tuple[str, str, str]],
        *,
        backend: str = "llm",
        status: str = "ok",
        reason: str = "",
        rejected_labels: Optional[List[str]] = None,
        raw_content: str = "",
    ):
        self.triplets = triplets
        self.backend = backend
        self.status = status          # "ok" | "skipped" | "error"
        self.reason = reason           # human-readable cause
        self.rejected_labels = rejected_labels or []
        self.raw_content = raw_content

    def __repr__(self) -> str:
        return (
            f"RelationExtractionResult(status={self.status!r}, reason={self.reason!r}, "
            f"triplets={len(self.triplets)}, rejected_labels={self.rejected_labels})"
        )


def _skip(reason: str) -> RelationExtractionResult:
    """Return a 'skipped' result — no LLM call was made."""
    return RelationExtractionResult([], status="skipped", reason=reason)


def _error(reason: str, raw: str = "") -> RelationExtractionResult:
    """Return an 'error' result — LLM call failed."""
    return RelationExtractionResult([], status="error", reason=reason, raw_content=raw)


# ─────────────────────────────────────────────────────────────
# Main extraction function
# ─────────────────────────────────────────────────────────────

def extract_relations_llm(
    abstract: str,
    entities: Dict[str, List[Any]],
    *,
    model: Optional[str] = None,
    max_entities: int = 30,
) -> RelationExtractionResult:
    """Call OpenRouter LLM to extract semantic relation triplets from an article.

    Args:
        abstract: Article abstract text.
        entities: Dict of {entity_type: [{"text": ..., ...}, ...]}.
        model: OpenRouter model ID (defaults to OPEN_AI_MODEL env var).
        max_entities: Cap on entities included in the prompt to avoid token overflow.

    Returns:
        RelationExtractionResult with .triplets list and debug metadata.
    """
    api_key = os.getenv("OPEN_ROUTER_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
    model = model or os.getenv("OPEN_AI_MODEL", "openai/gpt-4o-mini")

    if not api_key:
        logger.warning("[relation_extractor] No API key (OPEN_ROUTER_KEY / OPENAI_API_KEY) — skipping")
        return _skip("no_api_key")

    if not abstract or not abstract.strip():
        return _skip("abstract_empty")

    # Flatten entity list with type labels, capped to avoid token overflow
    flat: List[str] = []
    for entity_type, items in entities.items():
        for ent in (items or []):
            text = ent.get("text", "") if isinstance(ent, dict) else str(ent)
            if text and text.strip():
                flat.append(f"{text.strip()} ({entity_type})")
    flat = flat[:max_entities]

    if len(flat) < 2:
        return _skip(f"too_few_entities ({len(flat)})")

    user_prompt = (
        f"Abstract:\n{abstract[:1500]}\n\n"
        f"Entities:\n" + "\n".join(f"- {e}" for e in flat) +
        "\n\nExtract semantic relation triplets as a JSON array:"
    )

    # ── HTTP call ──────────────────────────────────────────
    try:
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.0,
                "max_tokens": 800,
            },
            timeout=_LLM_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        logger.warning("[relation_extractor] LLM timeout (%ds)", _LLM_TIMEOUT)
        return _error(f"http_timeout_{_LLM_TIMEOUT}s")
    except requests.exceptions.HTTPError as exc:
        logger.warning("[relation_extractor] HTTP %s: %s", exc.response.status_code if exc.response else "?", exc)
        return _error(f"http_{exc.response.status_code if exc.response else 'unknown'}")
    except requests.exceptions.RequestException as exc:
        logger.warning("[relation_extractor] Request failed: %s", exc)
        return _error(f"http_request_error: {exc}")

    # ── Parse response ─────────────────────────────────────
    try:
        content = resp.json()["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, ValueError) as exc:
        logger.warning("[relation_extractor] Unexpected response structure: %s", exc)
        return _error("response_structure", raw=resp.text[:500])

    # Strip markdown code fences if the model wraps the JSON
    raw_content = content
    if "```" in content:
        parts = content.split("```")
        content = parts[1] if len(parts) > 1 else parts[0]
        if content.startswith("json"):
            content = content[4:]

    try:
        raw = json.loads(content.strip())
    except json.JSONDecodeError as exc:
        logger.warning("[relation_extractor] JSON decode error: %s — raw: %s", exc, raw_content[:300])
        return _error("json_decode", raw=raw_content[:500])

    if not isinstance(raw, list):
        logger.warning("[relation_extractor] LLM returned non-list: %s", type(raw).__name__)
        return _error("not_a_list", raw=raw_content[:500])

    # ── Filter and collect triplets ────────────────────────
    results: List[Tuple[str, str, str]] = []
    rejected: List[str] = []
    for t in raw:
        if not isinstance(t, dict):
            continue
        subj = (t.get("subject") or "").strip()
        rel = (t.get("relation") or "").strip().lower().replace(" ", "_")
        obj = (t.get("object") or "").strip()
        if not (subj and rel and obj):
            continue
        if rel in RELATION_TYPES:
            results.append((subj, rel, obj))
        else:
            rejected.append(rel)

    if rejected:
        logger.info(
            "[relation_extractor] %d triplet(s) rejected — unknown labels: %s",
            len(rejected), list(set(rejected)),
        )

    logger.debug(
        "[relation_extractor] %d triplets extracted, %d rejected (model=%s)",
        len(results), len(rejected), model,
    )
    return RelationExtractionResult(
        results,
        status="ok",
        reason=f"{len(results)}_triplets",
        rejected_labels=list(set(rejected)),
        raw_content=raw_content[:500],
    )
