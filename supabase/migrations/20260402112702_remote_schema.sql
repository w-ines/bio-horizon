create extension if not exists "vector" with schema "public";

create sequence "public"."entities_id_seq";

create sequence "public"."entity_assertions_id_seq";

create sequence "public"."healthcheck_id_seq";

create sequence "public"."kg_snapshots_id_seq";

create sequence "public"."relations_id_seq";

create sequence "public"."signals_id_seq";

create sequence "public"."watch_topic_executions_id_seq";

create sequence "public"."watch_topics_id_seq";


  create table "public"."articles" (
    "pmid" text not null,
    "title" text not null,
    "abstract" text,
    "journal" text,
    "pub_date" date,
    "authors" jsonb,
    "mesh_terms" jsonb,
    "indexed_at" timestamp with time zone default now()
      );



  create table "public"."conversation_messages" (
    "message_id" uuid not null,
    "conversation_id" text not null,
    "role" text not null,
    "content" text not null default ''::text,
    "created_at" timestamp with time zone not null
      );



  create table "public"."digests" (
    "id" uuid not null default extensions.uuid_generate_v4(),
    "user_id" uuid not null,
    "digest_type" character varying(20) default 'daily'::character varying,
    "period_start" date not null,
    "period_end" date not null,
    "title" character varying(255),
    "summary" text,
    "html_content" text,
    "article_count" integer default 0,
    "pmids" text[],
    "trends" jsonb,
    "sent_at" timestamp with time zone,
    "delivery_status" character varying(20) default 'pending'::character varying,
    "delivery_error" text,
    "opened_at" timestamp with time zone,
    "clicked_at" timestamp with time zone,
    "created_at" timestamp with time zone default CURRENT_TIMESTAMP,
    "updated_at" timestamp with time zone default CURRENT_TIMESTAMP
      );



  create table "public"."documents" (
    "content" text,
    "metadata" jsonb,
    "embedding" public.vector(1536),
    "id" uuid not null default gen_random_uuid()
      );



  create table "public"."entities" (
    "id" integer not null default nextval('public.entities_id_seq'::regclass),
    "text" text not null,
    "normalized_text" text,
    "entity_type" text not null,
    "is_custom" boolean default false,
    "frequency" integer default 1,
    "first_seen" date,
    "last_seen" date
      );



  create table "public"."entity_assertions" (
    "id" integer not null default nextval('public.entity_assertions_id_seq'::regclass),
    "entity_id" integer,
    "pmid" text,
    "assertion_status" text not null,
    "confidence" double precision,
    "context_sentence" text,
    "created_at" timestamp with time zone default now()
      );



  create table "public"."file_items" (
    "id" uuid not null default gen_random_uuid(),
    "file_id" text not null,
    "content" text not null,
    "tokens" integer,
    "metadata" jsonb,
    "created_at" timestamp with time zone default now()
      );



  create table "public"."healthcheck" (
    "id" integer not null default nextval('public.healthcheck_id_seq'::regclass),
    "pinged_at" timestamp with time zone default now()
      );



  create table "public"."kg_edges" (
    "source_id" text not null,
    "target_id" text not null,
    "weight" integer not null default 1,
    "relation_type" text not null default 'co_occurrence'::text,
    "sources" text[] not null default '{}'::text[],
    "metadata" jsonb not null default '{}'::jsonb,
    "updated_at" timestamp with time zone not null default now()
      );



  create table "public"."kg_nodes" (
    "id" text not null,
    "label" text not null,
    "entity_type" text not null,
    "frequency" integer not null default 1,
    "sources" text[] not null default '{}'::text[],
    "confidence_max" double precision,
    "metadata" jsonb not null default '{}'::jsonb,
    "updated_at" timestamp with time zone not null default now()
      );



  create table "public"."kg_snapshots" (
    "id" integer not null default nextval('public.kg_snapshots_id_seq'::regclass),
    "week_label" text not null,
    "snapshot_date" date not null,
    "node_count" integer,
    "edge_count" integer,
    "data" jsonb,
    "created_at" timestamp with time zone default now()
      );



  create table "public"."pubmed_articles" (
    "pmid" text not null,
    "title" text not null default ''::text,
    "abstract" text not null default ''::text,
    "journal" text not null default ''::text,
    "pub_date" text not null default ''::text,
    "authors" jsonb not null default '[]'::jsonb,
    "mesh_terms" jsonb not null default '[]'::jsonb,
    "job_id" text,
    "ner_processed" boolean not null default false,
    "created_at" timestamp with time zone not null default now(),
    "updated_at" timestamp with time zone not null default now(),
    "pmc_id" text not null default ''::text,
    "doi" text not null default ''::text,
    "pubmed_url" text not null default ''::text,
    "pdf_url" text not null default ''::text
      );



  create table "public"."relations" (
    "id" integer not null default nextval('public.relations_id_seq'::regclass),
    "source_entity_id" integer,
    "target_entity_id" integer,
    "weight" integer default 1,
    "confidence_avg" double precision,
    "pmids" jsonb,
    "consensus_positive" double precision,
    "consensus_negative" double precision,
    "consensus_hypothetical" double precision,
    "first_seen" date,
    "last_seen" date
      );



  create table "public"."signals" (
    "id" integer not null default nextval('public.signals_id_seq'::regclass),
    "week_label" text not null,
    "signal_type" text not null,
    "entity_a" text,
    "entity_b" text,
    "emergence_score" double precision,
    "velocity" double precision,
    "source_diversity" integer,
    "consensus_positive" double precision,
    "consensus_negative" double precision,
    "consensus_hypothetical" double precision,
    "consensus_label" text,
    "pmids" jsonb,
    "details" jsonb,
    "created_at" timestamp with time zone default now()
      );



  create table "public"."topic_searches" (
    "id" uuid not null default extensions.uuid_generate_v4(),
    "topic_id" uuid not null,
    "user_id" uuid not null,
    "query" text not null,
    "filters" jsonb,
    "total_results" integer default 0,
    "new_articles" integer default 0,
    "pmids" text[],
    "executed_at" timestamp with time zone default CURRENT_TIMESTAMP,
    "execution_time_ms" integer,
    "status" character varying(20) default 'success'::character varying,
    "error_message" text,
    "created_at" timestamp with time zone default CURRENT_TIMESTAMP
      );



  create table "public"."topics" (
    "id" uuid not null default extensions.uuid_generate_v4(),
    "user_id" uuid not null,
    "query" text not null,
    "label" character varying(255),
    "description" text,
    "filters" jsonb default '{}'::jsonb,
    "max_results" integer default 20,
    "sort_by" character varying(20) default 'relevance'::character varying,
    "is_active" boolean default true,
    "last_search_at" timestamp with time zone,
    "last_article_date" date,
    "total_articles_found" integer default 0,
    "created_at" timestamp with time zone default CURRENT_TIMESTAMP,
    "updated_at" timestamp with time zone default CURRENT_TIMESTAMP,
    "deleted_at" timestamp with time zone
      );



  create table "public"."user_articles" (
    "id" uuid not null default extensions.uuid_generate_v4(),
    "user_id" uuid not null,
    "topic_id" uuid,
    "pmid" character varying(20) not null,
    "title" text,
    "abstract" text,
    "journal" character varying(255),
    "pub_date" character varying(50),
    "authors" text[],
    "mesh_terms" text[],
    "is_read" boolean default false,
    "is_starred" boolean default false,
    "is_archived" boolean default false,
    "user_notes" text,
    "first_seen_at" timestamp with time zone default CURRENT_TIMESTAMP,
    "last_seen_at" timestamp with time zone default CURRENT_TIMESTAMP,
    "times_seen" integer default 1,
    "created_at" timestamp with time zone default CURRENT_TIMESTAMP,
    "updated_at" timestamp with time zone default CURRENT_TIMESTAMP
      );



  create table "public"."user_preferences" (
    "id" uuid not null default extensions.uuid_generate_v4(),
    "user_id" uuid not null,
    "key" character varying(100) not null,
    "value" jsonb,
    "created_at" timestamp with time zone default CURRENT_TIMESTAMP,
    "updated_at" timestamp with time zone default CURRENT_TIMESTAMP
      );



  create table "public"."users" (
    "id" uuid not null default extensions.uuid_generate_v4(),
    "email" character varying(255) not null,
    "full_name" character varying(255),
    "password_hash" character varying(255),
    "is_active" boolean default true,
    "is_verified" boolean default false,
    "frequency" character varying(20) default 'daily'::character varying,
    "delivery_time" time without time zone default '08:00:00'::time without time zone,
    "timezone" character varying(50) default 'UTC'::character varying,
    "language" character varying(10) default 'en'::character varying,
    "created_at" timestamp with time zone default CURRENT_TIMESTAMP,
    "updated_at" timestamp with time zone default CURRENT_TIMESTAMP,
    "last_login_at" timestamp with time zone,
    "deleted_at" timestamp with time zone
      );



  create table "public"."watch_topic_executions" (
    "id" integer not null default nextval('public.watch_topic_executions_id_seq'::regclass),
    "topic_id" integer,
    "executed_at" timestamp with time zone default now(),
    "status" text not null,
    "articles_found" integer,
    "entities_extracted" integer,
    "snapshot_id" integer,
    "signals_detected" integer,
    "error_message" text,
    "execution_time_seconds" double precision,
    "details" jsonb default '{}'::jsonb
      );



  create table "public"."watch_topics" (
    "id" integer not null default nextval('public.watch_topics_id_seq'::regclass),
    "user_id" text,
    "query" text not null,
    "filters" jsonb default '{}'::jsonb,
    "custom_labels" jsonb default '[]'::jsonb,
    "frequency" text default 'weekly'::text,
    "is_active" boolean default true,
    "last_run_at" timestamp with time zone,
    "next_run_at" timestamp with time zone,
    "created_at" timestamp with time zone default now(),
    "updated_at" timestamp with time zone default now()
      );


