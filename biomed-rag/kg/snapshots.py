"""
Temporal Knowledge Graph Snapshot Management.

This module implements the core temporal dimension of BioHorizon:
- Save weekly snapshots of the KG to track evolution over time
- Load snapshots from specific weeks for comparison
- Compare two snapshots to detect emerging signals
- Store snapshots both in Supabase (persistent) and as JSON files (backup)

The snapshot system is the foundation for signal detection: by comparing
KG(week N) vs KG(week N-4), we can identify which entities and relations
are emerging, accelerating, or declining.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx

from kg.build import graph_to_snapshot, new_graph
from kg.schemas import KgEdge, KgNode, KgSnapshot


# =============================================================================
# Week Label Utilities
# =============================================================================

def get_week_label(target_date: Optional[date] = None) -> str:
    """
    Generate ISO week label (e.g., '2026-W12') for a given date.
    
    Args:
        target_date: Date to convert. If None, uses today.
        
    Returns:
        ISO week string in format 'YYYY-Www' (e.g., '2026-W12')
        
    Example:
        >>> get_week_label(date(2026, 3, 19))
        '2026-W12'
    """
    if target_date is None:
        target_date = date.today()
    
    # Get ISO calendar: (year, week_number, weekday)
    iso_year, iso_week, _ = target_date.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def parse_week_label(week_label: str) -> date:
    """
    Parse ISO week label back to the Monday of that week.
    
    Args:
        week_label: ISO week string (e.g., '2026-W12')
        
    Returns:
        Date object representing the Monday of that week
        
    Example:
        >>> parse_week_label('2026-W12')
        date(2026, 3, 16)  # Monday of week 12
    """
    # Parse format: '2026-W12' -> year=2026, week=12
    year_str, week_str = week_label.split('-W')
    year = int(year_str)
    week = int(week_str)
    
    # ISO week date: year, week, weekday (1=Monday)
    return datetime.strptime(f"{year}-W{week}-1", "%Y-W%W-%w").date()


def get_week_label_offset(weeks_ago: int = 0) -> str:
    """
    Get week label for N weeks ago.
    
    Args:
        weeks_ago: Number of weeks to go back (0 = current week)
        
    Returns:
        ISO week label
        
    Example:
        >>> get_week_label_offset(4)  # 4 weeks ago
        '2026-W08'
    """
    target_date = date.today() - timedelta(weeks=weeks_ago)
    return get_week_label(target_date)


# =============================================================================
# File-based Snapshot Storage (JSON backup)
# =============================================================================

def get_snapshot_filepath(week_label: str, base_dir: Optional[Path] = None) -> Path:
    """
    Get the file path for a snapshot JSON file.
    
    Args:
        week_label: ISO week label (e.g., '2026-W12')
        base_dir: Base directory for snapshots. Defaults to ./data/kg_snapshots/
        
    Returns:
        Path to snapshot file
        
    Example:
        >>> get_snapshot_filepath('2026-W12')
        Path('data/kg_snapshots/2026-W12.json')
    """
    if base_dir is None:
        # Default: ./data/kg_snapshots/ relative to project root
        base_dir = Path(__file__).parent.parent / "data" / "kg_snapshots"
    
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / f"{week_label}.json"


def save_snapshot_to_file(
    G: nx.Graph,
    week_label: Optional[str] = None,
    base_dir: Optional[Path] = None,
) -> Path:
    """
    Save a NetworkX graph as a JSON snapshot file.
    
    This provides a file-based backup of snapshots, independent of Supabase.
    Useful for debugging, archiving, and offline analysis.
    
    Args:
        G: NetworkX graph to save
        week_label: ISO week label. If None, uses current week.
        base_dir: Directory to save snapshots
        
    Returns:
        Path to the saved file
        
    Example:
        >>> G = build_graph_from_ner_results(ner_results)
        >>> path = save_snapshot_to_file(G, '2026-W12')
        >>> print(path)
        data/kg_snapshots/2026-W12.json
    """
    if week_label is None:
        week_label = get_week_label()
    
    filepath = get_snapshot_filepath(week_label, base_dir)
    
    # Convert NetworkX graph to serializable snapshot
    snapshot = graph_to_snapshot(G)
    
    # Prepare JSON-serializable dict
    snapshot_dict = {
        "week_label": week_label,
        "snapshot_date": date.today().isoformat(),
        "node_count": len(snapshot.nodes),
        "edge_count": len(snapshot.edges),
        "nodes": [
            {
                "id": n.id,
                "label": n.label,
                "entity_type": n.entity_type,
                "frequency": n.frequency,
                "sources": n.sources or [],
                "confidence_max": n.confidence_max,
                "metadata": n.metadata or {},
            }
            for n in snapshot.nodes
        ],
        "edges": [
            {
                "source_id": e.source_id,
                "target_id": e.target_id,
                "weight": e.weight,
                "relation_type": e.relation_type,
                "sources": e.sources or [],
                "metadata": e.metadata or {},
            }
            for e in snapshot.edges
        ],
    }
    
    # Write to file with pretty formatting
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(snapshot_dict, f, indent=2, ensure_ascii=False)
    
    return filepath


def load_snapshot_from_file(
    week_label: str,
    base_dir: Optional[Path] = None,
) -> Optional[nx.Graph]:
    """
    Load a NetworkX graph from a JSON snapshot file.
    
    Args:
        week_label: ISO week label (e.g., '2026-W12')
        base_dir: Directory where snapshots are stored
        
    Returns:
        NetworkX graph, or None if file doesn't exist
        
    Example:
        >>> G = load_snapshot_from_file('2026-W12')
        >>> if G:
        ...     print(f"Loaded {G.number_of_nodes()} nodes")
    """
    filepath = get_snapshot_filepath(week_label, base_dir)
    
    if not filepath.exists():
        return None
    
    with open(filepath, "r", encoding="utf-8") as f:
        snapshot_dict = json.load(f)
    
    # Rebuild NetworkX graph from JSON
    G = new_graph()
    
    for node_data in snapshot_dict.get("nodes", []):
        G.add_node(
            node_data["id"],
            label=node_data.get("label", ""),
            entity_type=node_data.get("entity_type", ""),
            frequency=node_data.get("frequency", 1),
            sources=node_data.get("sources", []),
            confidence_max=node_data.get("confidence_max"),
            metadata=node_data.get("metadata", {}),
        )
    
    for edge_data in snapshot_dict.get("edges", []):
        G.add_edge(
            edge_data["source_id"],
            edge_data["target_id"],
            weight=edge_data.get("weight", 1),
            relation_type=edge_data.get("relation_type", "co_occurrence"),
            sources=edge_data.get("sources", []),
            metadata=edge_data.get("metadata", {}),
        )
    
    return G


# =============================================================================
# Supabase-based Snapshot Storage (persistent database)
# =============================================================================

def save_snapshot_to_supabase(
    G: nx.Graph,
    week_label: Optional[str] = None,
) -> Optional[int]:
    """
    Save a snapshot to Supabase kg_snapshots table.
    
    This is the primary persistent storage. The snapshot is stored as JSONB
    in PostgreSQL, allowing efficient querying and comparison.
    
    Args:
        G: NetworkX graph to save
        week_label: ISO week label. If None, uses current week.
        
    Returns:
        Snapshot ID from Supabase, or None if Supabase not configured
        
    Example:
        >>> G = build_graph_from_ner_results(ner_results)
        >>> snapshot_id = save_snapshot_to_supabase(G, '2026-W12')
    """
    from storage.supabase_client import get_supabase_client, SupabaseNotConfigured
    
    if week_label is None:
        week_label = get_week_label()
    
    snapshot = graph_to_snapshot(G)
    
    # Prepare snapshot data
    snapshot_data = {
        "week_label": week_label,
        "snapshot_date": date.today().isoformat(),
        "node_count": len(snapshot.nodes),
        "edge_count": len(snapshot.edges),
        "data": {
            "nodes": [
                {
                    "id": n.id,
                    "label": n.label,
                    "entity_type": n.entity_type,
                    "frequency": n.frequency,
                    "sources": n.sources or [],
                    "confidence_max": n.confidence_max,
                    "metadata": n.metadata or {},
                }
                for n in snapshot.nodes
            ],
            "edges": [
                {
                    "source_id": e.source_id,
                    "target_id": e.target_id,
                    "weight": e.weight,
                    "relation_type": e.relation_type,
                    "sources": e.sources or [],
                    "metadata": e.metadata or {},
                }
                for e in snapshot.edges
            ],
        },
    }
    
    try:
        client = get_supabase_client()
        
        # Upsert: if week_label exists, update; otherwise insert
        result = client.table("kg_snapshots").upsert(
            snapshot_data,
            on_conflict="week_label"
        ).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0].get("id")
        return None
        
    except SupabaseNotConfigured:
        return None
    except Exception as e:
        print(f"[snapshots] Failed to save to Supabase: {e}")
        return None


def load_snapshot_from_supabase(week_label: str) -> Optional[nx.Graph]:
    """
    Load a snapshot from Supabase kg_snapshots table.
    
    Args:
        week_label: ISO week label (e.g., '2026-W12')
        
    Returns:
        NetworkX graph, or None if not found
        
    Example:
        >>> G = load_snapshot_from_supabase('2026-W12')
        >>> if G:
        ...     print(f"Loaded {G.number_of_nodes()} nodes from Supabase")
    """
    from storage.supabase_client import get_supabase_client, SupabaseNotConfigured
    
    try:
        client = get_supabase_client()
        
        result = client.table("kg_snapshots").select("*").eq(
            "week_label", week_label
        ).execute()
        
        if not result.data or len(result.data) == 0:
            return None
        
        snapshot_row = result.data[0]
        snapshot_data = snapshot_row.get("data", {})
        
        # Rebuild NetworkX graph
        G = new_graph()
        
        for node_data in snapshot_data.get("nodes", []):
            G.add_node(
                node_data["id"],
                label=node_data.get("label", ""),
                entity_type=node_data.get("entity_type", ""),
                frequency=node_data.get("frequency", 1),
                sources=node_data.get("sources", []),
                confidence_max=node_data.get("confidence_max"),
                metadata=node_data.get("metadata", {}),
            )
        
        for edge_data in snapshot_data.get("edges", []):
            G.add_edge(
                edge_data["source_id"],
                edge_data["target_id"],
                weight=edge_data.get("weight", 1),
                relation_type=edge_data.get("relation_type", "co_occurrence"),
                sources=edge_data.get("sources", []),
                metadata=edge_data.get("metadata", {}),
            )
        
        return G
        
    except SupabaseNotConfigured:
        return None
    except Exception as e:
        print(f"[snapshots] Failed to load from Supabase: {e}")
        return None


# =============================================================================
# High-level Snapshot API (tries Supabase first, falls back to files)
# =============================================================================

def save_snapshot(
    G: nx.Graph,
    week_label: Optional[str] = None,
) -> Tuple[Optional[int], Path]:
    """
    Save a snapshot to both Supabase and file system.
    
    This is the recommended way to save snapshots: it ensures redundancy
    (Supabase for querying, files for backup/debugging).
    
    Args:
        G: NetworkX graph to save
        week_label: ISO week label. If None, uses current week.
        
    Returns:
        Tuple of (supabase_id, filepath)
        
    Example:
        >>> G = build_graph_from_ner_results(ner_results)
        >>> snapshot_id, filepath = save_snapshot(G)
        >>> print(f"Saved to Supabase (ID={snapshot_id}) and {filepath}")
    """
    if week_label is None:
        week_label = get_week_label()
    
    # Save to both storages
    supabase_id = save_snapshot_to_supabase(G, week_label)
    filepath = save_snapshot_to_file(G, week_label)
    
    return supabase_id, filepath


def load_snapshot(week_label: str) -> Optional[nx.Graph]:
    """
    Load a snapshot, trying Supabase first, then falling back to file.
    
    Args:
        week_label: ISO week label (e.g., '2026-W12')
        
    Returns:
        NetworkX graph, or None if not found in either storage
        
    Example:
        >>> G = load_snapshot('2026-W12')
        >>> if G:
        ...     print(f"Loaded {G.number_of_nodes()} nodes")
        ... else:
        ...     print("Snapshot not found")
    """
    # Try Supabase first (faster, queryable)
    G = load_snapshot_from_supabase(week_label)
    if G is not None:
        return G
    
    # Fallback to file
    G = load_snapshot_from_file(week_label)
    return G


def list_available_snapshots() -> List[str]:
    """
    List all available snapshot week labels.
    
    Returns:
        List of ISO week labels, sorted chronologically
        
    Example:
        >>> snapshots = list_available_snapshots()
        >>> print(snapshots)
        ['2026-W08', '2026-W09', '2026-W10', '2026-W11', '2026-W12']
    """
    from storage.supabase_client import get_supabase_client, SupabaseNotConfigured
    
    week_labels = set()
    
    # Get from Supabase
    try:
        client = get_supabase_client()
        result = client.table("kg_snapshots").select("week_label").execute()
        if result.data:
            week_labels.update(row["week_label"] for row in result.data)
    except (SupabaseNotConfigured, Exception):
        pass
    
    # Get from files
    snapshot_dir = Path(__file__).parent.parent / "data" / "kg_snapshots"
    if snapshot_dir.exists():
        for filepath in snapshot_dir.glob("*.json"):
            week_label = filepath.stem  # filename without .json
            week_labels.add(week_label)
    
    return sorted(week_labels)


# =============================================================================
# Snapshot Comparison (foundation for signal detection)
# =============================================================================

def compare_snapshots(
    G_new: nx.Graph,
    G_old: nx.Graph,
) -> Dict[str, Any]:
    """
    Compare two snapshots to identify changes (delta).
    
    This is the core of signal detection: by comparing KG(week N) vs KG(week N-4),
    we can identify:
    - New nodes (entities that appeared)
    - New edges (relations that appeared)
    - Edges with increased weight (relations that strengthened)
    - Edges with decreased weight (relations that weakened)
    - Disappeared nodes/edges
    
    Args:
        G_new: Recent snapshot (e.g., week N)
        G_old: Older snapshot (e.g., week N-4)
        
    Returns:
        Dict with keys:
        - new_nodes: List of node IDs that appeared
        - disappeared_nodes: List of node IDs that disappeared
        - new_edges: List of (source, target) tuples
        - disappeared_edges: List of (source, target) tuples
        - weight_increased: List of (source, target, old_weight, new_weight)
        - weight_decreased: List of (source, target, old_weight, new_weight)
        
    Example:
        >>> G_new = load_snapshot('2026-W12')
        >>> G_old = load_snapshot('2026-W08')
        >>> delta = compare_snapshots(G_new, G_old)
        >>> print(f"New entities: {len(delta['new_nodes'])}")
        >>> print(f"New relations: {len(delta['new_edges'])}")
    """
    # Node comparison
    nodes_new = set(G_new.nodes())
    nodes_old = set(G_old.nodes())
    
    new_nodes = list(nodes_new - nodes_old)
    disappeared_nodes = list(nodes_old - nodes_new)
    
    # Edge comparison
    edges_new = set(G_new.edges())
    edges_old = set(G_old.edges())
    
    new_edges = list(edges_new - edges_old)
    disappeared_edges = list(edges_old - edges_new)
    
    # Weight changes (for edges present in both snapshots)
    common_edges = edges_new & edges_old
    weight_increased = []
    weight_decreased = []
    
    for u, v in common_edges:
        old_weight = G_old.edges[u, v].get("weight", 1)
        new_weight = G_new.edges[u, v].get("weight", 1)
        
        if new_weight > old_weight:
            weight_increased.append((u, v, old_weight, new_weight))
        elif new_weight < old_weight:
            weight_decreased.append((u, v, old_weight, new_weight))
    
    return {
        "new_nodes": new_nodes,
        "disappeared_nodes": disappeared_nodes,
        "new_edges": new_edges,
        "disappeared_edges": disappeared_edges,
        "weight_increased": weight_increased,
        "weight_decreased": weight_decreased,
        "summary": {
            "total_new_nodes": len(new_nodes),
            "total_new_edges": len(new_edges),
            "total_weight_increased": len(weight_increased),
            "total_disappeared_nodes": len(disappeared_nodes),
            "total_disappeared_edges": len(disappeared_edges),
        },
    }