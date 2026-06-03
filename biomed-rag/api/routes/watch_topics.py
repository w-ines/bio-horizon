"""
Watch Topics API routes.

Allows users to configure automated surveillance topics that trigger
weekly snapshot creation and signal detection.
"""

from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from storage.supabase_client import get_supabase_client

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class WatchTopicCreate(BaseModel):
    """Request to create a new watch topic."""
    query: str = Field(..., description="PubMed search query")
    filters: dict = Field(default_factory=dict, description="Advanced PubMed filters")
    custom_labels: List[str] = Field(default_factory=list, description="Custom entity labels for Zero-shot NER")
    frequency: str = Field("weekly", description="Execution frequency: weekly or monthly")


class WatchTopicUpdate(BaseModel):
    """Request to update an existing watch topic."""
    query: Optional[str] = None
    filters: Optional[dict] = None
    custom_labels: Optional[List[str]] = None
    frequency: Optional[str] = None
    is_active: Optional[bool] = None


class WatchTopicResponse(BaseModel):
    """Watch topic data."""
    id: int
    query: str
    filters: dict
    custom_labels: List[str]
    frequency: str
    is_active: bool
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class WatchTopicExecutionResponse(BaseModel):
    """Execution history entry."""
    id: int
    topic_id: int
    executed_at: datetime
    status: str
    articles_found: Optional[int]
    entities_extracted: Optional[int]
    snapshot_id: Optional[int]
    signals_detected: Optional[int]
    error_message: Optional[str]
    execution_time_seconds: Optional[float]


# =============================================================================
# Helper Functions
# =============================================================================

def calculate_next_run(frequency: str, from_time: datetime = None) -> datetime:
    """Calculate next execution time based on frequency."""
    base_time = from_time or datetime.utcnow()
    
    if frequency == "weekly":
        # Next Sunday at 00:00 UTC
        days_until_sunday = (6 - base_time.weekday()) % 7
        if days_until_sunday == 0:
            days_until_sunday = 7
        next_run = base_time + timedelta(days=days_until_sunday)
        return next_run.replace(hour=0, minute=0, second=0, microsecond=0)
    
    elif frequency == "monthly":
        # First day of next month at 00:00 UTC
        if base_time.month == 12:
            next_run = base_time.replace(year=base_time.year + 1, month=1, day=1)
        else:
            next_run = base_time.replace(month=base_time.month + 1, day=1)
        return next_run.replace(hour=0, minute=0, second=0, microsecond=0)
    
    else:
        raise ValueError(f"Invalid frequency: {frequency}")


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/", response_model=List[WatchTopicResponse])
async def list_watch_topics(
    active_only: bool = False,
    user_id: Optional[str] = None
):
    """
    List all watch topics.
    
    Args:
        active_only: If True, only return active topics
        user_id: Filter by user ID (optional)
    """
    try:
        supabase = get_supabase_client()
        
        query = supabase.table("watch_topics").select("*")
        
        if active_only:
            query = query.eq("is_active", True)
        
        if user_id:
            query = query.eq("user_id", user_id)
        
        query = query.order("created_at", desc=True)
        
        response = query.execute()
        
        return response.data or []
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list watch topics: {str(e)}")


@router.post("/", response_model=WatchTopicResponse)
async def create_watch_topic(topic: WatchTopicCreate):
    """
    Create a new watch topic.
    
    The scheduler will automatically execute this topic based on the frequency.
    """
    try:
        supabase = get_supabase_client()
        
        # Calculate next run time
        next_run = calculate_next_run(topic.frequency)
        
        data = {
            "query": topic.query,
            "filters": topic.filters,
            "custom_labels": topic.custom_labels,
            "frequency": topic.frequency,
            "is_active": True,
            "next_run_at": next_run.isoformat(),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        response = supabase.table("watch_topics").insert(data).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create watch topic")
        
        return response.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create watch topic: {str(e)}")


@router.get("/{topic_id}", response_model=WatchTopicResponse)
async def get_watch_topic(topic_id: int):
    """Get a specific watch topic by ID."""
    try:
        supabase = get_supabase_client()
        
        response = supabase.table("watch_topics").select("*").eq("id", topic_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail=f"Watch topic {topic_id} not found")
        
        return response.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get watch topic: {str(e)}")


@router.patch("/{topic_id}", response_model=WatchTopicResponse)
async def update_watch_topic(topic_id: int, update: WatchTopicUpdate):
    """Update an existing watch topic."""
    try:
        supabase = get_supabase_client()
        
        # Build update data
        data = {"updated_at": datetime.utcnow().isoformat()}
        
        if update.query is not None:
            data["query"] = update.query
        if update.filters is not None:
            data["filters"] = update.filters
        if update.custom_labels is not None:
            data["custom_labels"] = update.custom_labels
        if update.frequency is not None:
            data["frequency"] = update.frequency
            # Recalculate next run if frequency changed
            data["next_run_at"] = calculate_next_run(update.frequency).isoformat()
        if update.is_active is not None:
            data["is_active"] = update.is_active
        
        response = supabase.table("watch_topics").update(data).eq("id", topic_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail=f"Watch topic {topic_id} not found")
        
        return response.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update watch topic: {str(e)}")


@router.delete("/{topic_id}")
async def delete_watch_topic(topic_id: int):
    """Delete a watch topic."""
    try:
        supabase = get_supabase_client()
        
        response = supabase.table("watch_topics").delete().eq("id", topic_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail=f"Watch topic {topic_id} not found")
        
        return {"success": True, "message": f"Watch topic {topic_id} deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete watch topic: {str(e)}")


@router.get("/{topic_id}/executions", response_model=List[WatchTopicExecutionResponse])
async def get_topic_executions(topic_id: int, limit: int = 10):
    """Get execution history for a watch topic."""
    try:
        supabase = get_supabase_client()
        
        response = (
            supabase.table("watch_topic_executions")
            .select("*")
            .eq("topic_id", topic_id)
            .order("executed_at", desc=True)
            .limit(limit)
            .execute()
        )
        
        return response.data or []
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get executions: {str(e)}")
