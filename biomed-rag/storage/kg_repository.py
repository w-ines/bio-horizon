from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from kg.schemas import KgEdge, KgNode
from storage.supabase_client import SupabaseNotConfigured, get_supabase_client

logger = logging.getLogger(__name__)

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
        "job_ids": node.job_ids or [],
        "confidence_max": node.confidence_max,
        "metadata": node.metadata or {},
    }


def upsert_node(node: KgNode, *, table: str = "kg_nodes") -> None:
    client = get_supabase_client()
    client.table(table).upsert(_node_to_payload(node), on_conflict="id").execute()


def upsert_nodes_batch(nodes: List[KgNode], *, table: str = "kg_nodes", chunk_size: int = 500) -> None:
    """
    Upsert nodes in batches to avoid Supabase timeout on large inserts.
    
    Args:
        nodes: List of nodes to upsert
        table: Table name
        chunk_size: Number of nodes per chunk (default 500 to avoid timeout)
    """
    if not nodes:
        return
    
    client = get_supabase_client()
    
    # Split into chunks to avoid timeout
    total_chunks = (len(nodes) + chunk_size - 1) // chunk_size
    logger.info(f"💾 Upserting {len(nodes)} nodes in {total_chunks} chunks of {chunk_size}")
    
    for i in range(0, len(nodes), chunk_size):
        chunk = nodes[i:i + chunk_size]
        chunk_num = (i // chunk_size) + 1
        payload = [_node_to_payload(n) for n in chunk]
        client.table(table).upsert(payload, on_conflict="id").execute()
        logger.debug(f"  ✓ Chunk {chunk_num}/{total_chunks} ({len(chunk)} nodes)")


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
        "job_ids": edge.job_ids or [],
        "metadata": edge.metadata or {},
    }


def upsert_edge(edge: KgEdge, *, table: str = "kg_edges") -> None:
    client = get_supabase_client()
    client.table(table).upsert(_edge_to_payload(edge), on_conflict="source_id,target_id").execute()


def upsert_edges_batch(edges: List[KgEdge], *, table: str = "kg_edges", chunk_size: int = 500) -> None:
    """
    Upsert edges in batches to avoid Supabase timeout on large inserts.
    
    Args:
        edges: List of edges to upsert
        table: Table name
        chunk_size: Number of edges per chunk (default 500 to avoid timeout)
    """
    if not edges:
        return
    
    client = get_supabase_client()
    
    # Split into chunks to avoid timeout
    total_chunks = (len(edges) + chunk_size - 1) // chunk_size
    logger.info(f"💾 Upserting {len(edges)} edges in {total_chunks} chunks of {chunk_size}")
    
    for i in range(0, len(edges), chunk_size):
        chunk = edges[i:i + chunk_size]
        chunk_num = (i // chunk_size) + 1
        payload = [_edge_to_payload(e) for e in chunk]
        client.table(table).upsert(payload, on_conflict="source_id,target_id").execute()
        logger.debug(f"  ✓ Chunk {chunk_num}/{total_chunks} ({len(chunk)} edges)")


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
