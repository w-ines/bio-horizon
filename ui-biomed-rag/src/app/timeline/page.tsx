"use client";

/**
 * Timeline Page
 * 
 * Displays temporal evolution of the Knowledge Graph.
 * Shows snapshots over time and allows comparison between periods.
 */

import { useState, useEffect } from "react";
import {
  listSnapshots,
  compareSnapshots,
  type SnapshotsList,
  type SnapshotComparison,
} from "@/lib/api";

export default function TimelinePage() {
  const [snapshots, setSnapshots] = useState<SnapshotsList | null>(null);
  const [selectedNew, setSelectedNew] = useState<string>("");
  const [selectedOld, setSelectedOld] = useState<string>("");
  const [comparison, setComparison] = useState<SnapshotComparison | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load available snapshots
  useEffect(() => {
    const load = async () => {
      try {
        const data = await listSnapshots();
        setSnapshots(data);
        
        // Auto-select most recent and 4 weeks ago
        if (data.snapshots.length >= 2) {
          setSelectedNew(data.snapshots[data.snapshots.length - 1]);
          setSelectedOld(data.snapshots[Math.max(0, data.snapshots.length - 5)]);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load snapshots");
      }
    };
    load();
  }, []);

  // Compare snapshots when selection changes
  useEffect(() => {
    if (selectedNew && selectedOld && selectedNew !== selectedOld) {
      const compare = async () => {
        setLoading(true);
        setError(null);
        try {
          const result = await compareSnapshots(selectedNew, selectedOld);
          setComparison(result);
        } catch (err) {
          setError(err instanceof Error ? err.message : "Failed to compare snapshots");
        } finally {
          setLoading(false);
        }
      };
      compare();
    }
  }, [selectedNew, selectedOld]);

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
          maxWidth: "1400px",
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
            Knowledge Graph Timeline
          </h1>
          <p style={{ color: "#64748b", fontSize: "1rem" }}>
            Track the evolution of biomedical knowledge over time
          </p>
        </div>

        {/* Snapshot selector */}
        {snapshots && (
          <div
            style={{
              background: "white",
              border: "1px solid #e2e8f0",
              borderRadius: "12px",
              padding: "1.5rem",
              marginBottom: "2rem",
            }}
          >
            <h2
              style={{
                fontSize: "1.125rem",
                fontWeight: "600",
                color: "#0f172a",
                marginBottom: "1rem",
              }}
            >
              Compare Snapshots
            </h2>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr auto 1fr",
                gap: "1rem",
                alignItems: "center",
              }}
            >
              {/* Recent snapshot */}
              <div>
                <label
                  htmlFor="snapshot-new"
                  style={{
                    display: "block",
                    fontSize: "0.875rem",
                    fontWeight: "500",
                    color: "#64748b",
                    marginBottom: "0.5rem",
                  }}
                >
                  Recent Snapshot
                </label>
                <select
                  id="snapshot-new"
                  value={selectedNew}
                  onChange={(e) => setSelectedNew(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "0.625rem",
                    border: "1px solid #e2e8f0",
                    borderRadius: "8px",
                    fontSize: "0.875rem",
                    background: "white",
                  }}
                >
                  <option value="">Select week...</option>
                  {snapshots.snapshots.map((week) => (
                    <option key={week} value={week}>
                      {week}
                      {week === snapshots.current_week ? " (current)" : ""}
                    </option>
                  ))}
                </select>
              </div>

              {/* Arrow */}
              <div style={{ paddingTop: "1.5rem" }}>
                <svg
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="#94a3b8"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <line x1="5" y1="12" x2="19" y2="12" />
                  <polyline points="12 5 19 12 12 19" />
                </svg>
              </div>

              {/* Older snapshot */}
              <div>
                <label
                  htmlFor="snapshot-old"
                  style={{
                    display: "block",
                    fontSize: "0.875rem",
                    fontWeight: "500",
                    color: "#64748b",
                    marginBottom: "0.5rem",
                  }}
                >
                  Older Snapshot
                </label>
                <select
                  id="snapshot-old"
                  value={selectedOld}
                  onChange={(e) => setSelectedOld(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "0.625rem",
                    border: "1px solid #e2e8f0",
                    borderRadius: "8px",
                    fontSize: "0.875rem",
                    background: "white",
                  }}
                >
                  <option value="">Select week...</option>
                  {snapshots.snapshots.map((week) => (
                    <option key={week} value={week}>
                      {week}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Available snapshots info */}
            <div
              style={{
                marginTop: "1rem",
                padding: "0.75rem",
                background: "#f8fafc",
                borderRadius: "6px",
                fontSize: "0.8125rem",
                color: "#64748b",
              }}
            >
              📊 {snapshots.total_count} snapshot{snapshots.total_count !== 1 ? "s" : ""} available
              {snapshots.snapshots.length > 0 && (
                <>
                  {" "}
                  • Range: {snapshots.snapshots[0]} to{" "}
                  {snapshots.snapshots[snapshots.snapshots.length - 1]}
                </>
              )}
            </div>
          </div>
        )}

        {/* Loading state */}
        {loading && (
          <div
            style={{
              padding: "3rem",
              textAlign: "center",
              background: "white",
              border: "1px solid #e2e8f0",
              borderRadius: "12px",
              color: "#94a3b8",
            }}
          >
            Comparing snapshots...
          </div>
        )}

        {/* Error state */}
        {error && (
          <div
            style={{
              padding: "1.5rem",
              background: "rgba(239, 68, 68, 0.1)",
              border: "1px solid rgba(239, 68, 68, 0.2)",
              borderRadius: "12px",
              color: "#ef4444",
              fontSize: "0.875rem",
            }}
          >
            {error}
          </div>
        )}

        {/* Comparison results */}
        {comparison && !loading && (
          <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
            {/* Summary cards */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                gap: "1rem",
              }}
            >
              <SummaryCard
                label="New Entities"
                value={comparison.summary.total_new_nodes}
                icon="🆕"
                color="#22c55e"
              />
              <SummaryCard
                label="New Relations"
                value={comparison.summary.total_new_edges}
                icon="🔗"
                color="#3b82f6"
              />
              <SummaryCard
                label="Strengthened"
                value={comparison.summary.total_weight_increased}
                icon="📈"
                color="#f59e0b"
              />
              <SummaryCard
                label="Disappeared"
                value={comparison.summary.total_disappeared_nodes}
                icon="📉"
                color="#94a3b8"
              />
            </div>

            {/* New entities */}
            {comparison.new_nodes.length > 0 && (
              <DetailSection
                title="New Entities"
                icon="🆕"
                items={comparison.new_nodes.map((node) => ({
                  label: node.label,
                  type: node.entity_type,
                  frequency: node.frequency,
                }))}
              />
            )}

            {/* New relations */}
            {comparison.new_edges.length > 0 && (
              <DetailSection
                title="New Relations"
                icon="🔗"
                items={comparison.new_edges.map((edge) => ({
                  label: `${edge.source.label} ↔ ${edge.target.label}`,
                  type: `${edge.source.entity_type} - ${edge.target.entity_type}`,
                }))}
              />
            )}

            {/* Strengthened relations */}
            {comparison.weight_increased.length > 0 && (
              <DetailSection
                title="Strengthened Relations"
                icon="📈"
                items={comparison.weight_increased.map((edge) => ({
                  label: `${edge.source.label} ↔ ${edge.target.label}`,
                  type: `${edge.source.entity_type} - ${edge.target.entity_type}`,
                  delta: edge.delta,
                  oldWeight: edge.old_weight,
                  newWeight: edge.new_weight,
                }))}
              />
            )}
          </div>
        )}

        {/* Empty state */}
        {!snapshots?.snapshots.length && !loading && !error && (
          <div
            style={{
              padding: "3rem",
              textAlign: "center",
              background: "white",
              border: "1px solid #e2e8f0",
              borderRadius: "12px",
            }}
          >
            <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>📊</div>
            <h3
              style={{
                fontSize: "1.125rem",
                fontWeight: "600",
                color: "#0f172a",
                marginBottom: "0.5rem",
              }}
            >
              No snapshots available
            </h3>
            <p style={{ color: "#64748b", fontSize: "0.875rem" }}>
              Create your first snapshot by running the PubMed → NER → KG pipeline.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

// Helper components
function SummaryCard({
  label,
  value,
  icon,
  color,
}: {
  label: string;
  value: number;
  icon: string;
  color: string;
}) {
  return (
    <div
      style={{
        background: "white",
        border: "1px solid #e2e8f0",
        borderRadius: "12px",
        padding: "1.25rem",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.75rem",
          marginBottom: "0.5rem",
        }}
      >
        <span style={{ fontSize: "1.5rem" }}>{icon}</span>
        <span style={{ fontSize: "0.875rem", color: "#64748b" }}>{label}</span>
      </div>
      <div style={{ fontSize: "2rem", fontWeight: "700", color }}>{value}</div>
    </div>
  );
}

function DetailSection({
  title,
  icon,
  items,
}: {
  title: string;
  icon: string;
  items: Array<{
    label: string;
    type: string;
    frequency?: number;
    delta?: number;
    oldWeight?: number;
    newWeight?: number;
  }>;
}) {
  return (
    <div
      style={{
        background: "white",
        border: "1px solid #e2e8f0",
        borderRadius: "12px",
        padding: "1.5rem",
      }}
    >
      <h3
        style={{
          fontSize: "1.125rem",
          fontWeight: "600",
          color: "#0f172a",
          marginBottom: "1rem",
          display: "flex",
          alignItems: "center",
          gap: "0.5rem",
        }}
      >
        <span>{icon}</span>
        <span>{title}</span>
        <span style={{ fontSize: "0.875rem", color: "#94a3b8", fontWeight: "400" }}>
          ({items.length})
        </span>
      </h3>

      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
        {items.slice(0, 10).map((item, i) => (
          <div
            key={i}
            style={{
              padding: "0.75rem",
              background: "#f8fafc",
              borderRadius: "8px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div>
              <div style={{ fontSize: "0.9375rem", fontWeight: "500", color: "#0f172a" }}>
                {item.label}
              </div>
              <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>{item.type}</div>
            </div>
            <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
              {item.frequency !== undefined && (
                <span style={{ fontSize: "0.8125rem", color: "#64748b" }}>
                  {item.frequency}× mentioned
                </span>
              )}
              {item.delta !== undefined && (
                <span
                  style={{
                    fontSize: "0.8125rem",
                    fontWeight: "600",
                    color: "#22c55e",
                  }}
                >
                  +{item.delta}
                </span>
              )}
            </div>
          </div>
        ))}
        {items.length > 10 && (
          <div style={{ fontSize: "0.8125rem", color: "#94a3b8", textAlign: "center" }}>
            ... and {items.length - 10} more
          </div>
        )}
      </div>
    </div>
  );
}
