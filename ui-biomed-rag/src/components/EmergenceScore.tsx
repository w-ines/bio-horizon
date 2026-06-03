/**
 * EmergenceScore Component
 * 
 * Displays an emergence score (0-100) with visual indicator and color coding.
 * Used to show how novel/important a signal is.
 */

interface EmergenceScoreProps {
  score: number; // 0-100
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
}

export function EmergenceScore({
  score,
  size = "md",
  showLabel = true,
}: EmergenceScoreProps) {
  // Clamp score between 0 and 100
  const clampedScore = Math.max(0, Math.min(100, score));

  // Color coding based on score
  const getColor = (s: number): string => {
    if (s >= 80) return "#ef4444"; // Red - strong signal
    if (s >= 60) return "#f59e0b"; // Orange - moderate signal
    if (s >= 40) return "#eab308"; // Yellow - weak signal
    return "#94a3b8"; // Gray - very weak
  };

  const getBackgroundColor = (s: number): string => {
    if (s >= 80) return "rgba(239, 68, 68, 0.1)";
    if (s >= 60) return "rgba(245, 158, 11, 0.1)";
    if (s >= 40) return "rgba(234, 179, 8, 0.1)";
    return "rgba(148, 163, 184, 0.1)";
  };

  const getLabel = (s: number): string => {
    if (s >= 80) return "Strong Signal";
    if (s >= 60) return "Moderate Signal";
    if (s >= 40) return "Weak Signal";
    return "Very Weak";
  };

  const color = getColor(clampedScore);
  const bgColor = getBackgroundColor(clampedScore);
  const label = getLabel(clampedScore);

  // Size variants
  const sizeStyles = {
    sm: {
      container: { padding: "0.375rem 0.625rem", gap: "0.375rem" },
      score: { fontSize: "0.875rem", fontWeight: "700" },
      label: { fontSize: "0.6875rem" },
      bar: { height: "3px", width: "40px" },
    },
    md: {
      container: { padding: "0.5rem 0.875rem", gap: "0.5rem" },
      score: { fontSize: "1.125rem", fontWeight: "700" },
      label: { fontSize: "0.75rem" },
      bar: { height: "4px", width: "60px" },
    },
    lg: {
      container: { padding: "0.75rem 1.125rem", gap: "0.625rem" },
      score: { fontSize: "1.5rem", fontWeight: "700" },
      label: { fontSize: "0.875rem" },
      bar: { height: "5px", width: "80px" },
    },
  };

  const styles = sizeStyles[size];

  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        ...styles.container,
        background: bgColor,
        borderRadius: "8px",
        border: `1px solid ${color}22`,
      }}
    >
      {/* Score number */}
      <span
        style={{
          ...styles.score,
          color,
          lineHeight: 1,
        }}
      >
        {Math.round(clampedScore)}
      </span>

      {/* Progress bar */}
      <div
        style={{
          ...styles.bar,
          background: "#e2e8f0",
          borderRadius: "2px",
          overflow: "hidden",
          position: "relative",
        }}
      >
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            bottom: 0,
            width: `${clampedScore}%`,
            background: color,
            transition: "width 0.3s ease",
          }}
        />
      </div>

      {/* Label */}
      {showLabel && (
        <span
          style={{
            ...styles.label,
            color: "#64748b",
            fontWeight: "500",
            whiteSpace: "nowrap",
          }}
        >
          {label}
        </span>
      )}
    </div>
  );
}
