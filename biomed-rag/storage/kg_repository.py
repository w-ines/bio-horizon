from __future__ import annotations

from typing import Any, Dict, List, Optional

from kg.schemas import KgEdge, KgNode
from storage.supabase_client import SupabaseNotConfigured, get_supabase_client


# ─────────────────────────────────────────────────────────────
# Nodes
# ─────────────────────────────────────────────────────────────

def _node_to_payload(node: KgNode) -> Dict[str, Any]:
    return {
        "id": node.id,
        "label": node.label,
        "entity_type": node.entity_type,
        "frequency": node.frequency,
        "sources": node.sources or [],
        "confidence_max": node.confidence_max,
        "metadata": node.metadata or {},
    }


def upsert_node(node: KgNode, *, table: str = "kg_nodes") -> None:
    client = get_supabase_client()
    client.table(table).upsert(_node_to_payload(node), on_conflict="id").execute()


def upsert_nodes_batch(nodes: List[KgNode], *, table: str = "kg_nodes") -> None:
    if not nodes:
        return
    client = get_supabase_client()
    payload = [_node_to_payload(n) for n in nodes]
    # Supabase upsert supports batches natively
    client.table(table).upsert(payload, on_conflict="id").execute()


def fetch_all_nodes(*, table: str = "kg_nodes") -> List[Dict[str, Any]]:
    client = get_supabase_client()
    # Paginate in chunks of 1000 (Supabase default limit)
    rows: List[Dict[str, Any]] = []
    page_size = 1000
    offset = 0
    while True:
        res = (
            client.table(table)
            .select("*")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = getattr(res, "data", None) or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return rows


# ─────────────────────────────────────────────────────────────
# Edges
# ─────────────────────────────────────────────────────────────

def _edge_to_payload(edge: KgEdge) -> Dict[str, Any]:
    return {
        "source_id": edge.source_id,
        "target_id": edge.target_id,
        "weight": edge.weight,
        "relation_type": edge.relation_type,
        "sources": edge.sources or [],
        "metadata": edge.metadata or {},
    }


def upsert_edge(edge: KgEdge, *, table: str = "kg_edges") -> None:
    client = get_supabase_client()
    client.table(table).upsert(_edge_to_payload(edge), on_conflict="source_id,target_id").execute()


def upsert_edges_batch(edges: List[KgEdge], *, table: str = "kg_edges") -> None:
    if not edges:
        return
    client = get_supabase_client()
    payload = [_edge_to_payload(e) for e in edges]
    client.table(table).upsert(payload, on_conflict="source_id,target_id").execute()


def fetch_all_edges(*, table: str = "kg_edges") -> List[Dict[str, Any]]:
    client = get_supabase_client()
    rows: List[Dict[str, Any]] = []
    page_size = 1000
    offset = 0
    while True:
        res = (
            client.table(table)
            .select("*")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = getattr(res, "data", None) or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return rows
