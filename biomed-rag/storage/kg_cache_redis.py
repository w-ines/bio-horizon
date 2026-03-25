from __future__ import annotations

"""Redis cache for Knowledge Graph to speed up queries."""

import json
import os
from typing import Any, Dict, List, Optional

import redis
from dotenv import load_dotenv

load_dotenv()


class RedisNotConfigured(RuntimeError):
    pass


def _get_redis_client() -> redis.Redis:
    """Get Redis client from environment variables."""
    redis_url = os.getenv("REDIS_URL")
    
    if not redis_url:
        raise RedisNotConfigured("REDIS_URL not configured in .env")
    
    return redis.from_url(redis_url, decode_responses=True)


def cache_graph_snapshot(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]], ttl: int = 3600) -> bool:
    """Cache the entire graph snapshot in Redis.
    
    Args:
        nodes: List of node dicts
        edges: List of edge dicts
        ttl: Time to live in seconds (default 1 hour)
    
    Returns:
        True if cached successfully, False otherwise
    """
    try:
        client = _get_redis_client()
        
        snapshot = {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "node_count": len(nodes),
                "edge_count": len(edges),
            }
        }
        
        # Store as JSON string
        client.setex(
            "kg:snapshot",
            ttl,
            json.dumps(snapshot)
        )
        
        return True
    except (RedisNotConfigured, redis.RedisError):
        return False


def get_cached_graph_snapshot() -> Optional[Dict[str, Any]]:
    """Get cached graph snapshot from Redis.
    
    Returns:
        Dict with 'nodes' and 'edges' lists, or None if not cached
    """
    try:
        client = _get_redis_client()
        
        cached = client.get("kg:snapshot")
        if not cached:
            return None
        
        return json.loads(cached)
    except (RedisNotConfigured, redis.RedisError):
        return None


def invalidate_graph_cache() -> bool:
    """Invalidate the cached graph snapshot.
    
    Returns:
        True if invalidated successfully, False otherwise
    """
    try:
        client = _get_redis_client()
        client.delete("kg:snapshot")
        return True
    except (RedisNotConfigured, redis.RedisError):
        return False


def cache_query_result(query: str, result: Any, ttl: int = 300) -> bool:
    """Cache a query result in Redis.
    
    Args:
        query: Query string (used as cache key)
        result: Query result to cache
        ttl: Time to live in seconds (default 5 minutes)
    
    Returns:
        True if cached successfully, False otherwise
    """
    try:
        client = _get_redis_client()
        
        cache_key = f"kg:query:{hash(query)}"
        client.setex(
            cache_key,
            ttl,
            json.dumps(result)
        )
        
        return True
    except (RedisNotConfigured, redis.RedisError):
        return False


def get_cached_query_result(query: str) -> Optional[Any]:
    """Get cached query result from Redis.
    
    Args:
        query: Query string
    
    Returns:
        Cached result or None if not found
    """
    try:
        client = _get_redis_client()
        
        cache_key = f"kg:query:{hash(query)}"
        cached = client.get(cache_key)
        
        if not cached:
            return None
        
        return json.loads(cached)
    except (RedisNotConfigured, redis.RedisError):
        return None


def get_cache_stats() -> Dict[str, Any]:
    """Get Redis cache statistics.
    
    Returns:
        Dict with cache stats
    """
    try:
        client = _get_redis_client()
        
        info = client.info("stats")
        
        return {
            "connected": True,
            "total_commands_processed": info.get("total_commands_processed", 0),
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0),
            "hit_rate": (
                info.get("keyspace_hits", 0) / 
                max(1, info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0))
            ) * 100
        }
    except (RedisNotConfigured, redis.RedisError) as e:
        return {
            "connected": False,
            "error": str(e)
        }
