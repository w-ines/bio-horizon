"""
Weekly Scheduler for Automated Surveillance.

Executes watch topics on schedule:
1. Fetch active topics due for execution
2. For each topic: PubMed → NER → KG → Snapshot → Signals
3. Log execution results
4. Update next_run_at

Usage:
    # Run manually
    python scheduler/weekly_update.py
    
    # Or via cron (every Sunday at 00:00 UTC)
    0 0 * * 0 cd /path/to/med-rag && python scheduler/weekly_update.py
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from storage.supabase_client import get_supabase_client
from tools.pubmed_tool import search_pubmed
from tools.ner_tool import extract_medical_entities_batch
from kg.build import build_graph_from_ner_results
from kg.snapshots import save_snapshot, get_week_label

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def get_due_topics() -> List[Dict[str, Any]]:
    """
    Get all active watch topics that are due for execution.
    
    Returns:
        List of topic dictionaries
    """
    try:
        supabase = get_supabase_client()
        
        now = datetime.utcnow()
        
        response = (
            supabase.table("watch_topics")
            .select("*")
            .eq("is_active", True)
            .lte("next_run_at", now.isoformat())
            .execute()
        )
        
        topics = response.data or []
        logger.info(f"Found {len(topics)} topics due for execution")
        
        return topics
        
    except Exception as e:
        logger.error(f"Failed to fetch due topics: {e}")
        return []


async def execute_topic(topic: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a single watch topic: PubMed → NER → KG → Snapshot.
    
    Args:
        topic: Watch topic dictionary
        
    Returns:
        Execution result dictionary
    """
    topic_id = topic["id"]
    query = topic["query"]
    
    logger.info(f"Executing topic {topic_id}: {query}")
    
    start_time = datetime.utcnow()
    result = {
        "topic_id": topic_id,
        "executed_at": start_time.isoformat(),
        "status": "failed",
        "articles_found": 0,
        "entities_extracted": 0,
        "snapshot_id": None,
        "signals_detected": 0,
        "error_message": None,
        "execution_time_seconds": 0,
    }
    
    try:
        # Step 1: Search PubMed
        logger.info(f"  Step 1/4: Searching PubMed...")
        articles = search_pubmed(
            query=query,
            max_results=50,  # Default for automated execution
            sort="relevance"
        )
        
        result["articles_found"] = len(articles)
        logger.info(f"  Found {len(articles)} articles")
        
        if not articles:
            result["status"] = "partial"
            result["error_message"] = "No articles found"
            return result
        
        # Step 2: Extract entities with NER
        logger.info(f"  Step 2/4: Extracting entities...")
        texts = []
        pmids = []
        for article in articles:
            text = article.get('title', '') + ' ' + article.get('abstract', '')
            if text.strip():
                texts.append(text)
                pmids.append(article.get('pmid', ''))
        
        ner_results = extract_medical_entities_batch(
            texts=texts,
            pmids=pmids
        )
        
        result["entities_extracted"] = len(ner_results)
        logger.info(f"  Extracted entities from {len(ner_results)} articles")
        
        # Step 3: Build Knowledge Graph
        logger.info(f"  Step 3/4: Building Knowledge Graph...")
        G = build_graph_from_ner_results(ner_results)
        
        node_count = G.number_of_nodes()
        edge_count = G.number_of_edges()
        logger.info(f"  Built graph: {node_count} nodes, {edge_count} edges")
        
        if node_count == 0:
            result["status"] = "partial"
            result["error_message"] = "No entities extracted"
            return result
        
        # Step 4: Save snapshot
        logger.info(f"  Step 4/4: Saving snapshot...")
        week_label = get_week_label()
        snapshot_id, filepath = save_snapshot(G, week_label)
        
        result["snapshot_id"] = snapshot_id
        logger.info(f"  Snapshot saved: {week_label} (ID: {snapshot_id})")
        
        # TODO Phase 2: Detect signals from snapshot comparison
        # signals = detect_signals(G, week_label)
        # result["signals_detected"] = len(signals)
        
        result["status"] = "success"
        
    except Exception as e:
        logger.error(f"  Execution failed: {e}")
        result["error_message"] = str(e)
        result["status"] = "failed"
    
    finally:
        # Calculate execution time
        end_time = datetime.utcnow()
        result["execution_time_seconds"] = (end_time - start_time).total_seconds()
        logger.info(f"  Execution completed in {result['execution_time_seconds']:.2f}s")
    
    return result


async def log_execution(result: Dict[str, Any]):
    """
    Log execution result to database.
    
    Args:
        result: Execution result dictionary
    """
    try:
        supabase = get_supabase_client()
        
        supabase.table("watch_topic_executions").insert(result).execute()
        
        logger.info(f"Logged execution for topic {result['topic_id']}")
        
    except Exception as e:
        logger.error(f"Failed to log execution: {e}")


async def update_next_run(topic: Dict[str, Any]):
    """
    Update the next_run_at timestamp for a topic.
    
    Args:
        topic: Watch topic dictionary
    """
    try:
        supabase = get_supabase_client()
        
        topic_id = topic["id"]
        frequency = topic["frequency"]
        
        # Calculate next run
        if frequency == "weekly":
            next_run = datetime.utcnow() + timedelta(weeks=1)
            # Align to Sunday 00:00 UTC
            days_until_sunday = (6 - next_run.weekday()) % 7
            if days_until_sunday == 0:
                days_until_sunday = 7
            next_run = next_run + timedelta(days=days_until_sunday)
            next_run = next_run.replace(hour=0, minute=0, second=0, microsecond=0)
        
        elif frequency == "monthly":
            next_run = datetime.utcnow() + timedelta(days=30)
            # Align to first day of month
            next_run = next_run.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        else:
            logger.warning(f"Unknown frequency: {frequency}, defaulting to weekly")
            next_run = datetime.utcnow() + timedelta(weeks=1)
        
        # Update database
        supabase.table("watch_topics").update({
            "last_run_at": datetime.utcnow().isoformat(),
            "next_run_at": next_run.isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", topic_id).execute()
        
        logger.info(f"Updated topic {topic_id}: next run at {next_run.isoformat()}")
        
    except Exception as e:
        logger.error(f"Failed to update next_run_at: {e}")


async def main():
    """
    Main scheduler function.
    
    Executes all due watch topics and logs results.
    """
    logger.info("="*80)
    logger.info("Weekly Scheduler Started")
    logger.info("="*80)
    
    # Get topics due for execution
    topics = await get_due_topics()
    
    if not topics:
        logger.info("No topics due for execution")
        return
    
    # Execute each topic
    for i, topic in enumerate(topics, 1):
        logger.info(f"\nProcessing topic {i}/{len(topics)}")
        logger.info("-"*80)
        
        # Execute
        result = await execute_topic(topic)
        
        # Log result
        await log_execution(result)
        
        # Update next run time
        await update_next_run(topic)
    
    logger.info("\n" + "="*80)
    logger.info(f"Scheduler Completed: {len(topics)} topics processed")
    logger.info("="*80)


if __name__ == "__main__":
    asyncio.run(main())
