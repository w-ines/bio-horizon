-- Migration 003: Watch Topics and Automated Surveillance
-- Creates tables for user-configured surveillance topics that trigger automatic weekly snapshots

-- Drop existing table if it exists (clean slate)
DROP TABLE IF EXISTS watch_topic_executions CASCADE;
DROP TABLE IF EXISTS watch_topics CASCADE;

-- Watch topics configured by users
CREATE TABLE watch_topics (
    id SERIAL PRIMARY KEY,
    user_id TEXT,                      -- User identifier (optional for MVP)
    query TEXT NOT NULL,               -- PubMed search query
    filters JSONB DEFAULT '{}',        -- Advanced PubMed filters (publication types, dates, etc.)
    custom_labels JSONB DEFAULT '[]', -- Custom entity labels for Zero-shot NER (Phase 5)
                                       -- Example: ["BRAIN_REGION", "BIOMARKER", "COGNITIVE_FUNCTION"]
    frequency TEXT DEFAULT 'weekly',   -- 'weekly' or 'monthly'
    is_active BOOLEAN DEFAULT TRUE,    -- Enable/disable without deleting
    last_run_at TIMESTAMPTZ,          -- Last execution timestamp
    next_run_at TIMESTAMPTZ,          -- Next scheduled execution
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for active topics lookup
CREATE INDEX idx_watch_topics_active ON watch_topics(is_active, next_run_at);

-- Index for user topics
CREATE INDEX idx_watch_topics_user ON watch_topics(user_id);

-- Execution history for watch topics
CREATE TABLE watch_topic_executions (
    id SERIAL PRIMARY KEY,
    topic_id INTEGER REFERENCES watch_topics(id) ON DELETE CASCADE,
    executed_at TIMESTAMPTZ DEFAULT NOW(),
    status TEXT NOT NULL,              -- 'success', 'failed', 'partial'
    articles_found INTEGER,
    entities_extracted INTEGER,
    snapshot_id INTEGER,               -- References kg_snapshots(id)
    signals_detected INTEGER,
    error_message TEXT,
    execution_time_seconds FLOAT,
    details JSONB DEFAULT '{}'
);

-- Index for execution history lookup
CREATE INDEX idx_watch_topic_executions_topic ON watch_topic_executions(topic_id, executed_at DESC);

-- Comments for documentation
COMMENT ON TABLE watch_topics IS 'User-configured surveillance topics for automated weekly KG snapshots';
COMMENT ON COLUMN watch_topics.query IS 'PubMed search query to execute';
COMMENT ON COLUMN watch_topics.custom_labels IS 'Custom entity types for Zero-shot NER extraction';
COMMENT ON COLUMN watch_topics.frequency IS 'Execution frequency: weekly or monthly';
COMMENT ON COLUMN watch_topics.is_active IS 'Whether this topic is currently active';
COMMENT ON COLUMN watch_topics.last_run_at IS 'Timestamp of last successful execution';
COMMENT ON COLUMN watch_topics.next_run_at IS 'Timestamp of next scheduled execution';

COMMENT ON TABLE watch_topic_executions IS 'Execution history and logs for watch topics';
COMMENT ON COLUMN watch_topic_executions.status IS 'Execution status: success, failed, or partial';
COMMENT ON COLUMN watch_topic_executions.snapshot_id IS 'ID of the snapshot created during this execution';
