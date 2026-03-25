"""Pydantic schemas for NER endpoints."""

from pydantic import BaseModel, Field
from typing import Optional, List


class NerExtractRequest(BaseModel):
    """
    Request schema for NER extraction.
    
    Supports:
    - F2a: Standard entity types (DISEASE, DRUG, GENE, etc.)
    - F2b: Custom zero-shot labels (BRAIN_REGION, BIOMARKER, etc.)
    - F2c: Assertion status qualification
    """
    text: str = Field(..., description="Text to extract entities from")
    entity_types: Optional[List[str]] = Field(
        None, 
        description="Standard entity types: DISEASE, DRUG, GENE, PROTEIN, ANATOMY, CHEMICAL, ONCOLOGY"
    )
    custom_labels: Optional[List[str]] = Field(
        None,
        description="Custom zero-shot labels (F2b): e.g., BRAIN_REGION, BIOMARKER, COGNITIVE_FUNCTION"
    )
    enable_assertion: bool = Field(
        False,
        description="Enable assertion status detection (F2c): PRESENT, NEGATED, HYPOTHETICAL, HISTORICAL"
    )
    provider: Optional[str] = Field(None, description="NER backend: gliner or openmed")
