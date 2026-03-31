"""Smoke test for PubTator3 NER backend.

Run:  python -m pytest tests/test_pubtator3_backend.py -v
      or:  python tests/test_pubtator3_backend.py
"""

import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_fetch_single_pmid():
    """Fetch annotations for a well-known article (BRAF mutations paper)."""
    from ner.backends.pubtator3_backend import extract_by_pmids

    results = extract_by_pmids(["12068308"])

    assert "12068308" in results
    r = results["12068308"]
    assert r.provider == "pubtator3"
    assert r.error is None

    # This paper about BRAF mutations should have GENE and DISEASE entities
    all_entities = {k: v for k, v in r.entities.items() if v}
    print(f"\n--- PMID 12068308 entities ---")
    for etype, elist in r.entities.items():
        if elist:
            print(f"  {etype}: {[e.text for e in elist]}")

    assert len(all_entities) > 0, "Expected at least one entity type with results"

    # BRAF should be in GENE
    gene_texts = [e.text.upper() for e in r.entities.get("GENE", [])]
    assert any("BRAF" in t for t in gene_texts), f"Expected BRAF in genes, got: {gene_texts}"


def test_fetch_batch():
    """Fetch annotations for multiple PMIDs in a single batch."""
    from ner.backends.pubtator3_backend import extract_by_pmids

    pmids = ["12068308", "21639808", "22663011"]
    t0 = time.time()
    results = extract_by_pmids(pmids)
    elapsed = time.time() - t0

    print(f"\n--- Batch of {len(pmids)} PMIDs fetched in {elapsed:.2f}s ---")

    for pmid in pmids:
        assert pmid in results
        r = results[pmid]
        assert r.provider == "pubtator3"
        all_entities = {k: v for k, v in r.entities.items() if v}
        total = sum(len(v) for v in r.entities.values())
        print(f"  PMID {pmid}: {total} entities across {len(all_entities)} types")

    assert elapsed < 10, f"Batch fetch took too long: {elapsed:.2f}s (expected < 10s)"


def test_extract_batch_from_articles():
    """Test the article-level batch interface used by the router."""
    from ner.backends.pubtator3_backend import extract_batch_from_articles

    articles = [
        {"pmid": "12068308", "title": "Mutations of the BRAF gene", "abstract": "..."},
        {"pmid": "21639808", "title": "Improved survival with vemurafenib", "abstract": "..."},
    ]

    t0 = time.time()
    results = extract_batch_from_articles(articles)
    elapsed = time.time() - t0

    print(f"\n--- extract_batch_from_articles: {len(articles)} articles in {elapsed:.2f}s ---")

    assert len(results) == len(articles)
    for i, r in enumerate(results):
        assert r.provider == "pubtator3"
        total = sum(len(v) for v in r.entities.values())
        print(f"  Article {i}: {total} entities")


def test_router_pubtator3():
    """Test that the NER router correctly dispatches to PubTator3."""
    from ner.router import extract_batch

    articles = [
        {"pmid": "12068308", "title": "Mutations of the BRAF gene", "abstract": "..."},
    ]

    results = extract_batch(articles, provider="pubtator3")
    assert len(results) == 1
    assert results[0]["provider"] == "pubtator3"

    entities = results[0].get("entities", {})
    total = sum(len(v) for v in entities.values())
    print(f"\n--- Router → PubTator3: {total} entities ---")
    for etype, elist in entities.items():
        if elist:
            print(f"  {etype}: {[e['text'] for e in elist]}")

    assert total > 0, "Expected entities from router+pubtator3"


if __name__ == "__main__":
    print("=" * 60)
    print("PubTator3 Backend Smoke Tests")
    print("=" * 60)

    test_fetch_single_pmid()
    print("\n✅ test_fetch_single_pmid PASSED")

    test_fetch_batch()
    print("\n✅ test_fetch_batch PASSED")

    test_extract_batch_from_articles()
    print("\n✅ test_extract_batch_from_articles PASSED")

    test_router_pubtator3()
    print("\n✅ test_router_pubtator3 PASSED")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED ✅")
    print("=" * 60)
