"""
Deep Agents module for bio-horizon - Biomedical Intelligence Agent.

This module provides a LangChain Deep Agents implementation
with capabilities for biomedical research, RAG, and Knowledge Graph integration.

The Deep Agent is invoked via the unified /ask endpoint (api/routes/ask.py).
"""

from deepagents.agents.main_agent import create_biomedical_agent

__all__ = [
    "create_biomedical_agent",
]
