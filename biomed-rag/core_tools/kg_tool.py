from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional


import os
from dotenv import load_dotenv
load_dotenv()

from kg import build, query, store

from kg.build import graph_to_snapshot
from core_tools.ner_tool import (
    extract_medical_entities_from_article,
    extract_medical_entities_batch,
    extract_medical_entities_from_text,
)

# Module-level graph: loaded from Supabase on first use.
# Falls back to an empty graph if Supabase is not configured.
_graph = store.load_graph()


def get_graph():
    """Return the current in-memory graph (for direct access / tests)."""
    return _graph


def reset_graph():
    """Reset the in-memory graph (useful for tests)."""
    global _graph
    _graph = build.new_graph()
    return _graph


def load_from_supabase() -> Dict[str, Any]:
    """Reload the in-memory graph from Supabase (e.g. after a restart)."""
    global _graph
    _graph = store.load_graph()
    return query.graph_stats(_graph)


def persist_to_supabase() -> Dict[str, Any]:
    """Manually flush the current in-memory graph to Supabase."""
    n = store.persist_graph(_graph)
    return {"nodes_persisted": n, "graph_stats": query.graph_stats(_graph)}


# ─────────────────────────────────────────────
# Build operations  (NER → KG)
# ─────────────────────────────────────────────

def ingest_text(
    text: str,
    *,
    source: str = "",
    entity_types: Optional[list] = None,
    provider: Optional[str] = None,
) -> Dict[str, Any]:
    """Run NER on free text, then ingest entities into the KG.

    Returns:
      {"ner": <ner_result>, "graph_stats": {...}}
    """
    ner_result = extract_medical_entities_from_text(
        text, entity_types=entity_types, provider=provider,
    )
    build.add_ner_result_to_graph(_graph, ner_result, source=source)
    store.persist_graph(_graph)
    return {
        "ner": ner_result,
        "graph_stats": query.graph_stats(_graph),
    }


def ingest_article(
    article: Mapping[str, Any],
    *,
    entity_types: Optional[list] = None,
    provider: Optional[str] = None,
) -> Dict[str, Any]:
    """Run NER on a PubMed article dict, then ingest into the KG."""
    ner_result = extract_medical_entities_from_article(
        article, entity_types=entity_types, provider=provider,
    )
    source = ner_result.get("pmid", "")
    build.add_ner_result_to_graph(_graph, ner_result, source=source)
    store.persist_graph(_graph)
    return {
        "ner": ner_result,
        "graph_stats": query.graph_stats(_graph),
    }


def ingest_articles_batch(
    articles: List[Mapping[str, Any]],
    *,
    entity_types: Optional[list] = None,
    provider: Optional[str] = None,
) -> Dict[str, Any]:
    """Run NER batch on multiple articles, then ingest all into the KG."""
    ner_results = extract_medical_entities_batch(
        articles, entity_types=entity_types, provider=provider,
    )
    build.add_ner_results_batch(_graph, ner_results)
    store.persist_graph(_graph)
    return {
        "articles_processed": len(ner_results),
        "graph_stats": query.graph_stats(_graph),
    }


