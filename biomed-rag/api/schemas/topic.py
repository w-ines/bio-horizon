"""Pydantic schemas for Topic endpoints."""

from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, List
from datetime import datetime
from uuid import UUID


class TopicCreate(BaseModel):
    query: str = Field(..., min_length=3, max_length=500)
    label: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    filters: Dict = Field(default_factory=dict)
    max_results: int = Field(default=20, ge=1, le=100)
    sort_by: Literal["relevance", "pub_date", "Author", "JournalName"] = "relevance"


class TopicUpdate(BaseModel):
    query: Optional[str] = Field(None, min_length=3, max_length=500)
    label: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    filters: Optional[Dict] = None
    max_results: Optional[int] = Field(None, ge=1, le=100)
    sort_by: Optional[Literal["relevance", "pub_date", "Author", "JournalName"]] = None
    is_active: Optional[bool] = None


class TopicResponse(BaseModel):
    id: UUID
    user_id: UUID
    query: str
    label: Optional[str]
    description: Optional[str]
    filters: Dict
    max_results: int
    sort_by: str
    is_active: bool
    last_search_at: Optional[datetime]
    last_article_date: Optional[str]
    total_articles_found: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
