"""
LangGraph ask-graph — replaces SimpleAgentExecutor.

This graph implements a routed ReAct loop:
  START → router → planner → agent ↔ tools → END

The router classifies queries into simple/ingest/signal.
The planner generates a step-by-step plan for complex queries.
The agent executes the plan using tools in a ReAct loop.
"""

import logging
import os
from typing import Any, Dict, List, Literal

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from deepagents.state import BioHorizonState
from deepagents.nodes.router import router_node, route_query
from deepagents.nodes.planner import planner_node

load_dotenv()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt (identical to the one in main_agent.py)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are Bio-Horizon, an intelligent biomedical research assistant.
You MUST be proactive: when the user asks a question, USE YOUR TOOLS immediately to find the answer. NEVER ask the user to reformulate or search themselves.

## Tool selection guide
- **pubmed_search**: Quick lookup, returns max 10 articles. Use for simple factual questions.
- **create_corpus_ingestion_job**: Bulk ingestion of hundreds/thousands of articles with NER + Knowledge Graph. Use when user says "ingest", "analyze corpus", "build KG", "analyze all literature". Do NOT use pubmed_search for bulk tasks.
- **check_ingestion_job_status**: Check progress of a running ingestion job.
- **search_ingested_articles**: Search articles that were already ingested.
- **retrieve_knowledge**: Search uploaded documents and the Knowledge Graph.

## Workflow
1. **Simple question**: ONE call to pubmed_search → synthesize answer.
2. **Large-scale ingestion**: ONE call to create_corpus_ingestion_job → report job_id to user.
3. **Signal/trend detection**: pubmed_search + retrieve_knowledge → synthesize findings.

