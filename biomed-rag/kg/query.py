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
