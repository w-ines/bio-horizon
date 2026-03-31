"""
Job models for async PubMed corpus ingestion.

Defines the Job data model with states, metadata, and checkpointing.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProcessingMode(str, Enum):
    """Job processing mode.
    
    - full: Fetch + NER + KG ingestion (slow, complete)
    - metadata_only: Fetch + store metadata only (fast, no NER/KG)
    - deferred_ner: Fetch + store metadata, NER/KG runs later as separate job
    """
    FULL = "full"
    METADATA_ONLY = "metadata_only"
    DEFERRED_NER = "deferred_ner"


class JobCreate(BaseModel):
    """Request model for creating a new job."""
    query: str = Field(..., description="PubMed search query")
    mindate: str = Field("", description="Minimum publication date (YYYY/MM/DD)")
    maxdate: str = Field("", description="Maximum publication date")
    publication_types: Optional[list[str]] = Field(None, description="Filter by publication types")
    journals: Optional[list[str]] = Field(None, description="Filter by journals")
    language: Optional[str] = Field(None, description="Language filter (e.g., 'eng')")
    species: Optional[list[str]] = Field(None, description="Species filter (e.g., ['Humans'])")
    batch_size: int = Field(200, description="Articles per batch", ge=1, le=500)
    max_batches: Optional[int] = Field(None, description="Optional limit on number of batches")
    processing_mode: str = Field("full", description="Processing mode: full, metadata_only, or deferred_ner")


class Job(BaseModel):
    """
    Job model for PubMed corpus ingestion.
    
    Tracks the state of a long-running ingestion job with checkpointing
    for fault tolerance.
    """
    job_id: str = Field(..., description="Unique job identifier (UUID)")
    status: JobStatus = Field(JobStatus.PENDING, description="Current job status")
    
    # Search parameters
    query: str = Field(..., description="PubMed search query")
    mindate: str = Field("", description="Minimum publication date")
    maxdate: str = Field("", description="Maximum publication date")
    publication_types: Optional[list[str]] = Field(None, description="Publication type filters")
    journals: Optional[list[str]] = Field(None, description="Journal filters")
    language: Optional[str] = Field(None, description="Language filter")
    species: Optional[list[str]] = Field(None, description="Species filter")
    
    # NCBI History Server tokens
    web_env: Optional[str] = Field(None, description="NCBI WebEnv token")
    query_key: Optional[str] = Field(None, description="NCBI QueryKey")
    
    # Progress tracking
    total_articles: int = Field(0, description="Total articles found in PubMed")
    processed_articles: int = Field(0, description="Number of articles processed")
    entities_extracted: int = Field(0, description="Total entities extracted")
    current_batch: int = Field(0, description="Current batch index")
    batch_size: int = Field(200, description="Articles per batch")
    max_batches: Optional[int] = Field(None, description="Optional batch limit")
    processing_mode: str = Field("full", description="Processing mode: full, metadata_only, deferred_ner")
    
    # Checkpointing
    last_retstart: int = Field(0, description="Last successful retstart position")
    
    # Error handling
    error: Optional[str] = Field(None, description="Error message if failed")
    retry_count: int = Field(0, description="Number of retries attempted")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Job creation time")
    started_at: Optional[datetime] = Field(None, description="Job start time")
    completed_at: Optional[datetime] = Field(None, description="Job completion time")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update time")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return self.model_dump(mode='json')
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Job":
        """Create Job from dictionary."""
        # Convert ISO strings back to datetime
        for field in ['created_at', 'started_at', 'completed_at', 'updated_at']:
            if field in data and data[field] and isinstance(data[field], str):
                data[field] = datetime.fromisoformat(data[field])
        return cls(**data)
    
    def progress_percentage(self) -> float:
        """Calculate progress percentage."""
        if self.total_articles == 0:
            return 0.0
        return (self.processed_articles / self.total_articles) * 100
    
    def is_terminal(self) -> bool:
        """Check if job is in a terminal state."""
        return self.status in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}
    
    def can_resume(self) -> bool:
        """Check if job can be resumed from checkpoint."""
        return (
            self.status == JobStatus.FAILED 
            and self.web_env is not None 
            and self.query_key is not None
            and self.last_retstart < self.total_articles
        )
