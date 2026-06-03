# Deep Agent — Architecture et Fonctionnement

## Vue d'ensemble

Le **Deep Agent** est le système d'intelligence artificielle au cœur de BioHorizon. Basé sur **LangChain**, il orchestre l'ensemble des outils biomédicaux (PubMed, NER, Knowledge Graph, RAG) pour répondre aux requêtes des utilisateurs de manière intelligente et contextuelle.

L'agent est invoqué via le **endpoint unifié `/ask`** (`api/routes/ask.py`), qui gère à la fois l'upload de documents et la délégation au Deep Agent.

---

## Qu'est-ce qu'un Deep Agent ?

### **Définition**

Un **Deep Agent** est un agent conversationnel autonome capable de :
1. **Planifier** : Décomposer une requête complexe en étapes
2. **Raisonner** : Choisir les bons outils au bon moment
3. **Exécuter** : Appeler des outils externes (PubMed, NER, RAG, KG)
4. **Mémoriser** : Maintenir le contexte de la conversation
5. **Répondre** : Synthétiser les résultats avec citations



## Architecture Globale

```
┌─────────────────────────────────────────────────────────────────┐
│                         UTILISATEUR                              │
│                                                                  │
│  "Quels sont les nouveaux traitements pour Alzheimer ?"         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FRONTEND (Next.js)                          │
│                                                                  │
│  POST /ask                                                       │
│  { "query": "...", "conversation_id": "abc123" }                 │
│  (supporte aussi multipart/form-data avec fichiers PDF)          │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP / NDJSON streaming
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  ENDPOINT UNIFIÉ /ask (FastAPI)                   │
│                  api/routes/ask.py                                │
│                                                                  │
│  • Reçoit la requête (JSON ou multipart avec fichiers)           │
│  • Si fichiers : upload + indexation dans le vector store        │
│  • Crée l'agent avec create_biomedical_agent()                   │
│  • Stream les étapes en temps réel (NDJSON)                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MAIN AGENT (LangChain)                        │
│                  deepagents/agents/main_agent.py                 │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  1. PLANIFICATION                                         │  │
│  │     • Analyse la requête utilisateur                      │  │
│  │     • Identifie les entités médicales clés                │  │
│  │     • Détermine les outils nécessaires                    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                             │                                    │
│  ┌───────────────────────────▼───────────────────────────────┐  │
│  │  2. BOUCLE D'EXÉCUTION (max 5 itérations)                 │  │
│  │                                                            │  │
│  │  Pour chaque étape :                                      │  │
│  │    a. LLM décide : répondre OU utiliser un tool           │  │
│  │    b. Si tool → exécute le tool                           │  │
│  │    c. Ajoute le résultat au contexte                      │  │
│  │    d. Retour à (a)                                        │  │
│  └────────────────────────────────────────────────────────────┘  │
│                             │                                    │
│  ┌───────────────────────────▼───────────────────────────────┐  │
│  │  3. SYNTHÈSE                                              │  │
│  │     • Agrège les résultats des tools                      │  │
│  │     • Génère une réponse structurée                       │  │
│  │     • Ajoute les citations [Source N]                     │  │
│  └───────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                         TOOLS (Outils)                           │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ retrieve_    │  │ search_      │  │ extract_     │          │
│  │ knowledge    │  │ pubmed       │  │ entities     │          │
│  │ (RAG)        │  │              │  │ (NER)        │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ query_kg     │  │ detect_      │  │ summarize_   │          │
│  │ (Knowledge   │  │ signals      │  │ document     │          │
│  │  Graph)      │  │              │  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Composants Détaillés

### **1. Endpoint Unifié /ask (api/routes/ask.py)**

**Rôle** : Point d'entrée unique pour toutes les requêtes utilisateur (questions + upload de fichiers)

#### `POST /ask` (Streaming NDJSON)

**Requête JSON** :
```python
{
  "query": "Quels sont les effets secondaires de l'imatinib ?",
  "conversation_id": "conv-123"
}
```

**Requête multipart** (avec upload de fichiers PDF) :
```
Content-Type: multipart/form-data
- query: "Résume ce document"
- conversation_id: "conv-123"
- files: [fichier.pdf]
```

**Réponse** : NDJSON (Newline-Delimited JSON)
```
{"step": "🚀 Starting Deep Agent..."}
{"step": " Thinking... (step 1/5)"}
{"step": " Using tool: retrieve_knowledge"}
{"step": " Tool result received (3 documents)"}
{"response": "Imatinib est un inhibiteur...", "canHandle": true}
```

**Flux interne** :
1. Si fichiers attachés → upload + parsing PDF + indexation vectorielle
2. Construction de la requête enrichie (avec contexte documents)
3. Création du Deep Agent via `create_biomedical_agent()`
4. Exécution dans un thread séparé avec streaming via queue
5. Retour NDJSON en temps réel au frontend

---

### **2. Main Agent (deepagents/agents/main_agent.py)**

**Rôle** : Cerveau de l'agent — orchestration et raisonnement

#### **Composants Internes**

**a. LLM (Large Language Model)**
```python
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.3,  # Précision (0.0 = déterministe, 1.0 = créatif)
    openai_api_base="https://openrouter.ai/api/v1"
)
```

**b. Tools Binding**
```python
tools = [
    retrieve_knowledge,
    search_pubmed,
    extract_entities,
    query_kg,
    detect_signals
]
llm_with_tools = llm.bind_tools(tools)
```

**c. System Prompt**
```
You are bio-horizon, an intelligent biomedical research assistant.

