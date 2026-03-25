"""Cache management endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/stats")
async def cache_stats():
    """Returns query cache statistics."""
    try:
        from deepagents.tools.document.query_cache import get_cache_stats
        stats = get_cache_stats()
        return stats
    except ImportError:
        return {"error": "Cache not available", "enabled": False}


@router.post("/clear")
async def clear_cache():
    """Clears the query cache."""
    try:
        from deepagents.tools.document.query_cache import clear_cache
        clear_cache()
        return {"status": "cache cleared", "success": True}
    except ImportError:
        return {"error": "Cache not available", "success": False}
