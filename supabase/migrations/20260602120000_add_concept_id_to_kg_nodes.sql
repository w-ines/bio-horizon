-- Entity resolution: link each KG node to a canonical concept id.
-- PubTator3 returns MeSH / NCBI Gene / NCBI Taxonomy ids, which become the
-- node identity so that every surface form of the same concept maps to a
-- single node (KG criterion: "chaque entité = un objet unique relié à un ID
-- canonique : UMLS, MeSH, CUI").

-- 1. Canonical concept id (e.g. "MESH:D009369", "NCBIGene:673"). NULL = unresolved.
ALTER TABLE "public"."kg_nodes"
  ADD COLUMN IF NOT EXISTS "concept_id" text;

-- 2. Source vocabulary of the canonical id (e.g. "MeSH", "NCBIGene", "NCBITaxon").
ALTER TABLE "public"."kg_nodes"
  ADD COLUMN IF NOT EXISTS "concept_source" text;

-- 3. Index for fast lookup / joins by canonical id (resolved nodes only).
CREATE INDEX IF NOT EXISTS idx_kg_nodes_concept_id
  ON "public"."kg_nodes" ("concept_id")
  WHERE "concept_id" IS NOT NULL;

-- 4. Index for filtering by vocabulary.
CREATE INDEX IF NOT EXISTS idx_kg_nodes_concept_source
  ON "public"."kg_nodes" ("concept_source")
  WHERE "concept_source" IS NOT NULL;
