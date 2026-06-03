"""
Planner node — decomposes complex queries into a step-by-step plan.

For "ingest" and "signal" routes, the planner creates a structured plan
that guides the agent through multi-step reasoning. For "simple" queries,
the planner is skipped (no planning needed).

The plan is injected as a SystemMessage into the conversation so the
agent follows it naturally during its tool-calling loop.
"""

import logging
import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from deepagents.state import BioHorizonState

load_dotenv()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Structured output schema for the plan
# ---------------------------------------------------------------------------

class TaskPlan(BaseModel):
    """A structured plan with ordered steps."""

    steps: List[str] = Field(
        description="Ordered list of concrete steps to accomplish the task. "
        "Each step should mention which tool to use if applicable."
    )
    summary: str = Field(
        description="One-sentence summary of what the plan will achieve."
    )


# ---------------------------------------------------------------------------
# Planner prompts per route
# ---------------------------------------------------------------------------

INGEST_PLANNER_PROMPT = """You are a research planning assistant.
The user wants to perform a large-scale corpus analysis. Create a concrete plan.

CRITICAL: For bulk ingestion, the agent MUST use create_corpus_ingestion_job.
Do NOT plan multiple pubmed_search calls — pubmed_search only returns 10 articles.

Available tools:
- create_corpus_ingestion_job(query, max_batches, processing_mode): Launch bulk ingestion (NER + KG). This is the PRIMARY tool for ingest tasks.
- check_ingestion_job_status(job_id): Check progress of an ingestion job
- search_ingested_articles(query): Search already ingested articles
- retrieve_knowledge(query): Search the Knowledge Graph and vector store
- pubmed_search(query): Quick search, returns only 10 articles. NOT for bulk ingestion.

The plan MUST:
1. Call create_corpus_ingestion_job with the user's query as first step
2. Optionally check status with check_ingestion_job_status
3. Summarize what was launched

Create a plan with 2-3 steps. Be specific to the user's query."""

SIGNAL_PLANNER_PROMPT = """You are a research planning assistant.
The user wants to detect emerging signals or trends. Create a concrete plan.

Available tools:
- pubmed_search(query): Search PubMed for recent articles (returns 10 max)
- retrieve_knowledge(query): Search the Knowledge Graph for entity relationships
- search_ingested_articles(query): Search previously ingested articles

The plan MUST:
1. Use pubmed_search to get recent articles on the topic (ONE call is enough)
2. Use retrieve_knowledge to query the Knowledge Graph for entity connections
3. Synthesize findings: compare new articles vs existing KG data to identify signals

Create a plan with 2-4 steps. Be specific to the user's query."""

# ---------------------------------------------------------------------------
# LLM for planning
# ---------------------------------------------------------------------------

_planner_llm = None


def _get_planner_llm():
    """Return a ChatOpenAI with structured output for planning."""
    global _planner_llm
    if _planner_llm is not None:
        return _planner_llm

    model_name = os.getenv("OPEN_AI_MODEL", "gpt-4o")
    base_url = os.getenv("BASE_URL", "https://openrouter.ai/api/v1")
    api_key = os.getenv("OPEN_ROUTER_KEY") or os.getenv("OPENAI_API_KEY")

    llm = ChatOpenAI(
        model=model_name,
        temperature=0.2,
        openai_api_base=base_url,
        openai_api_key=api_key,
    )

    _planner_llm = llm.with_structured_output(TaskPlan)
    return _planner_llm


# ---------------------------------------------------------------------------
# Graph node
# ---------------------------------------------------------------------------

def planner_node(state: BioHorizonState) -> Dict[str, Any]:
    """Generate a plan and inject it as a SystemMessage for the agent.

    Reads the route from stream_events to pick the right planner prompt.
    """
    # Determine route
    route = "simple"
    for event in reversed(state.get("stream_events", [])):
        if event.get("type") == "route":
            route = event["content"]
            break

    # Pick the appropriate prompt
    if route == "ingest":
        system_prompt = INGEST_PLANNER_PROMPT
    elif route == "signal":
        system_prompt = SIGNAL_PLANNER_PROMPT
    else:
        # No planning needed for simple queries
        return {"stream_events": []}

    # Extract user message
    user_msg = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            user_msg = msg.content
            break

    try:
        llm = _get_planner_llm()
        plan: TaskPlan = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_msg),
        ])

        # Format plan as a directive the agent MUST follow
        plan_text = f"## TASK PLAN — YOU MUST FOLLOW THIS PLAN\n**Goal:** {plan.summary}\n\n"
        for i, step in enumerate(plan.steps, 1):
            plan_text += f"{i}. {step}\n"
        if route == "ingest":
            plan_text += "\n⚠️ IMPORTANT: Use create_corpus_ingestion_job for bulk ingestion. Do NOT call pubmed_search repeatedly."
        plan_text += "\nFollow this plan step by step. Use the exact tools mentioned above."

        logger.info("[planner] Generated %d-step plan for route '%s': %s", len(plan.steps), route, plan.summary)

        # Inject plan as a SystemMessage so the agent sees it
        plan_message = SystemMessage(content=plan_text)

        return {
            "messages": [plan_message],
            "stream_events": [
                {"type": "thought", "content": f"📋 Plan: {plan.summary} ({len(plan.steps)} steps)"},
            ],
        }

    except Exception as e:
        logger.warning("[planner] Planning failed (%s), agent will proceed without plan", e)
        return {
            "stream_events": [
                {"type": "thought", "content": f"⚠️ Planning skipped: {e}"},
            ],
        }
