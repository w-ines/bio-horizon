"use client";

/**
 * Settings Page - Watch Topics Configuration
 * 
 * Configure automated surveillance topics that will be executed weekly by the scheduler.
 * Each topic triggers: PubMed search → NER → KG update → Snapshot → Signal detection
 */

import { useState, useEffect } from "react";

interface WatchTopic {
  id: number;
  query: string;
  filters: Record<string, any>;
  custom_labels: string[];
  frequency: "weekly" | "monthly";
  is_active: boolean;
  created_at: string;
}

export default function SettingsPage() {
  const [topics, setTopics] = useState<WatchTopic[]>([]);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newQuery, setNewQuery] = useState("");
  const [newFrequency, setNewFrequency] = useState<"weekly" | "monthly">("weekly");
  const [customLabels, setCustomLabels] = useState("");

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#f8fafc",
        padding: "2rem",
      }}
    >
      <div
        style={{
          maxWidth: "1000px",
          margin: "0 auto",
        }}
      >
        {/* Header */}
        <div style={{ marginBottom: "2rem" }}>
          <h1
            style={{
              fontSize: "1.875rem",
              fontWeight: "700",
              color: "#0f172a",
              marginBottom: "0.5rem",
            }}
          >
            Surveillance Settings
          </h1>
          <p style={{ color: "#64748b", fontSize: "1rem" }}>
            Configure automated watch topics for weekly snapshot creation and signal detection
          </p>
        </div>

        {/* Info banner */}
        <div
          style={{
            background: "#dbeafe",
            border: "1px solid #93c5fd",
            borderRadius: "12px",
            padding: "1.5rem",
            marginBottom: "2rem",
          }}
        >
          <div style={{ display: "flex", gap: "1rem" }}>
            <span style={{ fontSize: "1.5rem" }}>ℹ️</span>
            <div>
              <h3
                style={{
                  fontSize: "1rem",
                  fontWeight: "600",
                  color: "#1e40af",
                  marginBottom: "0.5rem",
                }}
              >
                How it works
              </h3>
              <ul
                style={{
                  margin: 0,
                  paddingLeft: "1.5rem",
                  color: "#1e40af",
                  fontSize: "0.875rem",
                  lineHeight: "1.6",
                }}
              >
                <li>Configure 1-5 surveillance topics with PubMed queries</li>
                <li>The scheduler runs automatically every week</li>
                <li>For each active topic: PubMed → NER → KG → Snapshot → Signals</li>
                <li>You receive alerts when strong signals are detected</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Add topic button */}
        {!showAddForm && (
          <button
            onClick={() => setShowAddForm(true)}
            style={{
              padding: "0.875rem 1.5rem",
              background: "#0f172a",
              color: "white",
              border: "none",
              borderRadius: "8px",
              fontSize: "0.9375rem",
              fontWeight: "600",
              cursor: "pointer",
              marginBottom: "2rem",
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
            }}
          >
            <span style={{ fontSize: "1.25rem" }}>+</span>
            <span>Add Watch Topic</span>
          </button>
        )}

        {/* Add topic form */}
        {showAddForm && (
          <div
            style={{
              background: "white",
              border: "1px solid #e2e8f0",
              borderRadius: "12px",
              padding: "2rem",
              marginBottom: "2rem",
            }}
          >
            <h3
              style={{
                fontSize: "1.125rem",
                fontWeight: "600",
                color: "#0f172a",
                marginBottom: "1.5rem",
              }}
            >
              New Watch Topic
            </h3>

            {/* Query */}
            <div style={{ marginBottom: "1.5rem" }}>
              <label
                style={{
                  display: "block",
                  fontSize: "0.875rem",
                  fontWeight: "600",
                  color: "#0f172a",
                  marginBottom: "0.5rem",
                }}
              >
                PubMed Query *
              </label>
              <input
                type="text"
                value={newQuery}
                onChange={(e) => setNewQuery(e.target.value)}
                placeholder="e.g., Alzheimer disease treatment"
                style={{
                  width: "100%",
                  padding: "0.75rem",
                  border: "1px solid #e2e8f0",
                  borderRadius: "8px",
                  fontSize: "1rem",
                }}
              />
            </div>

            {/* Frequency */}
            <div style={{ marginBottom: "1.5rem" }}>
              <label
                style={{
                  display: "block",
                  fontSize: "0.875rem",
                  fontWeight: "600",
                  color: "#0f172a",
                  marginBottom: "0.5rem",
                }}
              >
                Frequency
              </label>
              <select
                value={newFrequency}
                onChange={(e) => setNewFrequency(e.target.value as "weekly" | "monthly")}
                style={{
                  padding: "0.75rem",
                  border: "1px solid #e2e8f0",
                  borderRadius: "8px",
                  fontSize: "1rem",
                  background: "white",
                }}
              >
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </select>
            </div>

            {/* Custom labels (Zero-shot NER) */}
            <div style={{ marginBottom: "1.5rem" }}>
              <label
                style={{
                  display: "block",
                  fontSize: "0.875rem",
                  fontWeight: "600",
                  color: "#0f172a",
                  marginBottom: "0.5rem",
                }}
              >
                Custom Entity Labels (Optional)
              </label>
              <input
                type="text"
                value={customLabels}
                onChange={(e) => setCustomLabels(e.target.value)}
                placeholder="e.g., BRAIN_REGION, BIOMARKER, COGNITIVE_FUNCTION"
                style={{
                  width: "100%",
                  padding: "0.75rem",
                  border: "1px solid #e2e8f0",
                  borderRadius: "8px",
                  fontSize: "1rem",
                }}
              />
              <p style={{ fontSize: "0.75rem", color: "#94a3b8", marginTop: "0.5rem" }}>
                Comma-separated list for Zero-shot NER (Phase 5)
              </p>
            </div>

            {/* Actions */}
            <div style={{ display: "flex", gap: "1rem" }}>
              <button
                onClick={() => {
                  // TODO: Save topic
                  setShowAddForm(false);
                }}
                disabled={!newQuery.trim()}
                style={{
                  padding: "0.75rem 1.5rem",
                  background: !newQuery.trim() ? "#94a3b8" : "#0f172a",
                  color: "white",
                  border: "none",
                  borderRadius: "8px",
                  fontSize: "0.9375rem",
                  fontWeight: "600",
                  cursor: !newQuery.trim() ? "not-allowed" : "pointer",
                }}
              >
                Save Topic
              </button>
              <button
                onClick={() => {
                  setShowAddForm(false);
                  setNewQuery("");
                  setCustomLabels("");
                }}
                style={{
                  padding: "0.75rem 1.5rem",
                  background: "white",
                  color: "#64748b",
                  border: "1px solid #e2e8f0",
                  borderRadius: "8px",
                  fontSize: "0.9375rem",
                  fontWeight: "600",
                  cursor: "pointer",
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Topics list */}
        <div>
          <h3
            style={{
              fontSize: "1.125rem",
              fontWeight: "600",
              color: "#0f172a",
              marginBottom: "1rem",
            }}
          >
            Active Watch Topics
          </h3>

          {topics.length === 0 ? (
            <div
              style={{
                background: "white",
                border: "1px solid #e2e8f0",
                borderRadius: "12px",
                padding: "3rem",
                textAlign: "center",
              }}
            >
              <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>👁️</div>
              <h4
                style={{
                  fontSize: "1.125rem",
                  fontWeight: "600",
                  color: "#0f172a",
                  marginBottom: "0.5rem",
                }}
              >
                No watch topics configured
              </h4>
              <p style={{ color: "#64748b", fontSize: "0.875rem" }}>
                Add your first surveillance topic to start automated snapshot creation
              </p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              {topics.map((topic) => (
                <TopicCard key={topic.id} topic={topic} />
              ))}
            </div>
          )}
        </div>

        {/* Scheduler status */}
        <div
          style={{
            background: "white",
            border: "1px solid #e2e8f0",
            borderRadius: "12px",
            padding: "1.5rem",
            marginTop: "2rem",
          }}
        >
          <h3
            style={{
              fontSize: "1.125rem",
              fontWeight: "600",
              color: "#0f172a",
              marginBottom: "1rem",
            }}
          >
            Scheduler Status
          </h3>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.75rem",
              padding: "1rem",
              background: "#f0fdf4",
              border: "1px solid #bbf7d0",
              borderRadius: "8px",
            }}
          >
            <div
              style={{
                width: "12px",
                height: "12px",
                background: "#22c55e",
                borderRadius: "50%",
              }}
            />
            <span style={{ fontSize: "0.875rem", color: "#166534", fontWeight: "500" }}>
              Scheduler is running • Next execution: Sunday 00:00 UTC
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

// Topic card component
function TopicCard({ topic }: { topic: WatchTopic }) {
  return (
    <div
      style={{
        background: "white",
        border: "1px solid #e2e8f0",
        borderRadius: "12px",
        padding: "1.5rem",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start" }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.75rem" }}>
            <h4
              style={{
                fontSize: "1.0625rem",
                fontWeight: "600",
                color: "#0f172a",
                margin: 0,
              }}
            >
              {topic.query}
            </h4>
            <span
              style={{
                padding: "0.25rem 0.625rem",
                background: topic.is_active ? "#dcfce7" : "#f1f5f9",
                color: topic.is_active ? "#166534" : "#64748b",
                borderRadius: "4px",
                fontSize: "0.75rem",
                fontWeight: "600",
              }}
            >
              {topic.is_active ? "Active" : "Inactive"}
            </span>
          </div>

          <div style={{ display: "flex", gap: "1.5rem", fontSize: "0.8125rem", color: "#64748b" }}>
            <span>📅 {topic.frequency}</span>
            {topic.custom_labels.length > 0 && (
              <span>🏷️ {topic.custom_labels.length} custom labels</span>
            )}
          </div>
        </div>

        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button
            style={{
              padding: "0.5rem 0.875rem",
              background: "white",
              border: "1px solid #e2e8f0",
              borderRadius: "6px",
              fontSize: "0.8125rem",
              color: "#64748b",
              cursor: "pointer",
            }}
          >
            Edit
          </button>
          <button
            style={{
              padding: "0.5rem 0.875rem",
              background: "white",
              border: "1px solid #fecaca",
              borderRadius: "6px",
              fontSize: "0.8125rem",
              color: "#dc2626",
              cursor: "pointer",
            }}
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}
