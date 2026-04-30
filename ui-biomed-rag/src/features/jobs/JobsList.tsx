/**
 * Jobs list component with filtering and actions
 */

"use client";

import { useEffect, useState } from "react";
import { Job, JobStatus } from "./types";
import { jobsApi } from "./api";

interface JobsListProps {
  onJobClick?: (jobId: string) => void;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

export function JobsList({ onJobClick, autoRefresh = true, refreshInterval = 5000 }: JobsListProps) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<JobStatus | "all">("all");

  const fetchJobs = async () => {
    try {
      const data = await jobsApi.listJobs(filter === "all" ? undefined : filter);
      setJobs(data.jobs);
      setLoading(false);
      setError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to fetch jobs";
      setError(message);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();

    if (autoRefresh) {
      const interval = setInterval(fetchJobs, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [filter, autoRefresh, refreshInterval]);

  const handleCancel = async (jobId: string) => {
    try {
      await jobsApi.cancelJob(jobId);
      fetchJobs();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to cancel job");
    }
  };

  const handleResume = async (jobId: string) => {
    try {
      await jobsApi.resumeJob(jobId);
      fetchJobs();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to resume job");
    }
  };

  const statusColors = {
    pending: "bg-gray-100 text-gray-700",
    running: "bg-blue-100 text-blue-700",
    completed: "bg-green-100 text-green-700",
    failed: "bg-red-100 text-red-700",
    cancelled: "bg-yellow-100 text-yellow-700",
  };

  const statusIcons = {
    pending: "⏳",
    running: "🔄",
    completed: "✅",
    failed: "❌",
    cancelled: "🚫",
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filter Tabs */}
      <div className="flex gap-2 border-b pb-2">
        {["all", "pending", "running", "completed", "failed", "cancelled"].map((status) => (
          <button
            key={status}
            onClick={() => setFilter(status as JobStatus | "all")}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filter === status
                ? "bg-blue-500 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            {status.charAt(0).toUpperCase() + status.slice(1)}
          </button>
        ))}
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-600">❌ {error}</p>
        </div>
      )}

      {/* Jobs List */}
      {jobs.length === 0 ? (
        <div className="text-center p-8 text-gray-500">
          <p>No jobs found</p>
        </div>
      ) : (
        <div className="space-y-3">
          {jobs.map((job) => (
            <div
              key={job.job_id}
              className="p-4 border rounded-lg hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => onJobClick?.(job.job_id)}
            >
              <div className="flex items-start justify-between">
                {/* Job Info */}
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xl">{statusIcons[job.status]}</span>
                    <h3 className="font-semibold text-lg">{job.query}</h3>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[job.status]}`}>
                      {job.status}
                    </span>
                    {job.processing_mode && (
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        job.processing_mode === "metadata_only" ? "bg-green-100 text-green-700" :
                        job.processing_mode === "deferred_ner" ? "bg-yellow-100 text-yellow-700" :
                        "bg-blue-100 text-blue-700"
                      }`}>
                        {job.processing_mode === "metadata_only" ? "⚡ Fast" :
                         job.processing_mode === "deferred_ner" ? "📦 Deferred" :
                         "🧬 Full"}
                      </span>
                    )}
                  </div>

                  {/* Progress Bar for Running Jobs */}
                  {job.status === "running" && (
                    <div className="mb-2">
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full transition-all"
                          style={{ width: `${job.progress_percentage}%` }}
                        />
                      </div>
                      <p className="text-xs text-gray-500 mt-1">{job.progress_percentage.toFixed(1)}% complete</p>
                    </div>
                  )}

                  {/* Stats */}
                  <div className="flex gap-4 text-sm text-gray-600">
                    <span>📄 {job.processed_articles.toLocaleString()} / {job.total_articles.toLocaleString()} articles</span>
                    <span>🧬 {job.entities_extracted.toLocaleString()} entities</span>
                    <span>📦 Batch {job.current_batch}</span>
                  </div>

                  {/* Error */}
                  {job.error && (
                    <p className="text-sm text-red-600 mt-2">Error: {job.error}</p>
                  )}

                  {/* Timestamp */}
                  <p className="text-xs text-gray-400 mt-2">
                    Created {new Date(job.created_at).toLocaleString()}
                  </p>
                </div>

                {/* Actions */}
                <div className="flex gap-2 ml-4">
                  {job.status === "running" && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleCancel(job.job_id);
                      }}
                      className="px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200"
                    >
                      Cancel
                    </button>
                  )}
                  {job.status === "failed" && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleResume(job.job_id);
                      }}
                      className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                    >
                      Resume
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