alter sequence "public"."entities_id_seq" owned by "public"."entities"."id";

alter sequence "public"."entity_assertions_id_seq" owned by "public"."entity_assertions"."id";

alter sequence "public"."healthcheck_id_seq" owned by "public"."healthcheck"."id";

alter sequence "public"."kg_snapshots_id_seq" owned by "public"."kg_snapshots"."id";

alter sequence "public"."relations_id_seq" owned by "public"."relations"."id";

alter sequence "public"."signals_id_seq" owned by "public"."signals"."id";

alter sequence "public"."watch_topic_executions_id_seq" owned by "public"."watch_topic_executions"."id";

alter sequence "public"."watch_topics_id_seq" owned by "public"."watch_topics"."id";

CREATE UNIQUE INDEX articles_pkey ON public.articles USING btree (pmid);

CREATE INDEX conversation_messages_conversation_id_created_at_idx ON public.conversation_messages USING btree (conversation_id, created_at);

CREATE UNIQUE INDEX conversation_messages_pkey ON public.conversation_messages USING btree (message_id);

CREATE UNIQUE INDEX digests_pkey ON public.digests USING btree (id);

CREATE INDEX documents_embedding_idx ON public.documents USING ivfflat (embedding public.vector_cosine_ops) WITH (lists='100');

CREATE INDEX documents_metadata_gin ON public.documents USING gin (metadata);

CREATE UNIQUE INDEX documents_pkey ON public.documents USING btree (id);

CREATE UNIQUE INDEX entities_normalized_text_entity_type_key ON public.entities USING btree (normalized_text, entity_type);

CREATE UNIQUE INDEX entities_pkey ON public.entities USING btree (id);

CREATE UNIQUE INDEX entity_assertions_pkey ON public.entity_assertions USING btree (id);

CREATE UNIQUE INDEX file_items_pkey ON public.file_items USING btree (id);

CREATE UNIQUE INDEX healthcheck_pkey ON public.healthcheck USING btree (id);

CREATE INDEX idx_digests_user_id ON public.digests USING btree (user_id);

CREATE INDEX idx_entity_assertions_pmid ON public.entity_assertions USING btree (pmid);

CREATE INDEX idx_entity_assertions_status ON public.entity_assertions USING btree (assertion_status);

CREATE INDEX idx_file_items_created_at ON public.file_items USING btree (created_at);

CREATE INDEX idx_file_items_file_id ON public.file_items USING btree (file_id);

CREATE INDEX idx_kg_edges_weight ON public.kg_edges USING btree (weight DESC);

CREATE INDEX idx_kg_nodes_freq ON public.kg_nodes USING btree (frequency DESC);

