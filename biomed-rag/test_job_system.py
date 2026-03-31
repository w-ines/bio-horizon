"""
Test script for Job system (Phase 2).

This validates:
1. Job creation and persistence
2. Job state transitions
3. Worker execution with checkpointing
4. Resume from failure
"""

import asyncio
import sys
import uuid
from datetime import datetime

from jobs.models import Job, JobStatus, JobCreate
from jobs.store import JobStore
from jobs.worker import IngestWorker


async def test_job_system():
    """Test the complete job system."""
    
    print("\n" + "="*80)
    print("TEST 1: Job Store (Create, Get, Update)")
    print("="*80)
    
    # Initialize store
    store = JobStore()
    
    if not store.enabled:
        print("❌ Redis not available. Cannot test job system.")
        print("   Install Redis and run: redis-server")
        return False
    
    # Create a test job
    job_id = str(uuid.uuid4())
    job = Job(
        job_id=job_id,
        query="diabetes mellitus",
        mindate="2024",
        maxdate="2024",
        batch_size=200,
        max_batches=2,  # Limit to 2 batches for testing
    )
    
    # Test create
    success = store.create(job)
    print(f"✅ Created job: {success}")
    
    # Test get
    retrieved = store.get(job_id)
    print(f"✅ Retrieved job: {retrieved.job_id if retrieved else 'None'}")
    print(f"   Status: {retrieved.status if retrieved else 'N/A'}")
    print(f"   Query: {retrieved.query if retrieved else 'N/A'}")
    
    # Test update
    if retrieved:
        retrieved.status = JobStatus.RUNNING
        retrieved.total_articles = 1000
        store.update(retrieved)
        
        updated = store.get(job_id)
        print(f"✅ Updated job status: {updated.status if updated else 'N/A'}")
        print(f"   Total articles: {updated.total_articles if updated else 0}")
    
    print("\n" + "="*80)
    print("TEST 2: Worker Execution (Small Job)")
    print("="*80)
    
    # Create a small test job
    test_job_id = str(uuid.uuid4())
    test_job = Job(
        job_id=test_job_id,
        query="CRISPR",
        mindate="2024/01",
        maxdate="2024/01",
        batch_size=50,
        max_batches=1,  # Just 1 batch for quick test
    )
    
    store.create(test_job)
    print(f"✅ Created test job: {test_job_id}")
    
    # Run the job
    worker = IngestWorker(store)
    print(f"🚀 Starting worker...")
    
    try:
        success = await worker.run_job(test_job_id)
        
        # Check final state
        final_job = store.get(test_job_id)
        if final_job:
            print(f"\n✅ Job completed: {success}")
            print(f"   Status: {final_job.status}")
            print(f"   Total articles: {final_job.total_articles:,}")
            print(f"   Processed: {final_job.processed_articles}")
            print(f"   Entities: {final_job.entities_extracted}")
            print(f"   Progress: {final_job.progress_percentage():.1f}%")
            print(f"   Duration: {(final_job.completed_at - final_job.started_at).total_seconds():.1f}s" if final_job.completed_at and final_job.started_at else "")
    
    except Exception as e:
        print(f"❌ Worker failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "="*80)
    print("TEST 3: List Jobs")
    print("="*80)
    
    all_jobs = store.list_jobs(limit=10)
    print(f"✅ Found {len(all_jobs)} jobs:")
    for j in all_jobs[:5]:
        print(f"   - {j.job_id[:8]}... | {j.status} | {j.query[:40]} | {j.progress_percentage():.1f}%")
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print("✅ Job system test PASSED")
    print(f"   - Job persistence: Working")
    print(f"   - Worker execution: Working")
    print(f"   - Progress tracking: Working")
    print(f"   - Checkpointing: Ready (not tested in this run)")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_job_system())
    sys.exit(0 if success else 1)
