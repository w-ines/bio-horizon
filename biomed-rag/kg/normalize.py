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


def normalize_concept_id(concept_id: str) -> str:
    """Canonicalise a concept id so equivalent ids collapse to one key.

    Uppercases the vocabulary prefix and trims whitespace, leaving the local
    id untouched (case-sensitive for things like gene symbols).

    Example:
      "mesh:D009369" -> "MESH:D009369"
      " NCBIGene:673 " -> "NCBIGENE:673"
    """
    if not concept_id:
        return ""
    cid = concept_id.strip()
    if ":" in cid:
        prefix, local = cid.split(":", 1)
        return f"{prefix.strip().upper()}:{local.strip()}"
    return cid


def make_node_id(entity_type: str, label: str, concept_id: Optional[str] = None) -> str:
    """Deterministic node id.

    Entity resolution: when a canonical ``concept_id`` is available (e.g. a
    MeSH or NCBI Gene id from PubTator3), the node identity is the canonical id
    so that every surface form of the same concept maps to a single node:
        TYPE::MESH:D009369

    Without a concept id we fall back to the normalised surface form:
        TYPE::normalised_label
    """
    if concept_id:
        normed_cid = normalize_concept_id(concept_id)
        if normed_cid:
            return f"{entity_type.upper()}::{normed_cid}"
    normed = normalize_entity_text(label)
    return f"{entity_type.upper()}::{normed}"
