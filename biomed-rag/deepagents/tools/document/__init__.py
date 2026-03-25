"""
Document processing tools — migrated from huggingsmolagent/tools/.
Provides PDF storage, parsing, indexing, summarization, and caching.
"""

from deepagents.tools.document.store_pdf import store_pdf
from deepagents.tools.document.pdf_loader import parse_pdf
from deepagents.tools.document.vector_store import (
    index_documents,
    compute_file_hash,
    check_existing_document,
)
from deepagents.tools.document.summarizer import summarize
from deepagents.tools.document.query_cache import get_cache_stats, clear_cache

__all__ = [
    "store_pdf",
    "parse_pdf",
    "index_documents",
    "compute_file_hash",
    "check_existing_document",
    "summarize",
    "get_cache_stats",
    "clear_cache",
]
