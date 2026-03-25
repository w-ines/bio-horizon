# NER Entity Extraction — Use Case Documentation

## Vue d'ensemble

L'extraction d'entités nommées (NER - Named Entity Recognition) est le **cœur du système BioHorizon**. Elle transforme du texte biomédical non structuré en entités médicales structurées qui alimentent le Knowledge Graph et la détection de signaux.

---

## Cas d'Usage Principal

### **Scénario : Surveillance de la Recherche sur Alzheimer**

Un chercheur souhaite surveiller l'évolution des traitements pour la maladie d'Alzheimer.

#### **Étape 1 : Collecte de Données**

Le système interroge PubMed avec la requête :
```
"Alzheimer disease" AND ("treatment" OR "therapy" OR "drug")
```

**Résultat** : 50 articles récents avec leurs abstracts.

#### **Étape 2 : Extraction NER**

Pour chaque abstract, le système OpenMed extrait les entités biomédicales.

**Exemple d'Abstract** :
```
"Semaglutide, a GLP-1 receptor agonist, shows neuroprotective effects 
in Alzheimer disease models. Patients with type 2 diabetes receiving 
semaglutide demonstrated reduced cognitive decline. The hippocampus 
showed elevated tau and amyloid-beta levels, but no significant 
hypertension was observed."
```

**Entités Extraites** :

| Type | Entité | Confiance | Assertion Status |
|------|--------|-----------|------------------|
| DRUG | Semaglutide | 0.95 | PRESENT |
| PROTEIN | GLP-1 receptor | 0.92 | PRESENT |
| DISEASE | Alzheimer disease | 0.94 | PRESENT |
| DISEASE | type 2 diabetes | 0.91 | PRESENT |
| ANATOMY | hippocampus | 0.88 | PRESENT |
| PROTEIN | tau | 0.90 | PRESENT |
| PROTEIN | amyloid-beta | 0.93 | PRESENT |
| DISEASE | hypertension | 0.87 | **NEGATED** |

---

## Les 3 Couches de NER (OpenMed)

### **Couche 1 : NER Standard (F2a)**

**Objectif** : Extraire les entités biomédicales standards

**Types d'Entités Supportés** :
- **DISEASE** : Maladies, pathologies (ex: Alzheimer disease, hypertension)
- **DRUG** : Médicaments, molécules (ex: Semaglutide, imatinib)
- **GENE** : Gènes (ex: BRCA1, TP53)
- **PROTEIN** : Protéines (ex: tau, amyloid-beta, GLP-1)
- **ANATOMY** : Organes, structures anatomiques (ex: hippocampus, cortex)
- **CHEMICAL** : Composés chimiques
- **ONCOLOGY** : Entités liées au cancer

**Code Python** :
```python
from ner.router import extract_from_text

result = extract_from_text(
    text="Patient started on imatinib for chronic myeloid leukemia.",
    entity_types=["DISEASE", "DRUG"],
    provider="openmed"
)

# Résultat :
# result.entities["DISEASE"] → ["chronic myeloid leukemia"]
# result.entities["DRUG"] → ["imatinib"]
```

**API REST** :
```bash
curl -X POST http://localhost:8000/ner/extract \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Patient started on imatinib for chronic myeloid leukemia.",
    "entity_types": ["DISEASE", "DRUG"],
    "provider": "openmed"
  }'
```

---

### **Couche 2 : NER Zero-shot (F2b)**

**Objectif** : Extraire des entités personnalisées **sans ré-entraînement de modèle**

**Cas d'Usage** : Un chercheur en neurosciences veut extraire des régions cérébrales et des biomarqueurs spécifiques.

**Labels Personnalisés** :
- BRAIN_REGION (hippocampus, amygdala, prefrontal cortex)
- BIOMARKER (tau, amyloid-beta, neurofilament)
- IMAGING_TECHNIQUE (fMRI, PET scan, DTI)
- COGNITIVE_FUNCTION (memory, attention, executive function)

