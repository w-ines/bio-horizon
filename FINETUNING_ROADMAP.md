# Fine-tuning Roadmap — Assertion Status & Relation Extraction

> Le NER standard est déjà résolu par PubTator3 (36M+ articles pré-annotés, gratuit, rapide).
> Le **vrai goulot** du pipeline BioHorizon se situe en aval : qualifier les entités et typer les relations.

---

## 1. Le Problème

### Assertion Status (absent)

PubTator3 extrait les entités mais ne dit **jamais** si elles sont affirmées, niées ou hypothétiques.

```
Texte : "No cognitive improvement was observed with semaglutide."
PubTator3 : ✅ DRUG:semaglutide, DISEASE:cognitive improvement
Assertion : ❌ Non fourni → le KG traite tout comme PRESENT
```

**Conséquence** : Le consensus scoring mélange résultats positifs et négatifs → signaux émergents bruités, faux positifs.

### Relation Extraction (absent)

Le KG ne contient que des co-occurrences brutes (A et B mentionnés dans le même article). Aucune sémantique.

```
Actuel  : Semaglutide ↔ Alzheimer (co_occurrence, weight=5)
Cible   : Semaglutide --TREATS--> Alzheimer (confirmé, 3 sources)
          Semaglutide --NO_EFFECT--> cognitive decline (réfuté, 1 source)
```

**Conséquence** : Impossible de distinguer "traite", "cause", "inhibe", "est associé à" → le drug repurposing et le signal scoring restent superficiels.

---

## 2. Impact sur BioHorizon

| Composant | Sans fine-tuning | Avec fine-tuning |
|-----------|-----------------|-----------------|
| **Consensus Scoring** | Bruité (tout = PRESENT) | Précis (PRESENT/NEGATED/HYPOTHETICAL) |
| **Knowledge Graph** | Arêtes co-occurrence only | Arêtes typées (TREATS, CAUSES, INHIBITS) |
| **Signal Detection** | Basé sur le nombre de mentions | Basé sur la sémantique des relations |
| **Drug Repurposing** | Approximatif | Relations drug→disease qualifiées |
| **Contradiction Detection** | Impossible | Natif (PRESENT vs NEGATED sur même paire) |

---

## 3. Pipeline A — Assertion Status Classifier

### Objectif

Classifier chaque entité NER extraite en : **PRESENT | NEGATED | HYPOTHETICAL | HISTORICAL**

### Modèle

| Paramètre | Valeur |
|-----------|--------|
| Base | `microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract` |
| Tâche | Sequence Classification (4 classes) |
| Input | Phrase contenant l'entité + marqueurs de position `[E]entity[/E]` |
| Output | Label d'assertion + score de confiance |
| Taille | ~110M params (BERT-base) |

### Datasets d'entraînement

| Dataset | Taille | Source | Annotations |
|---------|--------|--------|-------------|
| **n2c2 2010 (i2b2)** | 871 rapports cliniques | Harvard/Partners | Assertion (present, absent, possible, conditional, hypothetical, associated) |
| **BioScope** | 20K phrases | Biomedical abstracts + clinical | Négation + spéculation (spans annotés) |
| **NegEx / NegBio** | Règles + corpus | NLM | Patterns de négation biomédicale |
| **SFU Review Corpus** | 400 docs | Simon Fraser University | Négation + spéculation |

### Étapes

```
1. Préparer les données
   - Télécharger n2c2 2010 + BioScope
   - Convertir au format : (phrase_avec_marqueurs, label_assertion)
   - Split train/val/test : 80/10/10

2. Fine-tuning
   - Charger PubMedBERT
   - Ajouter une tête de classification (4 classes)
   - Entraîner 5-10 epochs, lr=2e-5, batch_size=16
   - Early stopping sur val F1-macro

3. Évaluation
   - F1-score par classe (objectif : >0.85 macro)
   - Matrice de confusion (attention aux HYPOTHETICAL vs HISTORICAL)
   - Comparaison avec heuristique actuelle (baseline)

4. Intégration
   - Nouveau backend : ner/backends/assertion_bert.py
   - Appelé après PubTator3 : pour chaque entité → classifier l'assertion
   - Stockage : champ assertion_status sur kg_nodes + kg_edges
```

### Exemple de code (skeleton)

