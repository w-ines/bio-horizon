"""
Signals API endpoints — detection and retrieval of emerging signals.

This module provides endpoints for:
- Listing available KG snapshots
- Comparing snapshots to detect changes
- Retrieving detected signals (Phase 2 - to be implemented)
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from kg.snapshots import (
    compare_snapshots,
    get_week_label,
    get_week_label_offset,
    list_available_snapshots,
    load_snapshot,
)

router = APIRouter()


# =============================================================================
# Snapshot Management Endpoints
# =============================================================================

@router.get("/snapshots")
async def list_snapshots():
    """
    List all available KG snapshots.
    
    Returns:
        List of week labels with metadata
        
    Example:
        GET /signals/snapshots
        
        Response:
        {
            "snapshots": ["2026-W08", "2026-W09", "2026-W10", "2026-W11", "2026-W12"],
            "current_week": "2026-W12",
            "total_count": 5
        }
    """
    snapshots = list_available_snapshots()
    current_week = get_week_label()
    
    return {
        "snapshots": snapshots,
        "current_week": current_week,
        "total_count": len(snapshots),
    }


@router.get("/snapshots/{week_label}")
async def get_snapshot_info(week_label: str):
    """
    Get metadata about a specific snapshot.
    
    Args:
        week_label: ISO week label (e.g., '2026-W12')
        
    Returns:
        Snapshot metadata (node count, edge count, etc.)
        
    Example:
        GET /signals/snapshots/2026-W12
    """
    G = load_snapshot(week_label)
    
    if G is None:
        raise HTTPException(
            status_code=404,
            detail=f"Snapshot for week {week_label} not found"
        )
    
    # Extract entity type distribution
    entity_types = {}
    for node_id, data in G.nodes(data=True):
        entity_type = data.get("entity_type", "UNKNOWN")
        entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
    
    return {
        "week_label": week_label,
        "node_count": G.number_of_nodes(),
        "edge_count": G.number_of_edges(),
        "entity_types": entity_types,
    }


@router.get("/compare")
async def compare_two_snapshots(
    week_new: str = Query(..., description="Recent week label (e.g., '2026-W12')"),
    week_old: str = Query(..., description="Older week label (e.g., '2026-W08')"),
):
    """
    Compare two snapshots to detect changes (delta).
    
    This is the foundation for signal detection: by comparing KG(week N) vs KG(week N-4),
    we identify new entities, new relations, and relations that strengthened or weakened.
    
    Query params:
        week_new: Recent snapshot week label
        week_old: Older snapshot week label
        
    Returns:
        Delta object with new/disappeared nodes and edges, weight changes
        
    Example:
        GET /signals/compare?week_new=2026-W12&week_old=2026-W08
        
        Response:
        {
            "week_new": "2026-W12",
            "week_old": "2026-W08",
            "summary": {
                "total_new_nodes": 15,
                "total_new_edges": 42,
                "total_weight_increased": 8,
                ...
            },
            "new_nodes": [...],
            "new_edges": [...],
            "weight_increased": [...]
        }
    """
    # Load both snapshots
    G_new = load_snapshot(week_new)
    G_old = load_snapshot(week_old)
    
    if G_new is None:
        raise HTTPException(
            status_code=404,
            detail=f"Snapshot for week {week_new} not found"
        )
    
    if G_old is None:
        raise HTTPException(
            status_code=404,
            detail=f"Snapshot for week {week_old} not found"
        )
    
    # Compare snapshots
    delta = compare_snapshots(G_new, G_old)
    
    # Enrich delta with entity labels for readability
    def enrich_node(node_id):
        if node_id in G_new.nodes:
            data = G_new.nodes[node_id]
            return {
                "id": node_id,
                "label": data.get("label", ""),
                "entity_type": data.get("entity_type", ""),
                "frequency": data.get("frequency", 1),
            }
        return {"id": node_id}
    
    def enrich_edge(edge_tuple):
        if len(edge_tuple) == 2:
            u, v = edge_tuple
            return {
                "source": enrich_node(u),
                "target": enrich_node(v),
            }
        elif len(edge_tuple) == 4:
            u, v, old_w, new_w = edge_tuple
            return {
                "source": enrich_node(u),
                "target": enrich_node(v),
                "old_weight": old_w,
                "new_weight": new_w,
                "delta": new_w - old_w,
            }
        return edge_tuple
    
    return {
        "week_new": week_new,
        "week_old": week_old,
        "summary": delta["summary"],
        "new_nodes": [enrich_node(n) for n in delta["new_nodes"][:50]],  # Limit to 50 for performance
        "new_edges": [enrich_edge(e) for e in delta["new_edges"][:50]],
        "weight_increased": [enrich_edge(e) for e in delta["weight_increased"][:50]],
        "disappeared_nodes": [enrich_node(n) for n in delta["disappeared_nodes"][:50]],
        "disappeared_edges": [enrich_edge(e) for e in delta["disappeared_edges"][:50]],
        "note": "Results limited to 50 items per category for performance. Use filters for more specific queries.",
    }


@router.get("/compare/current")
async def compare_current_vs_past(
    weeks_ago: int = Query(4, description="Number of weeks to compare against (default: 4)"),
):
    """
    Compare current week snapshot vs N weeks ago.
    
    Convenience endpoint that automatically selects the current week and compares
    it to N weeks ago (default: 4 weeks).
    
    Query params:
        weeks_ago: Number of weeks to go back (default: 4)
        
    Returns:
        Same as /compare endpoint
        
    Example:
        GET /signals/compare/current?weeks_ago=4
    """
    week_new = get_week_label()
    week_old = get_week_label_offset(weeks_ago)
    
    # Redirect to main compare endpoint logic
    G_new = load_snapshot(week_new)
    G_old = load_snapshot(week_old)
    
    if G_new is None:
        raise HTTPException(
            status_code=404,
            detail=f"No snapshot found for current week {week_new}. Run a PubMed → NER → KG pipeline first."
        )
    
    if G_old is None:
        raise HTTPException(
            status_code=404,
            detail=f"No snapshot found for week {week_old} ({weeks_ago} weeks ago). Not enough historical data yet."
        )
    
    delta = compare_snapshots(G_new, G_old)
    
    def enrich_node(node_id):
        if node_id in G_new.nodes:
            data = G_new.nodes[node_id]
            return {
                "id": node_id,
                "label": data.get("label", ""),
                "entity_type": data.get("entity_type", ""),
                "frequency": data.get("frequency", 1),
            }
        return {"id": node_id}
    
    def enrich_edge(edge_tuple):
        if len(edge_tuple) == 2:
            u, v = edge_tuple
            return {
                "source": enrich_node(u),
                "target": enrich_node(v),
            }
        elif len(edge_tuple) == 4:
            u, v, old_w, new_w = edge_tuple
            return {
                "source": enrich_node(u),
                "target": enrich_node(v),
                "old_weight": old_w,
                "new_weight": new_w,
                "delta": new_w - old_w,
            }
        return edge_tuple
    
    return {
        "week_new": week_new,
        "week_old": week_old,
        "weeks_ago": weeks_ago,
        "summary": delta["summary"],
        "new_nodes": [enrich_node(n) for n in delta["new_nodes"][:50]],
        "new_edges": [enrich_edge(e) for e in delta["new_edges"][:50]],
        "weight_increased": [enrich_edge(e) for e in delta["weight_increased"][:50]],
        "note": "Results limited to 50 items per category. Use /compare for custom week ranges.",
    }


# =============================================================================
# Signal Detection Endpoints (Phase 2 - stubs for now)
# =============================================================================

@router.get("/")
async def list_signals(
    week: Optional[str] = None,
    signal_type: Optional[str] = None,
    min_score: float = Query(0.0, description="Minimum emergence score (0-100)"),
):
    """
    List detected emerging signals.
    
    Query params:
        week: Filter by week label (e.g., "2026-W12")
        signal_type: Filter by type ('emerging', 'accelerating', 'declining', 'contradictory')
        min_score: Minimum emergence score threshold
        
    Returns:
        List of signals sorted by emergence score
        
    Note:
        This endpoint will be fully implemented in Phase 2 when signals/detector.py
        and signals/scoring.py are built. For now, use /compare endpoints to see
        raw deltas between snapshots.
    """
    return {
        "signals": [],
        "message": "Signal detection module (Phase 2) not yet implemented. Use /signals/compare to see raw snapshot deltas.",
        "available_endpoints": {
            "snapshots": "/signals/snapshots",
            "compare": "/signals/compare?week_new=2026-W12&week_old=2026-W08",
            "compare_current": "/signals/compare/current?weeks_ago=4",
        }
    }


@router.get("/{signal_id}")
async def get_signal(signal_id: int):
    """
    Get a specific signal by ID with full details.
    
    Returns:
        Signal details including articles, consensus, timeline
        
    Note:
        To be implemented in Phase 2 when signals are stored in the database.
    """
    raise HTTPException(
        status_code=501,
        detail="Signal retrieval not yet implemented (Phase 2). Use /signals/compare for now."
    )


@router.get("/consensus/{entity_a}/{entity_b}")
async def get_relation_consensus(entity_a: str, entity_b: str):
    """
    Get consensus score for a specific relation between two entities.
    
    Args:
        entity_a: First entity ID
        entity_b: Second entity ID
        
    Returns:
        Consensus breakdown (% positive / negative / hypothetical)
        
    Note:
        To be implemented in Phase 5 when OpenMed Assertion Status is integrated.
    """
    raise HTTPException(
        status_code=501,
        detail="Consensus scoring not yet implemented (Phase 5 - requires OpenMed Assertion Status)"
    )
