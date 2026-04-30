"use client";

import { useAgentSteps } from "@/features/rag/hooks/use-agent-steps";
import MarkdownRenderer from "@/components/MarkdownRenderer";

export default function AgentStepsDisplay() {
  const { agentSteps, isDisplayingSteps } = useAgentSteps();

  if (agentSteps.length === 0 && !isDisplayingSteps) {
    return null;
  }

  return (
    <div style={{ marginTop: "1.5rem" }}>
      <div className="medical-card" style={{ padding: "1.5rem", borderLeft: "4px solid var(--medical-accent)" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <div style={{
              width: "36px",
              height: "36px",
              background: "linear-gradient(135deg, var(--medical-accent) 0%, var(--medical-primary) 100%)",
              borderRadius: "8px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center"
            }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="16" x2="12" y2="12" />
                <line x1="12" y1="8" x2="12.01" y2="8" />
              </svg>
            </div>
            <h3 style={{ fontSize: "1.125rem", fontWeight: "600", color: "var(--medical-gray-900)", margin: 0 }}>
              Reasoning Steps
            </h3>
          </div>
          {agentSteps.length > 0 && (
            <span className="medical-badge" style={{ background: "var(--medical-accent)", color: "white" }}>
              {agentSteps.length} step{agentSteps.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {agentSteps.map((step, index) => (
            <div
              key={index}
              className="animate-fadeIn"
              style={{
                padding: "1rem",
                background: "var(--medical-primary-light)",
                borderRadius: "8px",
                border: "1px solid var(--medical-primary)",
                transition: "all 0.2s ease"
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "var(--medical-primary-dark)";
                e.currentTarget.style.boxShadow = "0 2px 4px rgba(0, 102, 204, 0.1)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "var(--medical-primary)";
                e.currentTarget.style.boxShadow = "none";
              }}
            >
              <div style={{ display: "flex", alignItems: "start", gap: "0.75rem" }}>
                <span style={{
                  fontSize: "0.75rem",
                  fontWeight: "700",
                  color: "var(--medical-primary-dark)",
                  background: "white",
                  padding: "0.25rem 0.5rem",
                  borderRadius: "4px",
                  minWidth: "2rem",
                  textAlign: "center",
                  marginTop: "0.125rem"
                }}>
                  #{index + 1}
                </span>
                <div style={{ flex: 1, fontSize: "0.875rem", color: "var(--medical-gray-800)" }}>
                  <MarkdownRenderer content={step} />
                </div>
              </div>
            </div>
          ))}
          {isDisplayingSteps && (
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.75rem", fontSize: "0.875rem", color: "var(--medical-gray-600)" }}>
              <div style={{
                width: "16px",
                height: "16px",
                border: "2px solid var(--medical-gray-200)",
                borderTop: "2px solid var(--medical-accent)",
                borderRadius: "50%",
                animation: "spin 1s linear infinite"
              }}></div>
              <span>Analyzing...</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
