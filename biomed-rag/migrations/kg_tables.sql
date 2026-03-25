-- ============================================================
-- KG tables for bio-horizon knowledge graph persistence
-- Run this once in your Supabase project (SQL editor)
-- ============================================================

-- Nodes (one row = one unique medical entity)
CREATE TABLE IF NOT EXISTS kg_nodes (
    id              TEXT PRIMARY KEY,          -- "DRUG::aspirin"
    label           TEXT NOT NULL,             -- normalised surface form
    entity_type     TEXT NOT NULL,             -- DISEASE | DRUG | GENE | ANATOMY | …
    frequency       INT  NOT NULL DEFAULT 1,   -- how many times seen
    sources         TEXT[] NOT NULL DEFAULT '{}',  -- PMIDs
    confidence_max  FLOAT,
    metadata        JSONB NOT NULL DEFAULT '{}',
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_kg_nodes_type ON kg_nodes(entity_type);
CREATE INDEX IF NOT EXISTS idx_kg_nodes_freq ON kg_nodes(frequency DESC);

-- Trigger: keep updated_at current
CREATE OR REPLACE FUNCTION _set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END; $$;

DROP TRIGGER IF EXISTS trg_kg_nodes_updated_at ON kg_nodes;
CREATE TRIGGER trg_kg_nodes_updated_at
    BEFORE UPDATE ON kg_nodes
    FOR EACH ROW EXECUTE FUNCTION _set_updated_at();


-- Edges (co-occurrence between two nodes)
CREATE TABLE IF NOT EXISTS kg_edges (
    source_id       TEXT NOT NULL REFERENCES kg_nodes(id),
    target_id       TEXT NOT NULL REFERENCES kg_nodes(id),
    weight          INT  NOT NULL DEFAULT 1,
    relation_type   TEXT NOT NULL DEFAULT 'co_occurrence',
    sources         TEXT[] NOT NULL DEFAULT '{}',
    metadata        JSONB NOT NULL DEFAULT '{}',
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (source_id, target_id)
);

CREATE INDEX IF NOT EXISTS idx_kg_edges_weight   ON kg_edges(weight DESC);
CREATE INDEX IF NOT EXISTS idx_kg_edges_source   ON kg_edges(source_id);
CREATE INDEX IF NOT EXISTS idx_kg_edges_target   ON kg_edges(target_id);

DROP TRIGGER IF EXISTS trg_kg_edges_updated_at ON kg_edges;
CREATE TRIGGER trg_kg_edges_updated_at
    BEFORE UPDATE ON kg_edges
    FOR EACH ROW EXECUTE FUNCTION _set_updated_at();
