from __future__ import annotations

import re
import unicodedata
from typing import Optional


def normalize_entity_text(text: str) -> str:
    """Produce a canonical key from a raw entity surface form.

    Steps:
      1. Unicode NFKD normalisation + strip accents
      2. Lowercase
      3. Collapse whitespace
      4. Strip leading/trailing punctuation
      5. Collapse hyphens

    Example:
      "  Myocardial   Infarction " -> "myocardial infarction"
      "COVID-19" -> "covid-19"
      "BRCA1 " -> "brca1"
    """
    if not text:
        return ""
    # NFKD decompose, strip combining marks (accents)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = text.strip(".,;:!?()[]{}\"'")
    return text


def make_node_id(entity_type: str, label: str) -> str:
    """Deterministic node id = TYPE::normalised_label."""
    normed = normalize_entity_text(label)
    return f"{entity_type.upper()}::{normed}"
