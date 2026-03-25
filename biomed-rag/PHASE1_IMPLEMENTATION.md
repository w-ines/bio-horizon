# Phase 1 Implementation — Temporal KG Snapshots

**Status**: ✅ Complete  
**Date**: March 19, 2026  
**Goal**: Transform the static Knowledge Graph into a temporal system that tracks evolution over time

---

## What Was Implemented

### 1. `kg/snapshots.py` — Temporal Snapshot Management (574 lines)

This is the **core module** that enables BioHorizon's temporal dimension. It provides:

#### **Week Label Utilities**
- `get_week_label(date)` — Convert any date to ISO week format (e.g., `2026-W12`)
- `parse_week_label(week_label)` — Convert week label back to Monday of that week
- `get_week_label_offset(weeks_ago)` — Get week label for N weeks ago

**Why ISO weeks?** They provide a standardized, unambiguous way to identify time periods across years.

#### **File-based Storage (JSON backup)**
- `save_snapshot_to_file(G, week_label)` — Save NetworkX graph as JSON file
- `load_snapshot_from_file(week_label)` — Load graph from JSON file
- `get_snapshot_filepath(week_label)` — Get path to snapshot file

**Storage location**: `data/kg_snapshots/2026-W12.json`

**Why files?** Provides offline backup, debugging capability, and portability independent of database.

#### **Supabase Storage (persistent database)**
- `save_snapshot_to_supabase(G, week_label)` — Save to PostgreSQL as JSONB
- `load_snapshot_from_supabase(week_label)` — Load from database

**Why Supabase?** Enables efficient querying, indexing, and integration with the rest of the app.

#### **High-level API (recommended)**
- `save_snapshot(G, week_label)` — Save to BOTH Supabase and file (redundancy)
- `load_snapshot(week_label)` — Load from Supabase first, fallback to file
- `list_available_snapshots()` — List all available week labels

**Redundancy strategy**: Always save to both storages. Load tries Supabase first (faster), falls back to file if unavailable.

#### **Snapshot Comparison (foundation for signal detection)**
- `compare_snapshots(G_new, G_old)` — Compare two graphs to detect changes

**Returns**:
```python
{
    "new_nodes": [...],              # Entities that appeared
    "disappeared_nodes": [...],      # Entities that disappeared
    "new_edges": [...],              # Relations that appeared
    "disappeared_edges": [...],      # Relations that disappeared
    "weight_increased": [...],       # Relations that strengthened
    "weight_decreased": [...],       # Relations that weakened
    "summary": {
        "total_new_nodes": 15,
        "total_new_edges": 42,
        ...
    }
}
```

**This is the foundation for signal detection**: By comparing KG(week N) vs KG(week N-4), we identify what's emerging.

---

### 2. `database/migrations/002_create_kg_snapshots.sql` — Database Schema

#### **Table: `kg_snapshots`**
Stores weekly snapshots of the entire Knowledge Graph.

```sql
CREATE TABLE kg_snapshots (
    id SERIAL PRIMARY KEY,
    week_label TEXT NOT NULL UNIQUE,      -- '2026-W12'
    snapshot_date DATE NOT NULL,          -- When snapshot was created
    node_count INTEGER,                   -- Quick metadata
    edge_count INTEGER,
    data JSONB NOT NULL,                  -- Full graph: {nodes: [...], edges: [...]}
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);
```

**Indexes**:
- `week_label` — Fast lookup by week
- `snapshot_date` — Temporal queries
- GIN index on `data` — Efficient JSONB querying

**Why JSONB?** PostgreSQL's JSONB type allows storing the entire graph structure while still being queryable with SQL.

#### **Table: `signals`**
Stores detected emerging signals (to be populated in Phase 2).

```sql
CREATE TABLE signals (
    id SERIAL PRIMARY KEY,
    week_label TEXT NOT NULL,
    signal_type TEXT NOT NULL,            -- 'emerging', 'accelerating', 'declining'
    entity_a TEXT,
    entity_b TEXT,
    emergence_score FLOAT,                -- 0-100
    velocity FLOAT,
    source_diversity INTEGER,
    consensus_positive FLOAT,             -- Phase 5
    consensus_negative FLOAT,             -- Phase 5
    consensus_hypothetical FLOAT,         -- Phase 5
    pmids JSONB,
    details JSONB,
    created_at TIMESTAMPTZ
);
```

**Prepared for future phases**: Consensus fields are ready for Phase 5 (Assertion Status).

#### **Table: `entity_assertions`**
Tracks assertion status per entity per article (Phase 5).

```sql
CREATE TABLE entity_assertions (
    id SERIAL PRIMARY KEY,
    entity_id INTEGER,
    pmid TEXT NOT NULL,
    assertion_status TEXT NOT NULL,       -- 'PRESENT', 'NEGATED', 'HYPOTHETICAL', 'HISTORICAL'
    confidence FLOAT,
    context_sentence TEXT,
    created_at TIMESTAMPTZ
);
```

---

### 3. `api/routes/signals.py` — REST API Endpoints (345 lines)

Provides HTTP endpoints to interact with the snapshot system.

