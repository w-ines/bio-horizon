"""
RAG tool for Deep Agents - migrated from huggingsmolagent/tools/vector_store.py
Uses the existing biomed-rag/rag/ module for RAG+KG functionality.
"""

from typing import Dict, Any, Optional
from langchain.tools import tool
from rag import query_rag


@tool
def retrieve_knowledge(
    query: str,
    top_k: int = 5,
    doc_id: Optional[str] = None,
    enable_kg_enrichment: bool = True
) -> Dict[str, Any]:
    """
    Retrieve relevant information from indexed documents using RAG with Knowledge Graph enrichment.
    
    This tool searches through uploaded documents using semantic similarity and enriches
    results with Knowledge Graph relationships for better medical context.
    
    Args:
        query: The search query or question
        top_k: Number of relevant chunks to retrieve (default: 5)
        doc_id: Optional document ID to search within a specific document
        enable_kg_enrichment: Enable Knowledge Graph enrichment (default: True)
        
    Returns:
        dict: Retrieved information with context, sources, and KG relationships
        
    Examples:
        >>> retrieve_knowledge("What are the side effects of aspirin?", top_k=5)
        >>> retrieve_knowledge("diabetes treatment", doc_id="doc_123", enable_kg_enrichment=True)
    """
    try:
        # Use the existing RAG system from biomed-rag/rag/
        from rag.retriever import get_retriever
        from rag.vector_store import get_vector_store
        
        # Get retriever with KG enrichment
        retriever = get_retriever(
            top_k=top_k,
            enable_kg_enrichment=enable_kg_enrichment
        )
        
        # Retrieve documents using invoke() method (LangChain BaseRetriever interface)
        docs = retriever.invoke(query)
        
        # Format results
        results = []
        sources = []
        context_parts = []
        
        for idx, doc in enumerate(docs, 1):
            metadata = doc.metadata or {}
            
            # Extract relevant metadata
            result = {
                "content": doc.page_content,
                "metadata": metadata,
                "score": metadata.get("hybrid_score", metadata.get("score", 0.0)),
                "kg_score": metadata.get("kg_score", 0.0),
                "doc_entities": metadata.get("doc_entities", []),
            }
            results.append(result)
            
            # Build sources list
            source_info = {
                "id": metadata.get("doc_id", f"chunk-{idx}"),
                "filename": metadata.get("filename", "Unknown"),
                "chunk_index": metadata.get("chunk_index", 0),
            }
            sources.append(source_info)
            
            # Build context for LLM
            source_label = f"[Source {idx}: {source_info['filename']}]"
            context_parts.append(f"{source_label}\n{doc.page_content}\n")
            
            # Add KG context if available
            kg_entities = metadata.get("kg_entities", [])
            if kg_entities:
                entity_names = [e.get("label", "") for e in kg_entities[:3]]
                context_parts.append(f"Related entities: {', '.join(entity_names)}\n")
        
        # Combine context
        context = "\n---\n".join(context_parts)
        
        return {
            "context": context,
            "results": results,
            "sources": sources,
            "total_results": len(results),
            "kg_enriched": enable_kg_enrichment,
        }
        
    except Exception as e:
        return {
            "error": f"Failed to retrieve knowledge: {str(e)}",
            "context": "",
            "results": [],
            "sources": [],
        }


@tool
def search_documents(
    query: str,
    filters: Optional[Dict[str, Any]] = None,
    top_k: int = 10
) -> Dict[str, Any]:
    """
    Search documents with optional filters (filename, date range, etc.).
    
    Args:
        query: Search query
        filters: Optional filters (e.g., {"filename": "report.pdf", "date_after": "2024-01-01"})
        top_k: Number of results
        
    Returns:
        dict: Search results with metadata
    """
    # TODO: Implement filtered search
    # For now, delegate to retrieve_knowledge
    return retrieve_knowledge(query=query, top_k=top_k, enable_kg_enrichment=False)