CREATE INDEX idx_kg_nodes_type ON public.kg_nodes USING btree (entity_type);

CREATE INDEX idx_kg_snapshots_data ON public.kg_snapshots USING gin (data);

CREATE INDEX idx_kg_snapshots_date ON public.kg_snapshots USING btree (snapshot_date);

CREATE INDEX idx_kg_snapshots_week_label ON public.kg_snapshots USING btree (week_label);

CREATE INDEX idx_pubmed_articles_has_pdf ON public.pubmed_articles USING btree (pdf_url) WHERE (pdf_url <> ''::text);

CREATE INDEX idx_pubmed_articles_job_id ON public.pubmed_articles USING btree (job_id);

CREATE INDEX idx_pubmed_articles_ner_pending ON public.pubmed_articles USING btree (ner_processed) WHERE (ner_processed = false);

CREATE INDEX idx_signals_score ON public.signals USING btree (emergence_score DESC);

CREATE INDEX idx_signals_type ON public.signals USING btree (signal_type);

CREATE INDEX idx_signals_week_label ON public.signals USING btree (week_label);

CREATE INDEX idx_signals_week_type_score ON public.signals USING btree (week_label, signal_type, emergence_score DESC);

CREATE INDEX idx_topic_searches_topic_id ON public.topic_searches USING btree (topic_id);

CREATE INDEX idx_topic_searches_user_id ON public.topic_searches USING btree (user_id);

CREATE INDEX idx_topics_active ON public.topics USING btree (is_active) WHERE (is_active = true);

CREATE INDEX idx_topics_user_id ON public.topics USING btree (user_id);

CREATE INDEX idx_user_articles_pmid ON public.user_articles USING btree (pmid);

CREATE INDEX idx_user_articles_user_id ON public.user_articles USING btree (user_id);

CREATE INDEX idx_user_preferences_user_id ON public.user_preferences USING btree (user_id);

CREATE INDEX idx_users_active ON public.users USING btree (is_active) WHERE (is_active = true);

CREATE INDEX idx_users_email ON public.users USING btree (email);

CREATE INDEX idx_watch_topic_executions_topic ON public.watch_topic_executions USING btree (topic_id, executed_at DESC);

CREATE INDEX idx_watch_topics_active ON public.watch_topics USING btree (is_active, next_run_at);

CREATE INDEX idx_watch_topics_user ON public.watch_topics USING btree (user_id);

CREATE UNIQUE INDEX kg_edges_pkey ON public.kg_edges USING btree (source_id, target_id);

CREATE UNIQUE INDEX kg_nodes_pkey ON public.kg_nodes USING btree (id);

CREATE UNIQUE INDEX kg_snapshots_pkey ON public.kg_snapshots USING btree (id);

CREATE UNIQUE INDEX pubmed_articles_pkey ON public.pubmed_articles USING btree (pmid);

CREATE UNIQUE INDEX relations_pkey ON public.relations USING btree (id);

CREATE UNIQUE INDEX relations_source_entity_id_target_entity_id_key ON public.relations USING btree (source_entity_id, target_entity_id);

CREATE UNIQUE INDEX signals_pkey ON public.signals USING btree (id);

CREATE UNIQUE INDEX topic_searches_pkey ON public.topic_searches USING btree (id);

CREATE UNIQUE INDEX topics_pkey ON public.topics USING btree (id);

CREATE UNIQUE INDEX user_articles_pkey ON public.user_articles USING btree (id);

CREATE UNIQUE INDEX user_articles_user_id_pmid_key ON public.user_articles USING btree (user_id, pmid);

CREATE UNIQUE INDEX user_preferences_pkey ON public.user_preferences USING btree (id);

CREATE UNIQUE INDEX user_preferences_user_id_key_key ON public.user_preferences USING btree (user_id, key);

CREATE UNIQUE INDEX users_email_key ON public.users USING btree (email);

CREATE UNIQUE INDEX users_pkey ON public.users USING btree (id);

CREATE UNIQUE INDEX watch_topic_executions_pkey ON public.watch_topic_executions USING btree (id);

CREATE UNIQUE INDEX watch_topics_pkey ON public.watch_topics USING btree (id);

alter table "public"."articles" add constraint "articles_pkey" PRIMARY KEY using index "articles_pkey";

alter table "public"."conversation_messages" add constraint "conversation_messages_pkey" PRIMARY KEY using index "conversation_messages_pkey";

alter table "public"."digests" add constraint "digests_pkey" PRIMARY KEY using index "digests_pkey";

alter table "public"."documents" add constraint "documents_pkey" PRIMARY KEY using index "documents_pkey";

alter table "public"."entities" add constraint "entities_pkey" PRIMARY KEY using index "entities_pkey";

alter table "public"."entity_assertions" add constraint "entity_assertions_pkey" PRIMARY KEY using index "entity_assertions_pkey";

alter table "public"."file_items" add constraint "file_items_pkey" PRIMARY KEY using index "file_items_pkey";

alter table "public"."healthcheck" add constraint "healthcheck_pkey" PRIMARY KEY using index "healthcheck_pkey";

alter table "public"."kg_edges" add constraint "kg_edges_pkey" PRIMARY KEY using index "kg_edges_pkey";

alter table "public"."kg_nodes" add constraint "kg_nodes_pkey" PRIMARY KEY using index "kg_nodes_pkey";

alter table "public"."kg_snapshots" add constraint "kg_snapshots_pkey" PRIMARY KEY using index "kg_snapshots_pkey";

alter table "public"."pubmed_articles" add constraint "pubmed_articles_pkey" PRIMARY KEY using index "pubmed_articles_pkey";

alter table "public"."relations" add constraint "relations_pkey" PRIMARY KEY using index "relations_pkey";

alter table "public"."signals" add constraint "signals_pkey" PRIMARY KEY using index "signals_pkey";

alter table "public"."topic_searches" add constraint "topic_searches_pkey" PRIMARY KEY using index "topic_searches_pkey";

alter table "public"."topics" add constraint "topics_pkey" PRIMARY KEY using index "topics_pkey";

alter table "public"."user_articles" add constraint "user_articles_pkey" PRIMARY KEY using index "user_articles_pkey";

alter table "public"."user_preferences" add constraint "user_preferences_pkey" PRIMARY KEY using index "user_preferences_pkey";

