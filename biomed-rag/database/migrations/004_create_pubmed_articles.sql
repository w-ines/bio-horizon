-- Migration: Create pubmed_articles table for metadata-only ingestion
-- This table stores raw PubMed article metadata for fast ingestion.
-- NER/KG processing can be deferred to a separate job.

CREATE TABLE IF NOT EXISTS pubmed_articles (
    pmid TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT '',
    abstract TEXT NOT NULL DEFAULT '',
    journal TEXT NOT NULL DEFAULT '',
    pub_date TEXT NOT NULL DEFAULT '',
    authors JSONB NOT NULL DEFAULT '[]'::jsonb,
    mesh_terms JSONB NOT NULL DEFAULT '[]'::jsonb,
    job_id TEXT,
    ner_processed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for job lookups
CREATE INDEX IF NOT EXISTS idx_pubmed_articles_job_id ON pubmed_articles(job_id);

-- Index for finding unprocessed articles (for deferred NER)
CREATE INDEX IF NOT EXISTS idx_pubmed_articles_ner_pending ON pubmed_articles(ner_processed) WHERE ner_processed = FALSE;

-- Index for full-text search on title and abstract
CREATE INDEX IF NOT EXISTS idx_pubmed_articles_title_trgm ON pubmed_articles USING gin(title gin_trgm_ops);

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_pubmed_articles_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_pubmed_articles_updated_at ON pubmed_articles;
CREATE TRIGGER trg_pubmed_articles_updated_at
    BEFORE UPDATE ON pubmed_articles
    FOR EACH ROW
    EXECUTE FUNCTION update_pubmed_articles_updated_at();
