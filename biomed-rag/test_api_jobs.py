"""
Test script for Jobs API endpoints (Phase 5).

This validates:
1. POST /jobs/ingest - Create job
2. GET /jobs/{job_id} - Get status
3. GET /jobs - List jobs
4. POST /jobs/{job_id}/cancel - Cancel job
"""

import requests
import time
import sys

BASE_URL = "http://localhost:8000"


def test_jobs_api():
    """Test the Jobs API endpoints."""
    
    print("\n" + "="*80)
    print("JOBS API TEST")
    print("="*80)
    
    # Test 1: Create a job
    print("\n" + "="*80)
    print("TEST 1: Create ingestion job")
    print("="*80)
    
    create_payload = {
        "query": "CRISPR gene editing",
        "mindate": "2024/03",
        "maxdate": "2024/03",
        "batch_size": 50,
        "max_batches": 1
    }
    
    try:
        response = requests.post(f"{BASE_URL}/jobs/ingest", json=create_payload)
        response.raise_for_status()
        create_result = response.json()
        
        job_id = create_result["job_id"]
        print(f"✅ Job created: {job_id}")
        print(f"   Status: {create_result['status']}")
        print(f"   Message: {create_result['message']}")
    except Exception as e:
        print(f"❌ Failed to create job: {e}")
        return False
    
    # Test 2: Get job status
    print("\n" + "="*80)
    print("TEST 2: Get job status (polling)")
    print("="*80)
    
    max_polls = 30
    poll_interval = 2
    
    for i in range(max_polls):
        try:
            response = requests.get(f"{BASE_URL}/jobs/{job_id}")
            response.raise_for_status()
            status_result = response.json()
            
            status = status_result["status"]
            progress = status_result["progress_percentage"]
            processed = status_result["processed_articles"]
            total = status_result["total_articles"]
            entities = status_result["entities_extracted"]
            
            print(f"Poll {i+1}/{max_polls}: {status} | {progress:.1f}% | {processed}/{total} articles | {entities} entities")
            
            if status in ["completed", "failed", "cancelled"]:
                print(f"\n✅ Job finished with status: {status}")
                if status_result.get("error"):
                    print(f"   Error: {status_result['error']}")
                break
            
            time.sleep(poll_interval)
        except Exception as e:
            print(f"❌ Failed to get status: {e}")
            return False
    else:
        print(f"\n⚠️  Job still running after {max_polls * poll_interval}s")
    
    # Test 3: List jobs
    print("\n" + "="*80)
    print("TEST 3: List all jobs")
    print("="*80)
    
    try:
        response = requests.get(f"{BASE_URL}/jobs")
        response.raise_for_status()
        list_result = response.json()
        
        print(f"✅ Found {list_result['total']} jobs:")
        for job in list_result["jobs"][:5]:
            print(f"   - {job['job_id'][:8]}... | {job['status']} | {job['query'][:40]} | {job['progress_percentage']:.1f}%")
    except Exception as e:
        print(f"❌ Failed to list jobs: {e}")
        return False
    
    # Test 4: Create and cancel a job
    print("\n" + "="*80)
    print("TEST 4: Create and cancel job")
    print("="*80)
    
    cancel_payload = {
        "query": "test cancellation",
        "batch_size": 200,
        "max_batches": 100  # Large job to ensure we can cancel it
    }
    
    try:
        # Create job
        response = requests.post(f"{BASE_URL}/jobs/ingest", json=cancel_payload)
        response.raise_for_status()
        cancel_job_id = response.json()["job_id"]
        print(f"✅ Created job to cancel: {cancel_job_id}")
        
        # Wait a bit
        time.sleep(1)
        
        # Cancel it
        response = requests.post(f"{BASE_URL}/jobs/{cancel_job_id}/cancel")
        response.raise_for_status()
        cancel_result = response.json()
        
        print(f"✅ Cancelled job: {cancel_job_id}")
        print(f"   Status: {cancel_result['status']}")
        print(f"   Message: {cancel_result['message']}")
    except Exception as e:
        print(f"❌ Failed to cancel job: {e}")
        return False
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print("✅ All API tests passed!")
    print(f"   - Job creation: Working")
    print(f"   - Status polling: Working")
    print(f"   - Job listing: Working")
    print(f"   - Job cancellation: Working")
    
    return True


if __name__ == "__main__":
    print("⚠️  Make sure the API server is running on http://localhost:8000")
    print("   Start it with: python main.py")
    
    try:
        success = test_jobs_api()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
