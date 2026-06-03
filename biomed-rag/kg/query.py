from __future__ import annotations

from typing import Any, Dict, List, Optional

import networkx as nx


def get_node(G: nx.Graph, node_id: str) -> Optional[Dict[str, Any]]:
    """Return node data or None."""
    if not G.has_node(node_id):
        return None
    data = dict(G.nodes[node_id])
    data["id"] = node_id
    return data


def neighbors(G: nx.Graph, node_id: str) -> List[Dict[str, Any]]:
    """Return immediate neighbors of a node with edge data."""
    if not G.has_node(node_id):
        return []
    result = []
    for nb in G.neighbors(node_id):
        edge_data = G.edges[node_id, nb]
        nb_data = dict(G.nodes[nb])
        nb_data["id"] = nb
        nb_data["edge_weight"] = edge_data.get("weight", 1)
        nb_data["relation_type"] = edge_data.get("relation_type", "co_occurrence")
        result.append(nb_data)
    result.sort(key=lambda x: x.get("edge_weight", 0), reverse=True)
    return result


def top_nodes(G: nx.Graph, n: int = 10, sort_by: str = "frequency") -> List[Dict[str, Any]]:
    """Return the top-n nodes sorted by frequency or degree."""
    nodes = []
    for nid, data in G.nodes(data=True):
        entry = dict(data)
        entry["id"] = nid
        entry["degree"] = G.degree(nid)
        nodes.append(entry)

    if sort_by == "degree":
        nodes.sort(key=lambda x: x.get("degree", 0), reverse=True)
    else:
        nodes.sort(key=lambda x: x.get("frequency", 0), reverse=True)

    return nodes[:n]


def top_edges(G: nx.Graph, n: int = 10) -> List[Dict[str, Any]]:
    """Return the top-n edges by weight."""
    edges = []
    for a, b, data in G.edges(data=True):
        entry = dict(data)
        entry["source_id"] = a
        entry["target_id"] = b
        edges.append(entry)
    edges.sort(key=lambda x: x.get("weight", 0), reverse=True)
    return edges[:n]


def shortest_path(G: nx.Graph, source_id: str, target_id: str) -> Optional[Dict[str, Any]]:
    """Find shortest path between two nodes."""
    if not G.has_node(source_id) or not G.has_node(target_id):
        return None
    try:
        path = nx.shortest_path(G, source_id, target_id)
        return {
            "path": path,
            "length": len(path) - 1,
            "nodes": [dict(G.nodes[nid], id=nid) for nid in path],
        }
    except nx.NetworkXNoPath:
        return None


def graph_stats(G: nx.Graph) -> Dict[str, Any]:
    """Basic statistics about the graph."""
    return {
        "node_count": G.number_of_nodes(),
        "edge_count": G.number_of_edges(),
        "connected_components": nx.number_connected_components(G),
        "density": round(nx.density(G), 6) if G.number_of_nodes() > 1 else 0.0,
    }


def subgraph_for_entity_type(G: nx.Graph, entity_type: str) -> nx.Graph:
    """Return a subgraph containing only nodes of a given entity type."""
    nodes = [n for n, d in G.nodes(data=True) if d.get("entity_type", "").upper() == entity_type.upper()]
    return G.subgraph(nodes).copy()


# ─────────────────────────────────────────────────────────────
# Bridge score
# ─────────────────────────────────────────────────────────────
#
# A "bridge" is an entity that connects otherwise separate ingestion jobs
# (corpora). Bridges are valuable because they let us:
#   - discover implicit links between separately-ingested topics,
#   - surface cross-cutting (transversal) entities,
#   - enrich RAG retrieval by following shared anchors across corpora,
#   - corroborate reliability (an entity independently mentioned by many jobs).
#
# The score combines three normalised signals (each in [0, 1]):
#   job_breadth      : how many distinct jobs reference the node directly,
#   neighbor_breadth : how many distinct jobs are reachable in one hop,
#   betweenness      : structural centrality on shortest paths.

# Weights for the composite score (must sum to 1.0).
_BRIDGE_W_JOB = 0.45
_BRIDGE_W_NEIGHBOR = 0.25
_BRIDGE_W_BETWEENNESS = 0.30

