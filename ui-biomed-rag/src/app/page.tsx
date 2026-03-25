"use client";

import Link from "next/link";

const TOOLS = [
  {
    href: "/signals",
    label: "Emerging Signals",
    subtitle: "Temporal Detection",
    description: "Detect emerging trends in biomedical literature by comparing knowledge graphs over time. Track what's new.",
    accent: "#ef4444",
    accentSoft: "rgba(239, 68, 68, 0.08)",
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
        <polyline points="17 6 23 6 23 12" />
      </svg>
    ),
  },
  {
    href: "/timeline",
    label: "KG Timeline",
    subtitle: "Evolution Tracking",
    description: "Track the evolution of the knowledge graph over time. Compare snapshots and identify what changed.",
    accent: "#8b5cf6",
    accentSoft: "rgba(139, 92, 246, 0.08)",
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <line x1="12" y1="2" x2="12" y2="6" />
        <line x1="12" y1="18" x2="12" y2="22" />
        <line x1="4.93" y1="4.93" x2="7.76" y2="7.76" />
        <line x1="16.24" y1="16.24" x2="19.07" y2="19.07" />
        <line x1="2" y1="12" x2="6" y2="12" />
        <line x1="18" y1="12" x2="22" y2="12" />
        <line x1="4.93" y1="19.07" x2="7.76" y2="16.24" />
        <line x1="16.24" y1="7.76" x2="19.07" y2="4.93" />
      </svg>
    ),
  },
  {
    href: "/ask",
    label: "RAG Q&A",
    subtitle: "Literature Search",
    description: "Ask questions on medical literature and your own documents. Powered by retrieval-augmented generation.",
    accent: "#38bdf8",
    accentSoft: "rgba(56, 189, 248, 0.08)",
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
    ),
  },
  {
    href: "/knowledge-graph",
    label: "Knowledge Graph",
    subtitle: "Entity Relations",
    description: "Explore biomedical relationships: drugs, diseases, symptoms and genes connected in an interactive graph.",
    accent: "#34d399",
    accentSoft: "rgba(52, 211, 153, 0.08)",
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="3" /><circle cx="6" cy="6" r="2" /><circle cx="18" cy="6" r="2" />
        <circle cx="6" cy="18" r="2" /><circle cx="18" cy="18" r="2" />
        <line x1="9" y1="12" x2="6" y2="9" /><line x1="15" y1="12" x2="18" y2="9" />
        <line x1="9" y1="12" x2="6" y2="15" /><line x1="15" y1="12" x2="18" y2="15" />
      </svg>
    ),
  },
  {
    href: "/pubmed",
    label: "PubMed Search",
    subtitle: "Advanced Filters",
    description: "Search PubMed with advanced filters: publication types, journals, date ranges, language and species.",
    accent: "#a78bfa",
    accentSoft: "rgba(167, 139, 250, 0.08)",
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
      </svg>
    ),
  },
  {
    href: "/ner",
    label: "NER Entities",
    subtitle: "Entity Extraction",
    description: "Extract medical named entities from free text: diseases, drugs, genes, anatomy — powered by GliNER.",
    accent: "#fbbf24",
    accentSoft: "rgba(251, 191, 36, 0.08)",
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="4 7 4 4 20 4 20 7" /><line x1="9" y1="20" x2="15" y2="20" /><line x1="12" y1="4" x2="12" y2="20" />
      </svg>
    ),
  },
  {
    href: "/settings",
    label: "Settings",
    subtitle: "Automated Surveillance",
    description: "Configure watch topics for automated weekly snapshots and signal detection. Set it and forget it.",
    accent: "#64748b",
    accentSoft: "rgba(100, 116, 139, 0.08)",
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="3" />
        <path d="M12 1v6m0 6v6m-9-9h6m6 0h6" />
        <path d="M4.93 4.93l4.24 4.24m5.66 5.66l4.24 4.24m0-14.14l-4.24 4.24M9.17 14.83l-4.24 4.24" />
      </svg>
    ),
  },
];

export default function DashboardPage() {
  return (
    <div style={{ minHeight: "100vh", background: "#f8fafc", display: "flex", flexDirection: "column", alignItems: "center" }}>

      {/* Hero */}
      <div style={{
        width: "100%",
        maxWidth: "860px",
        padding: "3rem 2rem 2rem",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.875rem", marginBottom: "0.75rem" }}>
          <div style={{
            width: "42px", height: "42px",
            background: "linear-gradient(135deg, #38bdf8, #34d399)",
            borderRadius: "12px",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2v20M2 12h20" /><circle cx="12" cy="12" r="10" />
            </svg>
          </div>
          <h1 style={{
            fontSize: "1.625rem",
            fontWeight: "700",
            color: "#0f172a",
            margin: 0,
            letterSpacing: "-0.02em",
          }}>
            Bio Horizon
          </h1>
        </div>
        <p style={{
          color: "#475569",
          fontSize: "1rem",
          margin: 0,
          lineHeight: "1.65",
        }}>
          Biomedical intelligence platform — search literature, explore knowledge graphs, extract entities and query your documents with AI.
        </p>
      </div>

      {/* Cards */}
      <div style={{
        width: "100%",
        maxWidth: "860px",
        padding: "0 2rem 4rem",
      }}>
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(2, 1fr)",
          gap: "1rem",
        }}>
          {TOOLS.map((tool, i) => (
            <Link
              key={tool.href}
              href={tool.href}
              className="animate-fadeIn"
              style={{
                textDecoration: "none",
                color: "inherit",
                background: "white",
                borderRadius: "14px",
                border: "1px solid #e2e8f0",
                padding: "1.75rem",
                display: "flex",
                flexDirection: "column",
                gap: "1rem",
                transition: "border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease",
                animationDelay: `${i * 70}ms`,
                animationFillMode: "backwards",
                boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
                cursor: "pointer",
                position: "relative",
                overflow: "hidden",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = tool.accent;
                e.currentTarget.style.boxShadow = `0 8px 24px -6px ${tool.accent}28`;
                e.currentTarget.style.transform = "translateY(-2px)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "#e2e8f0";
                e.currentTarget.style.boxShadow = "0 1px 3px rgba(0,0,0,0.04)";
                e.currentTarget.style.transform = "translateY(0)";
              }}
            >
              {/* Accent top line */}
              <div style={{
                position: "absolute", top: 0, left: 0, right: 0,
                height: "3px",
                background: `linear-gradient(90deg, ${tool.accent}, ${tool.accent}44)`,
                borderRadius: "14px 14px 0 0",
              }} />

              {/* Icon + title row */}
              <div style={{ display: "flex", alignItems: "center", gap: "0.875rem" }}>
                <div style={{
                  width: "46px",
                  height: "46px",
                  background: tool.accentSoft,
                  borderRadius: "12px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                  color: tool.accent,
                }}>
                  {tool.icon}
                </div>
                <div style={{ flex: 1 }}>
                  <h2 style={{
                    fontSize: "1.0625rem",
                    fontWeight: "650",
                    color: "#0f172a",
                    margin: 0,
                    lineHeight: 1.25,
                  }}>
                    {tool.label}
                  </h2>
                  <span style={{
                    fontSize: "0.8125rem",
                    fontWeight: "500",
                    color: tool.accent,
                  }}>
                    {tool.subtitle}
                  </span>
                </div>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
                  <polyline points="9 18 15 12 9 6" />
                </svg>
              </div>

              {/* Description */}
              <p style={{
                fontSize: "0.9375rem",
                color: "#64748b",
                margin: 0,
                lineHeight: "1.65",
              }}>
                {tool.description}
              </p>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
