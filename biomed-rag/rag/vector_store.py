"""
Vector store utilities for RAG system.
Copied from huggingsmolagent/tools/vector_store.py and adapted for LangChain integration.
"""

from typing import List, Optional, Dict, Any
import hashlib
import time

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
import os

load_dotenv()

# Monkey patch for Supabase v2.23+ compatibility with LangChain
# The issue: LangChain expects query_builder.params.set() but Supabase v2.23+ uses .limit() directly
import langchain_community.vectorstores.supabase as lc_supabase

_original_similarity_search = lc_supabase.SupabaseVectorStore.similarity_search_by_vector_with_relevance_scores

def _patched_similarity_search(self, query, k=4, filter=None, postgrest_filter=None, score_threshold=None, **kwargs):
    """Patched version that uses .limit() instead of .params.set()"""
    # Build the filter if provided
    if filter:
        postgrest_filter = self._build_postgrest_filter(filter)
    
    # Call the RPC function
    match_documents_params = self.match_args(query, filter)
    query_builder = self._client.rpc(self.query_name, match_documents_params)
    
    # Use .limit() instead of .params.set("limit", k)
    query_builder = query_builder.limit(k * 3 if postgrest_filter else k)
    
    res = query_builder.execute()
    
    # Build results
    match_result = [
        (
            Document(
                metadata=search.get("metadata", {}),
                page_content=search.get("content", ""),
            ),
            search.get("similarity", 0.0),
        )
        for search in res.data
        if search.get("content")
    ]
    
    # Apply score threshold if provided
    if score_threshold is not None:
        match_result = [
            (doc, score) for doc, score in match_result if score >= score_threshold
        ]
    
    return match_result[:k]

# Apply the monkey patch
lc_supabase.SupabaseVectorStore.similarity_search_by_vector_with_relevance_scores = _patched_similarity_search


def get_embeddings(*, embedding_model: Optional[str] = None):
    """Get embeddings model (OpenAI or Ollama)."""
    provider = (os.getenv("EMBEDDINGS_PROVIDER") or os.getenv("LLM_PROVIDER") or "openrouter").lower()
    
    if provider in {"openrouter", "openai"}:
        api_key = os.getenv("OPEN_ROUTER_KEY") if provider == "openrouter" else os.getenv("OPENAI_API_KEY")
        api_base = os.getenv("BASE_URL", "https://openrouter.ai/api/v1") if provider == "openrouter" else os.getenv("OPENAI_API_BASE")
        model_name = embedding_model or os.getenv("EMBEDDINGS_MODEL") or "text-embedding-3-small"
        
        if not api_key:
            raise RuntimeError(
                "Embeddings provider requires API key. "
                "Set OPEN_ROUTER_KEY (OpenRouter) or OPENAI_API_KEY (OpenAI)"
            )
        
        return OpenAIEmbeddings(
            model=model_name,
            openai_api_base=api_base,
            openai_api_key=api_key
        )
    
    if provider == "ollama":
        from langchain_community.embeddings import OllamaEmbeddings
        model_name = embedding_model or os.getenv("OLLAMA_EMBEDDINGS_MODEL") or "mxbai-embed-large"
        base_url = os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_HOST")
        
        if not base_url:
            raise RuntimeError(
                "Ollama embeddings require OLLAMA_BASE_URL or OLLAMA_HOST"
            )
        
        return OllamaEmbeddings(model=model_name, base_url=base_url)
    
    raise RuntimeError(
        f"Unsupported embeddings provider '{provider}'. "
        "Set EMBEDDINGS_PROVIDER to: openrouter, openai, or ollama"
    )


def chunk_documents(
    documents: List[Document],
    *,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> List[Document]:
    """
    Split documents into chunks for embedding.
    
    Args:
        documents: List of documents to chunk
        chunk_size: Target chunk size in characters
        chunk_overlap: Overlap between chunks
    
    Returns:
        List of document chunks with metadata
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    chunks = splitter.split_documents(documents)
    
    # Add chunk_index metadata
    numbered: List[Document] = []
    counter_by_doc: Dict[str, int] = {}
    
    for ch in chunks:
        base_id = (ch.metadata or {}).get("doc_id", "")
        idx = counter_by_doc.get(base_id, 0)
        meta = dict(ch.metadata or {})
        meta["chunk_index"] = idx
        numbered.append(Document(page_content=ch.page_content, metadata=meta))
        counter_by_doc[base_id] = idx + 1
    
    return numbered


def sanitize_text(text: str) -> str:
    """Remove problematic characters for Postgres."""
    if text is None:
        return ""
    # Remove NUL bytes
    text = text.replace("\x00", " ").replace("\u0000", " ")
    return text.strip()


def get_vector_store(
    *,
    table_name: str = "documents",
    query_name: str = "match_documents",
    embedding_model: Optional[str] = None
) -> SupabaseVectorStore:
    """
    Get or create Supabase vector store.
    
    Args:
        table_name: Supabase table name
        query_name: RPC function name for similarity search
        embedding_model: Optional embedding model override
    
    Returns:
        SupabaseVectorStore instance
    """
    from storage.supabase_client import get_supabase_client
    
    supabase = get_supabase_client()
    embeddings = get_embeddings(embedding_model=embedding_model)
    
    return SupabaseVectorStore(
        embedding=embeddings,
        client=supabase,
        table_name=table_name,
        query_name=query_name
    )
