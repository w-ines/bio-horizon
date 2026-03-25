from __future__ import annotations

"""KG persistence layer.

Mirrors the pattern of memory/store.py:
  - persist_graph(G)  : write nodes+edges snapshot to Supabase
  - load_graph()      : rebuild NetworkX graph from Supabase
  - Both fall back to in-memory if Supabase is not configured or the table
    is missing, so the app never crashes just because the DB is unreachable.
"""

from typing import Any, Dict, List, Optional

import networkx as nx

from kg.build import graph_to_snapshot, new_graph
from kg.schemas import KgEdge, KgNode


def _is_network_error(err: BaseException) -> bool:
    try:
        import httpx
        return isinstance(err, httpx.RequestError)
    except Exception:
        return False


def _is_missing_table_error(err: BaseException) -> bool:
    """Detect PostgREST PGRST205 (schema cache / table missing)."""
    try:
        args = getattr(err, "args", None)
        if args and isinstance(args[0], dict):
            if args[0].get("code") == "PGRST205":
                return True
        if "PGRST205" in str(err):
            return True
    except Exception:
        pass
    return False


def persist_graph(G: nx.Graph) -> int:
    """Persist all nodes + edges from the NetworkX graph to Supabase.

    Returns the number of nodes upserted (edges are also written).
    Falls back silently if Supabase is not reachable.
    """
    from kg.build import graph_to_snapshot
    from storage.kg_repository import (
        SupabaseNotConfigured,
        upsert_edges_batch,
        upsert_nodes_batch,
    )
    from storage.kg_cache_redis import cache_graph_snapshot

    snap = graph_to_snapshot(G)

    try:
        upsert_nodes_batch(snap.nodes)
        upsert_edges_batch(snap.edges)
        
        # Update cache with fresh data after write
        node_dicts = [
            {
                "id": n.id,
                "label": n.label,
                "entity_type": n.entity_type,
                "frequency": n.frequency,
                "sources": n.sources or [],
                "confidence_max": n.confidence_max,
                "metadata": n.metadata or {},
            }
            for n in snap.nodes
        ]
        edge_dicts = [
            {
                "source_id": e.source_id,
                "target_id": e.target_id,
                "weight": e.weight,
                "relation_type": e.relation_type,
                "sources": e.sources or [],
                "metadata": e.metadata or {},
            }
            for e in snap.edges
        ]
        cache_graph_snapshot(node_dicts, edge_dicts)
        
        return len(snap.nodes)
    except SupabaseNotConfigured:
        return 0
    except Exception as e:
        if _is_missing_table_error(e) or _is_network_error(e):
            return 0
        raise


def load_graph() -> nx.Graph:
    """Load the KG from cache or Supabase and return a NetworkX graph.

    Falls back to an empty graph if Supabase is not configured or the
    tables do not exist yet.
    """
    from storage.kg_cache_redis import cache_graph_snapshot, get_cached_graph_snapshot
    from storage.kg_repository import (
        SupabaseNotConfigured,
        fetch_all_edges,
        fetch_all_nodes,
    )

    G = new_graph()

    # Try Redis cache first
    cached = get_cached_graph_snapshot()
    if cached:
        node_rows = cached.get("nodes", [])
        edge_rows = cached.get("edges", [])
    else:
        # Cache miss - fetch from Supabase
        try:
            node_rows = fetch_all_nodes()
            edge_rows = fetch_all_edges()
            
            # Cache the result for next time
            cache_graph_snapshot(node_rows, edge_rows)
        except SupabaseNotConfigured:
            return G
        except Exception as e:
            if _is_missing_table_error(e) or _is_network_error(e):
                return G
            raise

    for r in node_rows:
        nid = r.get("id")
        if not nid:
            continue
        G.add_node(
            nid,
            label=r.get("label", ""),
            entity_type=r.get("entity_type", ""),
            frequency=r.get("frequency", 1),
            sources=r.get("sources") or [],
            confidence_max=r.get("confidence_max"),
            metadata=r.get("metadata") or {},
        )

    for r in edge_rows:
        src = r.get("source_id")
        tgt = r.get("target_id")
        if not src or not tgt:
            continue
        G.add_edge(
            src,
            tgt,
            weight=r.get("weight", 1),
            relation_type=r.get("relation_type", "co_occurrence"),
            sources=r.get("sources") or [],
            metadata=r.get("metadata") or {},
        )

    return G
