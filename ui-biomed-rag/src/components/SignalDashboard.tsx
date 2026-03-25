/**
 * SignalDashboard Component
 * 
 * Main dashboard for displaying emerging signals.
 * Shows signals grouped by type with filtering and sorting options.
 */

"use client";

import { useState, useEffect } from "react";
import { SignalCard } from "./SignalCard";
import type { Signal } from "@/lib/api";
import { listSignals } from "@/lib/api";

interface SignalDashboardProps {
  initialSignals?: Signal[];
}

export function SignalDashboard({ initialSignals = [] }: SignalDashboardProps) {
  const [signals, setSignals] = useState<Signal[]>(initialSignals);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<string>("all");
  const [minScore, setMinScore] = useState<number>(0);

  // Load signals
  useEffect(() => {
    const loadSignals = async () => {
      setLoading(true);
      setError(null);
      try {
        const params: any = { min_score: minScore };
        if (filterType !== "all") {
          params.signal_type = filterType;
        }
        const result = await listSignals(params);
        setSignals(result.signals || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load signals");
      } finally {
        setLoading(false);
      }
    };

    loadSignals();
  }, [filterType, minScore]);

  // Group signals by type
  const groupedSignals = {
    emerging: signals.filter((s) => s.signal_type === "emerging"),
    accelerating: signals.filter((s) => s.signal_type === "accelerating"),
    declining: signals.filter((s) => s.signal_type === "declining"),
    contradictory: signals.filter((s) => s.signal_type === "contradictory"),
  };

  // Filter buttons
  const filterButtons = [
    { value: "all", label: "All Signals", icon: "🔍" },
    { value: "emerging", label: "Emerging", icon: "🔴" },
    { value: "accelerating", label: "Accelerating", icon: "🟡" },
    { value: "declining", label: "Declining", icon: "⚫" },
    { value: "contradictory", label: "Contradictory", icon: "🟣" },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
      {/* Header */}
      <div>
        <h1
          style={{
            fontSize: "1.875rem",
            fontWeight: "700",
            color: "#0f172a",
            marginBottom: "0.5rem",
          }}
        >
          Emerging Signals
        </h1>
        <p style={{ color: "#64748b", fontSize: "1rem" }}>
          Detected changes in the biomedical knowledge graph over time
        </p>
      </div>

      {/* Filters */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "0.75rem",
          alignItems: "center",
        }}
      >
        {/* Type filters */}
        {filterButtons.map((btn) => (
          <button
            key={btn.value}
            onClick={() => setFilterType(btn.value)}
            style={{
              padding: "0.5rem 1rem",
              background: filterType === btn.value ? "#0f172a" : "white",
              color: filterType === btn.value ? "white" : "#64748b",
              border: "1px solid #e2e8f0",
              borderRadius: "8px",
              fontSize: "0.875rem",
              fontWeight: "500",
              cursor: "pointer",
              transition: "all 0.2s ease",
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
            }}
            onMouseEnter={(e) => {
              if (filterType !== btn.value) {
                e.currentTarget.style.background = "#f8fafc";
                e.currentTarget.style.borderColor = "#cbd5e1";
              }
            }}
            onMouseLeave={(e) => {
              if (filterType !== btn.value) {
                e.currentTarget.style.background = "white";
                e.currentTarget.style.borderColor = "#e2e8f0";
              }
            }}
          >
            <span>{btn.icon}</span>
            <span>{btn.label}</span>
          </button>
        ))}

        {/* Score filter */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            marginLeft: "auto",
          }}
        >
          <label
            htmlFor="min-score"
            style={{ fontSize: "0.875rem", color: "#64748b" }}
          >
            Min Score:
          </label>
          <input
            id="min-score"
            type="number"
            min="0"
            max="100"
            value={minScore}
            onChange={(e) => setMinScore(Number(e.target.value))}
            style={{
              width: "80px",
              padding: "0.5rem",
              border: "1px solid #e2e8f0",
              borderRadius: "6px",
              fontSize: "0.875rem",
            }}
          />
        </div>
      </div>

      {/* Loading state */}
      {loading && (
        <div
          style={{
            padding: "3rem",
            textAlign: "center",
            color: "#94a3b8",
          }}
        >
          Loading signals...
        </div>
      )}

      {/* Error state */}
      {error && (
        <div
          style={{
            padding: "1.5rem",
            background: "rgba(239, 68, 68, 0.1)",
            border: "1px solid rgba(239, 68, 68, 0.2)",
            borderRadius: "8px",
            color: "#ef4444",
            fontSize: "0.875rem",
          }}
        >
          {error}
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && signals.length === 0 && (
        <div
          style={{
            padding: "3rem",
            textAlign: "center",
            background: "white",
            border: "1px solid #e2e8f0",
            borderRadius: "12px",
          }}
        >
          <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>🔍</div>
          <h3
            style={{
              fontSize: "1.125rem",
              fontWeight: "600",
              color: "#0f172a",
              marginBottom: "0.5rem",
            }}
          >
            No signals detected yet
          </h3>
          <p style={{ color: "#64748b", fontSize: "0.875rem" }}>
            Run the PubMed → NER → KG pipeline and create snapshots to detect
            emerging signals.
          </p>
        </div>
      )}

      {/* Signals grid */}
      {!loading && !error && signals.length > 0 && (
        <div>
          {/* Emerging signals */}
          {groupedSignals.emerging.length > 0 && (
            <div style={{ marginBottom: "2rem" }}>
              <h2
                style={{
                  fontSize: "1.25rem",
                  fontWeight: "600",
                  color: "#0f172a",
                  marginBottom: "1rem",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem",
                }}
              >
                <span>🔴</span>
                <span>Emerging Signals</span>
                <span
                  style={{
                    fontSize: "0.875rem",
                    color: "#94a3b8",
                    fontWeight: "400",
                  }}
                >
                  ({groupedSignals.emerging.length})
                </span>
              </h2>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(400px, 1fr))",
                  gap: "1rem",
                }}
              >
                {groupedSignals.emerging.map((signal) => (
                  <SignalCard key={signal.id} signal={signal} />
                ))}
              </div>
            </div>
          )}

          {/* Accelerating signals */}
          {groupedSignals.accelerating.length > 0 && (
            <div style={{ marginBottom: "2rem" }}>
              <h2
                style={{
                  fontSize: "1.25rem",
                  fontWeight: "600",
                  color: "#0f172a",
                  marginBottom: "1rem",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem",
                }}
              >
                <span>🟡</span>
                <span>Accelerating Trends</span>
                <span
                  style={{
                    fontSize: "0.875rem",
                    color: "#94a3b8",
                    fontWeight: "400",
                  }}
                >
                  ({groupedSignals.accelerating.length})
                </span>
              </h2>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(400px, 1fr))",
                  gap: "1rem",
                }}
              >
                {groupedSignals.accelerating.map((signal) => (
                  <SignalCard key={signal.id} signal={signal} />
                ))}
              </div>
            </div>
          )}

          {/* Contradictory signals */}
          {groupedSignals.contradictory.length > 0 && (
            <div style={{ marginBottom: "2rem" }}>
              <h2
                style={{
                  fontSize: "1.25rem",
                  fontWeight: "600",
                  color: "#0f172a",
                  marginBottom: "1rem",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem",
                }}
              >
                <span>🟣</span>
                <span>Contradictory Evidence</span>
                <span
                  style={{
                    fontSize: "0.875rem",
                    color: "#94a3b8",
                    fontWeight: "400",
                  }}
                >
                  ({groupedSignals.contradictory.length})
                </span>
              </h2>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(400px, 1fr))",
                  gap: "1rem",
                }}
              >
                {groupedSignals.contradictory.map((signal) => (
                  <SignalCard key={signal.id} signal={signal} />
                ))}
              </div>
            </div>
          )}

          {/* Declining signals */}
          {groupedSignals.declining.length > 0 && (
            <div>
              <h2
                style={{
                  fontSize: "1.25rem",
                  fontWeight: "600",
                  color: "#0f172a",
                  marginBottom: "1rem",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem",
                }}
              >
                <span>⚫</span>
                <span>Declining Topics</span>
                <span
                  style={{
                    fontSize: "0.875rem",
                    color: "#94a3b8",
                    fontWeight: "400",
                  }}
                >
                  ({groupedSignals.declining.length})
                </span>
              </h2>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(400px, 1fr))",
                  gap: "1rem",
                }}
              >
                {groupedSignals.declining.map((signal) => (
                  <SignalCard key={signal.id} signal={signal} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
