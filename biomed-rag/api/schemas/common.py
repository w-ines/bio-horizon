"""Shared Pydantic schemas used across multiple routes."""

from pydantic import BaseModel


class Query(BaseModel):
    question: str
