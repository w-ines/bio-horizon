# Migration vers LangGraph — Bio-Horizon

## Objectif

Remplacer l'orchestration custom (`SimpleAgentExecutor`, checkpointing maison, mémoire manuelle) par **LangGraph**, le framework de graphes d'états de LangChain. La logique métier (tools, NER, KG, signals, RAG) reste intacte — seule la **plomberie** change.

### Gains attendus

- **Checkpointing natif** : reprise sur erreur sans code custom (remplace `jobs/worker.py` ~490 lignes)
- **Streaming natif** : chaque nœud émet ses résultats (remplace le callback SSE maison)
- **Mémoire intégrée** : short-term (par conversation) + long-term (cross-sessions) via `checkpointer`
- **Flux explicite** : le graphe est visualisable, testable nœud par nœud, débugable
- **Human-in-the-loop** : `interrupt()` natif pour les actions critiques
- **Sub-graphs** : chaque pipeline (ingestion, surveillance, signaux) = un sous-graphe réutilisable

---

## Architecture cible

```
                    ┌──────────┐
             START──▶  Router  │
                    └────┬─────┘
              ┌──────────┼──────────┐
              ▼          ▼          ▼
         ask_graph  ingestion   signal
         (RAG+KG)   _graph      _graph
              │          │          │
              ▼          ▼          ▼
           Answer    Persist    Report
              │          │          │
              └──────────┼──────────┘
                        END
```

### Correspondance actuel → cible

| Composant actuel | Remplacé par | Statut |
|---|---|---|
| `SimpleAgentExecutor` (main_agent.py) | `ask_graph` StateGraph | À faire |
| `IngestWorker` (jobs/worker.py) | `ingestion_graph` sub-graph | À faire |
| `weekly_update.py` (scheduler/) | `surveillance_graph` sub-graph | À faire |
| `signals/detector + scoring + consensus` | `signal_graph` sub-graph | À faire |
| `memory.py` (dual-write 276 lignes) | LangGraph `MemorySaver` | À simplifier |
| `deepagents/tools/` (12+ @tool) | **Inchangé** | ✅ OK |
| `ner/`, `kg/`, `rag/`, `signals/` | **Inchangé** (logique métier) | ✅ OK |

---

## Structure de fichiers cible

```
deepagents/
├── state.py                    # État partagé (TypedDict)
├── config.py                   # Configuration centralisée
├── nodes/                      # Fonctions de nœuds
│   ├── router.py               # Classifie la requête
│   ├── planner.py              # Décompose en sous-tâches
│   ├── pubmed_node.py          # Recherche PubMed
│   ├── ner_node.py             # Extraction d'entités
│   ├── kg_node.py              # Mise à jour KG
│   ├── rag_node.py             # Retrieval + contexte
│   ├── signal_node.py          # Détection signaux
│   ├── answer_node.py          # Génération réponse
│   └── critic_node.py          # Auto-évaluation
├── graphs/                     # Graphes LangGraph
│   ├── ask_graph.py            # Graphe principal (question → réponse)
│   ├── ingestion_graph.py      # Pipeline PubMed → NER → KG
│   ├── surveillance_graph.py   # Surveillance hebdomadaire
│   └── signal_graph.py         # Détection + consensus
├── prompts/                    # Prompts par nœud
│   ├── router_prompt.py
│   ├── planner_prompt.py
│   └── critic_prompt.py
├── tools/                      # INCHANGÉ — @tool existants
│   ├── biomedical/
│   ├── document/
│   └── knowledge/
└── memory.py                   # Simplifié (wrapper LangGraph checkpointer)
```

---

## Plan d'action

### Phase 1 — Fondations ✅

- [x] Installer `langgraph` dans `requirements.txt` (v1.1.3)
- [x] Créer `state.py` avec le `BioHorizonState` (TypedDict)
- [x] Créer `ask_graph.py` minimal qui reproduit le comportement actuel de `SimpleAgentExecutor`
- [x] Brancher `ask_graph` sur l'endpoint `/ask` existant
- [x] Imports et compilation vérifiés

### Phase 2 — Router + Planning ✅

- [x] Créer `nodes/router.py` : classifie la requête (simple / ingest / signal) via LLM structured output
- [x] Créer `nodes/planner.py` : génère un plan pour les requêtes complexes (no-op pour simple)
- [x] Intégrer router + planner dans `ask_graph.py` : START → router → planner → agent ↔ tools → END
- [x] Graph compilé et testé (6 nœuds, 6 edges)

### Phase 3 — Sub-graph Ingestion ✅

- [x] Créer `graphs/ingestion_graph.py` : PubMed → NER → KG → Persist (7 nœuds, 7 edges)
- [x] Migrer la logique de `IngestWorker._process_batches()` en nœuds (`nodes/ingestion.py`)
- [x] Utiliser le checkpointer LangGraph (`MemorySaver`, reprise via thread_id)
- [ ] Tester la reprise sur erreur en production (nécessite PubMed + Redis)

### Phase 4 — Sub-graph Signals (1 jour)

- [ ] Créer `graphs/signal_graph.py` : KG snapshots → detect → score → consensus
- [ ] Connecter au `ask_graph` comme sub-graph
- [ ] Tester avec des paires d'entités connues

### Phase 5 — Surveillance (1 jour)

- [ ] Créer `graphs/surveillance_graph.py` : topics → PubMed → NER → KG → Signals
- [ ] Remplacer `scheduler/weekly_update.py` par un appel au graph
- [ ] Tester l'exécution planifiée

### Phase 6 — Mémoire + HITL (1 jour)

- [ ] Remplacer `memory.py` custom par LangGraph `PostgresSaver` (Supabase)
- [ ] Ajouter `interrupt()` avant ingestion de gros corpus (>1000 articles)
- [ ] Ajouter un nœud `critic` pour l'auto-évaluation des réponses

---

## Dépendances

```txt
langgraph>=0.4.0
langchain-core>=0.3.0
langchain-openai>=0.3.0
```

## Références

- [LangGraph docs](https://docs.langchain.com/oss/python/langgraph/overview)
- [RAG Research Agent Template](https://github.com/langchain-ai/rag-research-agent-template) — pattern sub-graph + researcher
- [Multi-Agent Research Assistant](https://github.com/AnnasMustafaDev/Multi-Agent-Research-Assistant-Langgraph) — pattern Supervisor + Workers