#### **Snapshot Management Endpoints**

##### `GET /signals/snapshots`
List all available snapshots.

**Response**:
```json
{
    "snapshots": ["2026-W08", "2026-W09", "2026-W10", "2026-W11", "2026-W12"],
    "current_week": "2026-W12",
    "total_count": 5
}
```

##### `GET /signals/snapshots/{week_label}`
Get metadata about a specific snapshot.

**Response**:
```json
{
    "week_label": "2026-W12",
    "node_count": 342,
    "edge_count": 1205,
    "entity_types": {
        "DISEASE": 45,
        "DRUG": 78,
        "GENE": 123,
        "PROTEIN": 96
    }
}
```

##### `GET /signals/compare?week_new=2026-W12&week_old=2026-W08`
Compare two snapshots to detect changes.

**Response**:
```json
{
    "week_new": "2026-W12",
    "week_old": "2026-W08",
    "summary": {
        "total_new_nodes": 15,
        "total_new_edges": 42,
        "total_weight_increased": 8
    },
    "new_nodes": [
        {
            "id": "DRUG::semaglutide",
            "label": "Semaglutide",
            "entity_type": "DRUG",
            "frequency": 5
        },
        ...
    ],
    "new_edges": [
        {
            "source": {"id": "DRUG::semaglutide", "label": "Semaglutide", ...},
            "target": {"id": "DISEASE::alzheimer_disease", "label": "Alzheimer Disease", ...}
        },
        ...
    ],
    "weight_increased": [
        {
            "source": {...},
            "target": {...},
            "old_weight": 2,
            "new_weight": 7,
            "delta": 5
        },
        ...
    ]
}
```

**This is the raw material for signal detection**: The delta shows what changed between two time periods.

##### `GET /signals/compare/current?weeks_ago=4`
Convenience endpoint: compare current week vs N weeks ago.

**Use case**: Weekly automated surveillance — "What emerged in the last 4 weeks?"

#### **Signal Detection Endpoints (Phase 2 stubs)**

These endpoints are **stubs** that will be implemented in Phase 2 when `signals/detector.py` and `signals/scoring.py` are built:

- `GET /signals/` — List detected signals (sorted by emergence score)
- `GET /signals/{signal_id}` — Get signal details
- `GET /signals/consensus/{entity_a}/{entity_b}` — Get consensus score (Phase 5)

**Current behavior**: They return helpful messages pointing users to the `/compare` endpoints.

---

## How It Works — End-to-End Flow

### **Scenario**: Weekly surveillance for Alzheimer research

#### **Week 1 (2026-W08)**
1. User runs PubMed search: `"Alzheimer disease" AND ("treatment" OR "therapy")`
2. Backend fetches 50 recent articles
3. NER extracts entities from abstracts
4. KG builder creates graph from entities
5. **Snapshot saved**: `save_snapshot(G, '2026-W08')`
   - Saved to Supabase: `kg_snapshots` table
   - Saved to file: `data/kg_snapshots/2026-W08.json`

**Graph at week 8**: 200 nodes, 800 edges

#### **Week 5 (2026-W12) — 4 weeks later**
1. Same PubMed search runs automatically (scheduled)
2. NER + KG pipeline runs
3. **Snapshot saved**: `save_snapshot(G, '2026-W12')`

**Graph at week 12**: 215 nodes (+15), 842 edges (+42)

#### **Signal Detection (automatic)**
```python
from kg.snapshots import load_snapshot, compare_snapshots

G_new = load_snapshot('2026-W12')
G_old = load_snapshot('2026-W08')

delta = compare_snapshots(G_new, G_old)

print(f"New entities: {len(delta['new_nodes'])}")  # 15
print(f"New relations: {len(delta['new_edges'])}")  # 42
print(f"Strengthened relations: {len(delta['weight_increased'])}")  # 8
```

**Example emerging signal**:
```python
# New edge detected:
{
    "source": {"label": "Semaglutide", "entity_type": "DRUG"},
    "target": {"label": "Alzheimer Disease", "entity_type": "DISEASE"},
    "weight": 5,  # 5 articles mention this association
}
```

**Interpretation**: "Semaglutide ↔ Alzheimer" is a **new association** that didn't exist 4 weeks ago. This is an **emerging signal** worth investigating.

---

## Code Architecture — Key Design Decisions

### **1. Dual Storage (Supabase + Files)**

**Why both?**
- **Supabase**: Fast querying, integration with app, scalable
- **Files**: Offline backup, debugging, portability, no DB dependency

**Graceful degradation**: If Supabase is down, the system falls back to files automatically.

### **2. ISO Week Labels**

**Why not dates?**
- Weeks are the natural granularity for biomedical surveillance
- ISO weeks are standardized (Monday-Sunday, unambiguous across years)
- Human-readable: `2026-W12` is clearer than `2026-03-16`

### **3. NetworkX for Graph Representation**

**Why NetworkX?**
- Industry-standard Python graph library
- Rich algorithms (shortest path, centrality, clustering)
- Easy serialization to/from JSON
- Integrates with visualization libraries