Your capabilities:
- Search and retrieve information from uploaded medical documents
- Analyze medical literature and research papers
- Extract and understand medical entities (diseases, drugs, genes, proteins)
- Provide evidence-based answers with proper citations

Guidelines:
1. Always cite sources using [Source N] format
2. Be precise - medical information requires accuracy
3. Use Knowledge Graph when available
4. Admit uncertainty if information is not in documents
5. Efficient tool use
```

#### **Boucle d'Exécution (Agent Loop)**

```python
for iteration in range(max_iterations):  # max 5 itérations
    # 1. LLM décide de l'action
    response = llm.invoke(messages)
    
    # 2. Si pas de tool_calls → réponse finale
    if not response.tool_calls:
        return {"output": response.content}
    
    # 3. Exécution des tools
    for tool_call in response.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        
        # Exécuter le tool
        result = tools[tool_name].invoke(tool_args)
        
        # Ajouter le résultat au contexte
        messages.append(ToolMessage(content=str(result)))
```

**Exemple de Trace d'Exécution** :

```
Requête : "Quels sont les nouveaux traitements pour Alzheimer ?"

Itération 1:
  LLM → "Je vais chercher dans PubMed"
  Tool Call → search_pubmed(query="Alzheimer treatment", max_results=10)
  Result → [10 articles récents]

Itération 2:
  LLM → "Je vais extraire les entités médicales"
  Tool Call → extract_entities(texts=[abstracts], entity_types=["DRUG", "DISEASE"])
  Result → {DRUG: ["Semaglutide", "Lecanemab"], DISEASE: ["Alzheimer disease"]}

Itération 3:
  LLM → "Je vais chercher plus d'infos dans les documents uploadés"
  Tool Call → retrieve_knowledge(query="Semaglutide Alzheimer", top_k=5)
  Result → [5 chunks de documents avec contexte]

Itération 4:
  LLM → "J'ai assez d'informations, je réponds"
  Response → "Les nouveaux traitements pour Alzheimer incluent..."
  [Pas de tool_call → FIN]
```

---

### **3. Memory Manager (deepagents/memory.py)**

**Rôle** : Module unifié de gestion de la mémoire conversationnelle avec **dual-write** (Supabase + in-memory)

Ce module remplace l'ancien `memory/store.py` et centralise toute la gestion mémoire du projet.

#### **Deux interfaces complémentaires**

**a. ConversationMemoryManager** (format LangChain BaseMessage)
Utilisé par `api/routes/conversations.py` pour les endpoints CRUD conversations.

```python
class ConversationMemoryManager:
    # Dual-write : in-memory cache + Supabase persistence
    _conversations: Dict[str, List[BaseMessage]] = {}
    
    @classmethod
    def get_history(cls, conversation_id: str, limit: int = 10):
        """Récupère l'historique des N derniers messages"""
        
    @classmethod
    def add_messages(cls, conversation_id: str, messages: List[BaseMessage]):
        """Ajoute des messages à l'historique"""
        
    @classmethod
    def clear_conversation(cls, conversation_id: str):
        """Efface une conversation"""
    
    @classmethod
    def list_conversations(cls) -> List[Dict]:
        """Liste toutes les conversations actives"""
    
    @classmethod
    def get_stats(cls) -> Dict:
        """Statistiques mémoire"""
