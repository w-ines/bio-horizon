"""
Pydantic schemas for Jobs API endpoints.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from jobs.models import JobStatus


class JobCreateRequest(BaseModel):
    """Request schema for creating a new ingestion job."""
    query: str = Field(..., description="PubMed search query", min_length=1)
    mindate: str = Field("", description="Minimum publication date (YYYY/MM/DD)")
    maxdate: str = Field("", description="Maximum publication date (YYYY/MM/DD)")
    publication_types: Optional[List[str]] = Field(None, description="Filter by publication types")
    journals: Optional[List[str]] = Field(None, description="Filter by journals")
    language: Optional[str] = Field(None, description="Language filter (e.g., 'eng')")
    species: Optional[List[str]] = Field(None, description="Species filter (e.g., ['Humans'])")
    batch_size: int = Field(200, description="Articles per batch", ge=10, le=500)
    max_batches: Optional[int] = Field(None, description="Optional limit on number of batches")
    processing_mode: str = Field("full", description="Processing mode: full, metadata_only, or deferred_ner")


class JobCreateResponse(BaseModel):
    """Response schema for job creation."""
    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Initial job status (pending)")
    message: str = Field(..., description="Success message")


class JobStatusResponse(BaseModel):
    """Response schema for job status."""
    job_id: str
    status: JobStatus
    query: str
    total_articles: int
    processed_articles: int
    entities_extracted: int
    current_batch: int
    progress_percentage: float
    processing_mode: str = "full"
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime


class JobListResponse(BaseModel):
    """Response schema for listing jobs."""
    jobs: List[JobStatusResponse]
    total: int


class JobCancelResponse(BaseModel):
    """Response schema for job cancellation."""
    job_id: str
    status: JobStatus
    message: str