alter table "public"."users" add constraint "users_pkey" PRIMARY KEY using index "users_pkey";

alter table "public"."watch_topic_executions" add constraint "watch_topic_executions_pkey" PRIMARY KEY using index "watch_topic_executions_pkey";

alter table "public"."watch_topics" add constraint "watch_topics_pkey" PRIMARY KEY using index "watch_topics_pkey";

alter table "public"."conversation_messages" add constraint "conversation_messages_role_check" CHECK ((role = ANY (ARRAY['user'::text, 'assistant'::text]))) not valid;

alter table "public"."conversation_messages" validate constraint "conversation_messages_role_check";

alter table "public"."digests" add constraint "digests_delivery_status_check" CHECK (((delivery_status)::text = ANY ((ARRAY['pending'::character varying, 'sent'::character varying, 'failed'::character varying, 'skipped'::character varying])::text[]))) not valid;

alter table "public"."digests" validate constraint "digests_delivery_status_check";

alter table "public"."digests" add constraint "digests_digest_type_check" CHECK (((digest_type)::text = ANY ((ARRAY['daily'::character varying, 'weekly'::character varying, 'monthly'::character varying, 'custom'::character varying])::text[]))) not valid;

alter table "public"."digests" validate constraint "digests_digest_type_check";

alter table "public"."digests" add constraint "digests_user_id_fkey" FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE not valid;

alter table "public"."digests" validate constraint "digests_user_id_fkey";

alter table "public"."entities" add constraint "entities_normalized_text_entity_type_key" UNIQUE using index "entities_normalized_text_entity_type_key";

alter table "public"."entity_assertions" add constraint "entity_assertions_entity_id_fkey" FOREIGN KEY (entity_id) REFERENCES public.entities(id) not valid;

alter table "public"."entity_assertions" validate constraint "entity_assertions_entity_id_fkey";

alter table "public"."entity_assertions" add constraint "entity_assertions_pmid_fkey" FOREIGN KEY (pmid) REFERENCES public.articles(pmid) not valid;

alter table "public"."entity_assertions" validate constraint "entity_assertions_pmid_fkey";

alter table "public"."kg_edges" add constraint "kg_edges_source_id_fkey" FOREIGN KEY (source_id) REFERENCES public.kg_nodes(id) not valid;

alter table "public"."kg_edges" validate constraint "kg_edges_source_id_fkey";

alter table "public"."kg_edges" add constraint "kg_edges_target_id_fkey" FOREIGN KEY (target_id) REFERENCES public.kg_nodes(id) not valid;

alter table "public"."kg_edges" validate constraint "kg_edges_target_id_fkey";

alter table "public"."relations" add constraint "relations_source_entity_id_fkey" FOREIGN KEY (source_entity_id) REFERENCES public.entities(id) not valid;

alter table "public"."relations" validate constraint "relations_source_entity_id_fkey";

alter table "public"."relations" add constraint "relations_source_entity_id_target_entity_id_key" UNIQUE using index "relations_source_entity_id_target_entity_id_key";

alter table "public"."relations" add constraint "relations_target_entity_id_fkey" FOREIGN KEY (target_entity_id) REFERENCES public.entities(id) not valid;

alter table "public"."relations" validate constraint "relations_target_entity_id_fkey";

alter table "public"."topic_searches" add constraint "topic_searches_status_check" CHECK (((status)::text = ANY ((ARRAY['success'::character varying, 'error'::character varying, 'timeout'::character varying])::text[]))) not valid;

alter table "public"."topic_searches" validate constraint "topic_searches_status_check";

alter table "public"."topic_searches" add constraint "topic_searches_topic_id_fkey" FOREIGN KEY (topic_id) REFERENCES public.topics(id) ON DELETE CASCADE not valid;

alter table "public"."topic_searches" validate constraint "topic_searches_topic_id_fkey";

alter table "public"."topic_searches" add constraint "topic_searches_user_id_fkey" FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE not valid;

alter table "public"."topic_searches" validate constraint "topic_searches_user_id_fkey";

alter table "public"."topics" add constraint "topics_sort_by_check" CHECK (((sort_by)::text = ANY ((ARRAY['relevance'::character varying, 'pub_date'::character varying, 'Author'::character varying, 'JournalName'::character varying])::text[]))) not valid;

alter table "public"."topics" validate constraint "topics_sort_by_check";

alter table "public"."topics" add constraint "topics_user_id_fkey" FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE not valid;

alter table "public"."topics" validate constraint "topics_user_id_fkey";

alter table "public"."user_articles" add constraint "user_articles_topic_id_fkey" FOREIGN KEY (topic_id) REFERENCES public.topics(id) ON DELETE SET NULL not valid;

alter table "public"."user_articles" validate constraint "user_articles_topic_id_fkey";

alter table "public"."user_articles" add constraint "user_articles_user_id_fkey" FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE not valid;

alter table "public"."user_articles" validate constraint "user_articles_user_id_fkey";

alter table "public"."user_articles" add constraint "user_articles_user_id_pmid_key" UNIQUE using index "user_articles_user_id_pmid_key";

alter table "public"."user_preferences" add constraint "user_preferences_user_id_fkey" FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE not valid;

alter table "public"."user_preferences" validate constraint "user_preferences_user_id_fkey";

alter table "public"."user_preferences" add constraint "user_preferences_user_id_key_key" UNIQUE using index "user_preferences_user_id_key_key";

alter table "public"."users" add constraint "users_email_key" UNIQUE using index "users_email_key";

alter table "public"."users" add constraint "users_frequency_check" CHECK (((frequency)::text = ANY ((ARRAY['daily'::character varying, 'weekly'::character varying, 'biweekly'::character varying, 'monthly'::character varying])::text[]))) not valid;

alter table "public"."users" validate constraint "users_frequency_check";

alter table "public"."watch_topic_executions" add constraint "watch_topic_executions_topic_id_fkey" FOREIGN KEY (topic_id) REFERENCES public.watch_topics(id) ON DELETE CASCADE not valid;

alter table "public"."watch_topic_executions" validate constraint "watch_topic_executions_topic_id_fkey";

set check_function_bodies = off;

CREATE OR REPLACE FUNCTION public.match_documents(query_embedding public.vector, match_count integer DEFAULT 5, filter jsonb DEFAULT '{}'::jsonb)
 RETURNS TABLE(id uuid, content text, metadata jsonb, similarity double precision)
 LANGUAGE sql
 STABLE
