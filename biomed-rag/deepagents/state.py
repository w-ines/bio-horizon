"""
Shared state definition for LangGraph-based Bio-Horizon agent.

This TypedDict is the single source of truth for all data flowing
through the agent graph. LangGraph nodes read from and write to this state.
"""

from typing import Annotated, Any, Dict, List, Optional, Sequence
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class BioHorizonState(TypedDict):
    """State shared across all nodes in the Bio-Horizon agent graph.

    Attributes:
        messages: Conversation messages (auto-merged by add_messages reducer).
        conversation_id: Persistent conversation identifier for memory.
        stream_events: Intermediate SSE events emitted during processing.
    """

    # Core conversation — add_messages reducer auto-deduplicates by message id
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # Conversation tracking
    conversation_id: str

    # Streaming events accumulated during the run (consumed by the API layer)
    stream_events: Annotated[List[Dict[str, Any]], lambda a, b: a + b]
