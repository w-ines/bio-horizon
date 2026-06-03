"""LangChain tool wrapper for PubMed corpus ingestion.

This wrapper allows Deep Agents to create large-scale PubMed ingestion jobs
instead of being limited to 10 articles.
"""

from typing import Optional
from langchain.tools import tool


@tool
def create_corpus_ingestion_job(
    query: str,
    mindate: str = "",
    maxdate: str = "",
    max_batches: Optional[int] = None,
    processing_mode: str = "full"
) -> str:
    """Create a PubMed corpus ingestion job for large-scale analysis.
    
    USE THIS TOOL when the user wants to:
    - Analyze a LARGE corpus (> 100 articles)
    - Extract entities from ALL matching articles
    - Build a comprehensive Knowledge Graph
    - Process the entire PubMed corpus on a topic
    
    DO NOT use pubmed_search for large corpora - it's limited to 10 articles.
    
    Args:
        query: PubMed search query (e.g., "diabetes treatment", "cancer immunotherapy")
        mindate: Minimum publication date (YYYY or YYYY/MM or YYYY/MM/DD)
        maxdate: Maximum publication date (YYYY or YYYY/MM or YYYY/MM/DD)
        max_batches: Optional limit on batches (None = process entire corpus)
                     Each batch = 500 articles (NCBI maximum).
                     RECOMMENDED: max_batches=6-10 for ~3000-5000 articles
                     For testing: max_batches=2 = 1000 articles (~1-2 min)
                     For full corpus: max_batches=None
        processing_mode: Processing speed/depth tradeoff:
                     "full" (DEFAULT, FAST ~1-3 min) = metadata + NER (PubTator3) + Knowledge Graph
                     "metadata_only" (FASTEST ~1-2 min) = store article metadata only, no entities
                     "deferred_ner" = metadata first, NER/KG later
                     USE full by default — PubTator3 pre-computed NER is nearly instant.
    
    Returns:
        JSON string with job ID and status information
    
    Examples:
        - "cancer treatment" → full mode with PubTator3 NER + KG
        - "diabetes treatment" with max_batches=10 → ~5000 articles, ~2-3 min
        - "CRISPR" with processing_mode="metadata_only" → metadata only, no KG
    
    The job runs asynchronously. In your response to the user:
    - Confirm the job was created and give the job_id
    - Tell them estimated processing time from the result
    - Provide the check_url from the result as a plain link, never wrapped in parentheses
    - Tell them they can continue working while it processes
    """
    import json
    import logging
    from core_tools.job_tool import create_ingestion_job
    
    logger = logging.getLogger(__name__)
    
    try:
        result = create_ingestion_job(
            query=query,
            mindate=mindate,
            maxdate=maxdate,
            max_batches=max_batches,
            batch_size=500,  # NCBI maximum to minimize API calls
            processing_mode=processing_mode,
        )
        
        if not result.get("success"):
            return json.dumps({
                "error": result.get("error", "Failed to create job"),
                "message": result.get("message", "")
            }, ensure_ascii=False, indent=2)
        
        check_url = result.get("check_status_url", "http://localhost:3000/jobs")
        logger.info(f"[corpus_ingestion_tool] Generated check_url: {check_url}")
        
        response = {
            "success": True,
            "job_id": result["job_id"],
            "status": result["status"],
            "query": result["query"],
            "estimated_articles": result["estimated_articles"],
            "processing_mode": result.get("processing_mode", "full"),
            "mode_description": result.get("mode_description", ""),
            "check_url": check_url,
            "estimated_time": "~1-2 minutes" if processing_mode != "full" else "~1-3 minutes"
        }
        
        logger.info(f"[corpus_ingestion_tool] Returning response: {json.dumps(response, indent=2)}")
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "message": "Failed to create ingestion job. Make sure Redis is running."
        }, ensure_ascii=False, indent=2)


@tool
def check_ingestion_job_status(job_id: str) -> str:
    """Check the status of a running PubMed corpus ingestion job.
    
    Args:
        job_id: Job identifier (returned by create_corpus_ingestion_job)
    
    Returns:
        JSON string with job progress and statistics
    """
    import json
    import logging
    from core_tools.job_tool import get_job_status
    
    logger = logging.getLogger(__name__)
    
    try:
        result = get_job_status(job_id)
        
        if not result.get("success"):
            return json.dumps({
                "error": result.get("error", "Job not found")
            }, ensure_ascii=False, indent=2)
        
        response = {
            "job_id": result["job_id"],
            "status": result["status"],
            "progress_percentage": result["progress_percentage"],
            "total_articles": result["total_articles"],
            "processed_articles": result["processed_articles"],
            "entities_extracted": result["entities_extracted"],
            "current_batch": result.get("current_batch", 0),
            "error": result.get("error"),
            "check_url": "http://localhost:3000/jobs"
        }
        
        logger.info(f"[check_ingestion_job_status] Job {job_id} status: {result['status']} ({result['progress_percentage']:.1f}%)")
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({
            "error": str(e)
        }, ensure_ascii=False, indent=2)
