"""OpenMed Assertion Status Detection - F2c

Qualifies each extracted entity with its contextual status:
- PRESENT: Affirmed/confirmed
- NEGATED: Denied/refuted  
- HYPOTHETICAL: Supposed/conditional
- HISTORICAL: Past/antecedent

Uses OpenMed Assertion models when available, falls back to heuristics.

Docs: https://openmed.life/docs/
"""

from __future__ import annotations

import os
from typing import Optional


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def detect_assertion_openmed(text: str, entity_text: str, model_name: str = "assertion_detection_superclinical") -> str:
    """Detect assertion status using OpenMed Assertion model.
    
    Args:
        text: Full text context
        entity_text: Entity to qualify
        model_name: OpenMed assertion model
    
    Returns:
        PRESENT, NEGATED, HYPOTHETICAL, or HISTORICAL
    """
    try:
        from openmed import analyze_text
        
        result = analyze_text(
            text,
            model_name=model_name,
            confidence_threshold=0.6,
        )
        
        if not result or not hasattr(result, 'entities'):
            return "PRESENT"
        
        # Map OpenMed assertion labels to our schema
        for entity in result.entities:
            entity_label = getattr(entity, 'label', '').upper()
            
            if entity_label in ['NEGATED', 'ABSENT', 'NEGATIVE']:
                return "NEGATED"
            elif entity_label in ['HYPOTHETICAL', 'POSSIBLE', 'CONDITIONAL']:
                return "HYPOTHETICAL"
            elif entity_label in ['HISTORICAL', 'PAST', 'HISTORY']:
                return "HISTORICAL"
            elif entity_label in ['PRESENT', 'AFFIRMED', 'CONFIRMED']:
                return "PRESENT"
        
        return "PRESENT"
    
    except Exception:
        # Fallback to heuristics
        return detect_assertion_heuristic(text, entity_text)


def detect_assertion_heuristic(text: str, entity_text: str) -> str:
    """Heuristic-based assertion detection (fallback).
    
    Args:
        text: Full text context
        entity_text: Entity to qualify
    
    Returns:
        PRESENT, NEGATED, HYPOTHETICAL, or HISTORICAL
    """
    text_lower = text.lower()
    entity_lower = entity_text.lower()
    
    # Find sentence containing the entity
    sentences = text.split('.')
    context = ""
    for sent in sentences:
        if entity_lower in sent.lower():
            context = sent.lower()
            break
    
    if not context:
        return "PRESENT"
    
    # Negation patterns (highest priority)
    negation_patterns = [
        "no ", "not ", "without ", "absence of", "lack of",
        "negative for", "ruled out", "excluded", "denied",
        "free of", "absent", "never", "unlikely", "improbable",
        "does not have", "did not have", "no evidence of",
        "no sign of", "no indication of", "fails to show",
        "unremarkable for", "clear of"
    ]
    for pattern in negation_patterns:
        if pattern in context:
            return "NEGATED"
    
    # Hypothetical patterns
    hypothetical_patterns = [
        "may ", "might ", "could ", "would ", "should ",
        "potential", "possible", "hypothesis", "suggest",
        "further studies", "needs to be", "remains to be",
        "if ", "whether ", "unclear", "suspected", "presumed",
        "likely", "probably", "possibly", "consider", "evaluate for",
        "rule out", "differential", "questionable"
    ]
    for pattern in hypothetical_patterns:
        if pattern in context:
            return "HYPOTHETICAL"
    
    # Historical patterns
    historical_patterns = [
        "history of", "previous", "prior", "past", "former",
        "previously", "had been", "was diagnosed", "antecedent",
        "old ", "chronic"
    ]
    for pattern in historical_patterns:
        if pattern in context:
            return "HISTORICAL"
    
    return "PRESENT"


def detect_assertion(
    text: str,
    entity_text: str,
    use_openmed: bool = False,
    model_name: str = "assertion_detection_superclinical"
) -> str:
    """Detect assertion status for an entity.
    
    Args:
        text: Full text context
        entity_text: Entity to qualify
        use_openmed: Whether to try OpenMed model first
        model_name: OpenMed assertion model name
    
    Returns:
        PRESENT, NEGATED, HYPOTHETICAL, or HISTORICAL
    
    Examples:
        >>> detect_assertion("Patient has no hypertension", "hypertension")
        'NEGATED'
        
        >>> detect_assertion("Further trials may confirm efficacy", "efficacy")
        'HYPOTHETICAL'
        
        >>> detect_assertion("History of diabetes", "diabetes")
        'HISTORICAL'
        
        >>> detect_assertion("Patient presents with fever", "fever")
        'PRESENT'
    """
    if use_openmed:
        return detect_assertion_openmed(text, entity_text, model_name)
    else:
        return detect_assertion_heuristic(text, entity_text)