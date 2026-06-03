/**
 * SignalCard Component
 * 
 * Displays a single emerging signal with:
 * - Entity relation (A ↔ B)
 * - Emergence score
 * - Consensus bar (Phase 5)
 * - Source PMIDs
 * - Signal type indicator
 */

import { EmergenceScore } from "./EmergenceScore";
import { ConsensusBar } from "./ConsensusBar";
import type { Signal } from "@/lib/api";

interface SignalCardProps {
  signal: Signal;
  onClick?: () => void;
}

export function SignalCard({ signal, onClick }: SignalCardProps) {
  // Signal type styling
  const getSignalTypeStyle = (type: Signal["signal_type"]) => {
    switch (type) {
      case "emerging":
        return {
          color: "#ef4444",
          bg: "rgba(239, 68, 68, 0.1)",
          icon: "🔴",
          label: "Emerging",
        };
      case "accelerating":
        return {
          color: "#f59e0b",
          bg: "rgba(245, 158, 11, 0.1)",
          icon: "🟡",
          label: "Accelerating",
        };
      case "declining":
        return {
          color: "#64748b",
          bg: "rgba(100, 116, 139, 0.1)",
          icon: "⚫",
          label: "Declining",
        };
      case "contradictory":
        return {
          color: "#a78bfa",
          bg: "rgba(167, 139, 250, 0.1)",
          icon: "🟣",
          label: "Contradictory",
        };
      default:
        return {
          color: "#94a3b8",
          bg: "rgba(148, 163, 184, 0.1)",
          icon: "⚪",
          label: "Unknown",
        };
    }
  };

  const typeStyle = getSignalTypeStyle(signal.signal_type);

  // Has consensus data (Phase 5)
  const hasConsensus =
    signal.consensus_positive !== undefined &&
    signal.consensus_negative !== undefined &&
    signal.consensus_hypothetical !== undefined;

  return (
    <div
      onClick={onClick}
      style={{
        background: "white",
        border: "1px solid #e2e8f0",
        borderRadius: "12px",
        padding: "1.5rem",
        cursor: onClick ? "pointer" : "default",
        transition: "all 0.2s ease",
        boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
      }}
      onMouseEnter={(e) => {
        if (onClick) {
          e.currentTarget.style.borderColor = typeStyle.color;
          e.currentTarget.style.boxShadow = `0 8px 24px -6px ${typeStyle.color}28`;
          e.currentTarget.style.transform = "translateY(-2px)";
        }
      }}
      onMouseLeave={(e) => {
        if (onClick) {
          e.currentTarget.style.borderColor = "#e2e8f0";
          e.currentTarget.style.boxShadow = "0 1px 3px rgba(0,0,0,0.04)";
          e.currentTarget.style.transform = "translateY(0)";
        }
      }}
    >
      {/* Header: Signal type badge + Week */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "1rem",
        }}
      >
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "0.5rem",
            padding: "0.375rem 0.75rem",
            background: typeStyle.bg,
            borderRadius: "6px",
            fontSize: "0.8125rem",
            fontWeight: "600",
            color: typeStyle.color,
          }}
        >
          <span>{typeStyle.icon}</span>
          <span>{typeStyle.label}</span>
        </div>

        <span style={{ fontSize: "0.75rem", color: "#94a3b8" }}>
          {signal.week_label}
        </span>
      </div>

      {/* Entity relation */}
      <div style={{ marginBottom: "1rem" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.75rem",
            fontSize: "1.125rem",
            fontWeight: "600",
            color: "#0f172a",
          }}
        >
          <span>{signal.entity_a}</span>
          <svg
            width="20"
            height="20"
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
          <span>{signal.entity_b}</span>
        </div>
      </div>

      {/* Emergence score */}
      <div style={{ marginBottom: "1rem" }}>
        <EmergenceScore score={signal.emergence_score} size="md" />
      </div>

      {/* Consensus bar (Phase 5) */}
      {hasConsensus && (
        <div style={{ marginBottom: "1rem" }}>
          <ConsensusBar
            positive={signal.consensus_positive!}
            negative={signal.consensus_negative!}
            hypothetical={signal.consensus_hypothetical!}
            totalArticles={signal.pmids?.length}
            showLegend={false}
            size="sm"
          />
        </div>
      )}

      {/* Metrics row */}
      <div
        style={{
          display: "flex",
          gap: "1.5rem",
          paddingTop: "1rem",
          borderTop: "1px solid #f1f5f9",
          fontSize: "0.8125rem",
          color: "#64748b",
        }}
      >
        {/* Velocity */}
        {signal.velocity !== undefined && (
          <div style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
              <polyline points="17 6 23 6 23 12" />
            </svg>
            <span>Velocity: {signal.velocity.toFixed(1)}</span>
          </div>
        )}

        {/* Source diversity */}
        {signal.source_diversity !== undefined && (
          <div style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
              <path d="M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
            <span>{signal.source_diversity} sources</span>
          </div>
        )}

        {/* PMIDs count */}
        {signal.pmids && signal.pmids.length > 0 && (
          <div style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10 9 9 9 8 9" />
            </svg>
            <span>{signal.pmids.length} articles</span>
          </div>
        )}
      </div>
    </div>
  );
}