```

**b. save_message / load_history** (format StoredMessage)
Utilisé par `rag/chain.py` pour la chaîne RAG conversationnelle.
Stratégie : Supabase en priorité, fallback in-memory automatique.

```python
def save_message(*, conversation_id, role, content) -> StoredMessage:
    """Sauvegarde un message (Supabase + fallback in-memory)"""

def load_history(*, conversation_id, limit=20) -> List[StoredMessage]:
    """Charge l'historique (Supabase en priorité, fallback in-memory)"""
```

#### **Utilisation dans l'Agent**

```python
# L'agent (SimpleAgentExecutor) gère sa propre mémoire interne :
history = SimpleAgentExecutor._conversations[conversation_id]
messages.extend(history[-10:])  # 10 derniers messages
messages.append(HumanMessage(content=user_query))

response = llm.invoke(messages)

# Sauvegarde automatique après chaque réponse
SimpleAgentExecutor._conversations[conversation_id].append(
    HumanMessage(content=user_input)
)
SimpleAgentExecutor._conversations[conversation_id].append(
    AIMessage(content=response.content)
)
```

#### **Utilisation dans la chaîne RAG**

```python
# rag/chain.py utilise les fonctions save_message / load_history :
from deepagents.memory import load_history, save_message

messages = load_history(conversation_id=conversation_id, limit=10)
# ... exécution de la chaîne RAG ...
save_message(conversation_id=conversation_id, role="user", content=question)
save_message(conversation_id=conversation_id, role="assistant", content=answer)
```

**Avantage** : L'agent se souvient des échanges précédents

**Exemple** :
```
User: "Qu'est-ce que l'imatinib ?"
Agent: "L'imatinib est un inhibiteur de tyrosine kinase..."

User: "Quels sont ses effets secondaires ?" 
       ↑ L'agent comprend "ses" = imatinib grâce à la mémoire
Agent: "Les effets secondaires de l'imatinib incluent..."
```

---

### **4. Tools (Outils)**

Les tools sont des fonctions spécialisées que l'agent peut appeler.

#### **Structure d'un Tool LangChain**

```python
from langchain_core.tools import tool



#### **Catégories de Tools**

**a. Knowledge Tools** (`deepagents/tools/knowledge/`)
- `retrieve_knowledge` : RAG sur documents uploadés
- Utilise le vector store Supabase
- Enrichissement via Knowledge Graph

**b. Biomedical Tools** (`deepagents/tools/biomedical/`)
- `search_pubmed` : Recherche PubMed
- `extract_entities` : NER avec OpenMed
- `query_kg` : Requêtes sur le Knowledge Graph
- `detect_signals` : Détection de signaux émergents

**c. Document Tools** (`deepagents/tools/document/`)
- `load_pdf` : Chargement et parsing de PDF
- `summarize_document` : Résumé de documents
- `store_pdf` : Stockage dans Supabase

**d. Utility Tools** (`deepagents/tools/utility/`)
- `web_search` : Recherche web
- `get_weather` : Météo (exemple)

---

## Workflow Complet : Exemple Concret

### **Requête Utilisateur**
```
"Trouve-moi des informations sur les nouveaux traitements pour Alzheimer et dis-moi s'il y a des signaux émergents dans la littérature récente."
```

### **Étape par Étape**

#### **1. Réception (api/routes/ask.py)**
```python
POST /ask
{
  "query": "Trouve-moi des informations...",
  "conversation_id": "conv-456"
}
```

#### **2. Création de l'Agent**
```python
# Dans _build_deep_agent_stream() :
from deepagents.agents.main_agent import create_biomedical_agent
agent = create_biomedical_agent()
```