# Above this node count, approximate betweenness with k-source sampling
# to keep the computation tractable (exact betweenness is O(V*E)).
_BETWEENNESS_SAMPLE_THRESHOLD = 800
_BETWEENNESS_SAMPLE_K = 400


def _node_jobs(data: Dict[str, Any]) -> set:
    """Return the set of job ids attached to a node, tolerating None/dupes."""
    return {j for j in (data.get("job_ids") or []) if j}


def compute_bridge_scores(G: nx.Graph) -> Dict[str, Dict[str, Any]]:
    """Compute a bridge score (and its components) for every node.

    Returns a mapping ``node_id -> {bridge_score, job_count, neighbor_job_count,
    betweenness, total_jobs}``. Scores are in [0, 1]; higher means the entity
    acts more strongly as a bridge between ingestion jobs / across the graph.

    Designed to run on the *full* graph so the score reflects a node's global
    role, independent of any UI filtering applied later.
    """
    if G.number_of_nodes() == 0:
        return {}

    # Total distinct jobs across the whole graph.
    all_jobs: set = set()
    node_jobs: Dict[str, set] = {}
    for nid, data in G.nodes(data=True):
        jobs = _node_jobs(data)
        node_jobs[nid] = jobs
        all_jobs |= jobs
    total_jobs = len(all_jobs)
    job_denom = (total_jobs - 1) if total_jobs > 1 else 1

    # Betweenness centrality (already normalised to [0, 1] by NetworkX), with
    # k-source sampling on large graphs to bound runtime.
    n = G.number_of_nodes()
    if n > _BETWEENNESS_SAMPLE_THRESHOLD:
        k = min(_BETWEENNESS_SAMPLE_K, n)
        betweenness = nx.betweenness_centrality(G, k=k, normalized=True, seed=42)
    else:
        betweenness = nx.betweenness_centrality(G, normalized=True)
    max_betw = max(betweenness.values()) if betweenness else 0.0

    scores: Dict[str, Dict[str, Any]] = {}
    for nid in G.nodes():
        jobs = node_jobs[nid]
        job_count = len(jobs)

        # Distinct jobs reachable within one hop (node's own jobs + neighbors').
        neighbor_jobs = set(jobs)
        for nb in G.neighbors(nid):
            neighbor_jobs |= node_jobs.get(nb, set())
        neighbor_job_count = len(neighbor_jobs)

        job_breadth = max(0.0, (job_count - 1) / job_denom)
        neighbor_breadth = max(0.0, (neighbor_job_count - 1) / job_denom)
        betw = betweenness.get(nid, 0.0)
        betw_norm = (betw / max_betw) if max_betw > 0 else 0.0

        bridge_score = (
            _BRIDGE_W_JOB * job_breadth
            + _BRIDGE_W_NEIGHBOR * neighbor_breadth
            + _BRIDGE_W_BETWEENNESS * betw_norm
        )

        scores[nid] = {
            "bridge_score": round(bridge_score, 4),
            "job_count": job_count,
            "neighbor_job_count": neighbor_job_count,
            "betweenness": round(betw, 6),
            "total_jobs": total_jobs,
        }

    return scores


def top_bridge_nodes(
    G: nx.Graph,
    n: int = 20,
    *,
    min_jobs: int = 2,
) -> List[Dict[str, Any]]:
    """Return the top-n bridge nodes, sorted by bridge score (desc).

    Args:
        G: the knowledge graph.
        n: number of nodes to return.
        min_jobs: only keep entities shared by at least this many jobs
            (default 2 → genuine cross-job bridges). Set to 1 to include
            purely structural bridges within a single corpus.
    """
    scores = compute_bridge_scores(G)
    rows: List[Dict[str, Any]] = []
    for nid, s in scores.items():
        if s["job_count"] < min_jobs:
            continue
        data = G.nodes[nid]
        rows.append({
            "id": nid,
            "label": data.get("label", nid),
            "entity_type": data.get("entity_type", "UNKNOWN"),
            "frequency": data.get("frequency", 1),
            "degree": G.degree(nid),
            "job_ids": data.get("job_ids", []),
            **s,
        })
    rows.sort(key=lambda x: x["bridge_score"], reverse=True)
    return rows[:n]
