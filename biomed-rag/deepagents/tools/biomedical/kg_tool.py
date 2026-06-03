"""LangChain tool wrapper for Knowledge Graph operations.

This wrapper allows Deep Agents to build and query the temporal Knowledge Graph.
It calls the kg module logic.
"""

from typing import Optional
from langchain.tools import tool

from kg.build import build_kg_from_entities
from kg.query import query_kg, get_entity_neighbors
from kg.snapshots import save_snapshot, load_snapshot


@tool
def build_knowledge_graph(
    entities_json: str,
    source_pmid: Optional[str] = None
) -> str:
    """Build Knowledge Graph from extracted entities.
    
    Args:
        entities_json: JSON string with entities (output from extract_entities)
        source_pmid: Optional PubMed ID for traceability
    
    Returns:
        JSON string with KG statistics (nodes, edges)
    
    Example:
        build_knowledge_graph('{"DISEASE": [{"text": "Alzheimer"}], "DRUG": [{"text": "Semaglutide"}]}')
    """
    import json
    
    try:
        entities = json.loads(entities_json)
        
        # Build KG
        kg = build_kg_from_entities(entities, source_pmid=source_pmid)
        
        return json.dumps({
            "nodes": kg.number_of_nodes(),
            "edges": kg.number_of_edges(),
            "source": source_pmid
        }, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool
def query_knowledge_graph(
    entity: str,
    max_hops: int = 2
) -> str:
    """Query Knowledge Graph for entity relationships.
    
    Args:
        entity: Entity name to query
        max_hops: Maximum distance to explore (default: 2)
    
    Returns:
        JSON string with related entities and relationships
    
    Example:
        query_knowledge_graph("Alzheimer disease", max_hops=2)
    """
    import json
    
    try:
        neighbors = get_entity_neighbors(entity, max_hops=max_hops)
        
        return json.dumps({
            "entity": entity,
            "neighbors": neighbors,
            "max_hops": max_hops
        }, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool
def save_kg_snapshot(
    snapshot_name: str
) -> str:
    """Save current Knowledge Graph as a snapshot.
    
    Args:
        snapshot_name: Name for the snapshot (e.g., "week_2024_12")
    
    Returns:
        JSON string with snapshot path
    
    Example:
        save_kg_snapshot("week_2024_12")
    """
    import json
    
    try:
        path = save_snapshot(snapshot_name)
        
        return json.dumps({
            "snapshot": snapshot_name,
            "path": str(path),
            "status": "saved"
        }, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)