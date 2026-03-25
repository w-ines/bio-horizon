"use client";

import { useState } from "react";

// F2a: Standard entity types from spec
const ENTITY_TYPE_OPTIONS = [
  { label: "Disease", value: "DISEASE", color: "#dc2626", bg: "#fee2e2" },
  { label: "Drug", value: "DRUG", color: "#7c3aed", bg: "#ede9fe" },
  { label: "Gene", value: "GENE", color: "#0066cc", bg: "#e6f2ff" },
  { label: "Protein", value: "PROTEIN", color: "#059669", bg: "#d1fae5" },
  { label: "Anatomy", value: "ANATOMY", color: "#b45309", bg: "#fef3c7" },
  { label: "Chemical", value: "CHEMICAL", color: "#0891b2", bg: "#cffafe" },
  { label: "Oncology", value: "ONCOLOGY", color: "#ec4899", bg: "#fce7f3" },
];

// F2c: Assertion status colors
const ASSERTION_COLORS: Record<string, { color: string; bg: string }> = {
  PRESENT: { color: "#059669", bg: "#d1fae5" },
  NEGATED: { color: "#dc2626", bg: "#fee2e2" },
  HYPOTHETICAL: { color: "#f59e0b", bg: "#fef3c7" },
  HISTORICAL: { color: "#6b7280", bg: "#f3f4f6" },
};

const ENTITY_COLORS: Record<string, { color: string; bg: string }> = Object.fromEntries(
  ENTITY_TYPE_OPTIONS.map((e) => [e.value, { color: e.color, bg: e.bg }])
);

const EXAMPLE_TEXTS = [
  {
    label: "CRISPR abstract",
    text: "CRISPR-Cas9 gene editing was used to correct the DMD gene mutation causing Duchenne muscular dystrophy. Patients received AAV vector delivery with no significant hepatotoxicity observed.",
  },
  {
    label: "Oncology trial",
    text: "Pembrolizumab combined with carboplatin showed significant overall survival benefit in NSCLC patients with PD-L1 expression > 50%. Grade 3 adverse events included pneumonitis and colitis.",
  },
  {
    label: "Antibiotic resistance",
    text: "NDM-1 producing Escherichia coli isolates were recovered from patients in an ICU outbreak. Resistance to meropenem and imipenem was confirmed. Colistin remained the only active agent.",
  },
];

interface Entity {
  text: string;
  start?: number;
  end?: number;
  confidence?: number;
  label?: string;
  assertion_status?: string;  // F2c: PRESENT, NEGATED, HYPOTHETICAL, HISTORICAL
}

interface NerResult {
  entities: Record<string, Entity[]>;
  provider?: string;
  error?: string;
  custom_labels?: string[];  // F2b: Zero-shot custom labels
  assertion_enabled?: boolean;  // F2c: Whether assertion was computed
}

