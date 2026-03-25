from __future__ import annotations

from itertools import combinations
from typing import Any, Dict, List, Mapping, Optional

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
    confidence: Optional[float] = None,
) -> str:
    """Add or update a node. Returns the node id."""
    nid = make_node_id(entity_type, label)
    if G.has_node(nid):
        G.nodes[nid]["frequency"] += 1
        if source and source not in G.nodes[nid]["sources"]:
            G.nodes[nid]["sources"].append(source)
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
            confidence_max=confidence,
        )
    return nid


def _ensure_edge(
    G: nx.Graph,
    nid_a: str,
    nid_b: str,
    *,
    source: str = "",
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
    else:
        G.add_edge(
            a,
            b,
            weight=1,
            relation_type=relation_type,
            sources=[source] if source else [],
        )


def add_ner_result_to_graph(
    G: nx.Graph,
    ner_result: Dict[str, Any],
    *,
    source: str = "",
) -> nx.Graph:
    """Ingest a single NER result dict into the graph.

    Expected shape (what ner_tool returns):
      {"entities": {"DISEASE": [{"text": ..., "confidence": ...}, ...], ...}, ...}

    All entities from the same source are connected by co-occurrence edges.
    """
    entities_by_type: Dict[str, list] = ner_result.get("entities", {})
    source = source or ner_result.get("pmid", "")

    node_ids: List[str] = []
    for entity_type, entities in entities_by_type.items():
        for ent in (entities or []):
            text = ent.get("text", "") if isinstance(ent, dict) else str(ent)
            if not text or not text.strip():
                continue
            confidence = ent.get("confidence") if isinstance(ent, dict) else None
            nid = _ensure_node(G, entity_type, text, source=source, confidence=confidence)
            node_ids.append(nid)

    # co-occurrence edges: all pairs within the same source
    for a, b in combinations(set(node_ids), 2):
        _ensure_edge(G, a, b, source=source)

    return G


def add_ner_results_batch(
    G: nx.Graph,
    ner_results: List[Dict[str, Any]],
) -> nx.Graph:
    """Ingest a batch of NER results (from extract_medical_entities_batch)."""
    for r in ner_results:
        source = r.get("pmid", "")
        add_ner_result_to_graph(G, r, source=source)
    return G


def build_graph_from_ner_results(
    ner_results: List[Dict[str, Any]],
) -> nx.Graph:
    """Convenience: create a new graph and ingest a batch of NER results."""
    G = new_graph()
    return add_ner_results_batch(G, ner_results)


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
            )
        )

    return KgSnapshot(nodes=nodes, edges=edges)
