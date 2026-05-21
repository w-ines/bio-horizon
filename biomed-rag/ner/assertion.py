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


def detect_assertion_bert(text: str, entity_text: str, entity_start: int = None, entity_end: int = None) -> str:
    """Detect assertion using fine-tuned PubMedBERT model.
    
    Args:
        text: Full text context
        entity_text: Entity to qualify
        entity_start: Start position of entity in text (optional)
        entity_end: End position of entity in text (optional)
    
    Returns:
        PRESENT, NEGATED, HYPOTHETICAL, or HISTORICAL
    """
    try:
        from ner.backends.assertion_bert import AssertionClassifier
        
        # Lazy-load singleton
        if not hasattr(detect_assertion_bert, "_classifier"):
            model_path = _env("ASSERTION_MODEL_PATH", "models/assertion-pubmedbert")
            detect_assertion_bert._classifier = AssertionClassifier(model_path)
        
        # Determine entity span
        if entity_start is None or entity_end is None:
            entity_start = text.lower().find(entity_text.lower())
            if entity_start == -1:
                return detect_assertion_heuristic(text, entity_text)
            entity_end = entity_start + len(entity_text)
        
        result = detect_assertion_bert._classifier.predict(text, (entity_start, entity_end))
        return result["label"]
    
    except Exception:
        return detect_assertion_heuristic(text, entity_text)


def detect_assertion(
    text: str,
    entity_text: str,
    entity_start: int = None,
    entity_end: int = None,
    use_bert: bool = None,
    use_openmed: bool = False,
    model_name: str = "assertion_detection_superclinical"
) -> str:
    """Detect assertion status for an entity.
    
    Priority chain: BERT (fine-tuned) → OpenMed → Heuristics
    
    Args:
        text: Full text context
        entity_text: Entity to qualify
        entity_start: Start position of entity in text (optional)
        entity_end: End position of entity in text (optional)
        use_bert: Whether to use fine-tuned PubMedBERT (default: from env)
        use_openmed: Whether to try OpenMed model
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
    # Default: use BERT if ASSERTION_MODEL_PATH is set
    if use_bert is None:
        use_bert = bool(_env("ASSERTION_MODEL_PATH"))
    
    if use_bert:
        return detect_assertion_bert(text, entity_text, entity_start, entity_end)
    elif use_openmed:
        return detect_assertion_openmed(text, entity_text, model_name)
    else:
        return detect_assertion_heuristic(text, entity_text)