#### **3. Planification (LLM)**
```
LLM analyse la requête et identifie :
- Besoin 1 : Rechercher dans PubMed
- Besoin 2 : Extraire les entités (traitements)
- Besoin 3 : Détecter les signaux émergents
- Besoin 4 : Synthétiser les résultats
```

#### **4. Exécution (Boucle Agent)**

**Itération 1 : Recherche PubMed**
```python
Tool Call: search_pubmed(
    query="Alzheimer disease treatment 2026",
    max_results=20,
    date_range="2026/01/01:2026/03/24"
)

Result: [
    {
        "pmid": "38123456",
        "title": "Semaglutide shows neuroprotective effects...",
        "abstract": "...",
        "date": "2026-03-15"
    },
    # ... 19 autres articles
]
```

**Itération 2 : Extraction NER**
```python
Tool Call: extract_entities(
    texts=[abstracts des 20 articles],
    entity_types=["DRUG", "DISEASE", "PROTEIN"],
    enable_assertion=True
)

Result: {
    "DRUG": [
        {"text": "Semaglutide", "confidence": 0.95, "assertion": "PRESENT"},
        {"text": "Lecanemab", "confidence": 0.93, "assertion": "PRESENT"},
        {"text": "Donanemab", "confidence": 0.91, "assertion": "PRESENT"}
    ],
    "DISEASE": [
        {"text": "Alzheimer disease", "confidence": 0.94, "assertion": "PRESENT"}
    ],
    "PROTEIN": [
        {"text": "amyloid-beta", "confidence": 0.92, "assertion": "PRESENT"},
        {"text": "tau", "confidence": 0.90, "assertion": "PRESENT"}
    ]
}
```

**Itération 3 : Détection de Signaux**
```python
Tool Call: detect_signals(
    entity_types=["DRUG", "DISEASE"],
    weeks_ago=4
)

Result: {
    "emerging_signals": [
        {
            "entity_a": "Semaglutide",
            "entity_b": "Alzheimer disease",
            "emergence_score": 85,
            "new_mentions": 5,
            "source_diversity": 3,
            "consensus": {
                "positive": 0.60,
                "negative": 0.20,
                "hypothetical": 0.20
            },
            "interpretation": "Signal émergent fort - 3 équipes indépendantes"
        }
    ]
}
```

**Itération 4 : Recherche dans Documents Uploadés**
```python
Tool Call: retrieve_knowledge(
    query="Semaglutide Alzheimer neuroprotection",
    top_k=5,
    enable_kg_enrichment=True
)

Result: {
    "context": "Plusieurs études récentes suggèrent que le semaglutide...",
    "sources": ["doc_123", "doc_456"],
    "kg_entities": ["GLP-1 receptor", "cognitive decline"]
}
```

**Itération 5 : Synthèse Finale**
```python
LLM génère la réponse finale (pas de tool_call)

Response: 
"Voici les informations sur les nouveaux traitements pour Alzheimer :

## Traitements Émergents

1. **Semaglutide** (GLP-1 agoniste)
   - Signal émergent fort détecté (score: 85/100)
   - 5 nouvelles mentions dans la littérature récente
   - 3 équipes indépendantes rapportent des effets neuroprotecteurs
   - Consensus : 60% positif, 20% négatif, 20% hypothétique
   - [Source: PMID 38123456, Documents uploadés]

2. **Lecanemab** (anticorps anti-amyloïde)
   - Approuvé par la FDA en 2023
   - Réduit les plaques amyloïdes de 27%
   - [Source: PMID 38123457]

3. **Donanemab** (anticorps anti-tau)
   - En phase 3 d'essais cliniques
   - Résultats prometteurs sur le déclin cognitif
   - [Source: PMID 38123458]

## Signaux Émergents Détectés

L'association **Semaglutide ↔ Alzheimer** est un signal émergent majeur :
- N'existait pas il y a 4 semaines
- Apparaît maintenant dans 5 publications récentes
- Provient de 3 pays différents (USA, UK, Japon)
- Mécanisme proposé : neuroprotection via récepteurs GLP-1

⚠️ Note : Le consensus scientifique est encore en formation (60% positif). 
Des études supplémentaires sont nécessaires pour confirmer l'efficacité."
```

