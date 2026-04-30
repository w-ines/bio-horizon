/**
 * Jobs management page
 * 
 * Allows users to:
 * - Create new PubMed corpus ingestion jobs
 * - View all jobs with filtering
 * - Monitor job progress in real-time
 * - Cancel/resume jobs
 */

"use client";

import { useState } from "react";
import { JobsList } from "@/features/jobs/JobsList";
import { JobProgress } from "@/features/jobs/JobProgress";
import { CreateJobForm } from "@/features/jobs/CreateJobForm";

export default function JobsPage() {
  const [view, setView] = useState<"list" | "create" | "detail">("list");
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);

  const handleJobCreated = (jobId: string) => {
    setSelectedJobId(jobId);
    setView("detail");
  };

  const handleJobClick = (jobId: string) => {
    setSelectedJobId(jobId);
    setView("detail");
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            PubMed Corpus Ingestion
          </h1>
          <p className="text-gray-600">
            Create and manage large-scale PubMed corpus ingestion jobs with NER and Knowledge Graph integration
          </p>
        </div>

        {/* Navigation */}
        <div className="flex gap-4 mb-6">
          <button
            onClick={() => setView("list")}
            className={`px-6 py-3 rounded-lg font-medium transition-colors ${
              view === "list"
                ? "bg-blue-600 text-white"
                : "bg-white text-gray-700 border hover:bg-gray-50"
            }`}
          >
            📋 All Jobs
          </button>
          <button
            onClick={() => setView("create")}
            className={`px-6 py-3 rounded-lg font-medium transition-colors ${
              view === "create"
                ? "bg-blue-600 text-white"
                : "bg-white text-gray-700 border hover:bg-gray-50"
            }`}
          >
            ➕ Create New Job
          </button>
          {selectedJobId && (
            <button
              onClick={() => setView("detail")}
              className={`px-6 py-3 rounded-lg font-medium transition-colors ${
                view === "detail"
                  ? "bg-blue-600 text-white"
                  : "bg-white text-gray-700 border hover:bg-gray-50"
              }`}
            >
              🔍 Job Details
            </button>
          )}
        </div>

        {/* Content */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          {view === "list" && (
            <JobsList onJobClick={handleJobClick} />
          )}

          {view === "create" && (
            <CreateJobForm
              onJobCreated={handleJobCreated}
              onCancel={() => setView("list")}
            />
          )}

          {view === "detail" && selectedJobId && (
            <div className="space-y-4">
              <button
                onClick={() => setView("list")}
                className="text-blue-600 hover:text-blue-700 font-medium"
              >
                ← Back to Jobs List
              </button>
              <JobProgress
                jobId={selectedJobId}
                onComplete={() => {
                  // Could show a success notification here
                }}
                onError={(error) => {
                  console.error("Job error:", error);
                }}
              />
            </div>
          )}
        </div>

        {/* Info Panel */}
        <div className="mt-8 p-6 bg-blue-50 border border-blue-200 rounded-lg">
          <h2 className="text-lg font-semibold text-blue-900 mb-3">
            💡 How it works
          </h2>
          <div className="space-y-2 text-sm text-blue-800">
            <p>
              <strong>1. Create a job:</strong> Define your PubMed search query and parameters
            </p>
            <p>
              <strong>2. Automatic processing:</strong> The system fetches articles in batches, extracts medical entities, and builds the Knowledge Graph
            </p>
            <p>
              <strong>3. Monitor progress:</strong> Track real-time progress with automatic updates every 2 seconds
            </p>
            <p>
              <strong>4. Fault tolerance:</strong> Jobs can be resumed from checkpoints if they fail
            </p>
            <p>
              <strong>5. Rate limiting:</strong> Respects NCBI API limits (3 req/s without API key, 10 req/s with key)
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