AS $function$
  select
    d.id,
    d.content,
    d.metadata,
    (1 - (d.embedding <=> query_embedding))::float as similarity
  from public.documents d
  where
    (
      filter is null
      or filter = '{}'::jsonb
      or (filter ? 'doc_id' and d.metadata->>'doc_id' = filter->>'doc_id')
      or not (filter ? 'doc_id')
    )
  order by d.embedding <=> query_embedding
  limit match_count;
$function$
;

CREATE OR REPLACE FUNCTION public.update_updated_at_column()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$function$
;

grant delete on table "public"."articles" to "anon";

grant insert on table "public"."articles" to "anon";

grant references on table "public"."articles" to "anon";

grant select on table "public"."articles" to "anon";

grant trigger on table "public"."articles" to "anon";

grant truncate on table "public"."articles" to "anon";

grant update on table "public"."articles" to "anon";

grant delete on table "public"."articles" to "authenticated";

grant insert on table "public"."articles" to "authenticated";

grant references on table "public"."articles" to "authenticated";

grant select on table "public"."articles" to "authenticated";

grant trigger on table "public"."articles" to "authenticated";

grant truncate on table "public"."articles" to "authenticated";

grant update on table "public"."articles" to "authenticated";

grant delete on table "public"."articles" to "service_role";

grant insert on table "public"."articles" to "service_role";

grant references on table "public"."articles" to "service_role";

grant select on table "public"."articles" to "service_role";

grant trigger on table "public"."articles" to "service_role";

grant truncate on table "public"."articles" to "service_role";

grant update on table "public"."articles" to "service_role";

grant delete on table "public"."conversation_messages" to "anon";

grant insert on table "public"."conversation_messages" to "anon";

grant references on table "public"."conversation_messages" to "anon";

grant select on table "public"."conversation_messages" to "anon";

grant trigger on table "public"."conversation_messages" to "anon";

grant truncate on table "public"."conversation_messages" to "anon";

grant update on table "public"."conversation_messages" to "anon";

grant delete on table "public"."conversation_messages" to "authenticated";

grant insert on table "public"."conversation_messages" to "authenticated";

grant references on table "public"."conversation_messages" to "authenticated";

grant select on table "public"."conversation_messages" to "authenticated";

grant trigger on table "public"."conversation_messages" to "authenticated";

grant truncate on table "public"."conversation_messages" to "authenticated";

grant update on table "public"."conversation_messages" to "authenticated";

grant delete on table "public"."conversation_messages" to "service_role";

grant insert on table "public"."conversation_messages" to "service_role";

grant references on table "public"."conversation_messages" to "service_role";

grant select on table "public"."conversation_messages" to "service_role";

grant trigger on table "public"."conversation_messages" to "service_role";

grant truncate on table "public"."conversation_messages" to "service_role";

grant update on table "public"."conversation_messages" to "service_role";

grant delete on table "public"."digests" to "anon";

grant insert on table "public"."digests" to "anon";

grant references on table "public"."digests" to "anon";

grant select on table "public"."digests" to "anon";

grant trigger on table "public"."digests" to "anon";

grant truncate on table "public"."digests" to "anon";

grant update on table "public"."digests" to "anon";

grant delete on table "public"."digests" to "authenticated";

grant insert on table "public"."digests" to "authenticated";

grant references on table "public"."digests" to "authenticated";

grant select on table "public"."digests" to "authenticated";

grant trigger on table "public"."digests" to "authenticated";

grant truncate on table "public"."digests" to "authenticated";

grant update on table "public"."digests" to "authenticated";

grant delete on table "public"."digests" to "service_role";

grant insert on table "public"."digests" to "service_role";

grant references on table "public"."digests" to "service_role";

grant select on table "public"."digests" to "service_role";

grant trigger on table "public"."digests" to "service_role";

grant truncate on table "public"."digests" to "service_role";

grant update on table "public"."digests" to "service_role";

grant delete on table "public"."documents" to "anon";

grant insert on table "public"."documents" to "anon";

grant references on table "public"."documents" to "anon";

grant select on table "public"."documents" to "anon";

grant trigger on table "public"."documents" to "anon";

grant truncate on table "public"."documents" to "anon";

grant update on table "public"."documents" to "anon";

grant delete on table "public"."documents" to "authenticated";

grant insert on table "public"."documents" to "authenticated";

grant references on table "public"."documents" to "authenticated";

grant select on table "public"."documents" to "authenticated";

grant trigger on table "public"."documents" to "authenticated";

grant truncate on table "public"."documents" to "authenticated";

grant update on table "public"."documents" to "authenticated";

grant delete on table "public"."documents" to "service_role";

grant insert on table "public"."documents" to "service_role";

grant references on table "public"."documents" to "service_role";

grant select on table "public"."documents" to "service_role";

grant trigger on table "public"."documents" to "service_role";

grant truncate on table "public"."documents" to "service_role";

grant update on table "public"."documents" to "service_role";

grant delete on table "public"."entities" to "anon";

grant insert on table "public"."entities" to "anon";

grant references on table "public"."entities" to "anon";

grant select on table "public"."entities" to "anon";

grant trigger on table "public"."entities" to "anon";

grant truncate on table "public"."entities" to "anon";

grant update on table "public"."entities" to "anon";

grant delete on table "public"."entities" to "authenticated";

grant insert on table "public"."entities" to "authenticated";

grant references on table "public"."entities" to "authenticated";

grant select on table "public"."entities" to "authenticated";

grant trigger on table "public"."entities" to "authenticated";

grant truncate on table "public"."entities" to "authenticated";

grant update on table "public"."entities" to "authenticated";

grant delete on table "public"."entities" to "service_role";

grant insert on table "public"."entities" to "service_role";

grant references on table "public"."entities" to "service_role";

grant select on table "public"."entities" to "service_role";

grant trigger on table "public"."entities" to "service_role";

grant truncate on table "public"."entities" to "service_role";

grant update on table "public"."entities" to "service_role";

grant delete on table "public"."entity_assertions" to "anon";

grant insert on table "public"."entity_assertions" to "anon";

grant references on table "public"."entity_assertions" to "anon";

grant select on table "public"."entity_assertions" to "anon";

