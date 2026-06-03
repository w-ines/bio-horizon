# bio-horizon (biomed-rag)

A **biomedical literature intelligence backend** — a FastAPI service that lets researchers query PubMed, extract biomedical entities and relations, build a Knowledge Graph from the literature, and ask natural-language questions over scientific papers and uploaded documents. An LLM agent orchestrates the tools and synthesizes cited answers.

---

## Features

- **Conversational research agent** — ask biomedical questions in natural language and get answers with `[PMID: ...]` citations.
- **PubMed search** — live retrieval from NCBI E-utilities.
- **Biomedical NER** — extract diseases, drugs, genes, proteins, chemicals, anatomy, etc. (standard + zero-shot).
- **Relation extraction** — classify semantic relations between entities (`treats`, `inhibits`, `causes`, `activates`, ...).
- **Knowledge Graph** — build and query a graph of entities and their relations from the literature.
- **Document RAG** — upload PDFs (with OCR), index them, and ask questions about their content.
- **Corpus ingestion jobs** — async large-scale analysis of literature on a topic (NER + KG).
- **Conversation memory** — persisted per-conversation history.

---

## Architecture

- **API layer** — FastAPI (`main.py` + `api/router.py`), streaming NDJSON responses, CORS, containerized with Docker / Railway.
  - Endpoints: `ask`, `upload`, `pubmed`, `ner`, `kg`, `jobs`, `conversations`, `users`, `topics`.
- **Agent core** (`deepagents/`) — LangChain / LangGraph "Deep Agent" (`SimpleAgentExecutor`) using `bind_tools()` for structured function calling; conversation memory persisted to Supabase.
- **NER engine** (`ner/`) — pluggable backends: **PubTator3** (default, NCBI API), **OpenMed**, **GLiNER2**; supports standard + zero-shot entities, assertion status, and relation extraction.
- **Knowledge Graph** (`kg/`) — entity/relation extraction into a NetworkX graph, with normalization and storage.
- **RAG** (`rag/`) — vector store + retriever + chain for uploaded PDFs.
- **Jobs/Scheduler** (`jobs/`, `scheduler/`) — async corpus ingestion jobs.
- **Storage** — Supabase (conversations, users, topics), Redis (cache / rate-limiting), local file storage for PDFs.

---

## Models

The project uses a **two-tier model strategy**: a general-purpose LLM for reasoning and conversation, and small specialized **PubMedBERT** models for precise biomedical extraction.

| Role | Model | Location | Notes |
|------|-------|----------|-------|
| Agent / reasoning / answers | `openai/gpt-4o-mini` | External (OpenRouter) | Tool orchestration via `bind_tools()` |
| OCR (scanned PDFs) | `gpt-4-vision-preview` | External (OpenRouter) | Optional |
| NER (default) | PubTator3 | External (NCBI API) | Switchable to local OpenMed / GLiNER2 |
| Relation extraction | `wesin/pubmedbert-relation-extraction` | **Local** (HuggingFace) | 9 relation types, no API key |
| Assertion status | `assertion-pubmedbert` | **Local** (HuggingFace) | PRESENT / NEGATED / HYPOTHETICAL / HISTORICAL |

All model providers are env-configurable. The LLM uses an OpenAI-compatible endpoint (`BASE_URL`), so it can be pointed at a local server (Ollama, vLLM, ...) that supports function calling.

---

## Tech Stack

- **Framework:** FastAPI, Uvicorn
- **Agent:** LangChain, LangGraph, `langchain-openai`
- **NER/Relations:** PubTator3, OpenMed, GLiNER2, `transformers` + `torch` (PubMedBERT)
- **Graph:** NetworkX
- **Storage:** Supabase, Redis
- **Documents:** PyMuPDF, pypdf, pytesseract (OCR)

---

## Getting Started

### Prerequisites
- Python 3.10+
- Redis (for caching)
- A Supabase project
- An OpenRouter API key (or any OpenAI-compatible endpoint)

### Installation

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configuration

Create a `.env` file (see existing keys). Key variables:

```bash
# LLM (OpenRouter / OpenAI-compatible)
LLM_PROVIDER=openrouter
BASE_URL=https://openrouter.ai/api/v1
OPEN_ROUTER_KEY=your_key_here
OPEN_AI_MODEL=openai/gpt-4o-mini

# NCBI / PubMed
NCBI_BASE_URL=https://eutils.ncbi.nlm.nih.gov/entrez/eutils
NCBI_API_KEY=your_key_here
NCBI_EMAIL=you@example.com

# Supabase
SUPABASE_URL=...
SUPABASE_KEY=...

# Redis
REDIS_URL=redis://localhost:6379/0

# NER / model backends
NER_PROVIDER=pubtator3
RELATION_MODEL_PATH=wesin/pubmedbert-relation-extraction
HF_TOKEN=your_hf_token   # for HuggingFace model access
```

### Run

```bash
python main.py
# or
uvicorn main:app --host 0.0.0.0 --port 8000
```

API available at `http://localhost:8000` (interactive docs at `/docs`).

### Docker

```bash
docker compose up --build
```

---

## Usage

### Ask a question

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the latest treatments for Alzheimer disease?"}'
```

Returns a streaming NDJSON response with the agent's steps and a final cited answer.

### Upload a PDF and ask about it

```bash
curl -X POST http://localhost:8000/ask \
  -F "files=@paper.pdf" \
  -F "query=Summarize the methods of this paper"
```

---

## Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /ask` | Conversational agent (with optional file upload) |
| `POST /upload` | Upload and index PDFs |
| `GET /pubmed` | PubMed search |
| `POST /ner` | Named entity recognition |
| `GET/POST /kg` | Knowledge Graph build/query |
| `POST /jobs` | Corpus ingestion jobs |
| `*/conversations`, `*/users`, `*/topics` | Memory & topic tracking |
| `GET /health` | Health check |