```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

LABELS = ["PRESENT", "NEGATED", "HYPOTHETICAL", "HISTORICAL"]

class AssertionClassifier:
    def __init__(self, model_path="./models/assertion-pubmedbert"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_path, num_labels=4
        )

    def predict(self, sentence: str, entity_span: tuple[int, int]) -> dict:
        """
        sentence: "No cognitive improvement was observed."
        entity_span: (3, 25)  # "cognitive improvement"
        """
        # Insérer les marqueurs autour de l'entité
        marked = (
            sentence[:entity_span[0]]
            + "[E]" + sentence[entity_span[0]:entity_span[1]] + "[/E]"
            + sentence[entity_span[1]:]
        )
        inputs = self.tokenizer(marked, return_tensors="pt", truncation=True)
        logits = self.model(**inputs).logits
        probs = torch.softmax(logits, dim=-1)[0]
        idx = probs.argmax().item()
        return {"label": LABELS[idx], "confidence": probs[idx].item()}
```

---

## 4. Pipeline B — Relation Extraction

### Objectif

Extraire des relations typées entre paires d'entités : **TREATS | CAUSES | INHIBITS | ASSOCIATED_WITH | NO_RELATION**

### Modèle

| Paramètre | Valeur |
|-----------|--------|
| Base | `microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract` ou `BioLinkBERT-base` |
| Tâche | Relation Classification (5+ classes) |
| Input | Phrase avec deux entités marquées `[E1]...[/E1]` et `[E2]...[/E2]` |
| Output | Type de relation + score |
| Taille | ~110M params |

### Datasets d'entraînement

| Dataset | Taille | Relations | Source |
|---------|--------|-----------|--------|
| **BioRED** | 600 articles, 6K+ relations | TREATS, CAUSES, ASSOCIATED, POSITIVE/NEGATIVE correlation | NCBI (2022) |
| **ChemProt** | 2.4K abstracts, 23K relations | Substrate, Inhibitor, Agonist, Antagonist, etc. | BioCreative VI |
| **DDI Corpus** | 1K docs, 5K relations | Drug-Drug Interactions (effect, mechanism, advise, int) | SemEval 2013 |
| **GAD** | 5K phrases | Gene-Disease associations (positive/negative) | Genetic Association DB |

### Étapes

```
1. Préparer les données
   - BioRED (prioritaire) : télécharger depuis NCBI
   - Convertir : (phrase_avec_marqueurs_E1_E2, label_relation)
   - Filtrer les types de relations pertinents pour BioHorizon
   - Split train/val/test : 80/10/10

2. Fine-tuning
   - Charger PubMedBERT / BioLinkBERT
   - Tête de classification (5+ classes)
   - Entraîner 10-15 epochs, lr=2e-5, batch_size=16
   - Weighted loss (NO_RELATION est la classe majoritaire)

3. Évaluation
   - F1-score par type de relation (objectif : >0.75 macro)
   - Precision@K pour le drug repurposing
   - Comparaison avec co-occurrence baseline

4. Intégration
   - Nouveau module : ner/backends/relation_bert.py
   - Appelé après NER : pour chaque paire d'entités dans un abstract
   - Stockage : champ relation_type enrichi sur kg_edges
     "co_occurrence" → "TREATS" / "CAUSES" / "INHIBITS" / etc.
```

### Exemple de code (skeleton)

```python
RELATIONS = ["TREATS", "CAUSES", "INHIBITS", "ASSOCIATED_WITH", "NO_RELATION"]

class RelationExtractor:
    def __init__(self, model_path="./models/relation-pubmedbert"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_path, num_labels=len(RELATIONS)
        )

    def predict(self, sentence: str, e1_span: tuple, e2_span: tuple) -> dict:
        """
        sentence: "Semaglutide shows neuroprotective effects in Alzheimer."
        e1_span: (0, 11)    # "Semaglutide"
        e2_span: (48, 57)   # "Alzheimer"
        """
        # Insérer les marqueurs (ordre croissant de position)
        spans = sorted([(e1_span, "E1"), (e2_span, "E2")], key=lambda x: x[0][0])
        marked = self._insert_markers(sentence, spans)

        inputs = self.tokenizer(marked, return_tensors="pt", truncation=True)
        logits = self.model(**inputs).logits
        probs = torch.softmax(logits, dim=-1)[0]
        idx = probs.argmax().item()
        return {"relation": RELATIONS[idx], "confidence": probs[idx].item()}
```

---

## 5. Impact sur le Schéma KG

### Avant (actuel)