grant trigger on table "public"."entity_assertions" to "anon";

grant truncate on table "public"."entity_assertions" to "anon";

grant update on table "public"."entity_assertions" to "anon";

grant delete on table "public"."entity_assertions" to "authenticated";

grant insert on table "public"."entity_assertions" to "authenticated";

grant references on table "public"."entity_assertions" to "authenticated";

grant select on table "public"."entity_assertions" to "authenticated";

grant trigger on table "public"."entity_assertions" to "authenticated";

grant truncate on table "public"."entity_assertions" to "authenticated";

grant update on table "public"."entity_assertions" to "authenticated";

grant delete on table "public"."entity_assertions" to "service_role";

grant insert on table "public"."entity_assertions" to "service_role";

grant references on table "public"."entity_assertions" to "service_role";

grant select on table "public"."entity_assertions" to "service_role";

grant trigger on table "public"."entity_assertions" to "service_role";

grant truncate on table "public"."entity_assertions" to "service_role";

grant update on table "public"."entity_assertions" to "service_role";

grant delete on table "public"."file_items" to "anon";

grant insert on table "public"."file_items" to "anon";

grant references on table "public"."file_items" to "anon";

grant select on table "public"."file_items" to "anon";

grant trigger on table "public"."file_items" to "anon";

grant truncate on table "public"."file_items" to "anon";

grant update on table "public"."file_items" to "anon";

grant delete on table "public"."file_items" to "authenticated";

grant insert on table "public"."file_items" to "authenticated";

grant references on table "public"."file_items" to "authenticated";

grant select on table "public"."file_items" to "authenticated";

grant trigger on table "public"."file_items" to "authenticated";

grant truncate on table "public"."file_items" to "authenticated";

grant update on table "public"."file_items" to "authenticated";

grant delete on table "public"."file_items" to "service_role";

grant insert on table "public"."file_items" to "service_role";

grant references on table "public"."file_items" to "service_role";

grant select on table "public"."file_items" to "service_role";

grant trigger on table "public"."file_items" to "service_role";

grant truncate on table "public"."file_items" to "service_role";

grant update on table "public"."file_items" to "service_role";

grant delete on table "public"."healthcheck" to "anon";

grant insert on table "public"."healthcheck" to "anon";

grant references on table "public"."healthcheck" to "anon";

grant select on table "public"."healthcheck" to "anon";

grant trigger on table "public"."healthcheck" to "anon";

grant truncate on table "public"."healthcheck" to "anon";

grant update on table "public"."healthcheck" to "anon";

grant delete on table "public"."healthcheck" to "authenticated";

grant insert on table "public"."healthcheck" to "authenticated";

grant references on table "public"."healthcheck" to "authenticated";

grant select on table "public"."healthcheck" to "authenticated";

grant trigger on table "public"."healthcheck" to "authenticated";

grant truncate on table "public"."healthcheck" to "authenticated";

grant update on table "public"."healthcheck" to "authenticated";

grant delete on table "public"."healthcheck" to "service_role";

grant insert on table "public"."healthcheck" to "service_role";

grant references on table "public"."healthcheck" to "service_role";

grant select on table "public"."healthcheck" to "service_role";

grant trigger on table "public"."healthcheck" to "service_role";

grant truncate on table "public"."healthcheck" to "service_role";

grant update on table "public"."healthcheck" to "service_role";

grant delete on table "public"."kg_edges" to "anon";

grant insert on table "public"."kg_edges" to "anon";

grant references on table "public"."kg_edges" to "anon";

grant select on table "public"."kg_edges" to "anon";

grant trigger on table "public"."kg_edges" to "anon";

grant truncate on table "public"."kg_edges" to "anon";

grant update on table "public"."kg_edges" to "anon";

grant delete on table "public"."kg_edges" to "authenticated";

grant insert on table "public"."kg_edges" to "authenticated";

grant references on table "public"."kg_edges" to "authenticated";

grant select on table "public"."kg_edges" to "authenticated";

grant trigger on table "public"."kg_edges" to "authenticated";

grant truncate on table "public"."kg_edges" to "authenticated";

grant update on table "public"."kg_edges" to "authenticated";

grant delete on table "public"."kg_edges" to "service_role";

grant insert on table "public"."kg_edges" to "service_role";

grant references on table "public"."kg_edges" to "service_role";

grant select on table "public"."kg_edges" to "service_role";

grant trigger on table "public"."kg_edges" to "service_role";

grant truncate on table "public"."kg_edges" to "service_role";

grant update on table "public"."kg_edges" to "service_role";

grant delete on table "public"."kg_nodes" to "anon";

grant insert on table "public"."kg_nodes" to "anon";

grant references on table "public"."kg_nodes" to "anon";

grant select on table "public"."kg_nodes" to "anon";

grant trigger on table "public"."kg_nodes" to "anon";

grant truncate on table "public"."kg_nodes" to "anon";

grant update on table "public"."kg_nodes" to "anon";

grant delete on table "public"."kg_nodes" to "authenticated";

grant insert on table "public"."kg_nodes" to "authenticated";

grant references on table "public"."kg_nodes" to "authenticated";

grant select on table "public"."kg_nodes" to "authenticated";

grant trigger on table "public"."kg_nodes" to "authenticated";

grant truncate on table "public"."kg_nodes" to "authenticated";

grant update on table "public"."kg_nodes" to "authenticated";

grant delete on table "public"."kg_nodes" to "service_role";

grant insert on table "public"."kg_nodes" to "service_role";

grant references on table "public"."kg_nodes" to "service_role";

grant select on table "public"."kg_nodes" to "service_role";

grant trigger on table "public"."kg_nodes" to "service_role";

grant truncate on table "public"."kg_nodes" to "service_role";

grant update on table "public"."kg_nodes" to "service_role";

grant delete on table "public"."kg_snapshots" to "anon";

grant insert on table "public"."kg_snapshots" to "anon";

grant references on table "public"."kg_snapshots" to "anon";

grant select on table "public"."kg_snapshots" to "anon";

grant trigger on table "public"."kg_snapshots" to "anon";

grant truncate on table "public"."kg_snapshots" to "anon";

grant update on table "public"."kg_snapshots" to "anon";

grant delete on table "public"."kg_snapshots" to "authenticated";

grant insert on table "public"."kg_snapshots" to "authenticated";

