"""Relation Extraction using fine-tuned PubMedBERT from HuggingFace."""

import os
from itertools import combinations
from typing import Dict, List, Optional, Tuple

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification


class RelationClassifier:
    """Predicts relations between entity pairs using fine-tuned PubMedBERT.
    
    Uses wesin/pubmedbert-relation-extraction model with 9 relation types:
    - activates
    - inhibits
    - converts
    - causes
    - treats
    - associated_with
    - interacts_with
    - located_in
    - NO_RELATION
    """

    def __init__(self, model_path: Optional[str] = None):
        model_path = model_path or os.getenv(
            "RELATION_MODEL_PATH", "wesin/pubmedbert-relation-extraction"
        )
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
        
        # Add entity markers as special tokens
        special_tokens = {"additional_special_tokens": ["[E1]", "[/E1]", "[E2]", "[/E2]"]}
        self.tokenizer.add_special_tokens(special_tokens)
        self.model.resize_token_embeddings(len(self.tokenizer))
        
        self.model.eval()

        # Get labels from model config or use defaults
        if hasattr(self.model.config, 'id2label'):
            self.labels = [self.model.config.id2label[i] for i in range(len(self.model.config.id2label))]
        else:
            self.labels = [
                "activates", "inhibits", "converts", "causes", "treats",
                "associated_with", "interacts_with", "located_in", "NO_RELATION"
            ]

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

    def predict(self, text: str, entity1_span: Tuple[int, int],
                entity2_span: Tuple[int, int]) -> Dict:
        """Predict relation between two entities in text.

        Args:
            text: Raw text containing both entities.
            entity1_span: (start, end) character offsets of entity 1.
            entity2_span: (start, end) character offsets of entity 2.

        Returns:
            dict with 'label', 'confidence', 'entity1', 'entity2'.
        """
        s1, e1 = entity1_span
        s2, e2 = entity2_span

        # Insert markers (right-to-left to preserve offsets)
        if s1 < s2:
            marked = (text[:s1] + "[E1]" + text[s1:e1] + "[/E1]" +
                      text[e1:s2] + "[E2]" + text[s2:e2] + "[/E2]" + text[e2:])
        else:
            marked = (text[:s2] + "[E2]" + text[s2:e2] + "[/E2]" +
                      text[e2:s1] + "[E1]" + text[s1:e1] + "[/E1]" + text[e1:])

        inputs = self.tokenizer(
            marked, return_tensors="pt", truncation=True, max_length=256
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            logits = self.model(**inputs).logits
        probs = torch.softmax(logits, dim=-1)
        pred_id = torch.argmax(probs).item()

        return {
            "label": self.labels[pred_id],
            "confidence": probs[0][pred_id].item(),
            "entity1": text[s1:e1],
            "entity2": text[s2:e2],
        }


def extract_relations(
    entities: List[Dict],
    text: str,
    classifier: Optional[RelationClassifier] = None,
    min_confidence: float = 0.5,
) -> List[Tuple[str, str, str, float]]:
    """Extract relations between all entity pairs.

    Args:
        entities: List of entity dicts with 'text', 'start', 'end'.
        text: Full article/sentence text.
        classifier: Pre-loaded RelationClassifier (created if None).
        min_confidence: Minimum confidence to include relation.

    Returns:
        List of (entity1_text, relation_type, entity2_text, confidence).
    """
    if classifier is None:
        classifier = RelationClassifier()

    relations = []

    for ent1, ent2 in combinations(entities, 2):
        if ent1.get("start") is None or ent2.get("start") is None:
            continue

        result = classifier.predict(
            text,
            (ent1["start"], ent1["end"]),
            (ent2["start"], ent2["end"]),
        )

        if result["label"] != "NO_RELATION" and result["confidence"] >= min_confidence:
            relations.append((
                ent1["text"],
                result["label"],
                ent2["text"],
                result["confidence"],
            ))

    return relations
