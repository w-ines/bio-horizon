"""Knowledge Graph endpoints."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/stats")
async def kg_stats():
    """Returns Knowledge Graph statistics."""
    try:
        from core_tools.kg_tool import stats
        return stats()
    except Exception as e:
        return {"error": str(e), "node_count": 0, "edge_count": 0}


@router.get("/graph")
async def kg_graph(
    entity_type: str = None,
    max_nodes: int = 100,
    min_frequency: int = 1,
    job_ids: str = None,
    sort_by: str = "frequency",
    min_bridge_score: float = 0.0,
):
    """
    Returns Knowledge Graph in node-link format for visualization.
    
    Query params:
    - entity_type: Filter by entity type (DRUG, DISEASE, GENE, etc.)
    - max_nodes: Maximum number of nodes to return (default: 100)
    - min_frequency: Minimum frequency for nodes (default: 1)
    - job_ids: Comma-separated job IDs to filter by (only show nodes/edges from these jobs)
    - sort_by: Which metric decides which nodes survive the max_nodes cap
      ("frequency" default, or "bridge" to prioritise cross-job bridges)
    - min_bridge_score: Only keep nodes whose bridge score is >= this value
    """
    try:
        from core_tools.kg_tool import get_graph, get_bridge_scores
        import networkx as nx
        
        G = get_graph()
        # Bridge scores are computed on the FULL graph so they reflect each
        # node's global role across all jobs, regardless of the filters below.
        bridge_scores = get_bridge_scores()
        
        # Filter by job_ids if specified
        if job_ids:
            selected_jobs = {j.strip() for j in job_ids.split(",") if j.strip()}
            nodes_to_keep = [
                n for n, d in G.nodes(data=True)
                if selected_jobs & set(d.get('job_ids') or [])
            ]
            G = G.subgraph(nodes_to_keep).copy()
        
        # Filter by entity type if specified
        if entity_type:
            nodes_to_keep = [
                n for n, d in G.nodes(data=True)
                if d.get('entity_type', '').upper() == entity_type.upper()
            ]
            G = G.subgraph(nodes_to_keep).copy()
        
        # Filter by frequency
        if min_frequency > 1:
            nodes_to_keep = [
                n for n, d in G.nodes(data=True)
                if d.get('frequency', 0) >= min_frequency
            ]
            G = G.subgraph(nodes_to_keep).copy()
        
        # Filter by minimum bridge score
        if min_bridge_score > 0.0:
            nodes_to_keep = [
                n for n in G.nodes()
                if bridge_scores.get(n, {}).get('bridge_score', 0.0) >= min_bridge_score
            ]
            G = G.subgraph(nodes_to_keep).copy()
        
        # Limit number of nodes (take top by the chosen metric)
        if G.number_of_nodes() > max_nodes:
            if sort_by == "bridge":
                key_fn = lambda x: bridge_scores.get(x[0], {}).get('bridge_score', 0.0)
            else:
                key_fn = lambda x: x[1].get('frequency', 0)
            nodes_sorted = sorted(G.nodes(data=True), key=key_fn, reverse=True)
            top_nodes = [n[0] for n in nodes_sorted[:max_nodes]]
            G = G.subgraph(top_nodes).copy()
        
        # Convert to node-link format
        nodes = []
        for node_id, data in G.nodes(data=True):
            sources = data.get('sources', [])
            bs = bridge_scores.get(node_id, {})
            nodes.append({
                "id": node_id,
                "label": data.get('label', node_id),
                "type": data.get('entity_type', 'UNKNOWN'),
                "frequency": data.get('frequency', 1),
                "degree": G.degree(node_id),
                "sources": sources[:20],
                "source_count": len(sources),
                "job_ids": data.get('job_ids', []),
                "bridge_score": bs.get('bridge_score', 0.0),
                "job_count": bs.get('job_count', len(data.get('job_ids') or [])),
                "neighbor_job_count": bs.get('neighbor_job_count', 0),
                "betweenness": bs.get('betweenness', 0.0),
            })
        
        links = []
        for source, target, data in G.edges(data=True):
            sources = data.get('sources', [])
            links.append({
                "source": source,
                "target": target,
                "weight": data.get('weight', 1),
                "relation_type": data.get('relation_type', 'co_occurrence'),
                "sources": sources[:20],
                "source_count": len(sources),
                "job_ids": data.get('job_ids', []),
            })
        
        return {
            "nodes": nodes,
            "links": links,
            "stats": {
                "total_nodes": G.number_of_nodes(),
                "total_edges": G.number_of_edges(),
                "filtered": entity_type is not None or min_frequency > 1 or job_ids is not None,
                "job_ids_filter": job_ids.split(",") if job_ids else None,
            }
        }
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e), "nodes": [], "links": []}


@router.get("/node/{node_id}")
async def kg_node_details(node_id: str):
    """Get details for a specific node and its neighbors."""
    try:
        from core_tools.kg_tool import query_node
        return query_node(node_id)
    except Exception as e:
        return {"error": str(e)}


@router.get("/top-nodes")
async def kg_top_nodes(n: int = 20, sort_by: str = "frequency"):
    """Get top N nodes by frequency or degree."""
    try:
        from core_tools.kg_tool import query_top_nodes
        return {"nodes": query_top_nodes(n=n, sort_by=sort_by)}
    except Exception as e:
        return {"error": str(e), "nodes": []}


@router.get("/bridges")
async def kg_bridges(n: int = 20, min_jobs: int = 2):
    """Get the top bridge entities — nodes that connect multiple ingestion jobs.

    Query params:
    - n: number of bridge nodes to return (default 20)
    - min_jobs: minimum number of distinct jobs an entity must appear in to
      count as a cross-job bridge (default 2; set to 1 for structural bridges)
    """
    try:
        from core_tools.kg_tool import query_top_bridges
        return {"bridges": query_top_bridges(n=n, min_jobs=min_jobs)}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e), "bridges": []}


@router.get("/articles")
async def kg_articles(pmids: str = "", limit: int = 20):
    """
    Fetch article metadata for given PMIDs (comma-separated).
    
    Used by the frontend when clicking on a KG node/edge to show
    the source articles with PubMed and PDF links.
    
    Query params:
    - pmids: Comma-separated list of PubMed IDs
    - limit: Max articles to return (default 20)
    """
    try:
        if not pmids.strip():
            return {"articles": [], "count": 0}
        
        pmid_list = [p.strip() for p in pmids.split(",") if p.strip()][:limit]
        
        from storage.articles_repository import fetch_articles_by_pmids
        articles = fetch_articles_by_pmids(pmid_list)
        
        return {
            "articles": articles,
            "count": len(articles),
            "requested": len(pmid_list),
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e), "articles": [], "count": 0}