#### **5. Streaming au Frontend (NDJSON)**
```
{"step": "🚀 Starting Deep Agent..."}
{"step": " Thinking... (step 1/5)"}
{"step": " Using tool: search_pubmed"}
{"step": " Tool result received (20 items)"}
{"step": " Using tool: extract_entities"}
{"step": " Tool result received"}
{"step": " Using tool: detect_signals"}
{"step": " Tool result received"}
{"step": " Using tool: retrieve_knowledge"}
{"step": " Tool result received (5 documents)"}
{"response": "Voici les informations sur les nouveaux traitements...", "canHandle": true}
```

---

## Arborescence Complète du Module Deep Agent

```
bio-horizon/biomed-rag/deepagents/
│
├── __init__.py                          # Export principal
│   └── create_biomedical_agent
│
├── README.md                            # Documentation
│
├── memory.py                            # 🧠 MÉMOIRE UNIFIÉE (dual-write)
│   ├── ConversationMemoryManager        # Interface LangChain (BaseMessage)
│   │   ├── get_history()                # Récupère l'historique
│   │   ├── add_messages()               # Ajoute des messages
│   │   ├── clear_conversation()         # Efface une conversation
│   │   ├── list_conversations()         # Liste les conversations
│   │   └── get_stats()                  # Statistiques mémoire
│   │
│   ├── save_message()                   # Interface StoredMessage (Supabase + fallback)
│   ├── load_history()                   # Charge depuis Supabase ou in-memory
│   └── StoredMessage                    # Dataclass compatible legacy
│
├── agents/                              # 🤖 AGENTS
│   ├── __init__.py
│   ├── main_agent.py                    # ⭐ AGENT PRINCIPAL
│   │   ├── create_biomedical_agent()    # Crée l'agent complet
│   │   ├── create_simple_rag_agent()    # Agent RAG simple (LangChain AgentExecutor)
│   │   └── SimpleAgentExecutor          # Boucle d'exécution custom avec streaming
│   │
│   ├── pubmed_agent.py                  # 🔨 À IMPLÉMENTER
│   ├── ner_agent.py                     # 🔨 À IMPLÉMENTER
│   ├── signal_agent.py                  # 🔨 À IMPLÉMENTER
│   └── prompts.py                       # 🔨 Prompts système
│
├── tools/                               # 🛠️ OUTILS (Tools LangChain)
│   │
│   ├── __init__.py
│   │
│   ├── biomedical/                      # 🧬 OUTILS BIOMÉDICAUX
│   │   ├── __init__.py
│   │   ├── pubmed_tool.py               # 🔨 Recherche PubMed
│   │   │   └── @tool search_pubmed()
│   │   │
│   │   ├── ner_tool.py                  # 🔨 Extraction NER
│   │   │   └── @tool extract_entities()
│   │   │
│   │   ├── kg_tool.py                   # 🔨 Requêtes Knowledge Graph
│   │   │   └── @tool query_kg()
│   │   │
│   │   └── signal_tool.py               # 🔨 Détection de signaux
│   │       └── @tool detect_signals()
│   │
│   ├── knowledge/                       # 📚 OUTILS CONNAISSANCES
│   │   ├── __init__.py
│   │   └── rag_tool.py                  # ✅ RAG (Retrieval-Augmented Generation)
│   │       └── @tool retrieve_knowledge()
│   │
│   └── document/                        # 📄 OUTILS DOCUMENTS
│       ├── __init__.py
│       ├── pdf_loader.py                # ✅ Parsing PDF (PyMuPDF)
│       ├── store_pdf.py                 # ✅ Stockage PDF (Supabase)
│       ├── summarizer.py                # ✅ Résumé de documents
│       ├── vector_store.py              # ✅ Indexation vectorielle
│       └── query_cache.py               # ✅ Cache de requêtes
│
└── graph/                               # 🕸️ LANGGRAPH WORKFLOWS (cible)
    ├── surveillance.py                  # 🔨 Workflow surveillance hebdo
    ├── ask_workflow.py                  # 🔨 Workflow question-réponse
    └── nodes.py                         # 🔨 Nœuds réutilisables
```

