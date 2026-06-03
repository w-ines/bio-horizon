"""
RAG (Retrieval-Augmented Generation) module with Knowledge Graph integration.

This module provides a LangChain-based RAG system that enriches vector search
with Knowledge Graph entity relationships for better medical question answering.
"""

from rag.retriever import KGEnhancedRetriever, get_retriever
from rag.chain import create_rag_chain, query_rag
from rag.vector_store import get_vector_store, get_embeddings, chunk_documents

__all__ = [
    # Retriever
    "KGEnhancedRetriever",
    "get_retriever",
    
    # Chain
    "create_rag_chain",
    "query_rag",
    
    # Vector store
    "get_vector_store",
    "get_embeddings",
    "chunk_documents",
]