**Code Python** :
```python
result = extract_from_text(
    text="The hippocampus shows elevated tau and amyloid-beta levels.",
    custom_labels=["BRAIN_REGION", "BIOMARKER"],
    provider="openmed"
)

# Résultat :
# result.entities["BRAIN_REGION"] → ["hippocampus"]
# result.entities["BIOMARKER"] → ["tau", "amyloid-beta"]
```

**Avantage** : Adaptable à n'importe quel sous-domaine (oncologie, cardiologie, immunologie) sans modification du code.

---

### **Couche 3 : Assertion Status (F2c)**

**Objectif** : Qualifier le **contexte** de chaque entité

**Pourquoi c'est crucial ?**

Savoir qu'un article mentionne "hypertension" ne suffit pas. Il faut savoir si l'article :
- **Confirme** la présence d'hypertension (PRESENT)
- **Nie** l'hypertension (NEGATED)
- **Spécule** sur l'hypertension (HYPOTHETICAL)
- Mentionne un **antécédent** d'hypertension (HISTORICAL)

**Statuts d'Assertion** :

| Statut | Signification | Exemple |
|--------|--------------|---------|
| **PRESENT** | Entité affirmée comme réelle/active | "Le patient présente une hypertension" |
| **NEGATED** | Entité explicitement niée | "Pas d'amélioration cognitive observée" |
| **HYPOTHETICAL** | Entité supposée ou conditionnelle | "Des essais supplémentaires sont nécessaires" |
| **HISTORICAL** | Entité mentionnée au passé | "Antécédent de diabète de type 2" |

**Code Python** :
```python
result = extract_from_text(
    text="Patient has no hypertension. Further trials may confirm efficacy.",
    entity_types=["DISEASE"],
    enable_assertion=True,
    provider="openmed"
)

# Résultat :
# result.entities["DISEASE"][0].text → "hypertension"
# result.entities["DISEASE"][0].assertion_status → "NEGATED"
```

**Impact sur le Knowledge Graph** :

Sans assertion :
```
Semaglutide ↔ Alzheimer (5 mentions)
```

Avec assertion :
```
Semaglutide ↔ Alzheimer
  - 3 PRESENT (confirmé)
  - 1 NEGATED (réfuté)
  - 1 HYPOTHETICAL (spéculatif)
  → Consensus : 60% positif, signal contradictoire
```

---

## Workflow Complet : De PubMed au Knowledge Graph

### **Étape par Étape**

#### **1. Recherche PubMed**
```python
from core_tools.pubmed_tool import search_pubmed

articles = search_pubmed(
    query="Alzheimer disease treatment",
    max_results=50,
    date_range="2026/03/01:2026/03/24"
)
```

**Résultat** : 50 articles avec PMID, titre, abstract, date, journal

#### **2. Extraction NER Batch**
```python
from ner.router import extract_from_text

ner_results = []
for article in articles:
    result = extract_from_text(
        text=article['abstract'],
        entity_types=["DISEASE", "DRUG", "GENE", "PROTEIN"],
        enable_assertion=True,
        provider="openmed"
    )
    ner_results.append({
        'pmid': article['pmid'],
        'entities': result.entities,
        'date': article['date']
    })
```

**Résultat** : Liste d'entités extraites par article

#### **3. Construction du Knowledge Graph**
```python
from kg.build import build_graph_from_ner_results

G = build_graph_from_ner_results(ner_results)
```

**Le graphe contient** :
- **Nœuds** : Entités uniques (Semaglutide, Alzheimer disease, tau, etc.)
- **Arêtes** : Co-occurrences dans le même abstract
- **Poids** : Fréquence × confiance moyenne
- **Métadonnées** : PMIDs sources, dates, assertion status

#### **4. Sauvegarde du Snapshot**
```python
from kg.snapshots import save_snapshot

save_snapshot(G, week_label='2026-W12')
```

**Résultat** : Snapshot sauvegardé dans Supabase + fichier JSON

#### **5. Comparaison Temporelle**
```python
from kg.snapshots import load_snapshot, compare_snapshots

G_new = load_snapshot('2026-W12')
G_old = load_snapshot('2026-W08')

delta = compare_snapshots(G_new, G_old)
```

