"""
Test script for complete pipeline (Phase 3).

This validates the full ingestion pipeline:
1. Search PubMed with History Server
2. Fetch articles in batches
3. Extract entities with NER
4. Ingest into Knowledge Graph
5. Persist to Supabase
"""

import asyncio
import sys
import uuid
from datetime import datetime

from jobs.models import Job, JobStatus
from jobs.store import JobStore
from jobs.worker import IngestWorker
from core_tools.kg_tool import get_graph
from kg import query as kg_query


async def test_complete_pipeline():
    """Test the complete ingestion pipeline."""
    
    print("\n" + "="*80)
    print("COMPLETE PIPELINE TEST")
    print("="*80)
    
    # Initialize store
    store = JobStore()
    
    if not store.enabled:
        print("❌ Redis not available. Cannot test pipeline.")
        print("   Install Redis and run: redis-server")
        return False
    
    # Get initial KG stats
    graph = get_graph()
    initial_stats = kg_query.graph_stats(graph)
    print(f"\n📊 Initial KG stats:")
    print(f"   Nodes: {initial_stats.get('num_nodes', 0)}")
    print(f"   Edges: {initial_stats.get('num_edges', 0)}")
    
    print("\n" + "="*80)
    print("Creating ingestion job (small test)")
    print("="*80)
    
    # Create a small test job
    # Using a very specific query to limit results
    job_id = str(uuid.uuid4())
    job = Job(
        job_id=job_id,
        query="CRISPR gene editing",
        mindate="2024/03",
        maxdate="2024/03",
        batch_size=20,      # Small batch for testing
        max_batches=1,      # Only 1 batch
    )
    
    store.create(job)
    print(f"✅ Created job: {job_id}")
    print(f"   Query: {job.query}")
    print(f"   Date range: {job.mindate} to {job.maxdate}")
    print(f"   Batch size: {job.batch_size}")
    print(f"   Max batches: {job.max_batches}")
    
    print("\n" + "="*80)
    print("Running pipeline...")
    print("="*80)
    
    # Run the job
    worker = IngestWorker(store)
    
    try:
        start_time = datetime.utcnow()
        success = await worker.run_job(job_id)
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Get final job state
        final_job = store.get(job_id)
        
        if not final_job:
            print("❌ Job not found after execution")
            return False
        
        print(f"\n{'✅' if success else '❌'} Job {'completed' if success else 'failed'}")
        print(f"   Status: {final_job.status}")
        print(f"   Duration: {duration:.1f}s")
        
        if final_job.error:
            print(f"   Error: {final_job.error}")
        
        print(f"\n📊 Job statistics:")
        print(f"   Total articles found: {final_job.total_articles:,}")
        print(f"   Articles processed: {final_job.processed_articles}")
        print(f"   Entities extracted: {final_job.entities_extracted}")
        print(f"   Batches completed: {final_job.current_batch}")
        print(f"   Progress: {final_job.progress_percentage():.1f}%")
        
        # Get final KG stats
        final_stats = kg_query.graph_stats(graph)
        print(f"\n📊 Final KG stats:")
        print(f"   Nodes: {final_stats.get('num_nodes', 0)} (+{final_stats.get('num_nodes', 0) - initial_stats.get('num_nodes', 0)})")
        print(f"   Edges: {final_stats.get('num_edges', 0)} (+{final_stats.get('num_edges', 0) - initial_stats.get('num_edges', 0)})")
        
        # Verify entities were actually extracted
        if final_job.entities_extracted == 0:
            print("\n⚠️  WARNING: No entities were extracted!")
            print("   This might indicate an issue with the NER provider.")
        
        print("\n" + "="*80)
        print("PIPELINE VALIDATION")
        print("="*80)
        
        checks = []
        
        # Check 1: Job completed successfully
        checks.append(("Job completed", final_job.status == JobStatus.COMPLETED))
        
        # Check 2: Articles were fetched
        checks.append(("Articles fetched", final_job.processed_articles > 0))
        
        # Check 3: Entities were extracted
        checks.append(("Entities extracted", final_job.entities_extracted > 0))
        
        # Check 4: KG was updated
        kg_updated = final_stats.get('num_nodes', 0) > initial_stats.get('num_nodes', 0)
        checks.append(("KG updated", kg_updated))
        
        # Check 5: Progress tracking works
        checks.append(("Progress tracking", final_job.progress_percentage() > 0))
        
        # Print results
        all_passed = True
        for check_name, passed in checks:
            status = "✅" if passed else "❌"
            print(f"   {status} {check_name}")
            if not passed:
                all_passed = False
        
        if all_passed:
            print("\n🎉 ALL CHECKS PASSED - Pipeline is working correctly!")
            return True
        else:
            print("\n⚠️  SOME CHECKS FAILED - Review the output above")
            return False
    
    except Exception as e:
        print(f"\n❌ Pipeline failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_complete_pipeline())
    sys.exit(0 if success else 1)
