"""
Async worker for PubMed corpus ingestion jobs.

Handles batch processing with checkpointing, error recovery, and progress tracking.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from jobs.models import Job, JobStatus
from jobs.store import JobStore
from core_tools.pubmed_corpus import PubMedBulkEngine

logger = logging.getLogger(__name__)


class IngestWorker:
    """
    Async worker for PubMed corpus ingestion.
    
    Features:
    - Batch processing with History Server
    - Checkpointing for fault tolerance
    - Progress tracking
    - NER + KG ingestion per batch
    """
    
    def __init__(self, job_store: JobStore):
        """
        Initialize worker.
        
        Args:
            job_store: Job persistence layer
        """
        self.job_store = job_store
        self.engine = PubMedBulkEngine()
    
    async def run_job(self, job_id: str) -> bool:
        """
        Run a PubMed ingestion job.
        
        This is the main entry point for job execution.
        
        Args:
            job_id: Job identifier
        
        Returns:
            True if job completed successfully
        """
        job = self.job_store.get(job_id)
        if not job:
            logger.error(f"❌ Job {job_id} not found")
            return False
        
        if job.status != JobStatus.PENDING:
            logger.warning(f"⚠️  Job {job_id} is not pending (status={job.status})")
            return False
        
        try:
            # Update status to running
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow()
            self.job_store.update(job)
            
            logger.info(f"🚀 Starting job {job_id}: {job.query}")
            
            # Step 1: Search with History Server
            if not job.web_env or not job.query_key:
                await self._execute_search(job)
            
            # Step 2: Process batches
            await self._process_batches(job)
            
            # Mark as completed
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            self.job_store.update(job)
            
            logger.info(f"✅ Job {job_id} completed: {job.processed_articles}/{job.total_articles} articles, {job.entities_extracted} entities")
            return True
        
        except Exception as e:
            logger.error(f"❌ Job {job_id} failed: {e}")
            import traceback
            traceback.print_exc()
            
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.utcnow()
            self.job_store.update(job)
            return False
    
    async def _execute_search(self, job: Job) -> None:
        """
        Execute PubMed search with History Server.
        
        Args:
            job: Job instance
        """
        import os
        from datetime import datetime, timedelta

        maxdate = job.maxdate

        # When using PubTator3, restrict to articles older than ~30 days
        # so they've been indexed by NCBI's annotation pipeline.
        ner_provider = os.getenv("NER_PROVIDER", "pubtator3")
        if ner_provider == "pubtator3" and not maxdate:
            cutoff = datetime.utcnow() - timedelta(days=30)
            maxdate = cutoff.strftime("%Y/%m/%d")
            logger.info(
                f"📅 PubTator3 mode: auto-setting maxdate={maxdate} "
                f"(articles must be >=30 days old for NCBI annotations)"
            )

        logger.info(f"� Searching PubMed: {job.query}")
        
        # Run search in thread pool (requests is blocking)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self.engine.search_with_history(
                query=job.query,
                mindate=job.mindate,
                maxdate=maxdate,
                publication_types=job.publication_types,
                journals=job.journals,
                language=job.language,
                species=job.species,
            )
        )
        
        # Update job with search results
        job.web_env = result["web_env"]
        job.query_key = result["query_key"]
        job.total_articles = result["count"]
        
        self.job_store.update(job)
        
        logger.info(f"✅ Search complete: {job.total_articles:,} articles found")
    
    async def _fetch_one_batch(self, job: Job, retstart: int) -> list:
        """Fetch a single batch from PubMed in a thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda rs=retstart: self.engine.fetch_batch(
                web_env=job.web_env,
                query_key=job.query_key,
                retstart=rs,
                retmax=job.batch_size,
            )
        )

    async def _persist_kg_snapshot(self, label: str = "") -> None:
        """Persist the in-memory KG to Supabase (called periodically + on crash)."""
        from kg import store
        from core_tools.kg_tool import get_graph
        graph = get_graph()
        if graph.number_of_nodes() == 0:
            return
        logger.info(
            f"💾 Persisting KG to Supabase{label}: "
            f"{graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges..."
        )
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: store.persist_graph(graph))
        logger.info(f"✅ KG persisted{label}")

    async def _process_batches(self, job: Job) -> None:
        """
        Process articles in batches with pipeline parallelism.
        
        Pipeline: while batch N is being processed (NER+KG),
        batch N+1 is already being fetched from PubMed.
        This overlaps network I/O with CPU processing.
        
        Args:
            job: Job instance
        """
        if not job.web_env or not job.query_key:
            raise ValueError("Missing WebEnv/QueryKey")
        
        # NCBI WebEnv sessions support max ~10 000 results via efetch.
        # Cap effective total so we don't hit 400 errors.
        NCBI_WEBENV_LIMIT = 10_000
        PERSIST_EVERY_N = 20  # persist KG every N batches (balance speed vs safety)

        batch_idx = job.current_batch
        retstart = job.last_retstart
        is_metadata_only = job.processing_mode in ("metadata_only", "deferred_ner")
        
        effective_total = job.total_articles
        if not is_metadata_only and effective_total > NCBI_WEBENV_LIMIT:
            logger.info(
                f"📊 Capping ingestion to {NCBI_WEBENV_LIMIT:,} articles "
                f"(NCBI WebEnv limit; total found: {job.total_articles:,})"
            )
            effective_total = NCBI_WEBENV_LIMIT

        mode_label = "metadata-only" if is_metadata_only else "full (NER+KG)"
        logger.info(f"⚙️  Processing mode: {mode_label}")
        
        batches_since_persist = 0  # track batches since last KG persist

        # --- Prefetch first batch ---
        prefetch_task: Optional[asyncio.Task] = None
        if retstart < effective_total and not (job.max_batches and batch_idx >= job.max_batches):
            logger.info(f"📄 Prefetching batch {batch_idx + 1}: retstart={retstart}")
            prefetch_task = asyncio.create_task(self._fetch_one_batch(job, retstart))
        
        while retstart < effective_total:
            # Check max_batches limit
            if job.max_batches and batch_idx >= job.max_batches:
                logger.info(f"⚠️  Reached max_batches limit ({job.max_batches})")
                break
            
            try:
                # Await the prefetched batch
                if prefetch_task is None:
                    break
                articles = await prefetch_task
                prefetch_task = None
                
                if not articles:
                    logger.warning(f"⚠️  No articles returned at retstart={retstart}")
                    break
                
                # --- Start prefetching NEXT batch while we process current ---
                next_retstart = retstart + job.batch_size
                should_prefetch = (
                    next_retstart < effective_total
                    and not (job.max_batches and (batch_idx + 1) >= job.max_batches)
                )
                if should_prefetch:
                    logger.info(f"📄 Prefetching batch {batch_idx + 2}: retstart={next_retstart}")
                    prefetch_task = asyncio.create_task(self._fetch_one_batch(job, next_retstart))
                
                # --- Process current batch (overlaps with prefetch) ---
                if is_metadata_only:
                    entities_count = await self._store_metadata_batch(job, articles)
                else:
                    entities_count = await self._process_batch(job, articles)
                
                # Update progress
                job.processed_articles += len(articles)
                job.entities_extracted += entities_count
                job.current_batch = batch_idx + 1
                job.last_retstart = retstart + job.batch_size
                
                self.job_store.update(job)
                
                progress = (job.processed_articles / effective_total * 100) if effective_total else 0
                logger.info(f"✅ Batch {batch_idx + 1} done: {len(articles)} articles, {entities_count} entities ({progress:.1f}% complete)")
                
                # Move to next batch
                batch_idx += 1
                retstart += job.batch_size
                batches_since_persist += 1
                
                # --- Periodic KG persist (every N batches) ---
                if not is_metadata_only and batches_since_persist >= PERSIST_EVERY_N:
                    await self._persist_kg_snapshot(f" (checkpoint after {batch_idx} batches)")
                    batches_since_persist = 0
                
                await asyncio.sleep(0.05)
            
            except Exception as e:
                logger.error(f"❌ Batch {batch_idx + 1} failed: {e}")
                # Cancel any outstanding prefetch
                if prefetch_task and not prefetch_task.done():
                    prefetch_task.cancel()
                # Persist KG before losing in-memory data
                if not is_metadata_only and job.entities_extracted > 0:
                    try:
                        await self._persist_kg_snapshot(" (emergency save before crash)")
                    except Exception as pe:
                        logger.error(f"⚠️  Emergency KG persist failed: {pe}")
                # Save checkpoint before raising
                job.current_batch = batch_idx
                job.last_retstart = retstart
                self.job_store.update(job)
                raise
        
        # --- Final KG persist ---
        if not is_metadata_only and job.entities_extracted > 0 and batches_since_persist > 0:
            await self._persist_kg_snapshot(f" (final, {batch_idx} batches total)")
    
    async def _store_metadata_batch(self, job: Job, articles: list) -> int:
        """
        Store article metadata only (no NER/KG). Much faster.
        
        Args:
            job: Job instance
            articles: List of article dictionaries
        
        Returns:
            0 (no entities extracted in this mode)
        """
        logger.info(f"📦 Storing {len(articles)} articles (metadata-only, no NER)")
        
        from storage.articles_repository import upsert_articles_batch
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: upsert_articles_batch(articles, job.job_id)
        )
        
        logger.info(f"✅ Stored {len(articles)} articles metadata")
        return 0

    async def _process_batch(self, job: Job, articles: list) -> int:
        """
        Process a batch of articles (NER + KG ingestion).
        
        Uses PubTator3 by default for NER: pre-computed annotations from NCBI,
        fetched via HTTP in ~1-2 seconds for 100 articles (vs minutes with
        local ML models like OpenMed/GLiNER).
        
        Args:
            job: Job instance
            articles: List of article dictionaries
        
        Returns:
            Number of entities extracted
        """
        import os
        ner_provider = os.getenv("NER_PROVIDER", "pubtator3")
        logger.info(f"🧠 Processing {len(articles)} articles (NER[{ner_provider}] + KG ingestion)")
        
        # Import KG tools
        from core_tools.ner_tool import extract_medical_entities_batch
        from kg import build
        from core_tools.kg_tool import get_graph
        
        # Step 0: Store article metadata (so articles are searchable even if NER fails)
        try:
            from storage.articles_repository import upsert_articles_batch
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: upsert_articles_batch(articles, job.job_id)
            )
        except Exception as e:
            logger.warning(f"⚠️  Metadata store failed (non-fatal): {e}")
        
        # Step 1: Extract entities — PubTator3 = ~2s per 100 articles (HTTP)
        #                             OpenMed  = ~minutes per 100 articles (ML)
        loop = asyncio.get_event_loop()
        ner_results = await loop.run_in_executor(
            None,
            lambda: extract_medical_entities_batch(
                articles,
                entity_types=None,
                provider=ner_provider,
            )
        )
        
        # Step 2: Count total entities extracted
        entities_count = 0
        for ner_result in ner_results:
            entities_dict = ner_result.get("entities", {})
            for entity_type, entity_list in entities_dict.items():
                entities_count += len(entity_list)
        
        logger.info(f"✅ Extracted {entities_count} entities from {len(articles)} articles")
        
        # Step 3: Add to in-memory KG (fast, no DB write)
        # Persistence happens once at end of job in _process_batches.
        if entities_count > 0:
            graph = get_graph()
            build.add_ner_results_batch(graph, ner_results)
            logger.info(f"✅ Added {entities_count} entities to in-memory KG ({graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges)")
        else:
            logger.info("⏭️  No new entities in this batch")
        
        return entities_count
    
    async def resume_job(self, job_id: str) -> bool:
        """
        Resume a failed job from checkpoint.
        
        Args:
            job_id: Job identifier
        
        Returns:
            True if resumed successfully
        """
        job = self.job_store.get(job_id)
        if not job:
            logger.error(f"❌ Job {job_id} not found")
            return False
        
        if not job.can_resume():
            logger.error(f"❌ Job {job_id} cannot be resumed (status={job.status})")
            return False
        
        logger.info(f"🔄 Resuming job {job_id} from checkpoint (retstart={job.last_retstart})")
        
        # Reset status to running
        job.status = JobStatus.RUNNING
        job.error = None
        job.retry_count += 1
        self.job_store.update(job)
        
        # Continue processing from checkpoint
        try:
            await self._process_batches(job)
            
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            self.job_store.update(job)
            
            logger.info(f"✅ Job {job_id} resumed and completed")
            return True
        
        except Exception as e:
            logger.error(f"❌ Job {job_id} failed again: {e}")
            job.status = JobStatus.FAILED
            job.error = str(e)
            self.job_store.update(job)
            return False


# =============================================================================
# Helper functions for running jobs
# =============================================================================

async def run_ingest_job(job_id: str, job_store: JobStore) -> bool:
    """
    Run a PubMed ingestion job.
    
    This is a convenience function for running jobs.
    
    Args:
        job_id: Job identifier
        job_store: Job persistence layer
    
    Returns:
        True if job completed successfully
    """
    worker = IngestWorker(job_store)
    return await worker.run_job(job_id)
