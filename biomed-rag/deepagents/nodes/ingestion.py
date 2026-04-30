"""
Ingestion pipeline nodes for LangGraph.

Replaces IngestWorker._process_batches() with discrete graph nodes:
  search → fetch_batch → process_batch (NER+KG) → persist_kg → [loop or end]

Each node reads/writes to IngestionState, and the LangGraph checkpointer
handles fault tolerance automatically (no manual _save_checkpoint).
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal, Optional

from deepagents.state import BioHorizonState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Ingestion-specific state (extends BioHorizonState for the sub-graph)
# ---------------------------------------------------------------------------

from typing import Annotated, Sequence
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class IngestionState(TypedDict):
    """State for the ingestion sub-graph."""

    # Job metadata
    job_id: str
    query: str
    processing_mode: str  # "full", "metadata_only", "deferred_ner"
    batch_size: int

    # Search filters
    mindate: str
    maxdate: str
    publication_types: Optional[List[str]]
    journals: Optional[List[str]]
    language: Optional[str]
    species: Optional[List[str]]

    # NCBI History Server tokens (set by search_node)
    web_env: Optional[str]
    query_key: Optional[str]
    total_articles: int

    # Batch processing state
    current_batch: int
    last_retstart: int
    processed_articles: int
    entities_extracted: int
    batches_since_persist: int

    # Current batch data (transient, overwritten each iteration)
    current_articles: List[Dict[str, Any]]

    # Configuration
    max_batches: Optional[int]
    effective_total: int

    # Error tracking
    error: Optional[str]

    # Streaming events
    stream_events: Annotated[List[Dict[str, Any]], lambda a, b: a + b]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NCBI_WEBENV_LIMIT = 10_000
PERSIST_EVERY_N = 20


# ---------------------------------------------------------------------------
# Node: search PubMed via History Server
# ---------------------------------------------------------------------------

def search_node(state: IngestionState) -> Dict[str, Any]:
    """Execute PubMed search and store WebEnv/QueryKey."""
    from core_tools.pubmed_corpus import PubMedBulkEngine

    engine = PubMedBulkEngine()
    query = state["query"]
    processing_mode = state.get("processing_mode", "full")

    # Auto-set maxdate for PubTator3 (needs 30+ day old articles)
    maxdate = state.get("maxdate", "")
    ner_provider = os.getenv("NER_PROVIDER", "pubtator3")
    if ner_provider == "pubtator3" and not maxdate:
        cutoff = datetime.utcnow() - timedelta(days=30)
        maxdate = cutoff.strftime("%Y/%m/%d")
        logger.info(f"📅 PubTator3 mode: auto-setting maxdate={maxdate}")

    logger.info(f"🔍 Searching PubMed: {query}")

    result = engine.search_with_history(
        query=query,
        mindate=state.get("mindate", ""),
        maxdate=maxdate,
        publication_types=state.get("publication_types"),
        journals=state.get("journals"),
        language=state.get("language"),
        species=state.get("species"),
    )

    total = result["count"]
    is_metadata_only = processing_mode in ("metadata_only", "deferred_ner")

    effective_total = total
    if not is_metadata_only and effective_total > NCBI_WEBENV_LIMIT:
        logger.info(f"📊 Capping to {NCBI_WEBENV_LIMIT:,} (NCBI limit; found: {total:,})")
        effective_total = NCBI_WEBENV_LIMIT

    logger.info(f"✅ Search complete: {total:,} articles found")

    return {
        "web_env": result["web_env"],
        "query_key": result["query_key"],
        "total_articles": total,
        "effective_total": effective_total,
        "stream_events": [
            {"type": "thought", "content": f"🔍 PubMed search: {total:,} articles found for '{query}'"},
        ],
    }


# ---------------------------------------------------------------------------
# Node: fetch one batch from PubMed
# ---------------------------------------------------------------------------

def fetch_batch_node(state: IngestionState) -> Dict[str, Any]:
    """Fetch the next batch of articles from PubMed."""
    from core_tools.pubmed_corpus import PubMedBulkEngine

    engine = PubMedBulkEngine()
    retstart = state["last_retstart"]
    batch_idx = state["current_batch"]
    batch_size = state.get("batch_size", 200)

    logger.info(f"📄 Fetching batch {batch_idx + 1}: retstart={retstart}")

    articles = engine.fetch_batch(
        web_env=state["web_env"],
        query_key=state["query_key"],
        retstart=retstart,
        retmax=batch_size,
    )

    if not articles:
        logger.warning(f"⚠️ No articles at retstart={retstart}")
        return {
            "current_articles": [],
            "stream_events": [
                {"type": "thought", "content": f"⚠️ No articles at retstart={retstart}"},
            ],
        }

    logger.info(f"✅ Fetched {len(articles)} articles")

    return {
        "current_articles": articles,
        "stream_events": [
            {"type": "action", "content": f"📄 Fetched batch {batch_idx + 1}: {len(articles)} articles"},
        ],
    }


# ---------------------------------------------------------------------------
# Node: process batch (NER + KG)
# ---------------------------------------------------------------------------

def process_batch_node(state: IngestionState) -> Dict[str, Any]:
    """Process current batch: store metadata, run NER, build KG."""
    articles = state.get("current_articles", [])
    if not articles:
        return {"stream_events": []}

    processing_mode = state.get("processing_mode", "full")
    is_metadata_only = processing_mode in ("metadata_only", "deferred_ner")
    batch_idx = state["current_batch"]
    batch_size = state.get("batch_size", 200)

    # Store metadata (always)
    try:
        from storage.articles_repository import upsert_articles_batch
        upsert_articles_batch(articles, state["job_id"])
    except Exception as e:
        logger.warning(f"⚠️ Metadata store failed (non-fatal): {e}")

    if is_metadata_only:
        new_processed = state["processed_articles"] + len(articles)
        effective_total = state.get("effective_total", state["total_articles"])
        progress = (new_processed / effective_total * 100) if effective_total else 0
        logger.info(f"✅ Batch {batch_idx + 1}: stored {len(articles)} metadata ({progress:.1f}%)")

        return {
            "processed_articles": new_processed,
            "current_batch": batch_idx + 1,
            "last_retstart": state["last_retstart"] + batch_size,
            "batches_since_persist": state.get("batches_since_persist", 0),
            "stream_events": [
                {"type": "observation", "content": f"✅ Batch {batch_idx + 1}: {len(articles)} metadata stored ({progress:.1f}%)"},
            ],
        }

    # Full mode: NER + KG
    ner_provider = os.getenv("NER_PROVIDER", "pubtator3")
    logger.info(f"🧠 NER[{ner_provider}] + KG for {len(articles)} articles")

    from core_tools.ner_tool import extract_medical_entities_batch
    from kg import build
    from core_tools.kg_tool import get_graph

    ner_results = extract_medical_entities_batch(
        articles,
        entity_types=None,
        provider=ner_provider,
    )

    # Count entities
    entities_count = 0
    for r in ner_results:
        for entity_list in r.get("entities", {}).values():
            entities_count += len(entity_list)

    logger.info(f"✅ Extracted {entities_count} entities")

    # Build KG
    if entities_count > 0:
        from kg.relation_extractor import extract_relations_llm

        graph = get_graph()
        article_map = {a.get("pmid", ""): a for a in articles if a.get("pmid")}
        semantic_count = 0

        for r in ner_results:
            source = r.get("pmid") or (r.get("article") or {}).get("pmid") or ""
            triplets = r.get("relations") or []

            # LLM fallback when no relations found
            if not triplets:
                abstract = article_map.get(source, {}).get("abstract", "")
                entities = r.get("entities", {})
                if abstract and entities:
                    try:
                        result = extract_relations_llm(abstract, entities)
                        triplets = result.triplets
                    except Exception as e:
                        logger.warning(f"⚠️ LLM relation extraction failed for {source}: {e}")

            semantic_count += len(triplets)
            build.add_ner_result_with_relations_to_graph(
                graph, r, source=source, semantic_triplets=triplets or None
            )

        logger.info(
            f"✅ KG updated: +{entities_count} entities, +{semantic_count} triplets "
            f"(total: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges)"
        )

    # Update progress
    new_processed = state["processed_articles"] + len(articles)
    new_entities = state["entities_extracted"] + entities_count
    effective_total = state.get("effective_total", state["total_articles"])
    progress = (new_processed / effective_total * 100) if effective_total else 0

    return {
        "processed_articles": new_processed,
        "entities_extracted": new_entities,
        "current_batch": batch_idx + 1,
        "last_retstart": state["last_retstart"] + batch_size,
        "batches_since_persist": state.get("batches_since_persist", 0) + 1,
        "stream_events": [
            {"type": "observation", "content": f"✅ Batch {batch_idx + 1}: {entities_count} entities ({progress:.1f}%)"},
        ],
    }


# ---------------------------------------------------------------------------
# Node: persist KG to Supabase (periodic + final)
# ---------------------------------------------------------------------------

def persist_kg_node(state: IngestionState) -> Dict[str, Any]:
    """Persist the in-memory KG to Supabase if enough batches have accumulated."""
    batches_since = state.get("batches_since_persist", 0)
    entities = state.get("entities_extracted", 0)
    is_metadata_only = state.get("processing_mode", "full") in ("metadata_only", "deferred_ner")

    if is_metadata_only or entities == 0:
        return {"batches_since_persist": 0, "stream_events": []}

    # Persist if threshold reached OR if this is called as final persist
    if batches_since < PERSIST_EVERY_N:
        return {"stream_events": []}

    from kg import store
    from core_tools.kg_tool import get_graph

    graph = get_graph()
    if graph.number_of_nodes() == 0:
        return {"batches_since_persist": 0, "stream_events": []}

    logger.info(f"💾 Persisting KG: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    store.persist_graph(graph)
    logger.info("✅ KG persisted")

    return {
        "batches_since_persist": 0,
        "stream_events": [
            {"type": "thought", "content": f"💾 KG persisted ({graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges)"},
        ],
    }


# ---------------------------------------------------------------------------
# Node: final persist (always persists remaining data)
# ---------------------------------------------------------------------------

def final_persist_node(state: IngestionState) -> Dict[str, Any]:
    """Final KG persist at end of ingestion — always runs if there's data."""
    entities = state.get("entities_extracted", 0)
    batches_since = state.get("batches_since_persist", 0)
    is_metadata_only = state.get("processing_mode", "full") in ("metadata_only", "deferred_ner")

    if is_metadata_only or entities == 0 or batches_since == 0:
        return {
            "stream_events": [
                {"type": "thought", "content": f"✅ Ingestion complete: {state.get('processed_articles', 0)} articles, {entities} entities"},
            ],
        }

    from kg import store
    from core_tools.kg_tool import get_graph

    graph = get_graph()
    if graph.number_of_nodes() == 0:
        return {"stream_events": []}

    logger.info(f"💾 Final KG persist: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    store.persist_graph(graph)

    return {
        "batches_since_persist": 0,
        "stream_events": [
            {"type": "thought", "content": f"✅ Ingestion complete: {state.get('processed_articles', 0)} articles, {entities} entities. KG persisted."},
        ],
    }


# ---------------------------------------------------------------------------
# Conditional edge: more batches to process?
# ---------------------------------------------------------------------------

def should_continue_batches(state: IngestionState) -> Literal["fetch_batch", "final_persist"]:
    """Decide if there are more batches to fetch or if we're done."""
    retstart = state.get("last_retstart", 0)
    effective_total = state.get("effective_total", 0)
    max_batches = state.get("max_batches")
    batch_idx = state.get("current_batch", 0)
    articles = state.get("current_articles", [])

    # Stop if no articles were returned (empty batch)
    if not articles:
        return "final_persist"

    # Stop if we've reached the end
    if retstart >= effective_total:
        return "final_persist"

    # Stop if max_batches limit reached
    if max_batches and batch_idx >= max_batches:
        logger.info(f"⚠️ max_batches limit ({max_batches}) reached")
        return "final_persist"

    return "fetch_batch"