export default function NerPage() {
  const [text, setText] = useState("");
  const [selectedTypes, setSelectedTypes] = useState<string[]>(
    ENTITY_TYPE_OPTIONS.map((e) => e.value)
  );
  const [customLabels, setCustomLabels] = useState("");  // F2b: Custom zero-shot labels
  const [enableAssertion, setEnableAssertion] = useState(false);  // F2c: Assertion status
  const [provider, setProvider] = useState("gliner");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<NerResult | null>(null);

  const toggleType = (val: string) =>
    setSelectedTypes((prev) =>
      prev.includes(val) ? prev.filter((x) => x !== val) : [...prev, val]
    );

  const handleExtract = async () => {
    if (!text.trim()) return;
    setLoading(true);
    setResult(null);

    // Parse custom labels (F2b)
    const customLabelsArray = customLabels
      .split(",")
      .map((l) => l.trim().toUpperCase())
      .filter((l) => l.length > 0);

    try {
      const res = await fetch("/api/ner", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text,
          entity_types: customLabelsArray.length > 0 ? null : (selectedTypes.length ? selectedTypes : null),
          custom_labels: customLabelsArray.length > 0 ? customLabelsArray : null,
          enable_assertion: enableAssertion,
          provider,
        }),
      });
      const data = await res.json();
      setResult(data);
    } catch (e) {
      setResult({ entities: {}, error: String(e) });
    } finally {
      setLoading(false);
    }
  };

  const totalEntities = result
    ? Object.values(result.entities).reduce((sum, arr) => sum + arr.length, 0)
    : 0;

  return (
    <div style={{ minHeight: "100vh", background: "#f8fafc" }}>
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
            background: "rgba(251, 191, 36, 0.08)", display: "flex", alignItems: "center",
            justifyContent: "center", color: "#fbbf24",
          }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="4 7 4 4 20 4 20 7" />
              <line x1="9" y1="20" x2="15" y2="20" />
              <line x1="12" y1="4" x2="12" y2="20" />
            </svg>
          </div>
          <div>
            <h1 style={{ margin: 0, fontSize: "1.5rem", fontWeight: "700", color: "#0f172a" }}>
              NER Entity Extraction
            </h1>
            <p style={{ margin: 0, fontSize: "0.875rem", color: "#64748b" }}>
              Extract medical entities with assertion status • Standard + Zero-shot custom labels
            </p>
          </div>
        </div>
      </div>

      <div style={{ padding: "0 2rem 3rem", maxWidth: "1100px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "260px 1fr", gap: "1.5rem", alignItems: "start" }}>

          {/* Config Panel */}
          <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
            {/* Entity Types */}
            <div className="medical-card" style={{ padding: "1.25rem" }}>
              <h3 style={{ margin: "0 0 0.875rem 0", fontSize: "0.9375rem", fontWeight: "600", color: "#0f172a" }}>
                Entity Types
              </h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {ENTITY_TYPE_OPTIONS.map((et) => {
                  const active = selectedTypes.includes(et.value);
                  return (
                    <button key={et.value} onClick={() => toggleType(et.value)}
                      style={{
                        display: "flex", alignItems: "center", gap: "0.625rem",
                        padding: "0.5rem 0.75rem", borderRadius: "8px", cursor: "pointer",
                        border: `1.5px solid ${active ? et.color : "var(--medical-gray-200)"}`,
                        background: active ? et.bg : "transparent",
                        textAlign: "left", width: "100%",
                      }}>
                      <span style={{
                        width: "10px", height: "10px", borderRadius: "50%",
                        background: et.color, flexShrink: 0,
                      }} />
                      <span style={{
                        fontSize: "0.8125rem", fontWeight: active ? "600" : "400",
                        color: active ? et.color : "#64748b",
                      }}>
                        {et.label}
                      </span>
                    </button>
                  );
                })}
              </div>
              <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.75rem" }}>
                <button onClick={() => setSelectedTypes(ENTITY_TYPE_OPTIONS.map((e) => e.value))}
                  style={{ fontSize: "0.75rem", color: "#0066cc", background: "none", border: "none", cursor: "pointer", padding: 0 }}>
                  All
                </button>
                <span style={{ color: "var(--medical-gray-300)" }}>·</span>
                <button onClick={() => setSelectedTypes([])}
                  style={{ fontSize: "0.75rem", color: "#64748b", background: "none", border: "none", cursor: "pointer", padding: 0 }}>
                  None
                </button>
              </div>
            </div>

            {/* Provider */}
            <div className="medical-card" style={{ padding: "1.25rem" }}>
              <h3 style={{ margin: "0 0 0.75rem 0", fontSize: "0.9375rem", fontWeight: "600", color: "#0f172a" }}>
                NER Provider
              </h3>
              {["gliner", "openmed"].map((p) => (
                <button key={p} onClick={() => setProvider(p)}
                  style={{
                    display: "flex", alignItems: "center", gap: "0.625rem",
                    padding: "0.5rem 0.75rem", borderRadius: "8px", cursor: "pointer",
                    border: `1.5px solid ${provider === p ? "#fbbf24" : "var(--medical-gray-200)"}`,
                    background: provider === p ? "rgba(251, 191, 36, 0.08)" : "transparent",
                    width: "100%", textAlign: "left", marginBottom: "0.375rem",
                  }}>
                  <span style={{
                    width: "10px", height: "10px", borderRadius: "50%",
                    background: provider === p ? "#fbbf24" : "var(--medical-gray-300)", flexShrink: 0,
                  }} />
                  <span style={{
                    fontSize: "0.8125rem", fontWeight: provider === p ? "600" : "400",
                    color: provider === p ? "#fbbf24" : "#64748b",
                  }}>
                    {p === "gliner" ? "GliNER (local)" : "OpenMed (API)"}
                  </span>
                </button>
              ))}
            </div>

            {/* Examples */}
            <div className="medical-card" style={{ padding: "1.25rem" }}>
              <h3 style={{ margin: "0 0 0.75rem 0", fontSize: "0.9375rem", fontWeight: "600", color: "#0f172a" }}>
                Examples
              </h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {EXAMPLE_TEXTS.map((ex) => (
                  <button key={ex.label} onClick={() => setText(ex.text)}
                    style={{
                      padding: "0.5rem 0.75rem", borderRadius: "8px", cursor: "pointer",
                      border: "1.5px solid var(--medical-gray-200)", background: "transparent",
                      textAlign: "left", fontSize: "0.8125rem", color: "#64748b",
                    }}>
                    {ex.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Main Area */}
          <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
            {/* Text Input */}
            <div className="medical-card" style={{ padding: "1.25rem" }}>
              <label style={{ fontSize: "0.875rem", fontWeight: "600", color: "#0f172a", display: "block", marginBottom: "0.625rem" }}>
                Input Text
              </label>
              <textarea className="medical-input" rows={6}
                placeholder="Paste or type a medical abstract, clinical note, or any biomedical text…"
                value={text} onChange={(e) => setText(e.target.value)}
                style={{ resize: "vertical", fontSize: "0.9375rem", lineHeight: "1.6" }}
              />
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "0.875rem" }}>
                <span style={{ fontSize: "0.8125rem", color: "#64748b" }}>
                  {text.length} characters
                </span>
                <button className="medical-button-primary" onClick={handleExtract}
                  disabled={loading || !text.trim()}
                  style={{ background: "#fbbf24", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  {loading ? (
                    <svg style={{ animation: "spin 1s linear infinite" }} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                    </svg>
                  ) : (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="4 7 4 4 20 4 20 7" /><line x1="9" y1="20" x2="15" y2="20" /><line x1="12" y1="4" x2="12" y2="20" />
                    </svg>
                  )}
                  {loading ? "Extracting…" : "Extract Entities"}
                </button>
              </div>
            </div>

            {/* F2b: Custom Labels (Zero-shot NER) */}
            <div className="medical-card" style={{ padding: "1.25rem", background: "#f0fdf4", border: "1px solid #bbf7d0" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.625rem" }}>
                <span style={{ fontSize: "1.125rem" }}>🎯</span>
                <label style={{ fontSize: "0.875rem", fontWeight: "600", color: "#166534" }}>
                  Custom Labels (Zero-shot NER)
                </label>
              </div>
              <input
                type="text"
                className="medical-input"
                placeholder="e.g., BRAIN_REGION, BIOMARKER, COGNITIVE_FUNCTION"
                value={customLabels}
                onChange={(e) => setCustomLabels(e.target.value)}
                style={{ fontSize: "0.875rem" }}
              />
              <p style={{ fontSize: "0.75rem", color: "#15803d", marginTop: "0.5rem", marginBottom: 0 }}>
                Enter custom entity types (comma-separated). When provided, standard types are ignored.
              </p>
            </div>

            {/* F2c: Assertion Status */}
            <div className="medical-card" style={{ padding: "1.25rem", background: "#eff6ff", border: "1px solid #bfdbfe" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <span style={{ fontSize: "1.125rem" }}>🔍</span>
                  <label style={{ fontSize: "0.875rem", fontWeight: "600", color: "#1e40af" }}>
                    Enable Assertion Status
                  </label>
                </div>
                <button
                  onClick={() => setEnableAssertion(!enableAssertion)}
                  style={{
                    padding: "0.375rem 0.75rem",
                    borderRadius: "6px",
                    border: `1.5px solid ${enableAssertion ? "#3b82f6" : "#cbd5e1"}`,
                    background: enableAssertion ? "#3b82f6" : "white",
                    color: enableAssertion ? "white" : "#64748b",
                    fontSize: "0.8125rem",
                    fontWeight: "600",
                    cursor: "pointer",
                  }}
                >
                  {enableAssertion ? "ON" : "OFF"}
                </button>
              </div>
              <p style={{ fontSize: "0.75rem", color: "#1e40af", marginTop: "0.5rem", marginBottom: 0 }}>
                Qualify entities: PRESENT, NEGATED, HYPOTHETICAL, HISTORICAL
              </p>
            </div>

            {/* Error */}
            {result?.error && (
              <div className="medical-card" style={{ padding: "1.25rem", borderLeft: "4px solid var(--medical-error)" }}>
                <strong style={{ color: "var(--medical-error)" }}>Error:</strong> {result.error}
              </div>
            )}

            {/* Results */}
            {result && !result.error && (
              <>
                {/* Stats row */}
                <div style={{ display: "flex", gap: "1rem" }}>
                  <div className="medical-card" style={{ padding: "1rem 1.25rem", flex: 1, textAlign: "center" }}>
                    <div style={{ fontSize: "1.5rem", fontWeight: "700", color: "#fbbf24" }}>{totalEntities}</div>
                    <div style={{ fontSize: "0.75rem", color: "#64748b", marginTop: "2px" }}>Total Entities</div>
                  </div>
                  <div className="medical-card" style={{ padding: "1rem 1.25rem", flex: 1, textAlign: "center" }}>
                    <div style={{ fontSize: "1.5rem", fontWeight: "700", color: "#fbbf24" }}>
                      {Object.values(result.entities).filter((arr) => arr.length > 0).length}
                    </div>
                    <div style={{ fontSize: "0.75rem", color: "#64748b", marginTop: "2px" }}>Entity Types Found</div>
                  </div>
                  <div className="medical-card" style={{ padding: "1rem 1.25rem", flex: 1, textAlign: "center" }}>
                    <div style={{ fontSize: "1.5rem", fontWeight: "700", color: "#fbbf24" }}>
                      {result.provider || provider}
                    </div>
                    <div style={{ fontSize: "0.75rem", color: "#64748b", marginTop: "2px" }}>Provider</div>
                  </div>
                </div>

                {/* Entity groups */}
                {Object.entries(result.entities).length > 0 ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                    {Object.entries(result.entities)
                      .filter(([, arr]) => arr.length > 0)
                      .map(([type, entities]) => {
                        const style = ENTITY_COLORS[type] || { color: "#475569", bg: "#f1f5f9" };
                        return (
                          <div key={type} className="medical-card" style={{ padding: "1.25rem" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: "0.625rem", marginBottom: "0.875rem" }}>
                              <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: style.color, flexShrink: 0 }} />
                              <h3 style={{ margin: 0, fontSize: "0.9375rem", fontWeight: "600", color: style.color }}>
                                {type}
                              </h3>
                              <span style={{
                                fontSize: "0.6875rem", fontWeight: "700", padding: "0.125rem 0.5rem",
                                borderRadius: "9999px", background: style.bg, color: style.color,
                              }}>
                                {entities.length}
                              </span>
                            </div>
                            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                              {entities.map((ent, i) => {
                                const assertionStyle = ent.assertion_status 
                                  ? ASSERTION_COLORS[ent.assertion_status] 
                                  : null;
                                
                                return (
                                  <div key={i}
                                    title={ent.confidence ? `Confidence: ${(ent.confidence * 100).toFixed(0)}%` : undefined}
                                    style={{
                                      padding: "0.375rem 0.875rem", borderRadius: "9999px",
                                      background: style.bg, color: style.color,
                                      fontSize: "0.875rem", fontWeight: "500",
                                      border: `1px solid ${style.color}33`,
                                      display: "flex", alignItems: "center", gap: "0.375rem",
                                    }}>
                                    {ent.text}
                                    {ent.confidence && (
                                      <span style={{ fontSize: "0.6875rem", opacity: 0.7 }}>
                                        {(ent.confidence * 100).toFixed(0)}%
                                      </span>
                                    )}
                                    {/* F2c: Assertion Status Badge */}
                                    {ent.assertion_status && assertionStyle && (
                                      <span style={{
                                        fontSize: "0.625rem",
                                        fontWeight: "700",
                                        padding: "0.125rem 0.375rem",
                                        borderRadius: "4px",
                                        background: assertionStyle.bg,
                                        color: assertionStyle.color,
                                        border: `1px solid ${assertionStyle.color}`,
                                      }}>
                                        {ent.assertion_status.charAt(0)}
                                      </span>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        );
                      })}
                  </div>
                ) : (
                  <div className="medical-card" style={{ padding: "2rem", textAlign: "center", color: "#64748b" }}>
                    No entities found. Try different text or entity types.
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
