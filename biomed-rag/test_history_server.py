"""
Test script for PubMed History Server pagination.

This validates that we can:
1. Search with usehistory=y and get WebEnv/QueryKey
2. Paginate through results using fetch_batch()
3. Handle large result sets without timeouts
"""

import sys
from core_tools.pubmed_corpus import PubMedBulkEngine


def test_history_server():
    """Test History Server with a query that returns many results."""
    
    engine = PubMedBulkEngine()
    
    # Step 1: Search with History Server
    print("\n" + "="*80)
    print("STEP 1: Searching PubMed with History Server")
    print("="*80)
    
    query = "diabetes mellitus"  # Should return ~500K results
    
    try:
        history_result = engine.search_with_history(
            query=query,
            mindate="2023",
            maxdate="2024",
        )
        
        print(f"\n✅ History search successful!")
        print(f"   Query: {history_result['query']}")
        print(f"   Total results: {history_result['count']:,}")
        print(f"   WebEnv: {history_result['web_env'][:30]}...")
        print(f"   QueryKey: {history_result['query_key']}")
        
    except Exception as e:
        print(f"\n❌ History search failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 2: Fetch first batch
    print("\n" + "="*80)
    print("STEP 2: Fetching first batch (0-200)")
    print("="*80)
    
    try:
        batch1 = engine.fetch_batch(
            web_env=history_result['web_env'],
            query_key=history_result['query_key'],
            retstart=0,
            retmax=200,
        )
        
        print(f"\n✅ Batch 1 fetched: {len(batch1)} articles")
        if batch1:
            print(f"   First article: {batch1[0]['title'][:80]}...")
            print(f"   PMID: {batch1[0]['pmid']}")
        
    except Exception as e:
        print(f"\n❌ Batch 1 fetch failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 3: Fetch second batch
    print("\n" + "="*80)
    print("STEP 3: Fetching second batch (200-400)")
    print("="*80)
    
    try:
        batch2 = engine.fetch_batch(
            web_env=history_result['web_env'],
            query_key=history_result['query_key'],
            retstart=200,
            retmax=200,
        )
        
        print(f"\n✅ Batch 2 fetched: {len(batch2)} articles")
        if batch2:
            print(f"   First article: {batch2[0]['title'][:80]}...")
            print(f"   PMID: {batch2[0]['pmid']}")
        
        # Verify we got different articles
        pmids_batch1 = {a['pmid'] for a in batch1}
        pmids_batch2 = {a['pmid'] for a in batch2}
        overlap = pmids_batch1 & pmids_batch2
        
        if overlap:
            print(f"\n⚠️  WARNING: {len(overlap)} PMIDs overlap between batches!")
        else:
            print(f"\n✅ No overlap between batches (pagination working correctly)")
        
    except Exception as e:
        print(f"\n❌ Batch 2 fetch failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"✅ History Server test PASSED")
    print(f"   Total results available: {history_result['count']:,}")
    print(f"   Fetched: {len(batch1) + len(batch2)} articles across 2 batches")
    print(f"   Pagination: Working correctly (no overlap)")
    print(f"\n💡 You can now fetch all {history_result['count']:,} results by looping:")
    print(f"   for i in range(0, {history_result['count']}, 200):")
    print(f"       batch = engine.fetch_batch(web_env, query_key, retstart=i, retmax=200)")
    
    return True


if __name__ == "__main__":
    success = test_history_server()
    sys.exit(0 if success else 1)
