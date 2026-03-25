"""
Emerging Signal Detector.

Compares two temporal snapshots of the Knowledge Graph to identify
entity-pair relationships that are *new*, *growing*, or *declining*.

Algorithm (from PROJECT_SPECIFICATION.md §F4):
  1. Load KG(week N) and KG(week N−k)
  2. For each relation in KG(N):
       - If absent in KG(N−k)  → new relation
       - If weight(N) > weight(N−k) × threshold → growing relation
  3. For each relation in KG(N−k):
       - If absent in KG(N) or weight declining → declining relation
  4. Compute emergence score for each delta
  5. Classify: emerging signal / accelerating trend / declining
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import networkx as nx

from kg.snapshots import (
    compare_snapshots,
    get_week_label,
    get_week_label_offset,
    load_snapshot,
    list_available_snapshots,
)
from signals.scoring import compute_emergence_score, classify_signal

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _entity_matches(node_id: str, G: nx.Graph, target: str) -> bool:
    """Check if a node_id or its label matches *target* (case-insensitive)."""
    if target.lower() in node_id.lower():
        return True
    label = G.nodes[node_id].get("label", "") if G.has_node(node_id) else ""
    return target.lower() in label.lower()


def _count_sources(G: nx.Graph, u: str, v: str) -> int:
    """Count distinct sources (PMIDs) for an edge."""
    if not G.has_edge(u, v):
        return 0
    sources = G.edges[u, v].get("sources", [])
    return len(sources) if isinstance(sources, list) else 1


def _node_info(G: nx.Graph, node_id: str) -> Dict[str, Any]:
    """Extract serialisable info for a node."""
    if not G.has_node(node_id):
        return {"id": node_id}
    data = dict(G.nodes[node_id])
    data["id"] = node_id
    return data


def _build_signal_entry(
    entity_a_id: str,
    entity_b_id: str,
    G_new: nx.Graph,
    G_old: Optional[nx.Graph],
    signal_type: str,
) -> Dict[str, Any]:
    """Build a single signal dict for an edge."""
    new_weight = G_new.edges[entity_a_id, entity_b_id].get("weight", 1) if G_new.has_edge(entity_a_id, entity_b_id) else 0
    old_weight = 0
    if G_old and G_old.has_edge(entity_a_id, entity_b_id):
        old_weight = G_old.edges[entity_a_id, entity_b_id].get("weight", 1)

    num_sources = _count_sources(G_new, entity_a_id, entity_b_id)

    score = compute_emergence_score(
        entity_a=entity_a_id,
        entity_b=entity_b_id,
        current_freq=new_weight,
        previous_freq=old_weight,
        num_sources=num_sources,
    )

    sources = []
    if G_new.has_edge(entity_a_id, entity_b_id):
        sources = G_new.edges[entity_a_id, entity_b_id].get("sources", [])

    return {
        "signal_type": signal_type,
        "classification": classify_signal(score),
        "entity_a": _node_info(G_new, entity_a_id) if G_new.has_node(entity_a_id) else {"id": entity_a_id},
        "entity_b": _node_info(G_new, entity_b_id) if G_new.has_node(entity_b_id) else {"id": entity_b_id},
        "current_weight": new_weight,
        "previous_weight": old_weight,
        "emergence_score": score,
        "num_sources": num_sources,
        "pmids": sources[:20],
        "velocity_pct": round(((new_weight - old_weight) / max(old_weight, 1)) * 100, 1),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_emerging_signals(
    *,
    entity_a: str,
    entity_b: str,
    time_window_weeks: int = 12,
) -> List[Dict[str, Any]]:
    """
    Detect emerging signals for a given entity pair by comparing KG snapshots.

    If both entity_a and entity_b are provided, looks specifically for edges
    connecting nodes that match those labels.  If no snapshots are available,
    returns an empty list with a diagnostic message.

    Args:
        entity_a:           First entity to look for (e.g. "Semaglutide")
        entity_b:           Second entity (e.g. "Alzheimer disease")
        time_window_weeks:  How many weeks back to compare (default: 12)

    Returns:
        List of signal dicts, each containing:
          signal_type, classification, entity_a, entity_b,
          current_weight, previous_weight, emergence_score, pmids, …
    """
    current_label = get_week_label()
    previous_label = get_week_label_offset(time_window_weeks)

    logger.info(
        f"[detector] Comparing {current_label} vs {previous_label} "
        f"for ({entity_a}, {entity_b})"
    )

    # --- Load snapshots ---
    G_new = load_snapshot(current_label)
    G_old = load_snapshot(previous_label)

    # If current snapshot missing, try the most recent one available
    if G_new is None:
        available = list_available_snapshots()
        if available:
            current_label = available[-1]
            G_new = load_snapshot(current_label)
            logger.info(f"[detector] Current snapshot missing, using latest: {current_label}")

    if G_new is None:
        logger.warning("[detector] No KG snapshots available")
        return [{
            "signal_type": "no_data",
            "classification": "NO_DATA",
            "message": f"No KG snapshot found for {current_label}. Run the KG pipeline first.",
            "entity_a": entity_a,
            "entity_b": entity_b,
            "emergence_score": 0,
        }]

    # G_old may be None (first snapshot ever) — that's fine, everything is "new"
    if G_old is None:
        G_old = nx.Graph()
        logger.info(f"[detector] No previous snapshot ({previous_label}), treating all as new")

    # --- Find matching nodes ---
    signals: List[Dict[str, Any]] = []

    nodes_a = [n for n in G_new.nodes() if _entity_matches(n, G_new, entity_a)]
    nodes_b = [n for n in G_new.nodes() if _entity_matches(n, G_new, entity_b)]

    if not nodes_a and not nodes_b:
        # Neither entity found → scan all edges for broad detection
        return _detect_all_signals(G_new, G_old, limit=20)

    # --- Check edges between matching node pairs ---
    for na in nodes_a:
        for nb in nodes_b:
            if na == nb:
                continue

            if G_new.has_edge(na, nb):
                is_new = not G_old.has_edge(na, nb)
                signal_type = "new_relation" if is_new else "existing_relation"

                if not is_new:
                    old_w = G_old.edges[na, nb].get("weight", 1)
                    new_w = G_new.edges[na, nb].get("weight", 1)
                    if new_w > old_w:
                        signal_type = "growing_relation"
                    elif new_w < old_w:
                        signal_type = "declining_relation"

                signals.append(_build_signal_entry(na, nb, G_new, G_old, signal_type))

    # If no direct edge found, report it
    if not signals:
        signals.append({
            "signal_type": "no_direct_edge",
            "classification": "NO_DATA",
            "message": (
                f"No direct co-occurrence edge found between "
                f"'{entity_a}' (matched {len(nodes_a)} nodes) and "
                f"'{entity_b}' (matched {len(nodes_b)} nodes) in {current_label}."
            ),
            "entity_a": entity_a,
            "entity_b": entity_b,
            "emergence_score": 0,
        })

    # Sort by emergence score descending
    signals.sort(key=lambda s: s.get("emergence_score", 0), reverse=True)
    return signals


def _detect_all_signals(
    G_new: nx.Graph,
    G_old: nx.Graph,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Broad signal detection across all edges when no specific entity pair
    is matched.  Returns the top-N most emerging signals.
    """
    delta = compare_snapshots(G_new, G_old)
    signals: List[Dict[str, Any]] = []

    # New edges → highest novelty
    for u, v in delta.get("new_edges", [])[:limit]:
        signals.append(_build_signal_entry(u, v, G_new, G_old, "new_relation"))

    # Weight increased → growing
    for u, v, old_w, new_w in delta.get("weight_increased", [])[:limit]:
        signals.append(_build_signal_entry(u, v, G_new, G_old, "growing_relation"))

    # Weight decreased → declining
    for u, v, old_w, new_w in delta.get("weight_decreased", [])[:limit]:
        if G_new.has_edge(u, v):
            signals.append(_build_signal_entry(u, v, G_new, G_old, "declining_relation"))

    signals.sort(key=lambda s: s.get("emergence_score", 0), reverse=True)
    return signals[:limit]