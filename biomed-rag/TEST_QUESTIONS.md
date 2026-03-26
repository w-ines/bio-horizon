# Questions de test — Bio-Horizon

Ce fichier contient des questions de test classées par outil attendu.
Pour chaque question, on indique le(s) tool(s) que l'agent **devrait** appeler et ce qu'il faut vérifier dans la réponse.

---

## 1. PubMed Search uniquement

Ces questions portent sur la littérature récente — l'agent **doit** appeler `pubmed_search`.

### Q1.1 — Recherche simple
> Quels sont les derniers traitements approuvés pour la maladie d'Alzheimer ?

**Vérifier :**
- [ ] `pubmed_search` appelé (visible dans les steps)
- [ ] Résultats avec PMIDs cités
- [ ] Réponse en français (langue de la question)

### Q1.2 — Recherche avec filtre temporel
> What are the most recent clinical trials on GLP-1 agonists for neurodegeneration published in 2024?

**Vérifier :**
- [ ] `pubmed_search` appelé avec `sort_by="date"`
- [ ] Articles récents (2024+)
- [ ] Réponse en anglais

### Q1.3 — Médicament spécifique
> Quels sont les effets secondaires du Lecanemab rapportés dans la littérature ?

**Vérifier :**
- [ ] `pubmed_search` appelé avec query type "Lecanemab adverse effects"
- [ ] Citations PMID dans la réponse

### Q1.4 — Gène et maladie
> What is the role of the APOE4 gene in Alzheimer's disease progression?

**Vérifier :**
- [ ] `pubmed_search` appelé
- [ ] Contenu scientifique pertinent sur APOE4

---

## 2. Retrieve Knowledge (documents locaux + KG)

Ces questions visent le knowledge base local. L'agent **doit** appeler `retrieve_knowledge`.
> **Prérequis** : avoir uploadé au moins un PDF via l'interface.

### Q2.1 — Question sur un document uploadé
> Résume les conclusions principales du document que j'ai uploadé.

**Vérifier :**
- [ ] `retrieve_knowledge` appelé
- [ ] Réponse basée sur le contenu du document uploadé
- [ ] Citations [Source N]

### Q2.2 — Question KG (Knowledge Graph)
> Quelles sont les relations connues entre le diabète de type 2 et la maladie d'Alzheimer ?

**Vérifier :**
- [ ] `retrieve_knowledge` appelé avec `enable_kg=true`
- [ ] Entités et relations du KG mentionnées si disponibles

---

## 3. Les deux outils combinés

L'agent **doit** appeler `pubmed_search` ET `retrieve_knowledge`.

### Q3.1 — Recherche complète
> Trouve-moi des informations sur les nouveaux traitements pour Alzheimer et dis-moi s'il y a des signaux émergents dans la littérature récente.

**Vérifier :**
- [ ] `pubmed_search` appelé (littérature récente)
- [ ] `retrieve_knowledge` appelé (base locale)
- [ ] Synthèse des deux sources
- [ ] Mention de signaux/tendances si pertinent

### Q3.2 — Comparaison document vs littérature
> Les résultats de mon document sont-ils cohérents avec la littérature récente sur ce sujet ?

**Vérifier :**
- [ ] `retrieve_knowledge` appelé (pour le document)
- [ ] `pubmed_search` appelé (pour la littérature)
- [ ] Comparaison explicite entre les deux

### Q3.3 — Sujet émergent
> Y a-t-il des preuves récentes d'un lien entre le microbiome intestinal et les maladies neurodégénératives ?

**Vérifier :**
- [ ] `pubmed_search` appelé (sujet tendance)
- [ ] `retrieve_knowledge` appelé
- [ ] Réponse structurée avec niveau de preuve

---

## 4. Questions edge-case

### Q4.1 — Question hors domaine
> Quelle est la capitale de la France ?

**Vérifier :**
- [ ] L'agent répond quand même (pas de crash)
- [ ] Idéalement, il ne gaspille pas de tool call

### Q4.2 — Question vague
> Parle-moi du cancer.

**Vérifier :**
- [ ] L'agent appelle au moins `pubmed_search`
- [ ] Réponse structurée malgré la question vague

### Q4.3 — Question multilingue
> Explique-moi les avancées récentes en immunothérapie pour le melanoma.

**Vérifier :**
- [ ] `pubmed_search` appelé avec query en anglais (traduction interne)
- [ ] Réponse en français

---

## 5. Analyse des réponses — Grille d'évaluation

| Critère                          | Score (0-2) | Notes |
|----------------------------------|-------------|-------|
| Tool(s) correct(s) appelé(s)    |             |       |
| Résultats PubMed pertinents     |             |       |
| Citations (PMID / Source N)      |             |       |
| Langue de réponse correcte      |             |       |
| Synthèse cohérente              |             |       |
| Pas de hallucination             |             |       |
| Temps de réponse acceptable     |             |       |

**Score** : 0 = absent/incorrect, 1 = partiel, 2 = correct

---

## 6. Commandes de test rapide (terminal)

```bash
# Test basique pubmed_search
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the latest Alzheimer treatments?", "conversation_id": "test_pubmed_1"}'

# Test retrieve_knowledge (nécessite des docs uploadés)
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "Résume les documents disponibles sur le diabète", "conversation_id": "test_rag_1"}'

# Test combiné
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "Quels sont les signaux émergents sur le lien GLP-1 et Alzheimer ?", "conversation_id": "test_combined_1"}'
```

> **Note** : Les réponses sont en streaming NDJSON. Chaque ligne est un JSON avec un champ `type` (thought, action, observation, answer).





What are the latest Alzheimer treatments?
# test memoire
Which of these treatments are disease-modifying vs symptomatic?"
"Can you rank the treatments you mentioned by effectiveness?"
"Which ones are approved by the FDA vs EMA?"

# test de co-reference
"Which of them have the most side effects?"
"Are any of those suitable for early-stage patients only?"
"Do they work the same way?"

# test coherence geographique
"Why are some of these treatments not covered in Europe?"
"Is coverage different between France and Germany?"
"Which countries are the most restrictive?"