## Rules
- ALWAYS answer in English by default, unless the user explicitly requests another language.
- Cite sources with [PMID: ...] format.
- Be precise: medical information requires accuracy.
- Never say "I couldn't find information" without having attempted at least one tool call.
- If a tool returns no results, rephrase the query and retry once.
- If the question is clearly outside the biomedical domain and no tool is relevant, answer directly from your general knowledge. Do NOT force a tool call.
- If a TASK PLAN is provided, follow it strictly."""

# Maximum iterations for the tool-calling loop
MAX_ITERATIONS = 7

# ---------------------------------------------------------------------------
# Tool registry (lazy-loaded once)
# ---------------------------------------------------------------------------

_tool_registry: Dict[str, Any] | None = None


def _get_tools():
    """Lazy-import and return the default biomedical tools."""
    global _tool_registry
    if _tool_registry is not None:
        return list(_tool_registry.values()), _tool_registry

    from deepagents.tools.knowledge.rag_tool import retrieve_knowledge
    from deepagents.tools.biomedical.pubmed_tool import pubmed_search
    from deepagents.tools.biomedical.corpus_ingestion_tool import (
        create_corpus_ingestion_job,
        check_ingestion_job_status,
    )
    from deepagents.tools.biomedical.search_articles_tool import search_ingested_articles

    tools = [
        pubmed_search,
        retrieve_knowledge,
        create_corpus_ingestion_job,
        check_ingestion_job_status,
        search_ingested_articles,
    ]
    _tool_registry = {t.name: t for t in tools}
    return tools, _tool_registry


# ---------------------------------------------------------------------------
# LLM (lazy-loaded once)
# ---------------------------------------------------------------------------

_llm_with_tools = None


def _get_llm():
    """Return a ChatOpenAI instance with tools bound."""
    global _llm_with_tools
    if _llm_with_tools is not None:
        return _llm_with_tools

    model_name = os.getenv("OPEN_AI_MODEL", "gpt-4o")
    base_url = os.getenv("BASE_URL", "https://openrouter.ai/api/v1")
    api_key = os.getenv("OPEN_ROUTER_KEY") or os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "No API key found. Set OPEN_ROUTER_KEY or OPENAI_API_KEY environment variable."
        )

    llm = ChatOpenAI(
        model=model_name,
        temperature=0.3,
        openai_api_base=base_url,
        openai_api_key=api_key,
    )

    tools, _ = _get_tools()
    _llm_with_tools = llm.bind_tools(tools)
    return _llm_with_tools


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------

def _sanitize_messages(messages: List) -> List:
    """Remove orphan tool_calls that have no matching ToolMessage response.

    OpenAI requires that every AIMessage with tool_calls is immediately
    followed by ToolMessages for each call_id. If a previous turn was
    interrupted, the history may contain orphan tool_calls. We strip them
    to avoid 400 errors.
    """
    sanitized = []
    i = 0
    while i < len(messages):
        msg = messages[i]

        # Check if this is an AIMessage with tool_calls
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            expected_ids = {tc["id"] for tc in msg.tool_calls if "id" in tc}

            # Collect all ToolMessages that immediately follow
            j = i + 1
            found_ids = set()
            while j < len(messages) and isinstance(messages[j], ToolMessage):
                tid = getattr(messages[j], "tool_call_id", None)
                if tid:
                    found_ids.add(tid)
                j += 1

            # If all tool_call_ids are answered, keep the block intact
            if expected_ids <= found_ids:
                sanitized.append(msg)
            else:
                # Strip orphan tool_calls — replace with plain AIMessage
                logger.warning(
                    f"Sanitizing orphan tool_calls: expected {expected_ids}, found {found_ids}"
                )
                # Keep just the text content (if any) as a regular AIMessage
                text_content = msg.content or ""
                if text_content:
                    sanitized.append(AIMessage(content=text_content))
                # Skip the partial ToolMessages that follow
                i = j
                continue
        else:
            sanitized.append(msg)
        i += 1

    return sanitized


def agent_node(state: BioHorizonState) -> Dict[str, Any]:
    """Call the LLM (with bound tools). It decides whether to use tools or answer."""
    llm = _get_llm()

    messages = list(state["messages"])

    # Inject system prompt if not already present
    if not messages or not isinstance(messages[0], SystemMessage):
        messages.insert(0, SystemMessage(content=SYSTEM_PROMPT))

    # Sanitize: remove orphan tool_calls without matching ToolMessages
    messages = _sanitize_messages(messages)

    # Emit streaming event
    step_count = sum(1 for m in messages if isinstance(m, ToolMessage))
    events = [{"type": "thought", "content": f" Thinking... (step {step_count + 1}/{MAX_ITERATIONS})"}]

    response = llm.invoke(messages)

    return {"messages": [response], "stream_events": events}


def tool_node(state: BioHorizonState) -> Dict[str, Any]:
    """Execute all tool calls from the last AI message."""
    _, tool_map = _get_tools()

    last_message = state["messages"][-1]
    tool_calls = last_message.tool_calls or []

    new_messages: List[ToolMessage] = []
    events: List[Dict[str, Any]] = []

    for tc in tool_calls:
        tool_name = tc["name"]
        tool_args = tc["args"]
        tool_id = tc.get("id", "call_0")

        events.append({
            "type": "action",
            "content": f" Using tool: {tool_name}",
            "args": str(tool_args)[:100],
        })

        if tool_name in tool_map:
            try:
                result = tool_map[tool_name].invoke(tool_args)
                result_str = str(result)
                preview = result_str[:300] + "..." if len(result_str) > 300 else result_str
                events.append({"type": "observation", "content": " Tool result received", "preview": preview})
                new_messages.append(ToolMessage(content=result_str, tool_call_id=tool_id))
            except Exception as e:
                logger.error("[agent] Tool %s error: %s", tool_name, e)
                events.append({"type": "error", "content": f" Tool error: {str(e)}"})
                new_messages.append(ToolMessage(content=f"Error: {str(e)}", tool_call_id=tool_id))
        else:
            new_messages.append(ToolMessage(content=f"Error: Tool '{tool_name}' not found.", tool_call_id=tool_id))

    logger.info("[agent] Executed %d tool call(s): %s", len(tool_calls), [tc["name"] for tc in tool_calls])

    return {"messages": new_messages, "stream_events": events}


# ---------------------------------------------------------------------------
# Conditional edge: should the loop continue?
# ---------------------------------------------------------------------------

def should_continue(state: BioHorizonState) -> Literal["tools", "end"]:
    """Decide if we should call tools or finish."""
    last_message = state["messages"][-1]

    # If the LLM made tool calls, execute them
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        # Safety: cap iterations
        tool_msg_count = sum(1 for m in state["messages"] if isinstance(m, ToolMessage))
        if tool_msg_count >= MAX_ITERATIONS:
            logger.warning("[agent] Max iterations (%d) reached, forcing end.", MAX_ITERATIONS)
            return "end"
        return "tools"

    return "end"


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------

def build_ask_graph(checkpointer=None):
    """Build and compile the ask-graph.

    Graph topology:
        START → router → planner → agent ↔ tools → END

    - Router classifies queries into simple / ingest / signal.
    - Planner generates a plan for ingest/signal (no-op for simple).
    - All three routes share the same agent+tools ReAct loop;
      the planner just injects a plan SystemMessage for complex routes.

    Args:
        checkpointer: LangGraph checkpointer for persistence.
                      Defaults to MemorySaver (in-memory).

    Returns:
        Compiled LangGraph application.
    """
    graph = StateGraph(BioHorizonState)

    # Nodes
    graph.add_node("router", router_node)
    graph.add_node("planner", planner_node)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)

    # Edges: START → router → planner → agent ↔ tools → END
    graph.add_edge(START, "router")
    graph.add_edge("router", "planner")
    graph.add_edge("planner", "agent")
    graph.add_conditional_edges("agent", should_continue, {
        "tools": "tools",
        "end": END,
    })
    graph.add_edge("tools", "agent")

    if checkpointer is None:
        checkpointer = MemorySaver()

    return graph.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# Convenience: module-level compiled graph (singleton)
# ---------------------------------------------------------------------------

_compiled_graph = None


def get_ask_graph():
    """Return the singleton compiled ask-graph."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_ask_graph()
    return _compiled_graph
