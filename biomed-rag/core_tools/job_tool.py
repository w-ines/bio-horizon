"""
Job creation tool for Deep Agent.

Allows the agent to create PubMed corpus ingestion jobs instead of using
the limited pubmed_search tool.
"""

import uuid
import logging
from typing import Optional, List, Dict, Any

from jobs.models import Job, JobStatus
from jobs.store import JobStore
from jobs.worker import IngestWorker
import asyncio

logger = logging.getLogger(__name__)


def create_ingestion_job(
    query: str,
    mindate: str = "",
    maxdate: str = "",
    publication_types: Optional[List[str]] = None,
    journals: Optional[List[str]] = None,
    language: Optional[str] = None,
    species: Optional[List[str]] = None,
    batch_size: int = 200,
    max_batches: Optional[int] = None,
    processing_mode: str = "full",
) -> Dict[str, Any]:
    """
    Create a PubMed corpus ingestion job for large-scale analysis.
    
    This tool should be used instead of pubmed_search when the user wants to:
    - Analyze a large corpus (> 100 articles)
    - Extract entities from all matching articles
    - Build a comprehensive Knowledge Graph
    
    The job runs asynchronously in the background and can process
    hundreds of thousands of articles.
    
    Args:
        query: PubMed search query
        mindate: Minimum publication date (YYYY or YYYY/MM or YYYY/MM/DD)
        maxdate: Maximum publication date
        publication_types: Filter by publication types
        journals: Filter by journal names
        language: Language filter (e.g., "eng")
        species: Species filter (e.g., ["Humans"])
        batch_size: Articles per batch (default 200)
        max_batches: Optional limit on number of batches (None = unlimited)
        processing_mode: "full" (NER+KG, slow), "metadata_only" (fast, ~5x faster),
                         or "deferred_ner" (metadata first, NER later)
    
    Returns:
        dict: {
            "job_id": str,
            "status": str,
            "message": str,
            "estimated_articles": int,
            "check_status_url": str
        }
    
    Example:
        >>> result = create_ingestion_job(
        ...     query="diabetes treatment",
        ...     mindate="2023",
        ...     max_batches=10  # Limit to 2000 articles for testing
        ... )
        >>> print(f"Job created: {result['job_id']}")
        >>> print(f"Check status at: {result['check_status_url']}")
    """
    # Initialize job store
    job_store = JobStore()
    
    if not job_store.enabled:
        return {
            "success": False,
            "error": "Job system not available (Redis required)",
            "message": "Please install and start Redis to use the job system"
        }
    
    # Create job
    job_id = str(uuid.uuid4())
    job = Job(
        job_id=job_id,
        query=query,
        mindate=mindate,
        maxdate=maxdate,
        publication_types=publication_types,
        journals=journals,
        language=language,
        species=species,
        batch_size=batch_size,
        max_batches=max_batches,
        processing_mode=processing_mode,
    )
    
    # Save to store
    success = job_store.create(job)
    if not success:
        return {
            "success": False,
            "error": "Failed to create job in store",
            "message": "Could not persist job to Redis"
        }
    
    # Start job in background (fire and forget)
    async def _run_job():
        try:
            worker = IngestWorker(job_store)
            await worker.run_job(job_id)
        except Exception as e:
            logger.error(f"Background job {job_id} failed: {e}")
    
    # Run in background without blocking
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(_run_job())
    except RuntimeError:
        # No event loop, create a new one
        import threading
        def _run_in_thread():
            asyncio.run(_run_job())
        thread = threading.Thread(target=_run_in_thread, daemon=True)
        thread.start()
    
    logger.info(f"✅ Created ingestion job {job_id}: {query}")
    
    # Estimate articles (will be updated once search completes)
    estimated_articles = "Unknown (will be determined after search)"
    if max_batches:
        estimated_articles = f"Up to {max_batches * batch_size:,}"
    
    mode_info = {
        "full": "Full processing (NER via PubTator3 + Knowledge Graph) — fast, ~1-3 min",
        "metadata_only": "Metadata only — fastest, no NER/KG",
        "deferred_ner": "Metadata first, NER/KG later — fast initial ingestion",
    }
    
    return {
        "success": True,
        "job_id": job_id,
        "status": "pending",
        "processing_mode": processing_mode,
        "mode_description": mode_info.get(processing_mode, processing_mode),
        "message": f"Job created successfully. Mode: {processing_mode}.",
        "query": query,
        "estimated_articles": estimated_articles,
        "batch_size": batch_size,
        "max_batches": max_batches or "unlimited",
        "check_status_url": "http://localhost:3000/jobs",
        "job_id_short": f"{job_id[:8]}...",
        "note": "This job runs asynchronously. You can check its progress in the Jobs UI or continue with other tasks."
    }


def get_job_status(job_id: str) -> Dict[str, Any]:
    """
    Get the status of a running ingestion job.
    
    Args:
        job_id: Job identifier
    
    Returns:
        dict: Job status with progress information
    """
    job_store = JobStore()
    
    if not job_store.enabled:
        return {
            "success": False,
            "error": "Job system not available"
        }
    
    job = job_store.get(job_id)
    
    if not job:
        return {
            "success": False,
            "error": f"Job {job_id} not found"
        }
    
    return {
        "success": True,
        "job_id": job.job_id,
        "status": job.status,
        "query": job.query,
        "progress_percentage": job.progress_percentage(),
        "total_articles": job.total_articles,
        "processed_articles": job.processed_articles,
        "entities_extracted": job.entities_extracted,
        "current_batch": job.current_batch,
        "error": job.error,
        "created_at": job.created_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }
