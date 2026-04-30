/**
 * API client for PubMed corpus ingestion jobs
 */

import { Job, JobCreateRequest, JobListResponse } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const jobsApi = {
  /**
   * Create a new ingestion job
   */
  async createJob(request: JobCreateRequest): Promise<{ job_id: string; status: string; message: string }> {
    const response = await fetch(`${API_BASE}/jobs/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to create job");
    }

    return response.json();
  },

  /**
   * Get job status by ID
   */
  async getJob(jobId: string): Promise<Job> {
    const response = await fetch(`${API_BASE}/jobs/${jobId}`);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to fetch job");
    }

    return response.json();
  },

  /**
   * List all jobs
   */
  async listJobs(status?: string, limit: number = 50): Promise<JobListResponse> {
    const params = new URLSearchParams();
    if (status) params.append("status", status);
    params.append("limit", limit.toString());

    const response = await fetch(`${API_BASE}/jobs?${params}`);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to list jobs");
    }

    return response.json();
  },

  /**
   * Cancel a running job
   */
  async cancelJob(jobId: string): Promise<{ job_id: string; status: string; message: string }> {
    const response = await fetch(`${API_BASE}/jobs/${jobId}/cancel`, {
      method: "POST",
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to cancel job");
    }

    return response.json();
  },

  /**
   * Resume a failed job
   */
  async resumeJob(jobId: string): Promise<{ job_id: string; status: string; message: string }> {
    const response = await fetch(`${API_BASE}/jobs/${jobId}/resume`, {
      method: "POST",
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to resume job");
    }

    return response.json();
  },
};
