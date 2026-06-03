"""LangChain tool to search ingested PubMed articles.

Allows the agent to query the pubmed_articles table after a metadata_only
ingestion job, providing fast access to thousands of articles without
waiting for NER/KG processing.
"""

from typing import Optional
from langchain.tools import tool


@tool
def search_ingested_articles(
    query: str,
    job_id: Optional[str] = None,
    limit: int = 20,
) -> str:
    """Search through previously ingested PubMed articles stored in the database.

    Use this tool AFTER an ingestion job has completed to explore and analyze
    the ingested corpus. This searches titles, abstracts, and MeSH terms.

    Args:
        query: Search keywords (e.g., "immunotherapy checkpoint inhibitor")
        job_id: Optional job ID to restrict search to a specific ingestion job
        limit: Maximum number of articles to return (default 20, max 50)

    Returns:
        JSON string with matching articles (pmid, title, abstract, journal, date, authors, mesh_terms)
    """
    import json
    import logging

    logger = logging.getLogger(__name__)

    try:
        from storage.supabase_client import get_supabase_client
        client = get_supabase_client()

        limit = min(limit, 50)

        # Build query — use ilike for simple keyword search on title + abstract
        keywords = [kw.strip() for kw in query.split() if len(kw.strip()) > 2]

        q = client.table("pubmed_articles").select(
            "pmid, title, abstract, journal, pub_date, authors, mesh_terms"
        )

        if job_id:
            q = q.eq("job_id", job_id)

        # Apply keyword filters (AND logic: all keywords must appear in title OR abstract)
        for kw in keywords[:5]:  # Limit to 5 keywords to avoid overly complex queries
            q = q.or_(f"title.ilike.%{kw}%,abstract.ilike.%{kw}%")

        result = q.limit(limit).execute()
        articles = result.data if result.data else []

        if not articles:
            return json.dumps({
                "success": True,
                "count": 0,
                "message": f"No articles found matching '{query}'" + (f" for job {job_id}" if job_id else ""),
                "articles": [],
            }, ensure_ascii=False, indent=2)

        # Truncate abstracts for readability
        for art in articles:
            if art.get("abstract") and len(art["abstract"]) > 500:
                art["abstract"] = art["abstract"][:500] + "..."

        # Build a readable summary
        summary_lines = []
        for i, art in enumerate(articles, 1):
            mesh = ", ".join(art.get("mesh_terms", [])[:5]) if art.get("mesh_terms") else "N/A"
            summary_lines.append(
                f"{i}. **[PMID:{art['pmid']}]** {art['title']}\n"
                f"   Journal: {art.get('journal', 'N/A')} | Date: {art.get('pub_date', 'N/A')}\n"
                f"   MeSH: {mesh}\n"
                f"   Abstract: {art['abstract'][:300]}..."
            )

        return json.dumps({
            "success": True,
            "count": len(articles),
            "query": query,
            "message": f"Found {len(articles)} articles matching '{query}'",
            "summary": "\n\n".join(summary_lines),
            "articles": articles,
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"search_ingested_articles error: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "Failed to search articles. Make sure the pubmed_articles table exists in Supabase.",
        }, ensure_ascii=False, indent=2)
