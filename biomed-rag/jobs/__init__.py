"""
Jobs module for async PubMed corpus ingestion.

This module provides:
- Job models and state management
- Job persistence (Redis/Supabase)
- Async workers for batch processing
"""

from jobs.models import Job, JobStatus, JobCreate
from jobs.store import JobStore

__all__ = ["Job", "JobStatus", "JobCreate", "JobStore"]