**Résultat** : Détection des signaux émergents

---

## Cas d'Usage Avancés

### **Use Case 1 : Détection de Contradictions**

**Scénario** : Un médicament a des résultats contradictoires dans la littérature

**Requête** :
```python
result = extract_from_text(
    text="""
    Study A: Semaglutide improves cognitive function in Alzheimer patients.
    Study B: No cognitive improvement was observed with semaglutide.
    Study C: Further trials are needed to confirm semaglutide efficacy.
    """,
    entity_types=["DRUG", "DISEASE"],
    enable_assertion=True
)
```

**Analyse** :
- Article 1 : Semaglutide ↔ Alzheimer (PRESENT)
- Article 2 : Semaglutide ↔ Alzheimer (NEGATED)
- Article 3 : Semaglutide ↔ Alzheimer (HYPOTHETICAL)

**Score de Consensus** : 33% positif, 33% négatif, 33% hypothétique → **Signal hautement contradictoire**

---

### **Use Case 2 : Drug Repurposing**

**Scénario** : Détecter des associations inattendues entre médicaments et maladies

**Exemple** : Un médicament anti-diabétique (Semaglutide) émerge dans la littérature Alzheimer

**Détection** :
```python
# Semaine 8 : Semaglutide ↔ Alzheimer (0 mentions)
# Semaine 12 : Semaglutide ↔ Alzheimer (5 mentions, 3 équipes indépendantes)

delta = compare_snapshots(G_new, G_old)
new_edges = delta['new_edges']

# Filtre : nouvelles associations DRUG ↔ DISEASE
drug_disease_bridges = [
    edge for edge in new_edges
    if edge['source']['entity_type'] == 'DRUG' 
    and edge['target']['entity_type'] == 'DISEASE'
]
```

**Résultat** : Liste d'opportunités de repositionnement de médicaments

---

### **Use Case 3 : Surveillance Multi-Domaines**

**Scénario** : Un chercheur veut surveiller plusieurs pathologies simultanément

**Configuration** :
```python
topics = [
    {
        "name": "Alzheimer",
        "query": "Alzheimer disease treatment",
        "custom_labels": ["BRAIN_REGION", "BIOMARKER"]
    },
    {
        "name": "Parkinson",
        "query": "Parkinson disease therapy",
        "custom_labels": ["BRAIN_REGION", "MOTOR_SYMPTOM"]
    },
    {
        "name": "ALS",
        "query": "amyotrophic lateral sclerosis treatment",
        "custom_labels": ["NEURON_TYPE", "BIOMARKER"]
    }
]

for topic in topics:
    articles = search_pubmed(topic['query'])
    ner_results = extract_batch(articles, custom_labels=topic['custom_labels'])
    G = build_graph(ner_results)
    save_snapshot(G, week_label='2026-W12', topic=topic['name'])
```

**Résultat** : Graphes séparés par pathologie, permettant des comparaisons croisées

---

## Performance et Optimisation

### **Temps de Traitement**

| Opération | Temps (CPU) | Temps (GPU) |
|-----------|------------|-------------|
| NER Standard (1 abstract) | 100-200ms | 30-50ms |
| NER Zero-shot (1 abstract) | 150-300ms | 50-80ms |
| Assertion Status (par entité) | +50-100ms | +20-30ms |
| Batch 50 abstracts | 8-12s | 2-4s |

### **Stratégies d'Optimisation**

**1. Traitement par Batch**
```python
# Au lieu de :
for article in articles:
    result = extract_from_text(article['abstract'])

# Utiliser :
results = extract_batch([article['abstract'] for article in articles])
```

**2. Cache des Requêtes**
```python
# Les résultats NER sont mis en cache par hash du texte
# Évite de re-traiter les mêmes abstracts
```

**3. Filtrage par Confiance**
```python
# Filtrer les entités avec confiance < 0.7
result = extract_from_text(
    text=abstract,
    confidence_threshold=0.7
)
```

---

## Intégration Frontend

### **Interface NER (ui-med-rag)**

