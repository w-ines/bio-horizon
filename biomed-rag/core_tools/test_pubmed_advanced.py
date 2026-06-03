"""
Test script for advanced PubMed search features.

Demonstrates:
1. Advanced filters (publication_types, journals, language, species)
2. Redis caching
3. PubMedSearchEngine class usage

Run with: python test_pubmed_advanced.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from pubmed_tool import search_pubmed, PubMedSearchEngine


def test_basic_search():
    """Test 1: Basic search without filters."""
    print("\n" + "="*80)
    print("TEST 1: Basic Search")
    print("="*80)
    
    result = search_pubmed(
        query="CRISPR gene editing",
        max_results=5,
        fetch_details=True
    )
    
    print(f"Query: CRISPR gene editing")
    print(f"Total results: {result['total']}")
    print(f"PMIDs returned: {len(result['pmids'])}")
    print(f"Articles fetched: {len(result['articles'])}")
    
    if result['articles']:
        print(f"\nFirst article:")
        article = result['articles'][0]
        print(f"  Title: {article['title'][:100]}...")
        print(f"  Journal: {article['journal']}")
        print(f"  PMID: {article['pmid']}")


def test_publication_type_filter():
    """Test 2: Filter by publication type."""
    print("\n" + "="*80)
    print("TEST 2: Publication Type Filter (Clinical Trials + Meta-Analysis)")
    print("="*80)
    
    result = search_pubmed(
        query="cancer immunotherapy",
        max_results=10,
        publication_types=["Clinical Trial", "Meta-Analysis"],
        fetch_details=True
    )
    
    print(f"Query: cancer immunotherapy")
    print(f"Filters: Clinical Trial, Meta-Analysis")
    print(f"Total results: {result['total']}")
    print(f"Articles fetched: {len(result['articles'])}")
    
    if result['articles']:
        print(f"\nSample articles:")
        for i, article in enumerate(result['articles'][:3], 1):
            print(f"{i}. {article['title'][:80]}...")
            print(f"   Journal: {article['journal']}")


def test_journal_filter():
    """Test 3: Filter by specific journals."""
    print("\n" + "="*80)
    print("TEST 3: Journal Filter (Nature, Science, Cell)")
    print("="*80)
    
    result = search_pubmed(
        query="mRNA vaccine",
        max_results=10,
        journals=["Nature", "Science", "Cell"],
        mindate="2020",
        fetch_details=True
    )
    
    print(f"Query: mRNA vaccine")
    print(f"Journals: Nature, Science, Cell")
    print(f"Date: Since 2020")
    print(f"Total results: {result['total']}")
    print(f"Articles fetched: {len(result['articles'])}")
    
    if result['articles']:
        print(f"\nJournals found:")
        journals = set(a['journal'] for a in result['articles'])
        for journal in journals:
            count = sum(1 for a in result['articles'] if a['journal'] == journal)
            print(f"  - {journal}: {count} articles")


def test_species_filter():
    """Test 4: Filter by species."""
    print("\n" + "="*80)
    print("TEST 4: Species Filter (Humans only)")
    print("="*80)
    
    result = search_pubmed(
        query="diabetes treatment",
        max_results=10,
        species=["Humans"],
        publication_types=["RCT"],
        fetch_details=True
    )
    
    print(f"Query: diabetes treatment")
    print(f"Species: Humans")
    print(f"Publication type: RCT")
    print(f"Total results: {result['total']}")
    print(f"Articles fetched: {len(result['articles'])}")


def test_combined_filters():
    """Test 5: Combine multiple filters (like Marie's use case)."""
    print("\n" + "="*80)
    print("TEST 5: Combined Filters (Marie's Antibiotic Resistance Use Case)")
    print("="*80)
    
    result = search_pubmed(
        query="antibiotic resistance E. coli",
        max_results=15,
        journals=["Nature Microbiology", "mBio"],
        publication_types=["Research Article", "Review"],
        language="eng",
        mindate="2024",
        fetch_details=True
    )
    
    print(f"Query: antibiotic resistance E. coli")
    print(f"Journals: Nature Microbiology, mBio")
    print(f"Types: Research Article, Review")
    print(f"Language: English")
    print(f"Date: Since 2024")
    print(f"Total results: {result['total']}")
    print(f"Articles fetched: {len(result['articles'])}")
    
    if result['articles']:
        print(f"\nTop 3 articles:")
        for i, article in enumerate(result['articles'][:3], 1):
            print(f"\n{i}. {article['title']}")
            print(f"   Journal: {article['journal']}")
            print(f"   Date: {article['pub_date']}")
            print(f"   PMID: {article['pmid']}")
            if article['mesh_terms']:
                print(f"   MeSH: {', '.join(article['mesh_terms'][:5])}")


def test_caching():
    """Test 6: Demonstrate caching (same query twice)."""
    print("\n" + "="*80)
    print("TEST 6: Redis Caching Test")
    print("="*80)
    
    import time
    
    query = "alzheimer disease"
    
    # First call (should hit PubMed API)
    print("First call (cache miss - hits PubMed API)...")
    start = time.time()
    result1 = search_pubmed(query=query, max_results=5)
    time1 = time.time() - start
    print(f"  Time: {time1:.3f}s")
    print(f"  Results: {result1['total']}")
    
    # Second call (should hit cache)
    print("\nSecond call (cache hit - from Redis)...")
    start = time.time()
    result2 = search_pubmed(query=query, max_results=5)
    time2 = time.time() - start
    print(f"  Time: {time2:.3f}s")
    print(f"  Results: {result2['total']}")
    
    if time2 < time1:
        speedup = time1 / time2
        print(f"\n✅ Cache speedup: {speedup:.1f}x faster!")
    else:
        print(f"\n⚠️  Cache may not be enabled (Redis not available)")


def test_engine_class():
    """Test 7: Direct use of PubMedSearchEngine class."""
    print("\n" + "="*80)
    print("TEST 7: Direct PubMedSearchEngine Class Usage")
    print("="*80)
    
    # Initialize engine
    engine = PubMedSearchEngine()
    
    # Search with advanced filters
    result = engine.search(
        query="COVID-19 vaccine",
        max_results=10,
        publication_types=["Clinical Trial"],
        mindate="2023",
        maxdate="2024",
    )
    
    search_result = result.get("esearchresult", {})
    pmids = search_result.get("idlist", [])
    total = search_result.get("count", 0)
    
    print(f"Query: COVID-19 vaccine")
    print(f"Type: Clinical Trial")
    print(f"Date: 2023-2024")
    print(f"Total results: {total}")
    print(f"PMIDs: {len(pmids)}")
    
    # Fetch details
    if pmids:
        articles = engine.fetch_articles(pmids[:5])
        print(f"Articles fetched: {len(articles)}")
        
        if articles:
            print(f"\nFirst article:")
            print(f"  Title: {articles[0]['title']}")
            print(f"  Journal: {articles[0]['journal']}")


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("PUBMED ADVANCED FEATURES TEST SUITE")
    print("="*80)
    
    tests = [
        test_basic_search,
        test_publication_type_filter,
        test_journal_filter,
        test_species_filter,
        test_combined_filters,
        test_caching,
        test_engine_class,
    ]
    
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*80)
    print("ALL TESTS COMPLETED")
    print("="*80)


if __name__ == "__main__":
    main()