def ingest_from_pubmed(
    query: str,
    *,
    max_results: int = 20,
    mindate: str = "",
    maxdate: str = "",
    entity_types: Optional[list] = None,
    provider: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Search PubMed and ingest articles into the Knowledge Graph.
    
    This function:
    1. Searches PubMed using the query
    2. Fetches article details (title, abstract, MeSH terms)
    3. Extracts medical entities from each article
    4. Adds entities and relationships to the KG
    5. Persists the updated KG to Supabase
    
    Args:
        query: PubMed search query (supports MeSH terms, filters, etc.)
               Examples: "alzheimer treatment", "diabetes[MeSH] AND 2024[pdat]"
        max_results: Maximum number of articles to retrieve (default: 20)
        mindate: Minimum publication date (YYYY or YYYY/MM or YYYY/MM/DD)
        maxdate: Maximum publication date (YYYY or YYYY/MM or YYYY/MM/DD)
        entity_types: Entity types to extract (default: medical entities)
        provider: NER provider to use (default: auto-select)
    
    Returns:
        dict: {
            "pubmed_query": str,
            "articles_found": int,
            "articles_processed": int,
            "entities_extracted": int,
            "graph_stats": dict,
            "error": str (if error occurred)
        }
    
    Examples:
        >>> # Enrich KG with Alzheimer research
        >>> ingest_from_pubmed("alzheimer treatment", max_results=50)
        
        >>> # Recent diabetes articles
        >>> ingest_from_pubmed("diabetes mellitus", mindate="2024", max_results=30)
        
        >>> # Specific topic with MeSH terms
        >>> ingest_from_pubmed("cardiovascular disease[MeSH] AND aspirin", max_results=40)
    """
    try:
        from core_tools.pubmed_tool import search_pubmed
    except ImportError:
        return {
            "error": "PubMed tool not available. Check tools/pubmed_tool.py",
            "pubmed_query": query,
            "articles_found": 0,
            "articles_processed": 0,
        }
    
    # Search PubMed
    print(f"[ingest_from_pubmed] Searching PubMed: '{query}' (max={max_results})")
    
    pubmed_result = search_pubmed(
        query=query,
        max_results=max_results,
        mindate=mindate,
        maxdate=maxdate,
        fetch_details=True,
    )
    
    # Check for errors
    if "error" in pubmed_result:
        return {
            "error": pubmed_result["error"],
            "pubmed_query": query,
            "articles_found": 0,
            "articles_processed": 0,
        }
    
    articles = pubmed_result.get("articles", [])
    total_found = pubmed_result.get("total", 0)
    
    if not articles:
        from kg import query as kg_query
        return {
            "pubmed_query": query,
            "articles_found": total_found,
            "articles_processed": 0,
            "entities_extracted": 0,
            "graph_stats": kg_query.graph_stats(_graph),
            "message": "No articles retrieved from PubMed"
        }
    
    print(f"[ingest_from_pubmed] Processing {len(articles)} articles...")
    
    # Extract entities from all articles (batch processing)
    ner_results = extract_medical_entities_batch(
        articles,
        entity_types=entity_types,
        provider=provider,
    )
    
    # Count total entities extracted
    total_entities = 0
    for ner_result in ner_results:
        entities_dict = ner_result.get("entities", {})
        for entity_type, entity_list in entities_dict.items():
            total_entities += len(entity_list)
    
    # Add to Knowledge Graph
    build.add_ner_results_batch(_graph, ner_results)
    
    # Persist to Supabase
    store.persist_graph(_graph)
    
    print(f"[ingest_from_pubmed] ✅ Processed {len(articles)} articles, extracted {total_entities} entities")
    
    from kg import query as kg_query
    return {
        "pubmed_query": query,
        "articles_found": total_found,
        "articles_processed": len(articles),
        "entities_extracted": total_entities,
        "graph_stats": kg_query.graph_stats(_graph),
    }


# ─────────────────────────────────────────────
# Query operations
# ─────────────────────────────────────────────

def query_node(node_id: str) -> Dict[str, Any]:
    """Get a node + its neighbors."""
    node = query.get_node(_graph, node_id)
    if node is None:
        return {"error": f"Node '{node_id}' not found"}
    return {
        "node": node,
        "neighbors": query.neighbors(_graph, node_id),
    }


def query_top_nodes(n: int = 10, sort_by: str = "frequency") -> List[Dict[str, Any]]:
    return query.top_nodes(_graph, n=n, sort_by=sort_by)


def query_top_edges(n: int = 10) -> List[Dict[str, Any]]:
    return query.top_edges(_graph, n=n)


def query_path(source_id: str, target_id: str) -> Dict[str, Any]:
    result = query.shortest_path(_graph, source_id, target_id)
    if result is None:
        return {"error": f"No path between '{source_id}' and '{target_id}'"}
    return result


def snapshot() -> Dict[str, Any]:
    """Export the full graph as a serialisable dict."""
    return graph_to_snapshot(_graph).to_dict()


def stats() -> Dict[str, Any]:
    return query.graph_stats(_graph)
