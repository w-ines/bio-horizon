"""Topic tracking endpoints (CRUD)."""

from fastapi import APIRouter, HTTPException
from typing import List

from api.schemas.topic import TopicCreate, TopicUpdate, TopicResponse
from services.topic_service import TopicService

router = APIRouter()


@router.post("/", response_model=TopicResponse, status_code=201)
async def create_topic(user_id: str, topic: TopicCreate):
    """Create a new topic for a user."""
    try:
        result = TopicService.create(user_id, topic)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[TopicResponse])
async def list_topics(user_id: str):
    """List all active topics for a user."""
    return TopicService.list_by_user(user_id)


@router.get("/{topic_id}", response_model=TopicResponse)
async def get_topic(topic_id: str):
    """Get a specific topic."""
    result = TopicService.get_by_id(topic_id)
    if not result:
        raise HTTPException(status_code=404, detail="Topic not found")
    return result


@router.put("/{topic_id}", response_model=TopicResponse)
async def update_topic(topic_id: str, topic: TopicUpdate):
    """Update a topic (query, filters, status, etc.)."""
    result = TopicService.update(topic_id, topic)
    if not result:
        raise HTTPException(status_code=404, detail="Topic not found")
    return result


@router.delete("/{topic_id}")
async def delete_topic(topic_id: str):
    """Soft-delete a topic."""
    success = TopicService.delete(topic_id)
    if not success:
        raise HTTPException(status_code=404, detail="Topic not found")
    return {"status": "deleted", "topic_id": topic_id}


@router.post("/{topic_id}/search")
async def trigger_topic_search(topic_id: str):
    """Manually trigger a PubMed search for a topic."""
    try:
        result = TopicService.execute_search(topic_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
