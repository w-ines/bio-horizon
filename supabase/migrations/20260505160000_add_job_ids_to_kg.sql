-- Add job_ids tracking to kg_nodes, kg_edges, and kg_snapshots
-- This enables per-job graph filtering and temporal comparison

-- 1. Add job_ids column to kg_nodes
ALTER TABLE "public"."kg_nodes"
  ADD COLUMN IF NOT EXISTS "job_ids" text[] NOT NULL DEFAULT '{}'::text[];

-- 2. Add job_ids column to kg_edges
ALTER TABLE "public"."kg_edges"
  ADD COLUMN IF NOT EXISTS "job_ids" text[] NOT NULL DEFAULT '{}'::text[];

-- 3. Add job_id and query columns to kg_snapshots for per-job snapshots
ALTER TABLE "public"."kg_snapshots"
  ADD COLUMN IF NOT EXISTS "job_id" text,
  ADD COLUMN IF NOT EXISTS "query" text;

-- 4. Make week_label nullable (per-job snapshots use job_id as key instead)
ALTER TABLE "public"."kg_snapshots"
  ALTER COLUMN "week_label" DROP NOT NULL;

-- 5. Add unique constraint on job_id for per-job snapshots
CREATE UNIQUE INDEX IF NOT EXISTS idx_kg_snapshots_job_id
  ON "public"."kg_snapshots" ("job_id")
  WHERE "job_id" IS NOT NULL;

-- 6. Index for fast job_ids filtering
CREATE INDEX IF NOT EXISTS idx_kg_nodes_job_ids ON "public"."kg_nodes" USING gin ("job_ids");
CREATE INDEX IF NOT EXISTS idx_kg_edges_job_ids ON "public"."kg_edges" USING gin ("job_ids");

-- 7. Index for querying snapshots by query text
CREATE INDEX IF NOT EXISTS idx_kg_snapshots_query ON "public"."kg_snapshots" ("query");
