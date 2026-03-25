-- Migration 002: Create kg_snapshots table for temporal KG tracking
-- This table stores weekly snapshots of the Knowledge Graph to enable
-- temporal comparison and signal detection.

-- =============================================================================
-- kg_snapshots: Weekly snapshots of the entire Knowledge Graph
-- =============================================================================

CREATE TABLE IF NOT EXISTS kg_snapshots (
    id SERIAL PRIMARY KEY,
    
    -- Week identifier (ISO format: '2026-W12')
    week_label TEXT NOT NULL UNIQUE,
    
    -- Date when this snapshot was created
    snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE,
    
    -- Metadata: counts for quick reference
    node_count INTEGER DEFAULT 0,
    edge_count INTEGER DEFAULT 0,
    
    -- The actual graph data stored as JSONB
    -- Structure: { "nodes": [...], "edges": [...] }
    -- Each node: { "id", "label", "entity_type", "frequency", "sources", "confidence_max", "metadata" }
    -- Each edge: { "source_id", "target_id", "weight", "relation_type", "sources", "metadata" }
    data JSONB NOT NULL,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index on week_label for fast lookups
CREATE INDEX IF NOT EXISTS idx_kg_snapshots_week_label ON kg_snapshots(week_label);

-- Index on snapshot_date for temporal queries
CREATE INDEX IF NOT EXISTS idx_kg_snapshots_date ON kg_snapshots(snapshot_date);

-- GIN index on JSONB data for efficient querying within the graph
CREATE INDEX IF NOT EXISTS idx_kg_snapshots_data ON kg_snapshots USING GIN(data);

-- =============================================================================
-- signals: Detected emerging signals from snapshot comparisons
-- =============================================================================

CREATE TABLE IF NOT EXISTS signals (
    id SERIAL PRIMARY KEY,
    
    -- Week when this signal was detected
    week_label TEXT NOT NULL,
    
    -- Signal type: 'emerging', 'accelerating', 'declining', 'contradictory'
    signal_type TEXT NOT NULL,
    
    -- Entities involved in the signal
    entity_a TEXT,
    entity_b TEXT,
    
    -- Scoring metrics
    emergence_score FLOAT,           -- Overall emergence score (0-100)
    velocity FLOAT,                  -- Rate of change
    source_diversity INTEGER,        -- Number of independent sources
    
    -- Consensus metrics (Phase 5 - to be populated later)
    consensus_positive FLOAT,        -- % of articles with PRESENT assertion
    consensus_negative FLOAT,        -- % of articles with NEGATED assertion
    consensus_hypothetical FLOAT,   -- % of articles with HYPOTHETICAL assertion
    consensus_label TEXT,            -- 'confirmed', 'contradictory', 'preliminary'
    
    -- Source PMIDs and additional details
    pmids JSONB,                     -- List of PubMed IDs supporting this signal
    details JSONB,                   -- Additional metadata (delta info, etc.)
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index on week_label for filtering by time period
CREATE INDEX IF NOT EXISTS idx_signals_week_label ON signals(week_label);

-- Index on signal_type for filtering by type
CREATE INDEX IF NOT EXISTS idx_signals_type ON signals(signal_type);

-- Index on emergence_score for sorting by importance
CREATE INDEX IF NOT EXISTS idx_signals_score ON signals(emergence_score DESC);

-- Composite index for common queries (week + type + score)
CREATE INDEX IF NOT EXISTS idx_signals_week_type_score 
    ON signals(week_label, signal_type, emergence_score DESC);

-- =============================================================================
-- entity_assertions: Track assertion status per entity per article (Phase 5)
-- =============================================================================
-- This table will be populated when OpenMed Assertion Status is integrated

CREATE TABLE IF NOT EXISTS entity_assertions (
    id SERIAL PRIMARY KEY,
    
    -- Link to entities table (to be created)
    entity_id INTEGER,  -- Will reference entities(id) once that table exists
    
    -- Link to article
    pmid TEXT NOT NULL,
    
    -- Assertion status from OpenMed
    -- Values: 'PRESENT', 'NEGATED', 'HYPOTHETICAL', 'HISTORICAL'
    assertion_status TEXT NOT NULL,
    
    -- Confidence score from NER model
    confidence FLOAT,
    
    -- Context: the sentence where this entity was found
    context_sentence TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index on pmid for article-based queries
CREATE INDEX IF NOT EXISTS idx_entity_assertions_pmid ON entity_assertions(pmid);

-- Index on assertion_status for filtering by status
CREATE INDEX IF NOT EXISTS idx_entity_assertions_status ON entity_assertions(assertion_status);

-- =============================================================================
-- Comments
-- =============================================================================

COMMENT ON TABLE kg_snapshots IS 
    'Weekly snapshots of the Knowledge Graph for temporal analysis and signal detection';

COMMENT ON COLUMN kg_snapshots.week_label IS 
    'ISO week label (e.g., 2026-W12) - unique identifier for each snapshot';

COMMENT ON COLUMN kg_snapshots.data IS 
    'Complete graph data as JSONB: nodes (entities) and edges (relations)';

COMMENT ON TABLE signals IS 
    'Emerging signals detected by comparing KG snapshots over time';

COMMENT ON COLUMN signals.emergence_score IS 
    'Composite score (0-100) quantifying how novel/important this signal is';

COMMENT ON COLUMN signals.consensus_label IS 
    'Scientific consensus classification: confirmed (>80% positive), contradictory (40-60%), preliminary (>50% hypothetical)';

COMMENT ON TABLE entity_assertions IS 
    'Assertion status per entity per article - enables consensus scoring (Phase 5)';