grant references on table "public"."kg_snapshots" to "authenticated";

grant select on table "public"."kg_snapshots" to "authenticated";

grant trigger on table "public"."kg_snapshots" to "authenticated";

grant truncate on table "public"."kg_snapshots" to "authenticated";

grant update on table "public"."kg_snapshots" to "authenticated";

grant delete on table "public"."kg_snapshots" to "service_role";

grant insert on table "public"."kg_snapshots" to "service_role";

grant references on table "public"."kg_snapshots" to "service_role";

grant select on table "public"."kg_snapshots" to "service_role";

grant trigger on table "public"."kg_snapshots" to "service_role";

grant truncate on table "public"."kg_snapshots" to "service_role";

grant update on table "public"."kg_snapshots" to "service_role";

grant delete on table "public"."pubmed_articles" to "anon";

grant insert on table "public"."pubmed_articles" to "anon";

grant references on table "public"."pubmed_articles" to "anon";

grant select on table "public"."pubmed_articles" to "anon";

grant trigger on table "public"."pubmed_articles" to "anon";

grant truncate on table "public"."pubmed_articles" to "anon";

grant update on table "public"."pubmed_articles" to "anon";

grant delete on table "public"."pubmed_articles" to "authenticated";

grant insert on table "public"."pubmed_articles" to "authenticated";

grant references on table "public"."pubmed_articles" to "authenticated";

grant select on table "public"."pubmed_articles" to "authenticated";

grant trigger on table "public"."pubmed_articles" to "authenticated";

grant truncate on table "public"."pubmed_articles" to "authenticated";

grant update on table "public"."pubmed_articles" to "authenticated";

grant delete on table "public"."pubmed_articles" to "service_role";

grant insert on table "public"."pubmed_articles" to "service_role";

grant references on table "public"."pubmed_articles" to "service_role";

grant select on table "public"."pubmed_articles" to "service_role";

grant trigger on table "public"."pubmed_articles" to "service_role";

grant truncate on table "public"."pubmed_articles" to "service_role";

grant update on table "public"."pubmed_articles" to "service_role";

grant delete on table "public"."relations" to "anon";

grant insert on table "public"."relations" to "anon";

grant references on table "public"."relations" to "anon";

grant select on table "public"."relations" to "anon";

grant trigger on table "public"."relations" to "anon";

grant truncate on table "public"."relations" to "anon";

grant update on table "public"."relations" to "anon";

grant delete on table "public"."relations" to "authenticated";

grant insert on table "public"."relations" to "authenticated";

grant references on table "public"."relations" to "authenticated";

grant select on table "public"."relations" to "authenticated";

grant trigger on table "public"."relations" to "authenticated";

grant truncate on table "public"."relations" to "authenticated";

grant update on table "public"."relations" to "authenticated";

grant delete on table "public"."relations" to "service_role";

grant insert on table "public"."relations" to "service_role";

grant references on table "public"."relations" to "service_role";

grant select on table "public"."relations" to "service_role";

grant trigger on table "public"."relations" to "service_role";

grant truncate on table "public"."relations" to "service_role";

grant update on table "public"."relations" to "service_role";

grant delete on table "public"."signals" to "anon";

grant insert on table "public"."signals" to "anon";

grant references on table "public"."signals" to "anon";

grant select on table "public"."signals" to "anon";

grant trigger on table "public"."signals" to "anon";

grant truncate on table "public"."signals" to "anon";

grant update on table "public"."signals" to "anon";

grant delete on table "public"."signals" to "authenticated";

grant insert on table "public"."signals" to "authenticated";

grant references on table "public"."signals" to "authenticated";

grant select on table "public"."signals" to "authenticated";

grant trigger on table "public"."signals" to "authenticated";

grant truncate on table "public"."signals" to "authenticated";

grant update on table "public"."signals" to "authenticated";

grant delete on table "public"."signals" to "service_role";

grant insert on table "public"."signals" to "service_role";

grant references on table "public"."signals" to "service_role";

grant select on table "public"."signals" to "service_role";

grant trigger on table "public"."signals" to "service_role";

grant truncate on table "public"."signals" to "service_role";

grant update on table "public"."signals" to "service_role";

grant delete on table "public"."topic_searches" to "anon";

grant insert on table "public"."topic_searches" to "anon";

grant references on table "public"."topic_searches" to "anon";

grant select on table "public"."topic_searches" to "anon";

grant trigger on table "public"."topic_searches" to "anon";

grant truncate on table "public"."topic_searches" to "anon";

grant update on table "public"."topic_searches" to "anon";

grant delete on table "public"."topic_searches" to "authenticated";

grant insert on table "public"."topic_searches" to "authenticated";

grant references on table "public"."topic_searches" to "authenticated";

grant select on table "public"."topic_searches" to "authenticated";

grant trigger on table "public"."topic_searches" to "authenticated";

grant truncate on table "public"."topic_searches" to "authenticated";

grant update on table "public"."topic_searches" to "authenticated";

grant delete on table "public"."topic_searches" to "service_role";

grant insert on table "public"."topic_searches" to "service_role";

grant references on table "public"."topic_searches" to "service_role";

grant select on table "public"."topic_searches" to "service_role";

grant trigger on table "public"."topic_searches" to "service_role";

grant truncate on table "public"."topic_searches" to "service_role";

grant update on table "public"."topic_searches" to "service_role";

grant delete on table "public"."topics" to "anon";

grant insert on table "public"."topics" to "anon";

grant references on table "public"."topics" to "anon";

grant select on table "public"."topics" to "anon";

grant trigger on table "public"."topics" to "anon";

grant truncate on table "public"."topics" to "anon";

grant update on table "public"."topics" to "anon";

grant delete on table "public"."topics" to "authenticated";

grant insert on table "public"."topics" to "authenticated";

grant references on table "public"."topics" to "authenticated";

grant select on table "public"."topics" to "authenticated";

grant trigger on table "public"."topics" to "authenticated";

grant truncate on table "public"."topics" to "authenticated";

grant update on table "public"."topics" to "authenticated";

grant delete on table "public"."topics" to "service_role";

grant insert on table "public"."topics" to "service_role";

grant references on table "public"."topics" to "service_role";

grant select on table "public"."topics" to "service_role";

grant trigger on table "public"."topics" to "service_role";

