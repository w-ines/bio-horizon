"""PubTator3 NER Backend — Pre-computed entity annotations from NCBI.

PubTator3 has already annotated 36M+ PubMed articles using state-of-the-art
NLP models. Instead of running NER locally, we fetch pre-computed annotations
via a single HTTP GET.  ~1-2 seconds for 100 articles vs minutes with local ML.

API docs: https://www.ncbi.nlm.nih.gov/research/pubtator3/
Paper:     https://academic.oup.com/nar/article/52/W1/W540/7640526

Entity types returned by PubTator3:
  Gene, Disease, Chemical, Species, Mutation, CellLine

Mapping to Bio-Horizon types:
  Gene     → GENE
  Disease  → DISEASE
  Chemical → DRUG  (chemicals include drugs in PubTator3)
  Species  → SPECIES
  Mutation → MUTATION
  CellLine → CELLLINE
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Iterable, List, Mapping, Optional

import requests

from ner.schemas import NerEntity, NerResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PUBTATOR3_BASE_URL = "https://www.ncbi.nlm.nih.gov/research/pubtator3-api"
PUBTATOR3_EXPORT_ENDPOINT = f"{PUBTATOR3_BASE_URL}/publications/export/biocjson"

# Max PMIDs per request (keep under 50 for reliability)
PUBTATOR3_BATCH_SIZE = 50

# A well-known PMID guaranteed to exist in PubTator3 (BRAF paper, 2002).
# Injected into every batch to prevent 400 when all user PMIDs are too recent.
_SENTINEL_PMID = "12068308"

# PubTator3 relation type (BioREx) → Bio-Horizon relation type
RELATION_TYPE_MAP: Dict[str, str] = {
    "Association":          "associated_with",
    "Positive_Correlation": "activates",
    "Negative_Correlation": "inhibits",
    "Bind":                 "binds",
    "Conversion":           "converts",
    "Cotreatment":          "cotreatment",
    "Comparison":           "associated_with",
    "Predisposes":          "predisposes",
}

# PubTator3 entity type → Bio-Horizon type
TYPE_MAP: Dict[str, str] = {
    "Gene": "GENE",
    "Disease": "DISEASE",
    "Chemical": "DRUG",
    "Species": "SPECIES",
    "Mutation": "MUTATION",
    "CellLine": "CELLLINE",
    # Some older annotations may use these
    "DNAMutation": "MUTATION",
    "ProteinMutation": "MUTATION",
    "SNP": "MUTATION",
}

# Default entity types to keep (subset most useful for KG)
DEFAULT_TYPES = {"GENE", "DISEASE", "DRUG", "MUTATION"}


def _get_timeout() -> int:
    return int(os.getenv("PUBTATOR3_TIMEOUT", "30"))


# ---------------------------------------------------------------------------
# Core API call
# ---------------------------------------------------------------------------

def _fetch_annotations_raw(pmids: List[str]) -> List[Dict[str, Any]]:
    """Fetch PubTator3 annotations for a list of PMIDs.

    Injects a sentinel PMID to guarantee the API returns 200 even when
    all requested PMIDs are too recent to be indexed.  The sentinel is
    stripped from the returned documents.

    Args:
        pmids: List of PubMed IDs (strings).  Max PUBTATOR3_BATCH_SIZE per call.

    Returns:
        List of BioC JSON document dicts, one per article (sentinel excluded).
    """
    if not pmids:
        return []

    # Inject sentinel so the API never returns 400 for all-new batches
    query_pmids = list(pmids[:PUBTATOR3_BATCH_SIZE])
    sentinel_injected = False
    if _SENTINEL_PMID not in query_pmids:
        query_pmids.append(_SENTINEL_PMID)
        sentinel_injected = True

    pmids_str = ",".join(str(p) for p in query_pmids)
    url = f"{PUBTATOR3_EXPORT_ENDPOINT}?pmids={pmids_str}"

    timeout = _get_timeout()
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
    except requests.exceptions.RequestException as exc:
        logger.warning("PubTator3 request failed: %s", exc)
        return []

    import json
    try:
        data = resp.json()
    except json.JSONDecodeError:
        logger.error("PubTator3: invalid JSON response")
        return []

    # PubTator3 returns {"PubTator3": [doc1, doc2, ...]}
    documents: List[Dict[str, Any]] = []
    if isinstance(data, dict) and "PubTator3" in data:
        raw = data["PubTator3"]
        documents = raw if isinstance(raw, list) else []
    elif isinstance(data, list):
        documents = data
    elif isinstance(data, dict):
        documents = [data]

    # Remove sentinel from results
    if sentinel_injected:
        documents = [
            d for d in documents
            if str(d.get("id", d.get("_id", ""))).split("|")[0] != _SENTINEL_PMID
        ]

    return documents


# ---------------------------------------------------------------------------
# BioC JSON → NerResult conversion
# ---------------------------------------------------------------------------

def _parse_bioc_document(
    doc: Dict[str, Any],
    entity_types: Optional[set] = None,
) -> NerResult:
    """Convert a single BioC JSON document into a NerResult.

    Parses both entities (PubTator3 NER) and relations (BioREx) from the
    BioC JSON. Relations are returned as (subject_text, relation_type, object_text)
    triplets, with relation types mapped to Bio-Horizon conventions.

    Args:
        doc: BioC JSON dict from PubTator3
        entity_types: Set of Bio-Horizon entity types to keep (e.g. {"GENE", "DISEASE"}).
                      None = keep DEFAULT_TYPES.
    """
    keep = entity_types or DEFAULT_TYPES

    entities_by_type: Dict[str, List[NerEntity]] = {t: [] for t in keep}
    seen: Dict[str, set] = {t: set() for t in keep}  # dedup by (type, text)

    # Build lookup tables for relation resolution:
    #   annotation_id → entity text
    #   identifier (MeSH/NCBI) → entity text
    ann_id_to_text: Dict[str, str] = {}
    identifier_to_text: Dict[str, str] = {}

    for passage in doc.get("passages", []):
        for ann in passage.get("annotations", []):
            infons = ann.get("infons", {})
            raw_type = infons.get("type", "")
            mapped = TYPE_MAP.get(raw_type)

            text = ann.get("text", "").strip()
            ann_id = ann.get("id", "")
            identifier = (infons.get("identifier") or infons.get("id") or "").strip()

            # Populate lookup tables regardless of whether entity type is kept
            if text:
                if ann_id:
                    ann_id_to_text[ann_id] = text
                if identifier and identifier != "None":
                    identifier_to_text[identifier] = text

            if not mapped or mapped not in keep:
                continue
            if not text or len(text) < 2:
                continue

            # Deduplicate within same article
            key = text.lower()
            if key in seen[mapped]:
                continue
            seen[mapped].add(key)

            # Location info
            locations = ann.get("locations", [])
            start = locations[0].get("offset") if locations else None
            length = locations[0].get("length") if locations else None
            end = (start + length) if (start is not None and length is not None) else None

            entities_by_type[mapped].append(
                NerEntity(
                    text=text,
                    confidence=1.0,  # Pre-computed by NCBI — high confidence
                    start=start,
                    end=end,
                    label=mapped,
                    assertion_status=None,
                )
            )

    # Parse BioREx relations from document-level relations array
    relations = []
    for rel in doc.get("relations", []):
        infons = rel.get("infons", {})
        rel_type_raw = infons.get("type", "")
        rel_type = RELATION_TYPE_MAP.get(rel_type_raw)
        if not rel_type:
            continue

        subj = obj = ""

        # Format A: role1/role2 dicts with normalized_name or identifier
        role1 = infons.get("role1")
        role2 = infons.get("role2")
        if isinstance(role1, dict) and isinstance(role2, dict):
            subj = (role1.get("normalized_name") or "").strip()
            if not subj:
                subj = identifier_to_text.get(role1.get("identifier", ""), "")
            obj = (role2.get("normalized_name") or "").strip()
            if not obj:
                obj = identifier_to_text.get(role2.get("identifier", ""), "")

        # Format B: entity1/entity2 as annotation IDs or identifiers
        if not (subj and obj):
            ent1 = str(infons.get("entity1", "")).strip()
            ent2 = str(infons.get("entity2", "")).strip()
            if ent1 and ent2:
                subj = ann_id_to_text.get(ent1) or identifier_to_text.get(ent1, "")
                obj = ann_id_to_text.get(ent2) or identifier_to_text.get(ent2, "")

        # Format C: nodes array with refid fields
        if not (subj and obj):
            nodes = rel.get("nodes", [])
            if len(nodes) >= 2:
                subj = ann_id_to_text.get(nodes[0].get("refid", ""), "")
                obj = ann_id_to_text.get(nodes[1].get("refid", ""), "")

        if subj and obj and subj.lower() != obj.lower():
            relations.append((subj, rel_type, obj))

    logger.debug(
        "PubTator3: parsed %d relations from doc %s",
        len(relations), doc.get("pmid", doc.get("id", "?")),
    )

    return NerResult(
        entities=entities_by_type,
        provider="pubtator3",
        error=None,
        relations=relations,
    )


# ---------------------------------------------------------------------------
# Public API  (same interface as openmed_backend / gliner_backend)
# ---------------------------------------------------------------------------

def extract_by_pmids(
    pmids: List[str],
    *,
    entity_types: Optional[Iterable[str]] = None,
) -> Dict[str, NerResult]:
    """Batch-fetch PubTator3 annotations for a list of PMIDs.

    This is the main entry point.  It handles chunking (max 50 per request)
    and returns a dict keyed by PMID.

    PMIDs not found in PubTator3 (e.g. very recent articles not yet indexed)
    get an empty NerResult with an informational error message.

    Args:
        pmids: PubMed IDs
        entity_types: Optional filter on Bio-Horizon entity types

    Returns:
        Dict mapping PMID → NerResult
    """
    keep = set(t.strip().upper() for t in (entity_types or DEFAULT_TYPES))

    results: Dict[str, NerResult] = {}

    # Chunk into batches of PUBTATOR3_BATCH_SIZE
    for i in range(0, len(pmids), PUBTATOR3_BATCH_SIZE):
        chunk = pmids[i : i + PUBTATOR3_BATCH_SIZE]
        docs = _fetch_annotations_raw(chunk)

        for doc in docs:
            # Extract PMID from BioC document
            pmid = str(doc.get("pmid", doc.get("id", "")))
            if not pmid:
                # Try _id field (format: "12068308|None")
                raw_id = str(doc.get("_id", ""))
                pmid = raw_id.split("|")[0] if raw_id else ""
            if pmid:
                results[pmid] = _parse_bioc_document(doc, keep)

    found = sum(1 for r in results.values() if r.error is None)
    missing = len(pmids) - found

    # Fill missing PMIDs with empty results
    empty = NerResult(
        entities={t: [] for t in keep},
        provider="pubtator3",
        error="PMID not yet indexed by PubTator3 (recently published article)",
    )
    for pmid in pmids:
        if pmid not in results:
            results[pmid] = empty

    if missing > 0:
        logger.info(
            "PubTator3: fetched %d/%d PMIDs (%d recent/unindexed)",
            found, len(pmids), missing,
        )
    else:
        logger.info("PubTator3: fetched annotations for all %d PMIDs", len(pmids))

    return results


def extract_batch_from_articles(
    articles: List[Mapping[str, Any]],
    *,
    entity_types: Optional[Iterable[str]] = None,
) -> List[NerResult]:
    """Extract entities from articles using PubTator3.

    Compatible with the interface expected by ner/router.py extract_batch.
    Articles must have a 'pmid' key.

    Args:
        articles: List of article dicts with at least a 'pmid' key
        entity_types: Entity types to extract

    Returns:
        List of NerResult, one per article, in the same order as input
    """
    pmids = [str(a.get("pmid", "")).strip() for a in articles]
    valid_pmids = [p for p in pmids if p]

    if not valid_pmids:
        keep = set(t.strip().upper() for t in (entity_types or DEFAULT_TYPES))
        return [
            NerResult(entities={t: [] for t in keep}, provider="pubtator3", error="No PMID")
            for _ in articles
        ]

    by_pmid = extract_by_pmids(valid_pmids, entity_types=entity_types)

    results: List[NerResult] = []
    keep = set(t.strip().upper() for t in (entity_types or DEFAULT_TYPES))
    empty = NerResult(entities={t: [] for t in keep}, provider="pubtator3", error="No PMID")

    for pmid in pmids:
        results.append(by_pmid.get(pmid, empty))

    return results
