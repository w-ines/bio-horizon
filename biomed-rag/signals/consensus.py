"""
Scientific Consensus Computation.

For a given entity-pair relationship and a list of source PMIDs,
aggregates the assertion statuses of each article to produce a
consensus breakdown:

  Consensus(A ↔ B) = {
      positive:      Nb articles [PRESENT]      / Total,
      negative:      Nb articles [NEGATED]       / Total,
      hypothetical:  Nb articles [HYPOTHETICAL]  / Total,
      historical:    Nb articles [HISTORICAL]    / Total,
  }

Classification labels (from PROJECT_SPECIFICATION.md §F9):
  - confirmed      → positive > 80%
  - contradictory  → positive 40-60%
  - preliminary    → hypothetical > 50%

Data source priority:
  1. Supabase ``entity_assertions`` table (if available)
  2. Fallback: heuristic keyword scan on article abstracts
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Assertion status constants
# ---------------------------------------------------------------------------
PRESENT      = "PRESENT"
NEGATED      = "NEGATED"
HYPOTHETICAL = "HYPOTHETICAL"
HISTORICAL   = "HISTORICAL"

ALL_STATUSES = [PRESENT, NEGATED, HYPOTHETICAL, HISTORICAL]


# ---------------------------------------------------------------------------
# Supabase-backed assertion lookup
# ---------------------------------------------------------------------------

def _load_assertions_from_supabase(
    entity_a: str,
    entity_b: str,
    pmids: List[str],
) -> Optional[List[Dict[str, Any]]]:
    """
    Try to load assertion rows from Supabase.

    Returns a list of dicts with keys: pmid, assertion_status, confidence.
    Returns None if Supabase is not configured or the table doesn't exist.
    """
    try:
        from storage.supabase_client import get_supabase_client, SupabaseNotConfigured

        client = get_supabase_client()

        # Query entity_assertions joined with entities for the given PMIDs
        result = client.table("entity_assertions").select(
            "pmid, assertion_status, confidence"
        ).in_("pmid", pmids).execute()

        if result.data:
            return result.data
        return []

    except Exception:
        # Table may not exist yet, or Supabase not configured
        return None


# ---------------------------------------------------------------------------
# Heuristic fallback (regex-based negation / hypothesis detection)
# ---------------------------------------------------------------------------

# Simple patterns — intentionally conservative
_NEGATION_PATTERNS = [
    re.compile(r"\bno\s+significant\b", re.IGNORECASE),
    re.compile(r"\bdid\s+not\s+(show|demonstrate|improve)\b", re.IGNORECASE),
    re.compile(r"\bfailed\s+to\b", re.IGNORECASE),
    re.compile(r"\bineffective\b", re.IGNORECASE),
    re.compile(r"\bno\s+evidence\b", re.IGNORECASE),
    re.compile(r"\bnot\s+associated\b", re.IGNORECASE),
]

_HYPOTHETICAL_PATTERNS = [
    re.compile(r"\bfurther\s+(studies|trials|research)\s+(are|is)\s+needed\b", re.IGNORECASE),
    re.compile(r"\bmay\s+(be|have|play)\b", re.IGNORECASE),
    re.compile(r"\bpotential(ly)?\b", re.IGNORECASE),
    re.compile(r"\bsuggests?\s+that\b", re.IGNORECASE),
    re.compile(r"\bhypothes[ie]", re.IGNORECASE),
    re.compile(r"\bpreliminary\b", re.IGNORECASE),
]

_HISTORICAL_PATTERNS = [
    re.compile(r"\bhistory\s+of\b", re.IGNORECASE),
    re.compile(r"\bpreviously\s+(reported|described|shown)\b", re.IGNORECASE),
]


def _heuristic_assertion(abstract: str) -> str:
    """
    Classify an abstract into an assertion status using keyword heuristics.

    This is a fallback when the OpenMed Assertion model is not yet available.
    """
    if not abstract:
        return PRESENT  # default: assume affirmative

    for pat in _NEGATION_PATTERNS:
        if pat.search(abstract):
            return NEGATED

    for pat in _HYPOTHETICAL_PATTERNS:
        if pat.search(abstract):
            return HYPOTHETICAL

    for pat in _HISTORICAL_PATTERNS:
        if pat.search(abstract):
            return HISTORICAL

    return PRESENT


def _fetch_abstracts_for_pmids(pmids: List[str]) -> Dict[str, str]:
    """
    Fetch abstracts for given PMIDs from Supabase articles table.

    Returns {pmid: abstract} mapping.  Missing articles are silently skipped.
    """
    try:
        from storage.supabase_client import get_supabase_client, SupabaseNotConfigured

        client = get_supabase_client()
        result = client.table("articles").select("pmid, abstract").in_(
            "pmid", pmids
        ).execute()

        if result.data:
            return {row["pmid"]: row.get("abstract", "") for row in result.data}
        return {}

    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_consensus(
    *,
    entity_a: str,
    entity_b: str,
    pmids: List[str],
) -> Dict[str, Any]:
    """
    Compute scientific consensus for an entity-pair relationship.

    Tries Supabase ``entity_assertions`` first.  If not available, falls
    back to heuristic keyword scanning on article abstracts.

    Args:
        entity_a:  First entity label
        entity_b:  Second entity label
        pmids:     List of PubMed IDs to analyse

    Returns:
        Dict with keys:
          - total:          Number of articles analysed
          - positive:       Proportion [0-1] classified PRESENT
          - negative:       Proportion [0-1] classified NEGATED
          - hypothetical:   Proportion [0-1] classified HYPOTHETICAL
          - historical:     Proportion [0-1] classified HISTORICAL
          - label:          "confirmed" | "contradictory" | "preliminary" | "insufficient_data"
          - method:         "supabase" | "heuristic"
          - details:        Per-PMID assertion breakdown
    """
    if not pmids:
        return {
            "total": 0,
            "positive": 0.0,
            "negative": 0.0,
            "hypothetical": 0.0,
            "historical": 0.0,
            "label": "insufficient_data",
            "method": "none",
            "details": [],
        }

    # --- Strategy 1: Supabase entity_assertions ---
    db_assertions = _load_assertions_from_supabase(entity_a, entity_b, pmids)

    if db_assertions is not None and len(db_assertions) > 0:
        return _aggregate(db_assertions, method="supabase")

    # --- Strategy 2: Heuristic fallback ---
    logger.info("[consensus] Supabase assertions unavailable, using heuristic fallback")
    abstracts = _fetch_abstracts_for_pmids(pmids)

    heuristic_assertions = []
    for pmid in pmids:
        abstract = abstracts.get(pmid, "")
        status = _heuristic_assertion(abstract)
        heuristic_assertions.append({
            "pmid": pmid,
            "assertion_status": status,
            "confidence": 0.6,  # lower confidence for heuristic
        })

    return _aggregate(heuristic_assertions, method="heuristic")


def _aggregate(
    assertions: List[Dict[str, Any]],
    method: str = "unknown",
) -> Dict[str, Any]:
    """Aggregate a list of assertion dicts into consensus percentages."""
    total = len(assertions)
    if total == 0:
        return {
            "total": 0,
            "positive": 0.0,
            "negative": 0.0,
            "hypothetical": 0.0,
            "historical": 0.0,
            "label": "insufficient_data",
            "method": method,
            "details": [],
        }

    counts = {s: 0 for s in ALL_STATUSES}
    for a in assertions:
        status = (a.get("assertion_status") or PRESENT).upper()
        if status in counts:
            counts[status] += 1
        else:
            counts[PRESENT] += 1  # unknown status → default PRESENT

    pct = {s: round(counts[s] / total, 4) for s in ALL_STATUSES}

    # Classification
    label = _classify_consensus(pct)

    return {
        "total": total,
        "positive": pct[PRESENT],
        "negative": pct[NEGATED],
        "hypothetical": pct[HYPOTHETICAL],
        "historical": pct[HISTORICAL],
        "label": label,
        "method": method,
        "details": [
            {
                "pmid": a.get("pmid"),
                "assertion_status": a.get("assertion_status"),
                "confidence": a.get("confidence"),
            }
            for a in assertions
        ],
    }


def _classify_consensus(pct: Dict[str, float]) -> str:
    """
    Classify based on percentage thresholds
    (PROJECT_SPECIFICATION.md §F9).
    """
    if pct[PRESENT] > 0.80:
        return "confirmed"
    if pct[HYPOTHETICAL] > 0.50:
        return "preliminary"
    if 0.40 <= pct[PRESENT] <= 0.60:
        return "contradictory"
    if pct[NEGATED] > 0.50:
        return "refuted"
    return "mixed"