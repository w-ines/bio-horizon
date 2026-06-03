/**
 * ConsensusBar Component
 * 
 * Displays scientific consensus breakdown for a relation:
 * - % positive (PRESENT assertion)
 * - % negative (NEGATED assertion)
 * - % hypothetical (HYPOTHETICAL assertion)
 * 
 * Phase 5 feature - will be populated when OpenMed Assertion Status is integrated.
 */

interface ConsensusBarProps {
  positive: number; // 0-100
  negative: number; // 0-100
  hypothetical: number; // 0-100
  totalArticles?: number;
  showLegend?: boolean;
  size?: "sm" | "md" | "lg";
}

export function ConsensusBar({
  positive,
  negative,
  hypothetical,
  totalArticles,
  showLegend = true,
  size = "md",
}: ConsensusBarProps) {
  // Normalize percentages to ensure they sum to 100
  const total = positive + negative + hypothetical;
  const normalizedPositive = total > 0 ? (positive / total) * 100 : 0;
  const normalizedNegative = total > 0 ? (negative / total) * 100 : 0;
  const normalizedHypothetical = total > 0 ? (hypothetical / total) * 100 : 0;

  // Consensus classification
  const getConsensusLabel = (): {
    label: string;
    color: string;
    description: string;
  } => {
    if (normalizedPositive > 80) {
      return {
        label: "Confirmed",
        color: "#22c55e",
        description: "Strong scientific consensus",
      };
    }
    if (normalizedPositive >= 40 && normalizedPositive <= 60) {
      return {
        label: "Contradictory",
        color: "#f59e0b",
        description: "Community is divided",
      };
    }
    if (normalizedHypothetical > 50) {
      return {
        label: "Preliminary",
        color: "#a78bfa",
        description: "Still speculative",
      };
    }
    if (normalizedNegative > 50) {
      return {
        label: "Refuted",
        color: "#ef4444",
        description: "Evidence against",
      };
    }
    return {
      label: "Mixed",
      color: "#64748b",
      description: "No clear consensus",
    };
  };

  const consensus = getConsensusLabel();

  // Size variants
  const heights = {
    sm: "6px",
    md: "8px",
    lg: "12px",
  };

  const height = heights[size];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
      {/* Consensus label */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <span
            style={{
              fontSize: "0.875rem",
              fontWeight: "600",
              color: consensus.color,
            }}
          >
            {consensus.label}
          </span>
          <span style={{ fontSize: "0.75rem", color: "#94a3b8" }}>
            {consensus.description}
          </span>
        </div>
        {totalArticles !== undefined && (
          <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
            {totalArticles} article{totalArticles !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {/* Stacked bar */}
      <div
        style={{
          width: "100%",
          height,
          background: "#f1f5f9",
          borderRadius: "4px",
          overflow: "hidden",
          display: "flex",
        }}
      >
        {/* Positive segment */}
        {normalizedPositive > 0 && (
          <div
            style={{
              width: `${normalizedPositive}%`,
              background: "#22c55e",
              transition: "width 0.3s ease",
            }}
            title={`${Math.round(normalizedPositive)}% positive`}
          />
        )}

        {/* Negative segment */}
        {normalizedNegative > 0 && (
          <div
            style={{
              width: `${normalizedNegative}%`,
              background: "#ef4444",
              transition: "width 0.3s ease",
            }}
            title={`${Math.round(normalizedNegative)}% negative`}
          />
        )}

        {/* Hypothetical segment */}
        {normalizedHypothetical > 0 && (
          <div
            style={{
              width: `${normalizedHypothetical}%`,
              background: "#a78bfa",
              transition: "width 0.3s ease",
            }}
            title={`${Math.round(normalizedHypothetical)}% hypothetical`}
          />
        )}
      </div>

      {/* Legend */}
      {showLegend && (
        <div
          style={{
            display: "flex",
            gap: "1rem",
            fontSize: "0.75rem",
            color: "#64748b",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
            <div
              style={{
                width: "12px",
                height: "12px",
                background: "#22c55e",
                borderRadius: "2px",
              }}
            />
            <span>
              ✅ {Math.round(normalizedPositive)}% Positive
            </span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
            <div
              style={{
                width: "12px",
                height: "12px",
                background: "#ef4444",
                borderRadius: "2px",
              }}
            />
            <span>
              ❌ {Math.round(normalizedNegative)}% Negative
            </span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
            <div
              style={{
                width: "12px",
                height: "12px",
                background: "#a78bfa",
                borderRadius: "2px",
              }}
            />
            <span>
              ❓ {Math.round(normalizedHypothetical)}% Hypothetical
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
