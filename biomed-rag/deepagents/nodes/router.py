"""
Router node — classifies incoming queries into one of three categories.

Categories:
  - "simple"  : quick biomedical question → direct agent with PubMed/RAG tools
  - "ingest"  : large-scale corpus analysis → ingestion pipeline
  - "signal"  : emerging signal / trend detection → signal analysis

The classification is done by the LLM itself (structured output) so it
can understand nuance, synonyms, and multi-language queries.
"""

import logging
import os
from typing import Any, Dict, Literal

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from deepagents.state import BioHorizonState

load_dotenv()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Structured output schema for route classification
# ---------------------------------------------------------------------------

class RouteDecision(BaseModel):
    """Classification of a user query into a processing route."""

    route: Literal["simple", "ingest", "signal"] = Field(
        description="The processing route: 'simple' for quick biomedical Q&A, "
        "'ingest' for large-scale corpus ingestion/analysis, "
        "'signal' for emerging signal or trend detection."
    )
    reasoning: str = Field(
        description="Brief one-sentence explanation of why this route was chosen."
    )


# ---------------------------------------------------------------------------
# Router prompt
# ---------------------------------------------------------------------------

ROUTER_SYSTEM_PROMPT = """You are a query classifier for a biomedical research assistant.

Classify the user's query into exactly ONE of these routes:

1. **simple** — The user asks a factual biomedical question, wants a literature summary,
   or needs information about a disease, drug, gene, or treatment.
   Examples: "What are the side effects of semaglutide?", "Recent studies on CRISPR for cancer", "Explain GLP-1 receptor agonists".

2. **ingest** — The user wants to analyze a large corpus, ingest literature,
   build a knowledge base, or process many articles at once.
   Examples: "Analyze all literature on Alzheimer and GLP-1", "Ingest the latest 500 papers on CAR-T",
   "Build a knowledge graph from oncology papers", "Ingérer le corpus sur CRISPR".

3. **signal** — The user asks about emerging trends, signal detection,
   what's new or accelerating in a research field, or consensus analysis.
   Examples: "Are there emerging signals between semaglutide and Alzheimer?",
   "What trends are accelerating in mRNA vaccine research?",
   "Detect new signals in the oncology knowledge graph".

Respond with the route and a brief reasoning.

## Rules
- ALWAYS answer in English by default, unless the user explicitly requests another language.
- Cite sources with [PMID: ...] format.
- Be precise: medical information requires accuracy."""

# ---------------------------------------------------------------------------
# LLM for routing (lightweight, fast)
# ---------------------------------------------------------------------------

_router_llm = None


def _get_router_llm():
    """Return a ChatOpenAI with structured output for routing."""
    global _router_llm
    if _router_llm is not None:
        return _router_llm

    model_name = os.getenv("OPEN_AI_MODEL", "gpt-4o")
    base_url = os.getenv("BASE_URL", "https://openrouter.ai/api/v1")
    api_key = os.getenv("OPEN_ROUTER_KEY") or os.getenv("OPENAI_API_KEY")

    llm = ChatOpenAI(
        model=model_name,
        temperature=0.0,
        openai_api_base=base_url,
        openai_api_key=api_key,
    )

    _router_llm = llm.with_structured_output(RouteDecision)
    return _router_llm


# ---------------------------------------------------------------------------
# Graph node
# ---------------------------------------------------------------------------

def router_node(state: BioHorizonState) -> Dict[str, Any]:
    """Classify the user query and store the route decision in stream_events.

    The route is stored as a stream_event with type "route" so
    downstream conditional edges can read it, and the API layer
    can display it.
    """
    # Extract the last user message
    user_msg = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            user_msg = msg.content
            break

    if not user_msg:
        logger.warning("[router] No user message found, defaulting to 'simple'")
        return {
            "stream_events": [
                {"type": "route", "content": "simple", "reasoning": "No user message found."}
            ]
        }

    try:
        llm = _get_router_llm()
        decision: RouteDecision = llm.invoke([
            SystemMessage(content=ROUTER_SYSTEM_PROMPT),
            HumanMessage(content=user_msg),
        ])
        route = decision.route
        reasoning = decision.reasoning
        logger.info("[router] Route: %s — %s", route, reasoning)
    except Exception as e:
        logger.warning("[router] Classification failed (%s), defaulting to 'simple'", e)
        route = "simple"
        reasoning = f"Classification failed: {e}"

    return {
        "stream_events": [
            {"type": "thought", "content": f"📍 Route: {route} — {reasoning}"},
            {"type": "route", "content": route, "reasoning": reasoning},
        ]
    }


# ---------------------------------------------------------------------------
# Conditional edge function
# ---------------------------------------------------------------------------

def route_query(state: BioHorizonState) -> Literal["agent", "ingest_agent", "signal_agent"]:
    """Read the route decision from stream_events and return the next node name."""
    for event in reversed(state.get("stream_events", [])):
        if event.get("type") == "route":
            route = event["content"]
            if route == "ingest":
                return "ingest_agent"
            elif route == "signal":
                return "signal_agent"
            else:
                return "agent"
    # Fallback
    return "agent"