```sql
-- kg_edges : co-occurrence uniquement
source_id  | target_id           | weight | relation_type
DRUG::smg  | DISEASE::alzheimer  | 5      | co_occurrence
```

### Après (enrichi)

```sql
-- kg_edges : relations typées + assertion
source_id  | target_id           | weight | relation_type | assertion    | confidence
DRUG::smg  | DISEASE::alzheimer  | 3      | TREATS        | PRESENT      | 0.91
DRUG::smg  | DISEASE::alzheimer  | 1      | TREATS        | NEGATED      | 0.87
DRUG::smg  | DISEASE::alzheimer  | 1      | TREATS        | HYPOTHETICAL | 0.83
```

Consensus = 3 PRESENT / 5 total = **60% confirmé**, 20% réfuté, 20% hypothétique → signal **qualifié**.

---

## 6. Ressources et Coûts Estimés

| Ressource | Pipeline A (Assertion) | Pipeline B (Relation) |
|-----------|----------------------|----------------------|
| **GPU** | 1x T4/A10 (4-8h) | 1x T4/A10 (8-16h) |
| **Données** | n2c2 + BioScope (~30K exemples) | BioRED + ChemProt (~30K exemples) |
| **Stockage modèle** | ~440 MB | ~440 MB |
| **Inférence** | ~5ms/phrase (GPU), ~50ms (CPU) | ~5ms/paire (GPU), ~50ms (CPU) |
| **Temps total** | 1-2 semaines (données → modèle déployé) | 2-3 semaines |

### Overhead pipeline complet (par batch de 500 articles)

```
Actuel :  PubTator3 NER        → 2-4s    → KG (co-occurrence)
Enrichi : PubTator3 NER (2-4s)
          + Assertion (500×5ms) → +2.5s
          + Relations (2K×5ms)  → +10s
          = ~15-17s total       → KG (typé + qualifié)
```

Surcoût acceptable (~4x) pour un gain qualitatif majeur.

---

## 7. Ordre d'Exécution Recommandé

```
Semaine 1-2 : Pipeline A — Assertion Status
  ├── Télécharger n2c2 + BioScope
  ├── Préparer le dataset (format marqueurs)
  ├── Fine-tuner PubMedBERT (4 classes)
  ├── Évaluer (F1 > 0.85)
  └── Intégrer dans ner/backends/assertion_bert.py

Semaine 3-4 : Pipeline B — Relation Extraction
  ├── Télécharger BioRED + ChemProt
  ├── Préparer le dataset (paires d'entités marquées)
  ├── Fine-tuner PubMedBERT (5+ classes)
  ├── Évaluer (F1 > 0.75)
  └── Intégrer dans ner/backends/relation_bert.py

Semaine 5 : Mise à jour du KG
  ├── Migrer kg_edges (ajout colonnes assertion, relation enrichie)
  ├── Re-processer les articles existants avec les nouveaux modèles
  ├── Mettre à jour l'API /kg/graph (filtres par relation_type, assertion)
  └── Mettre à jour le frontend (couleurs arêtes par type de relation)

Semaine 6 : Signal Scoring v2
  ├── Intégrer assertion dans le consensus scoring
  ├── Pondérer les signaux par type de relation
  └── Évaluer la qualité des signaux émergents détectés
```




PHASE 1 : ENTRAÎNEMENT (une seule fois, hors-ligne)
┌────────────────────────────────┐
│  Datasets annotés par humains  │    ← n2c2, BioRED, ChemProt
│  (phrases + labels manuels)    │
└───────────────┬────────────────┘
                │ fine-tuning
                ▼
┌────────────────────────────────┐
│  Modèle fine-tuné              │    ← assertion_classifier.pt
│  (PubMedBERT spécialisé)      │       relation_extractor.pt
└───────────────┬────────────────┘
                │ sauvegardé
                ▼

PHASE 2 : UTILISATION (en continu, dans BioHorizon)
┌────────────────────────────────┐
│  Articles PubMed (quotidien)   │    ← Source de BioHorizon
└───────────────┬────────────────┘
                │ PubTator3 → entités
                ▼
┌────────────────────────────────┐
│  Modèle fine-tuné appliqué     │    ← Enrichit chaque entité/paire
│  sur les articles PubMed       │
└───────────────┬────────────────┘
                │
                ▼
┌────────────────────────────────┐
│  KG enrichi                    │    ← Relations typées + assertions
│  (BioHorizon amélioré)         │
└────────────────────────────────┘