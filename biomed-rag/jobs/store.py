"""
Job persistence layer for async PubMed corpus ingestion.

Stores job state in Redis (primary) with Supabase fallback.
"""

import json
import logging
from typing import Optional, List
from datetime import datetime

from jobs.models import Job, JobStatus

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class JobStore:
    """
    Job persistence using Redis.
    
    Jobs are stored as JSON in Redis with TTL for automatic cleanup.
    Completed jobs are kept for 7 days, failed jobs for 30 days.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """
        Initialize job store.
        
        Args:
            redis_url: Redis connection URL
        """
        self.redis_client = None
        self.enabled = False
        
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available. Job persistence disabled. Install with: pip install redis")
            return
        
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
            self.enabled = True
            logger.info("✅ Job store (Redis) enabled")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}. Job persistence disabled.")
            self.enabled = False
    
    def _make_key(self, job_id: str) -> str:
        """Generate Redis key for job."""
        return f"job:{job_id}"
    
    def _get_ttl(self, status: JobStatus) -> int:
        """Get TTL based on job status."""
        if status == JobStatus.COMPLETED:
            return 7 * 24 * 3600  # 7 days
        elif status == JobStatus.FAILED:
            return 30 * 24 * 3600  # 30 days
        elif status == JobStatus.CANCELLED:
            return 3 * 24 * 3600  # 3 days
        else:
            return 24 * 3600  # 1 day for running/pending
    
    def create(self, job: Job) -> bool:
        """
        Create a new job.
        
        Args:
            job: Job instance to create
        
        Returns:
            True if created successfully
        """
        if not self.enabled:
            logger.warning("Job store disabled, cannot create job")
            return False
        
        try:
            key = self._make_key(job.job_id)
            data = json.dumps(job.to_dict())
            ttl = self._get_ttl(job.status)
            
            self.redis_client.setex(key, ttl, data)
            logger.info(f"✅ Created job {job.job_id} (TTL={ttl}s)")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to create job {job.job_id}: {e}")
            return False
    
    def get(self, job_id: str) -> Optional[Job]:
        """
        Get job by ID.
        
        Args:
            job_id: Job identifier
        
        Returns:
            Job instance or None if not found
        """
        if not self.enabled:
            return None
        
        try:
            key = self._make_key(job_id)
            data = self.redis_client.get(key)
            
            if not data:
                return None
            
            job_dict = json.loads(data)
            return Job.from_dict(job_dict)
        except Exception as e:
            logger.error(f"❌ Failed to get job {job_id}: {e}")
            return None
    
    def update(self, job: Job) -> bool:
        """
        Update existing job.
        
        Args:
            job: Job instance with updated data
        
        Returns:
            True if updated successfully
        """
        if not self.enabled:
            return False
        
        try:
            # Update timestamp
            job.updated_at = datetime.utcnow()
            
            key = self._make_key(job.job_id)
            data = json.dumps(job.to_dict())
            ttl = self._get_ttl(job.status)
            
            self.redis_client.setex(key, ttl, data)
            return True
        except Exception as e:
            logger.error(f"❌ Failed to update job {job.job_id}: {e}")
            return False
    
    def delete(self, job_id: str) -> bool:
        """
        Delete job.
        
        Args:
            job_id: Job identifier
        
        Returns:
            True if deleted successfully
        """
        if not self.enabled:
            return False
        
        try:
            key = self._make_key(job_id)
            self.redis_client.delete(key)
            logger.info(f"🗑️  Deleted job {job_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to delete job {job_id}: {e}")
            return False
    
    def list_jobs(self, status: Optional[JobStatus] = None, limit: int = 100) -> List[Job]:
        """
        List jobs, optionally filtered by status.
        
        Args:
            status: Optional status filter
            limit: Maximum number of jobs to return
        
        Returns:
            List of Job instances
        """
        if not self.enabled:
            return []
        
        try:
            # Scan for all job keys
            jobs = []
            for key in self.redis_client.scan_iter(match="job:*", count=limit):
                data = self.redis_client.get(key)
                if data:
                    job_dict = json.loads(data)
                    job = Job.from_dict(job_dict)
                    
                    if status is None or job.status == status:
                        jobs.append(job)
                    
                    if len(jobs) >= limit:
                        break
            
            # Sort by created_at descending
            jobs.sort(key=lambda j: j.created_at, reverse=True)
            return jobs
        except Exception as e:
            logger.error(f"❌ Failed to list jobs: {e}")
            return []
    
    def cleanup_old_jobs(self) -> int:
        """
        Cleanup jobs that have exceeded their TTL.
        
        Note: Redis handles TTL automatically, but this can be used
        to manually cleanup if needed.
        
        Returns:
            Number of jobs cleaned up
        """
        # Redis handles TTL automatically, so this is a no-op
        # Could be extended to cleanup Supabase if we add that
        return 0
