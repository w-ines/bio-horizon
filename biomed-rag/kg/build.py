from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Tuple

import networkx as nx

from kg.normalize import make_node_id, normalize_entity_text
from kg.schemas import KgEdge, KgNode, KgSnapshot


def new_graph() -> nx.Graph:
    """Create an empty undirected knowledge graph."""
    return nx.Graph()


def _ensure_node(
    G: nx.Graph,
    entity_type: str,
    label: str,
    *,
    source: str = "",
    job_id: str = "",
    confidence: Optional[float] = None,
) -> str:
    """Add or update a node. Returns the node id."""
    nid = make_node_id(entity_type, label)
    if G.has_node(nid):
        G.nodes[nid]["frequency"] += 1
        if source and source not in G.nodes[nid]["sources"]:
            G.nodes[nid]["sources"].append(source)
        if job_id and job_id not in G.nodes[nid].get("job_ids", []):
            G.nodes[nid].setdefault("job_ids", []).append(job_id)
        if confidence is not None:
            prev = G.nodes[nid].get("confidence_max")
            if prev is None or confidence > prev:
                G.nodes[nid]["confidence_max"] = confidence
    else:
        G.add_node(
            nid,
            label=normalize_entity_text(label),
            entity_type=entity_type.upper(),
            frequency=1,
            sources=[source] if source else [],
            job_ids=[job_id] if job_id else [],
            confidence_max=confidence,
        )
    return nid


def _ensure_edge(
    G: nx.Graph,
    nid_a: str,
    nid_b: str,
    *,
    source: str = "",
    job_id: str = "",
    relation_type: str = "co_occurrence",
) -> None:
    """Add or update an edge between two nodes."""
    if nid_a == nid_b:
        return
    key = tuple(sorted([nid_a, nid_b]))
    a, b = key
    if G.has_edge(a, b):
        G.edges[a, b]["weight"] += 1
        if source and source not in G.edges[a, b]["sources"]:
            G.edges[a, b]["sources"].append(source)
        if job_id and job_id not in G.edges[a, b].get("job_ids", []):
            G.edges[a, b].setdefault("job_ids", []).append(job_id)
    else:
        G.add_edge(
            a,
            b,
            weight=1,
            relation_type=relation_type,
            sources=[source] if source else [],
            job_ids=[job_id] if job_id else [],
        )


def add_ner_result_with_relations_to_graph(
    G: nx.Graph,
    ner_result: Dict[str, Any],
    *,
    source: str = "",
    job_id: str = "",
    semantic_triplets: Optional[List[Tuple[str, str, str]]] = None,
) -> nx.Graph:
    """Ingest a NER result into the graph using LLM semantic relation triplets.

    Nodes are always created for all extracted entities.
    Edges are only created for entity pairs covered by semantic_triplets
    (e.g. 'treats', 'inhibits', 'causes'). Pairs with no LLM-extracted
    relation get no edge — no co_occurrence fallback.

    Args:
        G: NetworkX graph.
        ner_result: NER result dict with 'entities' key.
        source: PMID of the source article.
        semantic_triplets: List of (subject_text, relation_type, object_text).
    """
    entities_by_type: Dict[str, list] = ner_result.get("entities", {})
    source = source or ner_result.get("pmid", "")

    # Map normalized text → node_id for triplet lookup
    text_to_nid: Dict[str, str] = {}
    node_ids: List[str] = []
    for entity_type, entities in entities_by_type.items():
        for ent in (entities or []):
            text = ent.get("text", "") if isinstance(ent, dict) else str(ent)
            if not text or not text.strip():
                continue
            confidence = ent.get("confidence") if isinstance(ent, dict) else None
            nid = _ensure_node(G, entity_type, text, source=source, job_id=job_id, confidence=confidence)
            node_ids.append(nid)
            text_to_nid[text.strip().lower()] = nid

    # Add semantic edges from LLM triplets only
    for subj_text, rel_type, obj_text in (semantic_triplets or []):
        nid_a = text_to_nid.get(subj_text.strip().lower())
        nid_b = text_to_nid.get(obj_text.strip().lower())
        if nid_a and nid_b and nid_a != nid_b:
            _ensure_edge(G, nid_a, nid_b, source=source, job_id=job_id, relation_type=rel_type)

    return G


def graph_to_snapshot(G: nx.Graph) -> KgSnapshot:
    """Export a NetworkX graph to a KgSnapshot (serialisable)."""
    nodes = []
    for nid, data in G.nodes(data=True):
        nodes.append(
            KgNode(
                id=nid,
                label=data.get("label", ""),
                entity_type=data.get("entity_type", ""),
                frequency=data.get("frequency", 1),
                sources=data.get("sources", []),
                job_ids=data.get("job_ids", []),
                confidence_max=data.get("confidence_max"),
            )
        )

    edges = []
    for a, b, data in G.edges(data=True):
        edges.append(
            KgEdge(
                source_id=a,
                target_id=b,
                weight=data.get("weight", 1),
                relation_type=data.get("relation_type", "co_occurrence"),
                sources=data.get("sources", []),
                job_ids=data.get("job_ids", []),
            )
        )

    return KgSnapshot(nodes=nodes, edges=edges)
