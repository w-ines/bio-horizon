"""
Deep Agents module for bio-horizon - Biomedical Intelligence Agent.

This module provides a LangGraph-based agent implementation
with capabilities for biomedical research, RAG, and Knowledge Graph integration.

The agent is invoked via the unified /ask endpoint (api/routes/ask.py).
"""

from deepagents.agents.main_agent import create_biomedical_agent
from deepagents.graphs.ask_graph import get_ask_graph

__all__ = [
    "create_biomedical_agent",
    "get_ask_graph",
]