grant truncate on table "public"."topics" to "service_role";

grant update on table "public"."topics" to "service_role";

grant delete on table "public"."user_articles" to "anon";

grant insert on table "public"."user_articles" to "anon";

grant references on table "public"."user_articles" to "anon";

grant select on table "public"."user_articles" to "anon";

grant trigger on table "public"."user_articles" to "anon";

grant truncate on table "public"."user_articles" to "anon";

grant update on table "public"."user_articles" to "anon";

grant delete on table "public"."user_articles" to "authenticated";

grant insert on table "public"."user_articles" to "authenticated";

grant references on table "public"."user_articles" to "authenticated";

grant select on table "public"."user_articles" to "authenticated";

grant trigger on table "public"."user_articles" to "authenticated";

grant truncate on table "public"."user_articles" to "authenticated";

grant update on table "public"."user_articles" to "authenticated";

grant delete on table "public"."user_articles" to "service_role";

grant insert on table "public"."user_articles" to "service_role";

grant references on table "public"."user_articles" to "service_role";

grant select on table "public"."user_articles" to "service_role";

grant trigger on table "public"."user_articles" to "service_role";

grant truncate on table "public"."user_articles" to "service_role";

grant update on table "public"."user_articles" to "service_role";

grant delete on table "public"."user_preferences" to "anon";

grant insert on table "public"."user_preferences" to "anon";

grant references on table "public"."user_preferences" to "anon";

grant select on table "public"."user_preferences" to "anon";

grant trigger on table "public"."user_preferences" to "anon";

grant truncate on table "public"."user_preferences" to "anon";

grant update on table "public"."user_preferences" to "anon";

grant delete on table "public"."user_preferences" to "authenticated";

grant insert on table "public"."user_preferences" to "authenticated";

grant references on table "public"."user_preferences" to "authenticated";

grant select on table "public"."user_preferences" to "authenticated";

grant trigger on table "public"."user_preferences" to "authenticated";

grant truncate on table "public"."user_preferences" to "authenticated";

grant update on table "public"."user_preferences" to "authenticated";

grant delete on table "public"."user_preferences" to "service_role";

grant insert on table "public"."user_preferences" to "service_role";

grant references on table "public"."user_preferences" to "service_role";

grant select on table "public"."user_preferences" to "service_role";

grant trigger on table "public"."user_preferences" to "service_role";

grant truncate on table "public"."user_preferences" to "service_role";

grant update on table "public"."user_preferences" to "service_role";

grant delete on table "public"."users" to "anon";

grant insert on table "public"."users" to "anon";

grant references on table "public"."users" to "anon";

grant select on table "public"."users" to "anon";

grant trigger on table "public"."users" to "anon";

grant truncate on table "public"."users" to "anon";

grant update on table "public"."users" to "anon";

grant delete on table "public"."users" to "authenticated";

grant insert on table "public"."users" to "authenticated";

grant references on table "public"."users" to "authenticated";

grant select on table "public"."users" to "authenticated";

grant trigger on table "public"."users" to "authenticated";

grant truncate on table "public"."users" to "authenticated";

grant update on table "public"."users" to "authenticated";

grant delete on table "public"."users" to "service_role";

grant insert on table "public"."users" to "service_role";

grant references on table "public"."users" to "service_role";

grant select on table "public"."users" to "service_role";

grant trigger on table "public"."users" to "service_role";

grant truncate on table "public"."users" to "service_role";

grant update on table "public"."users" to "service_role";

grant delete on table "public"."watch_topic_executions" to "anon";

grant insert on table "public"."watch_topic_executions" to "anon";

grant references on table "public"."watch_topic_executions" to "anon";

grant select on table "public"."watch_topic_executions" to "anon";

grant trigger on table "public"."watch_topic_executions" to "anon";

grant truncate on table "public"."watch_topic_executions" to "anon";

grant update on table "public"."watch_topic_executions" to "anon";

grant delete on table "public"."watch_topic_executions" to "authenticated";

grant insert on table "public"."watch_topic_executions" to "authenticated";

grant references on table "public"."watch_topic_executions" to "authenticated";

grant select on table "public"."watch_topic_executions" to "authenticated";

grant trigger on table "public"."watch_topic_executions" to "authenticated";

grant truncate on table "public"."watch_topic_executions" to "authenticated";

grant update on table "public"."watch_topic_executions" to "authenticated";

grant delete on table "public"."watch_topic_executions" to "service_role";

grant insert on table "public"."watch_topic_executions" to "service_role";

grant references on table "public"."watch_topic_executions" to "service_role";

grant select on table "public"."watch_topic_executions" to "service_role";

grant trigger on table "public"."watch_topic_executions" to "service_role";

grant truncate on table "public"."watch_topic_executions" to "service_role";

grant update on table "public"."watch_topic_executions" to "service_role";

grant delete on table "public"."watch_topics" to "anon";

grant insert on table "public"."watch_topics" to "anon";

grant references on table "public"."watch_topics" to "anon";

grant select on table "public"."watch_topics" to "anon";

grant trigger on table "public"."watch_topics" to "anon";

grant truncate on table "public"."watch_topics" to "anon";

grant update on table "public"."watch_topics" to "anon";

grant delete on table "public"."watch_topics" to "authenticated";

grant insert on table "public"."watch_topics" to "authenticated";

grant references on table "public"."watch_topics" to "authenticated";

grant select on table "public"."watch_topics" to "authenticated";

grant trigger on table "public"."watch_topics" to "authenticated";

grant truncate on table "public"."watch_topics" to "authenticated";

grant update on table "public"."watch_topics" to "authenticated";

grant delete on table "public"."watch_topics" to "service_role";

grant insert on table "public"."watch_topics" to "service_role";

grant references on table "public"."watch_topics" to "service_role";

grant select on table "public"."watch_topics" to "service_role";

grant trigger on table "public"."watch_topics" to "service_role";

grant truncate on table "public"."watch_topics" to "service_role";

grant update on table "public"."watch_topics" to "service_role";

CREATE TRIGGER update_digests_updated_at BEFORE UPDATE ON public.digests FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_topics_updated_at BEFORE UPDATE ON public.topics FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_user_articles_updated_at BEFORE UPDATE ON public.user_articles FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_user_preferences_updated_at BEFORE UPDATE ON public.user_preferences FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