### **Légende**
- ✅ = Implémenté et fonctionnel
- 🔨 = À implémenter (fichier existe, contenu stub)
- ⭐ = Composant central

---

## Projection sur l'Arborescence Globale du Projet

```
bio-horizon/
│
├── biomed-rag/                                    # 🐍 BACKEND PYTHON
│   │
│   ├── main.py                                 # Point d'entrée FastAPI
│   │   └── app.include_router(api_router)       # Un seul routeur monté
│   │
│   ├── api/                                    # 🌐 API LAYER
│   │   ├── router.py                           # Routeur principal (combine les sub-routers)
│   │   └── routes/
│   │       ├── ask.py                          # ⭐ POST /ask → Deep Agent (NDJSON streaming)
│   │       ├── upload.py                       # POST /upload (PDF → indexation)
│   │       ├── health.py                       # GET /health
│   │       ├── conversations.py                # /conversations/* (CRUD via deepagents/memory)
│   │       ├── pubmed.py                       # /pubmed/*
│   │       ├── ner.py                          # /ner/*
│   │       ├── kg.py                           # /kg/*
│   │       ├── signals.py                      # /signals/*
│   │       ├── cache.py                        # /cache/* (via deepagents/tools/document)
│   │       ├── users.py                        # /users/*
│   │       └── topics.py                       # /topics/*
│   │
│   ├── deepagents/                             # 🤖 DEEP AGENTS (FOCUS)
│   │   ├── __init__.py                         # Export : create_biomedical_agent
│   │   ├── memory.py                           # Mémoire unifiée (Supabase + in-memory)
│   │   ├── agents/
│   │   │   └── main_agent.py                   # create_biomedical_agent() + SimpleAgentExecutor
│   │   └── tools/
│   │       ├── biomedical/                     # 🔨 PubMed, NER, KG, Signals (stubs)
│   │       ├── knowledge/                      # ✅ RAG (retrieve_knowledge)
│   │       └── document/                       # ✅ PDF, Summarization, Vector Store, Cache
│   │
│   ├── core_tools/                             # 🔧 OUTILS MÉTIER (non-agent)
│   │   ├── pubmed_tool.py                      # Recherche PubMed (NCBI E-utilities)
│   │   ├── ner_tool.py                         # Extraction NER (wrapper)
│   │   └── kg_tool.py                          # Construction et requête KG
│   │
│   ├── ner/                                    # 🧬 MODULE NER
│   │   ├── backends/
│   │   │   ├── openmed_backend.py              # NER standard
│   │   │   ├── openmed_zeroshot.py             # NER zero-shot
│   │   │   └── gliner_backend.py               # Fallback
│   │   ├── assertion.py                        # Assertion Status
│   │   └── router.py                           # Sélection backend
│   │
│   ├── kg/                                     # 🕸️ MODULE KNOWLEDGE GRAPH
│   │   ├── build.py                            # Construction KG
│   │   ├── query.py                            # Requêtes KG
│   │   ├── snapshots.py                        # Snapshots temporels
│   │   └── normalize.py                        # Normalisation entités
│   │
│   ├── signals/                                # 📊 MODULE DÉTECTION SIGNAUX
│   │   ├── detector.py                         # Algorithme détection
│   │   ├── scoring.py                          # Score d'émergence
│   │   ├── consensus.py                        # Score de consensus
│   │   └── reporter.py                         # Génération rapports
│   │
│   ├── rag/                                    # 📚 MODULE RAG
│   │   ├── chain.py                            # Chaîne RAG (importe deepagents/memory)
│   │   ├── retriever.py                        # Retriever + KG enrichment
│   │   └── vector_store.py                     # Vector store Supabase
│   │
│   ├── services/                               # 🏢 SERVICES MÉTIER
│   │   ├── topic_service.py                    # Gestion sujets de veille
│   │   └── user_service.py                     # Gestion préférences utilisateur
│   │
│   ├── storage/                                # 💾 STOCKAGE
│   │   └── supabase_client.py                  # Client Supabase singleton
│   │
│   ├── config/                                 # ⚙️ CONFIGURATION
│   │   └── config.py                           # Env, encodage, CORS, logging
│   │
│   └── database/                               # 🗄️ MIGRATIONS SQL
│       └── migrations/
│
├── ui-biomed-rag/                              # ⚛️ FRONTEND NEXT.JS
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx                        # Page d'accueil
│   │   │   ├── ask/page.tsx                    # Interface chat (appelle POST /ask)
│   │   │   ├── ner/page.tsx                    # Interface NER
│   │   │   └── kg/page.tsx                     # Visualisation KG
│   │   │
│   │   └── components/
│   │       ├── ChatInterface.tsx               # Composant chat
│   │       └── AgentSteps.tsx                  # Affichage des étapes agent
│   │
│   └── package.json
│
├── supabase/                                   # 🗄️ BASE DE DONNÉES
│   └── config.toml
│
├── DEEPAGENT_ARCHITECTURE.md                   # 📖 Ce document
└── PRESENTATION.md                             # 📊 Présentation projet
```

