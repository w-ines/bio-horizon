"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  {
    href: "/",
    label: "Dashboard",
    accent: "#94a3b8",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
      </svg>
    ),
  },
  {
    href: "/ask",
    label: "RAG Q&A",
    accent: "#38bdf8",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
    ),
  },
  {
    href: "/knowledge-graph",
    label: "Knowledge Graph",
    accent: "#34d399",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
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
    accent: "#a78bfa",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
      </svg>
    ),
  },
  {
    href: "/ner",
    label: "NER Entities",
    accent: "#fbbf24",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="4 7 4 4 20 4 20 7" /><line x1="9" y1="20" x2="15" y2="20" /><line x1="12" y1="4" x2="12" y2="20" />
      </svg>
    ),
  },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside style={{
      position: "fixed",
      top: 0,
      left: 0,
      width: "250px",
      height: "100vh",
      background: "white",
      borderRight: "1px solid #e2e8f0",
      display: "flex",
      flexDirection: "column",
      zIndex: 100,
      overflowY: "auto",
    }}>
      {/* Logo */}
      <Link href="/" style={{ textDecoration: "none", display: "block" }}>
        <div style={{
          padding: "1.375rem 1.25rem",
          display: "flex",
          alignItems: "center",
          gap: "0.875rem",
          cursor: "pointer",
        }}>
          <div style={{
            width: "38px",
            height: "38px",
            background: "linear-gradient(135deg, #38bdf8 0%, #34d399 100%)",
            borderRadius: "11px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
          }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2v20M2 12h20" />
              <circle cx="12" cy="12" r="10" />
            </svg>
          </div>
          <div>
            <div style={{ color: "#0f172a", fontWeight: "700", fontSize: "1rem", lineHeight: 1.2, letterSpacing: "-0.01em" }}>
              Bio Horizon
            </div>
            <div style={{ color: "#94a3b8", fontSize: "0.6875rem", marginTop: "3px", letterSpacing: "0.02em" }}>
              Biomedical Intelligence
            </div>
          </div>
        </div>
      </Link>

      {/* Divider */}
      <div style={{ height: "1px", background: "#e2e8f0", margin: "0 1rem" }} />

      {/* Nav */}
      <nav style={{ padding: "1.125rem 0.875rem", flex: 1 }}>
        <div style={{
          fontSize: "0.625rem",
          fontWeight: "700",
          color: "#94a3b8",
          letterSpacing: "0.12em",
          textTransform: "uppercase",
          padding: "0 0.625rem",
          marginBottom: "0.75rem",
        }}>
          Modules
        </div>
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          const accentSoft = `${item.accent}14`; // 8% opacity
          return (
            <Link
              key={item.href}
              href={item.href}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.75rem",
                padding: "0.6875rem 0.75rem",
                borderRadius: "10px",
                marginBottom: "3px",
                textDecoration: "none",
                color: isActive ? "#0f172a" : "#64748b",
                background: isActive ? "#f1f5f9" : "transparent",
                fontWeight: isActive ? "600" : "450",
                fontSize: "0.875rem",
                transition: "background-color 0.15s ease, color 0.15s ease",
                position: "relative",
              }}
            >
              {/* Active indicator */}
              {isActive && (
                <span style={{
                  position: "absolute",
                  left: "-0.875rem",
                  top: "50%",
                  transform: "translateY(-50%)",
                  width: "3px",
                  height: "20px",
                  borderRadius: "0 3px 3px 0",
                  background: item.accent,
                }} />
              )}
              <span style={{
                width: "32px",
                height: "32px",
                borderRadius: "8px",
                background: accentSoft,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
                color: item.accent,
                transition: "background-color 0.15s ease",
              }}>
                {item.icon}
              </span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div style={{
        padding: "1rem 1.25rem",
        borderTop: "1px solid #e2e8f0",
        display: "flex",
        alignItems: "center",
        gap: "0.5rem",
      }}>
        <div style={{
          width: "6px",
          height: "6px",
          borderRadius: "50%",
          background: "#34d399",
          flexShrink: 0,
        }} />
        <span style={{ fontSize: "0.6875rem", color: "#94a3b8", letterSpacing: "0.02em" }}>
          Med Assist · CNRS
        </span>
      </div>
    </aside>
  );
}
