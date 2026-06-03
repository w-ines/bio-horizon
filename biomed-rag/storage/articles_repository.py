"""
Articles persistence layer using Supabase.

Stores raw PubMed article metadata for fast ingestion (metadata_only mode).
NER/KG processing can be deferred to a separate job.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from storage.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def upsert_articles_batch(
    articles: List[Dict[str, Any]],
    job_id: str,
    *,
    table: str = "pubmed_articles",
    chunk_size: int = 500,
) -> int:
    """
    Store raw PubMed article metadata in Supabase.
    
    Args:
        articles: List of article dicts from PubMed (pmid, title, abstract, etc.)
        job_id: Job ID that ingested this batch
        table: Supabase table name
        chunk_size: Insert chunk size to avoid timeout
    
    Returns:
        Number of articles stored
    """
    if not articles:
        return 0

    client = get_supabase_client()

    payloads = []
    for art in articles:
        pmid = art.get("pmid") or ""
        payloads.append({
            "pmid": pmid,
            "title": art.get("title") or "",
            "abstract": art.get("abstract") or "",
            "journal": art.get("journal") or "",
            "pub_date": art.get("pub_date") or "",
            "authors": art.get("authors") or [],
            "mesh_terms": art.get("mesh_terms") or [],
            "pmc_id": art.get("pmc_id") or "",
            "doi": art.get("doi") or "",
            "pubmed_url": art.get("pubmed_url") or (f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""),
            "pdf_url": art.get("pdf_url") or "",
            "job_id": job_id,
        })

    total_chunks = (len(payloads) + chunk_size - 1) // chunk_size
    logger.info(f"💾 Storing {len(payloads)} articles in {total_chunks} chunks")

    stored = 0
    for i in range(0, len(payloads), chunk_size):
        chunk = payloads[i : i + chunk_size]
        client.table(table).upsert(chunk, on_conflict="pmid").execute()
        stored += len(chunk)

    return stored


def fetch_articles_by_pmids(
    pmids: List[str],
    *,
    table: str = "pubmed_articles",
) -> List[Dict[str, Any]]:
    """
    Fetch articles from Supabase by a list of PMIDs.
    
    Args:
        pmids: List of PubMed IDs to fetch
        table: Supabase table name
    
    Returns:
        List of article dicts
    """
    if not pmids:
        return []

    client = get_supabase_client()

    # Supabase IN filter has a practical limit; chunk if needed
    all_rows: List[Dict[str, Any]] = []
    chunk_size = 100
    for i in range(0, len(pmids), chunk_size):
        chunk = pmids[i : i + chunk_size]
        res = (
            client.table(table)
            .select("pmid, title, journal, pub_date, authors, pmc_id, doi, pubmed_url, pdf_url")
            .in_("pmid", chunk)
            .execute()
        )
        all_rows.extend(getattr(res, "data", None) or [])

    return all_rows
