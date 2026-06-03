"""Pydantic schemas for PubMed endpoints."""

from pydantic import BaseModel
from typing import Optional, List


class PubMedSearchRequest(BaseModel):
    query: str
    max_results: int = 20
    start: int = 0
    sort: str = "relevance"
    mindate: str = ""
    maxdate: str = ""
    fetch_details: bool = True
    publication_types: Optional[List[str]] = None
    journals: Optional[List[str]] = None
    language: str = ""
    species: Optional[List[str]] = None
