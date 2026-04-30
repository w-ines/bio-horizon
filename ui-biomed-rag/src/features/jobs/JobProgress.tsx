/**
 * Job progress component with real-time updates
 */

"use client";

import { useEffect, useState } from "react";
import { Job } from "./types";
import { jobsApi } from "./api";

interface JobProgressProps {
  jobId: string;
  onComplete?: (job: Job) => void;
  onError?: (error: string) => void;
}

export function JobProgress({ jobId, onComplete, onError }: JobProgressProps) {
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let interval: NodeJS.Timeout;

    const fetchJob = async () => {
      try {
        const data = await jobsApi.getJob(jobId);
        setJob(data);
        setLoading(false);

        if (data.status === "completed") {
          onComplete?.(data);
          clearInterval(interval);
        } else if (data.status === "failed") {
          onError?.(data.error || "Job failed");
          clearInterval(interval);
        } else if (data.status === "cancelled") {
          clearInterval(interval);
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to fetch job";
        setError(message);
        setLoading(false);
        onError?.(message);
        clearInterval(interval);
      }
    };

    fetchJob();
    interval = setInterval(fetchJob, 2000);

    return () => clearInterval(interval);
  }, [jobId, onComplete, onError]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 p-4 border rounded-lg">
        <div className="animate-spin h-5 w-5 border-2 border-blue-500 border-t-transparent rounded-full" />
        <span className="text-sm text-gray-600">Loading job status...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 border border-red-200 rounded-lg bg-red-50">
        <p className="text-sm text-red-600">❌ {error}</p>
      </div>
    );
  }

  if (!job) return null;

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

  return (
    <div className="space-y-4 p-4 border rounded-lg">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{statusIcons[job.status]}</span>
          <div>
            <h3 className="font-semibold text-lg">{job.query}</h3>
            <p className="text-sm text-gray-500">Job ID: {job.job_id.slice(0, 8)}...</p>
          </div>
        </div>
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${statusColors[job.status]}`}>
          {job.status.toUpperCase()}
        </span>
      </div>

      {/* Progress Bar */}
      {job.status === "running" && (
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">Progress</span>
            <span className="font-medium">{job.progress_percentage.toFixed(1)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2.5">
            <div
              className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
              style={{ width: `${job.progress_percentage}%` }}
            />
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="text-center p-3 bg-gray-50 rounded-lg">
          <p className="text-2xl font-bold text-gray-900">{job.total_articles.toLocaleString()}</p>
          <p className="text-xs text-gray-500">Total Articles</p>
        </div>
        <div className="text-center p-3 bg-blue-50 rounded-lg">
          <p className="text-2xl font-bold text-blue-600">{job.processed_articles.toLocaleString()}</p>
          <p className="text-xs text-gray-500">Processed</p>
        </div>
        <div className="text-center p-3 bg-green-50 rounded-lg">
          <p className="text-2xl font-bold text-green-600">{job.entities_extracted.toLocaleString()}</p>
          <p className="text-xs text-gray-500">Entities</p>
        </div>
      </div>

      {/* Error Message */}
      {job.error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-600">
            <strong>Error:</strong> {job.error}
          </p>
        </div>
      )}

      {/* Timestamps */}
      <div className="text-xs text-gray-500 space-y-1">
        <p>Created: {new Date(job.created_at).toLocaleString()}</p>
        {job.started_at && <p>Started: {new Date(job.started_at).toLocaleString()}</p>}
        {job.completed_at && <p>Completed: {new Date(job.completed_at).toLocaleString()}</p>}
      </div>
    </div>
  );
}
