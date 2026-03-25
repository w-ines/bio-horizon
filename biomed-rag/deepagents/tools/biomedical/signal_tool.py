"""LangChain tool wrapper for emerging signal detection.

This wrapper allows Deep Agents to detect emerging biomedical signals.
It calls the signals module logic.
"""

from typing import Optional
from langchain.tools import tool

from signals.detector import detect_emerging_signals
from signals.consensus import compute_consensus
from signals.scoring import compute_emergence_score


@tool
def detect_signals(
    entity_pair: str,
    time_window_weeks: int = 12
) -> str:
    """Detect emerging signals for an entity pair.
    
    Args:
        entity_pair: Comma-separated entity pair (e.g., "Semaglutide,Alzheimer disease")
        time_window_weeks: Time window for comparison (default: 12 weeks)
    
    Returns:
        JSON string with detected signals and emergence scores
    
    Example:
        detect_signals("Semaglutide,Alzheimer disease", time_window_weeks=12)
    """
    import json
    
    try:
        entities = [e.strip() for e in entity_pair.split(",")]
        if len(entities) != 2:
            return json.dumps({"error": "entity_pair must contain exactly 2 entities separated by comma"}, ensure_ascii=False)
        
        entity_a, entity_b = entities
        
        # Detect signals
        signals = detect_emerging_signals(
            entity_a=entity_a,
            entity_b=entity_b,
            time_window_weeks=time_window_weeks
        )
        
        return json.dumps({
            "entity_pair": [entity_a, entity_b],
            "time_window_weeks": time_window_weeks,
            "signals": signals
        }, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool
def compute_signal_consensus(
    entity_pair: str,
    pmids: str
) -> str:
    """Compute scientific consensus for an entity relationship.
    
    Args:
        entity_pair: Comma-separated entity pair (e.g., "GLP-1,neuroprotection")
        pmids: Comma-separated PubMed IDs to analyze
    
    Returns:
        JSON string with consensus breakdown (PRESENT/NEGATED/HYPOTHETICAL/HISTORICAL percentages)
    
    Example:
        compute_signal_consensus("GLP-1,neuroprotection", "12345678,87654321,11223344")
    """
    import json
    
    try:
        entities = [e.strip() for e in entity_pair.split(",")]
        pmid_list = [p.strip() for p in pmids.split(",")]
        
        if len(entities) != 2:
            return json.dumps({"error": "entity_pair must contain exactly 2 entities"}, ensure_ascii=False)
        
        entity_a, entity_b = entities
        
        # Compute consensus
        consensus = compute_consensus(
            entity_a=entity_a,
            entity_b=entity_b,
            pmids=pmid_list
        )
        
        return json.dumps({
            "entity_pair": [entity_a, entity_b],
            "pmids_analyzed": len(pmid_list),
            "consensus": consensus
        }, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool
def score_emergence(
    entity_pair: str,
    current_frequency: int,
    previous_frequency: int,
    num_sources: int = 1
) -> str:
    """Compute emergence score for an entity relationship.
    
    Args:
        entity_pair: Comma-separated entity pair
        current_frequency: Current co-occurrence frequency
        previous_frequency: Previous co-occurrence frequency
        num_sources: Number of independent sources (default: 1)
    
    Returns:
        JSON string with emergence score (0-100)
    
    Example:
        score_emergence("Semaglutide,Alzheimer", current_frequency=15, previous_frequency=2, num_sources=5)
    """
    import json
    
    try:
        entities = [e.strip() for e in entity_pair.split(",")]
        if len(entities) != 2:
            return json.dumps({"error": "entity_pair must contain exactly 2 entities"}, ensure_ascii=False)
        
        entity_a, entity_b = entities
        
        # Compute emergence score
        score = compute_emergence_score(
            entity_a=entity_a,
            entity_b=entity_b,
            current_freq=current_frequency,
            previous_freq=previous_frequency,
            num_sources=num_sources
        )
        
        # Classify signal
        if score >= 70:
            classification = "EMERGING_SIGNAL"
        elif score >= 50:
            classification = "ACCELERATING_TREND"
        elif score >= 30:
            classification = "STABLE"
        else:
            classification = "DECLINING"
        
        return json.dumps({
            "entity_pair": [entity_a, entity_b],
            "emergence_score": score,
            "classification": classification,
            "current_frequency": current_frequency,
            "previous_frequency": previous_frequency,
            "velocity": ((current_frequency - previous_frequency) / max(previous_frequency, 1)) * 100
        }, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)