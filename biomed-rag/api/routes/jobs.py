"""
API routes for PubMed corpus ingestion jobs.

Endpoints:
- POST /jobs/ingest - Create a new ingestion job
- GET /jobs/{job_id} - Get job status
- GET /jobs - List all jobs
- POST /jobs/{job_id}/cancel - Cancel a running job
"""

import asyncio
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from api.schemas.jobs import (
    JobCreateRequest,
    JobCreateResponse,
    JobStatusResponse,
    JobListResponse,
    JobCancelResponse,
)
from jobs.models import Job, JobStatus
from jobs.store import JobStore
from jobs.worker import IngestWorker

logger = logging.getLogger(__name__)

router = APIRouter(tags=["jobs"])

# Initialize job store
job_store = JobStore()


def _job_to_response(job: Job) -> JobStatusResponse:
    """Convert Job model to API response."""
    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        query=job.query,
        total_articles=job.total_articles,
        processed_articles=job.processed_articles,
        entities_extracted=job.entities_extracted,
        current_batch=job.current_batch,
        progress_percentage=job.progress_percentage(),
        processing_mode=job.processing_mode,
        error=job.error,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        updated_at=job.updated_at,
    )


async def _run_job_background(job_id: str):
    """Background task to run a job."""
    try:
        worker = IngestWorker(job_store)
        await worker.run_job(job_id)
    except Exception as e:
        logger.error(f"Background job {job_id} failed: {e}")
        import traceback
        traceback.print_exc()


@router.post("/ingest", response_model=JobCreateResponse)
async def create_ingestion_job(
    request: JobCreateRequest,
    background_tasks: BackgroundTasks,
):
    """
    Create a new PubMed corpus ingestion job.
    
    This endpoint creates a job that will:
    1. Search PubMed using the History Server
    2. Fetch articles in batches
    3. Extract medical entities (NER)
    4. Ingest into Knowledge Graph
    5. Persist to Supabase
    
    The job runs asynchronously in the background. Use GET /jobs/{job_id}
    to check progress.
    
    Args:
        request: Job creation parameters
        background_tasks: FastAPI background tasks
    
    Returns:
        Job ID and initial status
    """
    if not job_store.enabled:
        raise HTTPException(
            status_code=503,
            detail="Job store (Redis) is not available. Cannot create jobs."
        )
    
    # Create job
    job_id = str(uuid.uuid4())
    job = Job(
        job_id=job_id,
        query=request.query,
        mindate=request.mindate,
        maxdate=request.maxdate,
        publication_types=request.publication_types,
        journals=request.journals,
        language=request.language,
        species=request.species,
        batch_size=request.batch_size,
        max_batches=request.max_batches,
        processing_mode=request.processing_mode,
    )
    
    # Save to store
    success = job_store.create(job)
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to create job in store"
        )
    
    # Start job in background
    background_tasks.add_task(_run_job_background, job_id)
    
    logger.info(f"✅ Created job {job_id}: {request.query}")
    
    return JobCreateResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        message=f"Job created successfully. Use GET /jobs/{job_id} to check progress."
    )


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get status of a specific job.
    
    Args:
        job_id: Job identifier
    
    Returns:
        Job status with progress information
    """
    job = job_store.get(job_id)
    
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )
    
    return _job_to_response(job)


@router.get("", response_model=JobListResponse)
async def list_jobs(
    status: Optional[JobStatus] = None,
    limit: int = 50,
):
    """
    List jobs, optionally filtered by status.
    
    Args:
        status: Optional status filter (pending, running, completed, failed, cancelled)
        limit: Maximum number of jobs to return (default 50)
    
    Returns:
        List of jobs with their status
    """
    jobs = job_store.list_jobs(status=status, limit=limit)
    
    return JobListResponse(
        jobs=[_job_to_response(job) for job in jobs],
        total=len(jobs)
    )


@router.post("/{job_id}/cancel", response_model=JobCancelResponse)
async def cancel_job(job_id: str):
    """
    Cancel a running or pending job.
    
    Note: This marks the job as cancelled but does not immediately stop
    the background task. The worker will check the status and stop at
    the next checkpoint.
    
    Args:
        job_id: Job identifier
    
    Returns:
        Cancellation confirmation
    """
    job = job_store.get(job_id)
    
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )
    
    if job.is_terminal():
        raise HTTPException(
            status_code=400,
            detail=f"Job {job_id} is already in terminal state: {job.status}"
        )
    
    # Mark as cancelled
    job.status = JobStatus.CANCELLED
    job_store.update(job)
    
    logger.info(f"🚫 Cancelled job {job_id}")
    
    return JobCancelResponse(
        job_id=job_id,
        status=JobStatus.CANCELLED,
        message="Job cancelled successfully"
    )


@router.post("/{job_id}/resume", response_model=JobCreateResponse)
async def resume_job(
    job_id: str,
    background_tasks: BackgroundTasks,
):
    """
    Resume a failed job from its last checkpoint.
    
    Only works for jobs that failed with a checkpoint available.
    
    Args:
        job_id: Job identifier
        background_tasks: FastAPI background tasks
    
    Returns:
        Resume confirmation
    """
    job = job_store.get(job_id)
    
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )
    
    if not job.can_resume():
        raise HTTPException(
            status_code=400,
            detail=f"Job {job_id} cannot be resumed (status={job.status}, checkpoint available={job.last_retstart > 0})"
        )
    
    # Reset to running
    job.status = JobStatus.RUNNING
    job.error = None
    job.retry_count += 1
    job_store.update(job)
    
    # Start resume in background
    async def _resume_background():
        try:
            worker = IngestWorker(job_store)
            await worker.resume_job(job_id)
        except Exception as e:
            logger.error(f"Resume job {job_id} failed: {e}")
    
    background_tasks.add_task(_resume_background)
    
    logger.info(f"🔄 Resuming job {job_id} from checkpoint")
    
    return JobCreateResponse(
        job_id=job_id,
        status=JobStatus.RUNNING,
        message=f"Job resumed from checkpoint (retstart={job.last_retstart})"
    )
