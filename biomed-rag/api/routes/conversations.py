"""Conversation memory endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_conversations():
    """List all active conversations with metadata."""
    try:
        from deepagents.memory import ConversationMemoryManager
        conversations = ConversationMemoryManager.list_conversations()
        stats = ConversationMemoryManager.get_stats()
        return {
            "conversations": conversations,
            "stats": stats
        }
    except Exception as e:
        return {"error": str(e), "conversations": []}


@router.get("/{conversation_id}")
async def get_conversation_history(conversation_id: str, limit: int = 50):
    """Get conversation history for a specific conversation."""
    try:
        from deepagents.memory import ConversationMemoryManager
        history = ConversationMemoryManager.get_history(conversation_id, limit=limit)
        return {
            "conversation_id": conversation_id,
            "message_count": len(history),
            "messages": [
                {
                    "type": msg.__class__.__name__,
                    "content": msg.content
                }
                for msg in history
            ]
        }
    except Exception as e:
        return {"error": str(e), "messages": []}


@router.delete("/{conversation_id}")
async def clear_conversation(conversation_id: str):
    """Clear conversation history for a specific conversation."""
    try:
        from deepagents.memory import ConversationMemoryManager
        ConversationMemoryManager.clear_conversation(conversation_id)
        return {"status": "success", "message": f"Conversation {conversation_id} cleared"}
    except Exception as e:
        return {"error": str(e), "status": "failed"}


@router.post("/cleanup")
async def cleanup_conversations(keep_last_n: int = 100):
    """Cleanup old conversations, keeping only the N most active ones."""
    try:
        from deepagents.memory import ConversationMemoryManager
        ConversationMemoryManager.cleanup_old_conversations(keep_last_n=keep_last_n)
        stats = ConversationMemoryManager.get_stats()
        return {
            "status": "success",
            "message": f"Kept {keep_last_n} most active conversations",
            "stats": stats
        }
    except Exception as e:
        return {"error": str(e), "status": "failed"}
