"""
LangGraph ingestion sub-graph — replaces IngestWorker.

Graph topology:
    START → search → fetch_batch → process_batch → persist_kg
                         ↑                              │
                         └──── (more batches?) ─────────┘
                                                        │
                                                  final_persist → END

The LangGraph checkpointer handles fault tolerance automatically:
if the process crashes mid-batch, restarting with the same thread_id
resumes from the last completed node.
"""

import logging

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from deepagents.nodes.ingestion import (
    IngestionState,
    search_node,
    fetch_batch_node,
    process_batch_node,
    persist_kg_node,
    final_persist_node,
    should_continue_batches,
)

logger = logging.getLogger(__name__)


def build_ingestion_graph(checkpointer=None):
    """Build and compile the ingestion sub-graph.

    Graph topology:
        START → search → fetch_batch → process_batch → persist_kg
                             ↑                              │
                             └──── should_continue ─────────┘
                                                            │
                                                      final_persist → END

    Args:
        checkpointer: LangGraph checkpointer. Defaults to MemorySaver.

    Returns:
        Compiled LangGraph application.
    """
    graph = StateGraph(IngestionState)

    # Nodes
    graph.add_node("search", search_node)
    graph.add_node("fetch_batch", fetch_batch_node)
    graph.add_node("process_batch", process_batch_node)
    graph.add_node("persist_kg", persist_kg_node)
    graph.add_node("final_persist", final_persist_node)

    # Edges
    graph.add_edge(START, "search")
    graph.add_edge("search", "fetch_batch")
    graph.add_edge("fetch_batch", "process_batch")
    graph.add_edge("process_batch", "persist_kg")

    # Loop: after persist_kg, check if there are more batches
    graph.add_conditional_edges("persist_kg", should_continue_batches, {
        "fetch_batch": "fetch_batch",
        "final_persist": "final_persist",
    })

    graph.add_edge("final_persist", END)

    if checkpointer is None:
        checkpointer = MemorySaver()

    return graph.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_compiled_graph = None


def get_ingestion_graph():
    """Return the singleton compiled ingestion graph."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_ingestion_graph()
    return _compiled_graph