**Alternative considered**: Neo4j (graph database) — overkill for MVP, adds complexity.

### **4. JSONB in PostgreSQL**

**Why JSONB?**
- Stores entire graph structure in a single column
- Still queryable with SQL (`data->'nodes'`, GIN indexes)
- No need for complex relational schema (nodes table, edges table, etc.)
- Flexible: can add metadata without schema migrations

**Trade-off**: Less normalized, but simpler and faster for this use case.

### **5. Snapshot Comparison Algorithm**

**Set-based comparison**:
```python
nodes_new = set(G_new.nodes())
nodes_old = set(G_old.nodes())
new_nodes = nodes_new - nodes_old  # Set difference
```

**Why sets?** O(n) time complexity, simple, efficient.

**Weight comparison**: Only for edges present in both snapshots.

---

## Testing the Implementation

### **1. Run the SQL migration**

```bash
# Connect to your Supabase database
psql $DATABASE_URL -f database/migrations/002_create_kg_snapshots.sql
```

Or use Supabase dashboard to run the SQL.

### **2. Test snapshot creation (Python)**

```python
from kg.build import build_graph_from_ner_results
from kg.snapshots import save_snapshot, load_snapshot

# Assume you have NER results from PubMed
ner_results = [...]  # From your PubMed → NER pipeline

# Build graph
G = build_graph_from_ner_results(ner_results)

# Save snapshot
snapshot_id, filepath = save_snapshot(G, '2026-W12')
print(f"Saved to Supabase (ID={snapshot_id}) and {filepath}")

# Load snapshot
G_loaded = load_snapshot('2026-W12')
print(f"Loaded {G_loaded.number_of_nodes()} nodes")
```

### **3. Test API endpoints**

```bash
# Start the backend
cd biomed-rag
uvicorn main:app --reload

# Test endpoints
curl http://localhost:8000/signals/snapshots
curl http://localhost:8000/signals/snapshots/2026-W12
curl "http://localhost:8000/signals/compare?week_new=2026-W12&week_old=2026-W08"
curl "http://localhost:8000/signals/compare/current?weeks_ago=4"
```

### **4. End-to-end test scenario**

See `test_pubmed_kg.py` for an example pipeline:

```python
# 1. Search PubMed
articles = search_pubmed("Alzheimer disease treatment")

# 2. Extract entities
ner_results = extract_entities_batch(articles)

# 3. Build KG
G = build_graph_from_ner_results(ner_results)

# 4. Save snapshot
save_snapshot(G, '2026-W12')

# 5. Compare with previous week
G_old = load_snapshot('2026-W11')
delta = compare_snapshots(G, G_old)

# 6. Analyze delta
print(f"New entities: {delta['summary']['total_new_nodes']}")
print(f"New relations: {delta['summary']['total_new_edges']}")
```

---

## What's Next — Phase 2

Phase 1 provides the **foundation** (temporal snapshots). Phase 2 builds **signal detection** on top:

### **To implement**:

1. **`signals/detector.py`** — Algorithm to identify emerging signals from deltas
2. **`signals/scoring.py`** — Calculate emergence score (novelty + velocity + diversity + impact)
3. **`signals/classifier.py`** — Classify signals (emerging / accelerating / declining)
4. **`signals/reporter.py`** — Generate structured reports
5. **Update `/signals/` endpoint** — Return actual detected signals, not stubs

### **Emergence Score Formula** (from spec):

```python
emergence_score = (
    0.30 * novelty_score +        # How recent is this relation?
    0.30 * velocity_score +       # How fast is it growing?
    0.20 * diversity_score +      # How many independent sources?
    0.20 * impact_score           # What's the journal impact factor?
)
```

### **Signal Classification**:
- **Emerging** (🔴): New relation, score > 70, 3+ independent sources
- **Accelerating** (🟡): Existing relation, weight increased > 2x
- **Declining** (⚫): Relation weight decreased significantly
- **Contradictory** (Phase 5): Consensus split (40-60% positive/negative)

---

## Summary

### **What was delivered**:
✅ `kg/snapshots.py` — 574 lines, fully documented, dual storage, comparison algorithm  
✅ `002_create_kg_snapshots.sql` — Database schema for snapshots, signals, assertions  
✅ `api/routes/signals.py` — 345 lines, 6 functional endpoints, 3 stubs for Phase 2  

### **Key achievement**:
The Knowledge Graph is now **temporal**. It's no longer a static photo — it's a **film** that tracks evolution over time.

### **What this enables**:
- Weekly snapshots of the biomedical landscape
- Comparison between time periods
- Detection of emerging entities and relations
- Foundation for signal scoring (Phase 2)
- Foundation for consensus analysis (Phase 5)

### **How to use it**:
1. Run your PubMed → NER → KG pipeline
2. Call `save_snapshot(G)` to save the current week
3. Wait 4 weeks, run again
4. Call `compare_snapshots(G_new, G_old)` to see what emerged
5. (Phase 2) Call `/signals/` to get scored, classified signals

**The temporal dimension is live. BioHorizon can now detect what's emerging.**