---

## Flux de Données : De la Requête à la Réponse

```
┌─────────────────────────────────────────────────────────────────────┐
│  1. UTILISATEUR                                                      │
│     "Quels sont les nouveaux traitements pour Alzheimer ?"          │
│     (+ optionnel : upload de fichiers PDF)                           │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  2. FRONTEND (ui-biomed-rag/src/app/ask/page.tsx)                   │
│     POST /ask                                                        │
│     { "query": "...", "conversation_id": "conv-123" }               │
│     (ou multipart/form-data si fichiers PDF attachés)               │
└────────────────────────────┬────────────────────────────────────────┘
                             │ HTTP
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  3. ENDPOINT /ask (api/routes/ask.py)                                │
│     • Si fichiers → upload + parse PDF + indexation vectorielle      │
│     • _build_deep_agent_stream()                                     │
│     • Crée l'agent dans un thread séparé                             │
│     • Stream les étapes via queue → NDJSON                           │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  4. MAIN AGENT (deepagents/agents/main_agent.py)                    │
│     SimpleAgentExecutor.invoke()                                    │
│                                                                     │
│     Itération 1:                                                    │
│     ├─ LLM → "Je vais chercher dans les documents"                  │
│     ├─ Tool Call → retrieve_knowledge(query="Alzheimer treatment")  │
│     └─ Result → {context: "...", sources: [...]}                    │
│                                                                     │
│     Itération 2 (si tools biomédicaux activés) :                    │
│     ├─ LLM → "Je vais chercher dans PubMed"                         │
│     ├─ Tool Call → search_pubmed(...)                               │
│     └─ Result → [articles]                                          │
│                                                                     │
│     Itération N :                                                   │
│     └─ LLM → "Voici les informations..." [RÉPONSE FINALE]           │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  5. TOOLS                                                            │
│                                                                     │
│  ✅ retrieve_knowledge() → rag/chain.py → rag/retriever.py          │
│                          → Supabase pgvector (embeddings)           │
│                          → kg/ (enrichissement KG)                   │
│                                                                     │
│  🔨 search_pubmed()      → core_tools/pubmed_tool.py               │
│                          → PubMed API (NCBI E-utilities)            │
│                                                                     │
│  🔨 extract_entities()   → core_tools/ner_tool.py → ner/           │
│                          → ner/backends/openmed_backend.py          │
│                                                                     │
│  🔨 detect_signals()     → signals/detector.py → kg/snapshots.py   │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  6. STOCKAGE (Supabase PostgreSQL)                                  │
│     • documents (PDFs uploadés)                                     │
│     • embeddings (vectors pour RAG / pgvector)                      │
│     • conversation_messages (historique conversations)               │
│     • kg_snapshots (snapshots temporels)                            │
│     • signals (signaux détectés)                                    │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  7. RÉPONSE STREAMÉE (NDJSON)                                        │
│     {"step": "� Starting Deep Agent..."}                            │
│     {"step": " Thinking... (step 1/5)"}                             │
│     {"step": " Using tool: retrieve_knowledge"}                     │
│     {"step": " Tool result received (3 documents)"}                 │
│     {"response": "Voici les informations...", "canHandle": true}    │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  8. FRONTEND AFFICHAGE                                              │
│     • Affiche les étapes en temps réel (NDJSON parsing)             │
│     • Affiche la réponse finale avec citations                      │
│     • Sauvegarde dans l'historique de conversation                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Comparaison : smolagents vs Deep Agents

| Aspect | smolagents (Ancien) | Deep Agents (Nouveau) |
|--------|---------------------|----------------------|
| **Framework** | Hugging Face smolagents | LangChain + LangGraph |
| **Planification** | Manuelle (write_todos) | Automatique (LLM décide) |
| **Sub-agents** | ❌ Non supporté | ✅ Agents spécialisés |
| **Mémoire** | Custom in-memory | Dual-write (Supabase + in-memory fallback) |
| **Streaming** | Custom SSE | NDJSON streaming via /ask |
| **Tools** | Custom format | LangChain @tool decorator |
| **Debugging** | Logs basiques | LangSmith (traçabilité complète) |
| **KG Integration** | Custom | Natif via tools |
| **Scalabilité** | Limitée | Haute (LangGraph workflows) |

---

## Avantages du Deep Agent

### **1. Autonomie**
L'agent décide lui-même quels outils utiliser et dans quel ordre.

### **2. Contextualité**
Grâce à la mémoire conversationnelle, l'agent comprend les références ("ses effets secondaires" → imatinib).

### **3. Précision**
Les tools spécialisés (PubMed, NER, KG) fournissent des données réelles, pas des hallucinations.

### **4. Traçabilité**
Chaque étape est loggée et peut être inspectée (LangSmith).

### **5. Extensibilité**
Ajouter un nouveau tool = créer une fonction avec `@tool` decorator.

---

## Prochaines Étapes (Roadmap)

### **Phase 1 : Infrastructure** (✅ Terminée)
- [x] Architecture Deep Agent (SimpleAgentExecutor + tool-calling)
- [x] Endpoint unifié `/ask` (api/routes/ask.py) avec streaming NDJSON
- [x] Mémoire unifiée (deepagents/memory.py) avec dual-write Supabase
- [x] Suppression des composants legacy (smolagents, agent_lc, router.py)
- [x] Nettoyage de main.py (un seul routeur api_router)

### **Phase 2 : Migration des Tools** (En cours)
- [x] `retrieve_knowledge` (RAG) — ✅ fonctionnel, seul tool actif
- [ ] `search_pubmed` (PubMed) — stub dans deepagents/tools/biomedical/
- [ ] `extract_entities` (NER) — stub dans deepagents/tools/biomedical/
- [ ] `query_kg` (Knowledge Graph) — stub dans deepagents/tools/biomedical/
- [ ] `detect_signals` (Signaux) — stub dans deepagents/tools/biomedical/

### **Phase 3 : Sub-Agents Spécialisés**
- [ ] **PubMed Research Agent** : Expert en recherche PubMed
- [ ] **NER Agent** : Expert en extraction d'entités
- [ ] **Signal Detection Agent** : Expert en détection de signaux

### **Phase 4 : LangGraph Workflows**
- [ ] **Surveillance Workflow** : PubMed → NER → KG → Signaux (automatisé)
- [ ] **Ask Workflow** : Question → RAG → Réponse (optimisé)
- [ ] Migration de SimpleAgentExecutor vers LangGraph StateGraph

---

## Conclusion

Le **Deep Agent** est le cerveau de BioHorizon. Il transforme une simple requête utilisateur en une orchestration complexe d'outils biomédicaux, permettant de :

1. **Rechercher** dans PubMed
2. **Extraire** des entités médicales
3. **Construire** des Knowledge Graphs
4. **Détecter** des signaux émergents
5. **Synthétiser** des réponses avec citations

**Architecture modulaire** : Chaque composant (agent, tools, memory) est indépendant et réutilisable.

**Évolutivité** : Ajouter de nouvelles capacités = ajouter de nouveaux tools.

**Traçabilité** : Chaque étape est visible et debuggable.

**Le Deep Agent est la clé qui transforme BioHorizon d'un simple chatbot en un véritable assistant de recherche biomédicale intelligent.**
