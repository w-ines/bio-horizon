from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

class AssertionClassifier:
    def __init__(self, model_path="models/assertion-pubmedbert"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
        self.labels = ["PRESENT", "NEGATED", "HYPOTHETICAL", "HISTORICAL"]
    
    def predict(self, text, entity_span):
        # Ajouter marqueurs [E]...[/E]
        start, end = entity_span
        marked = text[:start] + "[E]" + text[start:end] + "[/E]" + text[end:]
        
        inputs = self.tokenizer(marked, return_tensors="pt", truncation=True, max_length=256)
        with torch.no_grad():
            logits = self.model(**inputs).logits
        probs = torch.softmax(logits, dim=-1)
        pred_id = torch.argmax(probs).item()
        
        return {
            "label": self.labels[pred_id],
            "confidence": probs[0][pred_id].item()
        }

# Utilisation dans le pipeline
def enrich_entities(entities, article_text):
    classifier = AssertionClassifier()
    for entity in entities:
        result = classifier.predict(article_text, (entity['start'], entity['end']))
        entity['assertion_status'] = result['label']
        entity['assertion_confidence'] = result['confidence']
    return entities