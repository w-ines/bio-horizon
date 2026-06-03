/**
 * Types for PubMed corpus ingestion jobs
 */

export type JobStatus = "pending" | "running" | "completed" | "failed" | "cancelled";

export interface JobCreateRequest {
  query: string;
  mindate?: string;
  maxdate?: string;
  publication_types?: string[];
  journals?: string[];
  language?: string;
  species?: string[];
  batch_size?: number;
  max_batches?: number;
  processing_mode?: "full" | "metadata_only" | "deferred_ner";
}

export interface Job {
  job_id: string;
  status: JobStatus;
  query: string;
  total_articles: number;
  processed_articles: number;
  entities_extracted: number;
  current_batch: number;
  progress_percentage: number;
  processing_mode?: string;
  error?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  updated_at: string;
}

export interface JobListResponse {
  jobs: Job[];
  total: number;
}
