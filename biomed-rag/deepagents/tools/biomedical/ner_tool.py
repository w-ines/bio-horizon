"""LangChain tool wrapper for NER entity extraction.

This wrapper allows Deep Agents to extract biomedical entities.
It calls the ner.router logic with OpenMed backend.
"""

from langchain.tools import tool

from ner.router import extract_from_text


@tool
def extract_entities(
    text: str,
    entity_types: Optional[str] = None,
    enable_assertion: bool = False
) -> str:
    """Extract biomedical entities from text using OpenMed NER.
    
    Args:
        text: Input text (abstract, clinical note, etc.)
        entity_types: Comma-separated entity types (DISEASE,DRUG,GENE,PROTEIN,ANATOMY,CHEMICAL,ONCOLOGY)
                     If not provided, extracts all types
        enable_assertion: Whether to detect assertion status (PRESENT/NEGATED/HYPOTHETICAL/HISTORICAL)
    
    Returns:
        JSON string with extracted entities grouped by type
    
    Examples:
        - extract_entities("Patient started on imatinib for CML", "DRUG,DISEASE")
        - extract_entities("No hypertension detected", enable_assertion=True)
    """
    import json
    
    try:
        # Parse entity types
        types = None
        types = None
        if entity_types:
            VALID_TYPES = {"DISEASE", "DRUG", "GENE", "PROTEIN", "ANATOMY", "CHEMICAL", "ONCOLOGY"}

            types = [t.strip().upper() for t in entity_types.split(",")]

            invalid = set(types) - VALID_TYPES
            if invalid:
                return json.dumps({
                    "error": f"Invalid entity types: {sorted(invalid)}"
                }, ensure_ascii=False)

        # Extract entities using OpenMed
        result = extract_from_text(
            text=text,
            entity_types=types,
            enable_assertion=enable_assertion,
            provider="openmed"
        )
        
        if result.error:
            return json.dumps({"error": result.error}, ensure_ascii=False)
        
        # Format results for agent
        formatted = {}
        for entity_type, entities in result.entities.items():
            formatted[entity_type] = [
                {
                    "text": e.text,
                    "confidence": e.confidence,
                    "assertion": e.assertion_status if enable_assertion else None
                }
                for e in entities
            ]
        
        return json.dumps({
            "provider": result.provider,
            "entities": formatted,
            "assertion_enabled": enable_assertion
        }, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool
def extract_custom_entities(
    text: str,
    custom_labels: str
) -> str:
    """Extract custom entities using zero-shot NER (F2b).
    
    Args:
        text: Input text
        custom_labels: Comma-separated custom entity types (e.g., "BRAIN_REGION,BIOMARKER,COGNITIVE_FUNCTION")
    
    Returns:
        JSON string with extracted custom entities
    
    Examples:
        - extract_custom_entities("The hippocampus shows tau accumulation", "BRAIN_REGION,BIOMARKER")
    """
    import json
    
    try:
        labels = [l.strip().upper() for l in custom_labels.split(",")]
        
        result = extract_from_text(
            text=text,
            custom_labels=labels,
            provider="openmed"
        )
        
        if result.error:
            return json.dumps({"error": result.error}, ensure_ascii=False)
        
        formatted = {}
        for label, entities in result.entities.items():
            formatted[label] = [{"text": e.text, "confidence": e.confidence} for e in entities]
        
        return json.dumps({
            "provider": result.provider,
            "custom_labels": labels,
            "entities": formatted
        }, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)