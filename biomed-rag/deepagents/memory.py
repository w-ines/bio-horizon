"""
Conversation memory management for Deep Agents.

Unified memory module with dual-write strategy:
- In-memory cache for fast access (LangChain BaseMessage format)
- Supabase persistence for durability (automatic fallback if unavailable)

This module replaces the legacy memory/store.py module.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from langchain_core.messages import BaseMessage

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Supabase helpers (isolated so import errors don't break in-memory mode)
# ---------------------------------------------------------------------------

def _supabase_insert(
    message_id: str,
    conversation_id: str,
    role: str,
    content: str,
    created_at: str,
    table: str = "conversation_messages",
) -> bool:
    """Insert a message into Supabase. Returns True on success."""
    try:
        from storage.supabase_client import SupabaseNotConfigured, get_supabase_client

        client = get_supabase_client()
        payload = {
            "message_id": message_id,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "created_at": created_at,
        }
        client.table(table).upsert(payload, on_conflict="message_id").execute()
        return True
    except Exception as exc:
        logger.debug("Supabase insert skipped: %s", exc)
        return False


def _supabase_fetch(
    conversation_id: str,
    limit: int = 20,
    table: str = "conversation_messages",
) -> Optional[List[Dict[str, Any]]]:
    """Fetch messages from Supabase. Returns None if unavailable."""
    try:
        from storage.supabase_client import SupabaseNotConfigured, get_supabase_client

        client = get_supabase_client()
        limit = max(1, min(int(limit), 200))
        res = (
            client.table(table)
            .select("message_id,conversation_id,role,content,created_at")
            .eq("conversation_id", conversation_id)
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )
        data = getattr(res, "data", None)
        return data if isinstance(data, list) else []
    except Exception as exc:
        logger.debug("Supabase fetch skipped: %s", exc)
        return None


# ---------------------------------------------------------------------------
# StoredMessage — lightweight DTO for save_message / load_history interface
# ---------------------------------------------------------------------------

@dataclass
class StoredMessage:
    """A plain message record compatible with the legacy memory/store API."""
    message_id: str
    conversation_id: str
    role: str
    content: str
    created_at: str


# ---------------------------------------------------------------------------
# ConversationMemoryManager — main class (LangChain BaseMessage format)
# ---------------------------------------------------------------------------

class ConversationMemoryManager:
    """
    Manages conversation memory for Deep Agents.
    Dual-write: in-memory cache + Supabase persistence.
    """

    _conversations: Dict[str, List[BaseMessage]] = {}

    @classmethod
    def get_history(cls, conversation_id: str, limit: Optional[int] = None) -> List[BaseMessage]:
        """
        Get conversation history for a given conversation_id.

        Args:
            conversation_id: Unique conversation identifier
            limit: Maximum number of messages to return (most recent)

        Returns:
            List of messages in chronological order
        """
        history = cls._conversations.get(conversation_id, [])
        if limit:
            return history[-limit:]
        return history

    @classmethod
    def add_messages(cls, conversation_id: str, messages: List[BaseMessage]):
        """Add messages to conversation history."""
        if conversation_id not in cls._conversations:
            cls._conversations[conversation_id] = []
        cls._conversations[conversation_id].extend(messages)

    @classmethod
    def clear_conversation(cls, conversation_id: str):
        """Clear all messages for a conversation."""
        if conversation_id in cls._conversations:
            del cls._conversations[conversation_id]

    @classmethod
    def list_conversations(cls) -> List[Dict]:
        """List all active conversations with metadata."""
        return [
            {
                "conversation_id": conv_id,
                "message_count": len(messages),
                "last_message": messages[-1].content[:100] if messages else None
            }
            for conv_id, messages in cls._conversations.items()
        ]

    @classmethod
    def get_stats(cls) -> Dict:
        """Get memory statistics."""
        total_messages = sum(len(msgs) for msgs in cls._conversations.values())
        return {
            "total_conversations": len(cls._conversations),
            "total_messages": total_messages,
            "avg_messages_per_conversation": total_messages / len(cls._conversations) if cls._conversations else 0
        }

    @classmethod
    def cleanup_old_conversations(cls, keep_last_n: int = 100):
        """
        Keep only the N most recent conversations (by message count as proxy for activity).
        Useful for preventing memory overflow.
        """
        if len(cls._conversations) <= keep_last_n:
            return

        # Sort by message count (most active conversations)
        sorted_convs = sorted(
            cls._conversations.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )

        # Keep only top N
        cls._conversations = dict(sorted_convs[:keep_last_n])


# ---------------------------------------------------------------------------
# save_message / load_history — drop-in replacements for memory/store.py
# ---------------------------------------------------------------------------

_memory_fallback: Dict[str, List[StoredMessage]] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_message(
    *,
    conversation_id: str,
    role: str,
    content: str,
    created_at: Optional[str] = None,
    limit_fallback_history: int = 50,
) -> StoredMessage:
    """Save a message to Supabase with in-memory fallback.

    Drop-in replacement for ``memory.store.save_message``.
    """
    if role not in {"user", "assistant"}:
        raise ValueError("role must be 'user' or 'assistant'")

    created_at = created_at or _now_iso()
    msg = StoredMessage(
        message_id=str(uuid4()),
        conversation_id=conversation_id,
        role=role,
        content=content or "",
        created_at=created_at,
    )

    # Try Supabase first
    persisted = _supabase_insert(
        message_id=msg.message_id,
        conversation_id=conversation_id,
        role=role,
        content=content or "",
        created_at=created_at,
    )

    # Always keep in-memory fallback
    bucket = _memory_fallback.setdefault(conversation_id, [])
    bucket.append(msg)
    if len(bucket) > limit_fallback_history:
        _memory_fallback[conversation_id] = bucket[-limit_fallback_history:]

    if persisted:
        logger.debug("Message saved to Supabase: %s", msg.message_id)
    else:
        logger.debug("Message saved to in-memory fallback: %s", msg.message_id)

    return msg


def load_history(
    *,
    conversation_id: str,
    limit: int = 20,
) -> List[StoredMessage]:
    """Load conversation history from Supabase with in-memory fallback.

    Drop-in replacement for ``memory.store.load_history``.
    """
    limit = max(1, min(int(limit), 200))

    # Try Supabase first
    rows = _supabase_fetch(conversation_id=conversation_id, limit=limit)
    if rows is not None:
        return [
            StoredMessage(
                message_id=r.get("message_id") or str(uuid4()),
                conversation_id=r.get("conversation_id") or conversation_id,
                role=r.get("role") or "user",
                content=r.get("content") or "",
                created_at=r.get("created_at") or _now_iso(),
            )
            for r in rows
        ]

    # Fallback to in-memory
    return list(_memory_fallback.get(conversation_id, [])[-limit:])


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = [
    "ConversationMemoryManager",
    "StoredMessage",
    "save_message",
    "load_history",
]
