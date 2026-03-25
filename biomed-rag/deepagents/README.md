# Deep Agents Migration - bio-horizon

Ce dossier contient la nouvelle implémentation basée sur **LangChain Deep Agents** pour remplacer progressivement `smolagents`.

## 🎯 Objectif

Migrer de `smolagents` vers `deepagents` (LangChain) pour bénéficier de :
- ✅ Planning automatique (write_todos)
- ✅ Sub-agents spécialisés
- ✅ Intégration Knowledge Graph native
- ✅ Filesystem backend pour contexte étendu
- ✅ LangSmith pour debugging
- ✅ Meilleure scalabilité

## 📁 Structure

```
deepagents/
├── agents/                    # Agents Deep Agents
│   └── main_agent.py         # Agent principal bio-horizon
├── tools/                     # Tools LangChain
│   ├── biomedical/           # Tools biomédicaux (PubMed, NER, etc.)
│   ├── knowledge/            # Tools RAG/KG
│   │   └── rag_tool.py      # ✅ MIGRÉ: retrieve_knowledge
│   └── utility/              # Tools utilitaires (web, scraping)
├── workflows/                 # LangGraph workflows
└── router.py                 # FastAPI router (/agent-deep)
```

## 🚀 État de la migration

### ✅ Phase 1 : Infrastructure (COMPLÉTÉ)
- [x] Structure de dossiers créée
- [x] Tool `retrieve_knowledge` migré
- [x] Agent principal `create_biomedical_agent()`
- [x] Router FastAPI `/agent-deep`
- [x] Intégration dans `main.py`

### 🔄 Phase 2 : Migration des tools (EN COURS)
- [x] `retrieve_knowledge` → `deepagents/tools/knowledge/rag_tool.py`
- [ ] `get_weather` → `deepagents/tools/utility/weather_tool.py`
- [ ] `web_search_ctx` → `deepagents/tools/utility/web_search_tool.py`
- [ ] `search_pubmed` → `deepagents/tools/biomedical/pubmed_tool.py`
- [ ] `extract_entities` → `deepagents/tools/biomedical/ner_tool.py`

### ⏳ Phase 3 : Sub-agents spécialisés (À FAIRE)
- [ ] PubMed Research Agent
- [ ] RAG Query Agent
- [ ] Knowledge Graph Agent
- [ ] Trend Analysis Agent
- [ ] Summarization Agent

### ⏳ Phase 4 : Tests et validation (À FAIRE)
- [ ] Tests unitaires pour chaque tool
- [ ] Tests d'intégration agent complet
- [ ] Tests A/B smolagents vs deepagents
- [ ] Validation performance

### ⏳ Phase 5 : Déploiement (À FAIRE)
- [ ] Feature flag `USE_DEEP_AGENTS`
- [ ] Migration progressive des endpoints
- [ ] Monitoring et logs
- [ ] Suppression de smolagents

## 🧪 Tests

### Test rapide du health check
```bash
curl http://localhost:8000/agent-deep/health
```

### Test simple (non-streaming)
```bash
curl -X POST http://localhost:8000/agent-deep-simple \
  -H "Content-Type: application/json" \
  -d '{"query": "What is RAG?"}'
```

### Test streaming (SSE)
```bash
curl -X POST http://localhost:8000/agent-deep \
  -H "Content-Type: application/json" \
  -d '{"query": "Explain retrieval augmented generation"}'
```

## 📝 Utilisation

### Créer un agent
```python
from deepagents.agents.main_agent import create_biomedical_agent

agent = create_biomedical_agent()
result = agent.invoke({
    "messages": [{"role": "user", "content": "What are aspirin side effects?"}]
})
```

### Utiliser un tool directement
```python
from deepagents.tools.knowledge.rag_tool import retrieve_knowledge

result = retrieve_knowledge(
    query="diabetes treatment",
    top_k=5,
    enable_kg_enrichment=True
)
print(result["context"])
```

## 🔧 Configuration

Variables d'environnement requises (dans `.env`) :
```bash
# LLM Configuration
OPEN_AI_MODEL=gpt-4o
BASE_URL=https://openrouter.ai/api/v1
OPEN_ROUTER_KEY=your_key_here

# Embeddings
EMBEDDINGS_PROVIDER=openrouter
EMBEDDINGS_MODEL=text-embedding-3-small

# Supabase (pour RAG)
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

## 🆚 Comparaison smolagents vs Deep Agents

| Feature | smolagents | Deep Agents |
|---------|-----------|-------------|
| Planning | Manuel | Automatique (write_todos) |
| Sub-agents | ❌ | ✅ |
| KG Integration | Custom | Natif |
| Streaming | Custom SSE | LangGraph streaming |
| Memory | Custom | LangGraph checkpointer |
| Debugging | Logs | LangSmith |

## 📚 Documentation

- [Deep Agents Docs](https://docs.langchain.com/oss/python/deepagents/overview)
- [LangGraph Docs](https://docs.langchain.com/oss/python/langgraph/overview)
- [Architecture complète](../ARCHITECTURE.md)

## 🐛 Troubleshooting

### ImportError: No module named 'deepagents'
```bash
pip install deepagents
```

### Agent ne démarre pas
Vérifier que les variables d'environnement sont définies :
```bash
python -c "from deepagents.agents.main_agent import create_biomedical_agent; create_biomedical_agent()"
```

### Tool retrieve_knowledge échoue
Vérifier que le module `rag` est accessible :
```bash
python -c "from rag import query_rag; print('OK')"
```