L'interface permet de :
1. Saisir du texte biomédical
2. Sélectionner les types d'entités (checkboxes)
3. Ajouter des labels personnalisés (zero-shot)
4. Activer l'assertion status (toggle)
5. Visualiser les résultats avec badges colorés

**Badges d'Assertion** :
- 🟢 **P** : PRESENT (vert)
- 🔴 **N** : NEGATED (rouge)
- 🟡 **H** : HYPOTHETICAL (jaune)
- 🔵 **H** : HISTORICAL (bleu)

---

## Exemples de Résultats

### **Exemple 1 : Article sur le Cancer**

**Input** :
```
"Imatinib is effective in chronic myeloid leukemia patients with BCR-ABL fusion. 
No cardiotoxicity was observed. BRCA1 mutations may increase risk."
```

**Output** :
```json
{
  "entities": {
    "DRUG": [
      {"text": "Imatinib", "confidence": 0.96, "assertion": "PRESENT"}
    ],
    "DISEASE": [
      {"text": "chronic myeloid leukemia", "confidence": 0.94, "assertion": "PRESENT"},
      {"text": "cardiotoxicity", "confidence": 0.89, "assertion": "NEGATED"}
    ],
    "GENE": [
      {"text": "BCR-ABL", "confidence": 0.92, "assertion": "PRESENT"},
      {"text": "BRCA1", "confidence": 0.91, "assertion": "HYPOTHETICAL"}
    ]
  }
}
```

### **Exemple 2 : Article Neurosciences avec Zero-shot**

**Input** :
```
"The prefrontal cortex and hippocampus show reduced connectivity in depression. 
Elevated cortisol and reduced BDNF levels were measured using fMRI."
```

**Custom Labels** : `["BRAIN_REGION", "BIOMARKER", "IMAGING_TECHNIQUE"]`

**Output** :
```json
{
  "entities": {
    "BRAIN_REGION": [
      {"text": "prefrontal cortex", "confidence": 0.93},
      {"text": "hippocampus", "confidence": 0.91}
    ],
    "BIOMARKER": [
      {"text": "cortisol", "confidence": 0.88},
      {"text": "BDNF", "confidence": 0.90}
    ],
    "IMAGING_TECHNIQUE": [
      {"text": "fMRI", "confidence": 0.95}
    ],
    "DISEASE": [
      {"text": "depression", "confidence": 0.92}
    ]
  }
}
```

---

## Fallback et Robustesse

### **Stratégie de Fallback**

Si OpenMed n'est pas disponible :
1. **NER Standard** → Fallback vers GLiNER2
2. **Zero-shot NER** → Fallback vers GLiNER2
3. **Assertion Status** → Fallback vers détection heuristique

**Détection Heuristique d'Assertion** :
```python
# Patterns de négation
negation_patterns = ["no", "not", "without", "absence of", "negative for"]

# Patterns hypothétiques
hypothetical_patterns = ["may", "might", "could", "possible", "potential"]

# Patterns historiques
historical_patterns = ["history of", "previous", "prior", "past"]
```

---

## Métriques de Qualité

### **Évaluation de la Performance NER**

| Métrique | OpenMed | GLiNER2 |
|----------|---------|---------|
| Précision (DISEASE) | 0.92 | 0.85 |
| Rappel (DISEASE) | 0.89 | 0.82 |
| F1-Score (DISEASE) | 0.90 | 0.83 |
| Précision (DRUG) | 0.94 | 0.87 |
| Assertion Accuracy | 0.88 | 0.72 (heuristique) |

---

## Conclusion

### **Valeur Ajoutée du NER**

1. **Structuration** : Transforme du texte non structuré en données structurées
2. **Qualification** : L'assertion status ajoute du contexte sémantique
3. **Flexibilité** : Le zero-shot permet l'adaptation à tout domaine
4. **Scalabilité** : Traitement batch de milliers d'articles
5. **Qualité** : OpenMed offre une précision état de l'art

### **Impact sur BioHorizon**

Sans NER → Impossible de construire le Knowledge Graph  
Avec NER → Graphe structuré, détection de signaux, consensus scoring

**Le NER est la pierre angulaire de BioHorizon.**
