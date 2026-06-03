"""Pydantic schemas for User endpoints."""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal
from datetime import time, datetime
from uuid import UUID


class UserCreate(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    password: str = Field(..., min_length=6)
    frequency: Literal["daily", "weekly", "biweekly", "monthly"] = "daily"
    delivery_time: time = time(8, 0)
    timezone: str = "UTC"
    language: str = "en"


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    frequency: Optional[Literal["daily", "weekly", "biweekly", "monthly"]] = None
    delivery_time: Optional[time] = None
    timezone: Optional[str] = None
    language: Optional[str] = None


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str]
    frequency: str
    delivery_time: time
    timezone: str
    language: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
