"""
Vector store utilities for document indexing — migrated from huggingsmolagent/tools/vector_store.py.
Uses rag/vector_store.py for core functions (embeddings, chunking, store).
"""

import hashlib
from typing import List, Optional, Dict, Any

from langchain_core.documents import Document


def compute_file_hash(content: bytes) -> str:
    """Compute SHA256 hash of file content for deduplication."""
    return hashlib.sha256(content).hexdigest()


def check_existing_document(file_hash: str, table_name: str = "documents") -> Optional[Dict[str, Any]]:
    """
    Check if a document with the given file hash already exists in the database.

    Returns:
        Dict with doc_id and chunk count if exists, None otherwise.
    """
    try:
        from storage.supabase_client import get_supabase_client
        supabase = get_supabase_client()
    except Exception as e:
        print(f"[check_existing_document] ⚠️  Supabase not available: {e}")
        return None

    try:
        response = supabase.table(table_name).select("metadata").eq(
            "metadata->>file_hash", file_hash
        ).limit(1).execute()

        if response.data and len(response.data) > 0:
            metadata = response.data[0].get("metadata", {})
            doc_id = metadata.get("doc_id")

            if doc_id:
                count_response = supabase.table(table_name).select(
                    "id", count="exact"
                ).eq("metadata->>doc_id", doc_id).execute()

                return {
                    "doc_id": doc_id,
                    "chunk_count": count_response.count or 0,
                    "filename": metadata.get("filename"),
                    "source": metadata.get("source"),
                }

        return None
    except Exception as e:
        print(f"[check_existing_document] Error: {e}")
        return None


def index_documents(
    documents: List[Document],
    *,
    base_metadata: Optional[Dict[str, Any]] = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    table_name: str = "documents",
    query_name: str = "match_documents",
    embedding_model: Optional[str] = None,
) -> int:
    """
    Index documents by chunking and storing embeddings in Supabase.

    Args:
        documents: List of LangChain Documents to index.
        base_metadata: Metadata to attach to all chunks.
        chunk_size: Target chunk size in characters.
        chunk_overlap: Overlap between chunks.
        table_name: Supabase table name.
        query_name: RPC function name.
        embedding_model: Optional embedding model override.

    Returns:
        Number of chunks stored.
    """
    from rag.vector_store import chunk_documents, get_vector_store, sanitize_text

    base_metadata = base_metadata or {}

    # Attach base metadata to each page-level document
    enriched_docs: List[Document] = []
    for doc in documents:
        md = dict(base_metadata)
        md.update(doc.metadata or {})
        enriched_docs.append(Document(page_content=doc.page_content, metadata=md))

    # Chunk
    chunks = chunk_documents(enriched_docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    if not chunks:
        print("[index_documents] No chunks to store")
        return 0

    # Sanitize text
    sanitized: List[Document] = []
    for ch in chunks:
        clean_text = sanitize_text(ch.page_content)
        if clean_text:
            sanitized.append(Document(page_content=clean_text, metadata=ch.metadata))

    if not sanitized:
        print("[index_documents] All chunks were empty after sanitization")
        return 0

    # Store embeddings
    try:
        vs = get_vector_store(
            table_name=table_name,
            query_name=query_name,
            embedding_model=embedding_model,
        )
        vs.add_documents(sanitized)
        stored = len(sanitized)
        print(f"[index_documents] ✅ Stored {stored} chunks in vector store")
        return stored
    except Exception as e:
        print(f"[index_documents] ❌ Error storing embeddings: {e}")
        import traceback
        traceback.print_exc()
        return 0
