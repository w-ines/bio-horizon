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
import Sidebar from "@/components/Sidebar";

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
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar />
      <main style={{ marginLeft: "250px", flex: 1, minHeight: "100vh", overflow: "auto", background: "#f8fafc" }}>
        {/* Page Header */}
        <div style={{
          borderBottom: "4px solid #cbd5e1",
          padding: "1.5rem 2rem",
          background: "white",
          marginBottom: "2rem",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <div style={{
              width: "40px", height: "40px", borderRadius: "10px",
              background: "rgba(244, 114, 182, 0.08)", display: "flex", alignItems: "center",
              justifyContent: "center", color: "#f472b6",
            }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <rect x="2" y="7" width="20" height="14" rx="2" />
                <path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" />
                <line x1="12" y1="12" x2="12" y2="16" />
                <line x1="10" y1="14" x2="14" y2="14" />
              </svg>
            </div>
            <div>
              <h1 style={{ margin: 0, fontSize: "1.5rem", fontWeight: "700", color: "#0f172a" }}>
                PubMed Corpus Ingestion
              </h1>
              <p style={{ margin: 0, fontSize: "0.875rem", color: "#64748b" }}>
                Create and manage large-scale PubMed corpus ingestion jobs with NER and Knowledge Graph integration
              </p>
            </div>
          </div>
        </div>

        <div style={{ padding: "0 2rem 3rem" }}>
          {/* Navigation */}
          <div style={{ display: "flex", gap: "1rem", marginBottom: "1.5rem" }}>
            <button
              onClick={() => setView("list")}
              style={{
                padding: "0.625rem 1.25rem",
                borderRadius: "8px",
                fontWeight: "500",
                fontSize: "0.875rem",
                cursor: "pointer",
                border: view === "list" ? "none" : "1px solid #e2e8f0",
                background: view === "list" ? "#f472b6" : "white",
                color: view === "list" ? "white" : "#374151",
                transition: "all 0.15s ease",
              }}
            >
              📋 All Jobs
            </button>
            <button
              onClick={() => setView("create")}
              style={{
                padding: "0.625rem 1.25rem",
                borderRadius: "8px",
                fontWeight: "500",
                fontSize: "0.875rem",
                cursor: "pointer",
                border: view === "create" ? "none" : "1px solid #e2e8f0",
                background: view === "create" ? "#f472b6" : "white",
                color: view === "create" ? "white" : "#374151",
                transition: "all 0.15s ease",
              }}
            >
              ➕ Create New Job
            </button>
            {selectedJobId && (
              <button
                onClick={() => setView("detail")}
                style={{
                  padding: "0.625rem 1.25rem",
                  borderRadius: "8px",
                  fontWeight: "500",
                  fontSize: "0.875rem",
                  cursor: "pointer",
                  border: view === "detail" ? "none" : "1px solid #e2e8f0",
                  background: view === "detail" ? "#f472b6" : "white",
                  color: view === "detail" ? "white" : "#374151",
                  transition: "all 0.15s ease",
                }}
              >
                🔍 Job Details
              </button>
            )}
          </div>

          {/* Content */}
          <div className="medical-card" style={{ padding: "1.5rem" }}>
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
              <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                <button
                  onClick={() => setView("list")}
                  style={{
                    alignSelf: "flex-start",
                    color: "#f472b6",
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    fontWeight: "500",
                    fontSize: "0.875rem",
                  }}
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
          <div style={{ marginTop: "2rem", padding: "1.5rem", background: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: "12px" }}>
            <h2 style={{ margin: "0 0 0.75rem 0", fontSize: "1rem", fontWeight: "600", color: "#1e40af" }}>
              💡 How it works
            </h2>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", fontSize: "0.875rem", color: "#1e40af" }}>
              <p style={{ margin: 0 }}><strong>1. Create a job:</strong> Define your PubMed search query and parameters</p>
              <p style={{ margin: 0 }}><strong>2. Automatic processing:</strong> The system fetches articles in batches, extracts medical entities, and builds the Knowledge Graph</p>
              <p style={{ margin: 0 }}><strong>3. Monitor progress:</strong> Track real-time progress with automatic updates every 2 seconds</p>
              <p style={{ margin: 0 }}><strong>4. Fault tolerance:</strong> Jobs can be resumed from checkpoints if they fail</p>
              <p style={{ margin: 0 }}><strong>5. Rate limiting:</strong> Respects NCBI API limits (3 req/s without API key, 10 req/s with key)</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
