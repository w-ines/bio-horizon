"use client";

import { useState, useMemo, useCallback, useRef } from "react";
import dynamic from "next/dynamic";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

const MAX_FILE_SIZE_MB = 50;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;
const CHUNK_SIZE = 5000; // characters per chunk for NER processing

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
  const [fileName, setFileName] = useState<string | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [progress, setProgress] = useState<{ current: number; total: number } | null>(null);
  const [viewMode, setViewMode] = useState<"entities" | "graph">("entities");
  const graphRef = useRef<any>(null);

  const toggleType = (val: string) =>
    setSelectedTypes((prev) =>
      prev.includes(val) ? prev.filter((x) => x !== val) : [...prev, val]
    );

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setFileError(null);

    if (file.size > MAX_FILE_SIZE_BYTES) {
      setFileError(
        `Le fichier "${file.name}" fait ${(file.size / (1024 * 1024)).toFixed(1)} MB. La taille maximale autorisée est de ${MAX_FILE_SIZE_MB} MB.`
      );
      setFileName(null);
      e.target.value = "";
      return;
    }

    setFileName(file.name);
    
    // Handle PDF files
    if (file.type === "application/pdf" || file.name.endsWith(".pdf")) {
      try {
        // Dynamic import of PDF.js (client-side only)
        const pdfjsLib = await import("pdfjs-dist");
        
        // Configure worker with exact version
        pdfjsLib.GlobalWorkerOptions.workerSrc = "https://unpkg.com/pdfjs-dist@5.6.205/build/pdf.worker.min.mjs";
        
        const arrayBuffer = await file.arrayBuffer();
        const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
        let fullText = "";
        
        // Extract text from all pages
        for (let i = 1; i <= pdf.numPages; i++) {
          const page = await pdf.getPage(i);
          const textContent = await page.getTextContent();
          const pageText = textContent.items
            .map((item: any) => item.str)
            .join(" ");
          fullText += pageText + "\n\n";
        }
        
        setText(fullText.trim());
      } catch (error) {
        alert("Erreur lors de la lecture du PDF");
        console.error(error);
        setFileName(null);
      }
      return;
    }
    
    // Handle text files
    const reader = new FileReader();
    
    reader.onload = (event) => {
      const content = event.target?.result as string;
      setText(content);
    };
    
    reader.onerror = () => {
      alert("Erreur lors de la lecture du fichier");
      setFileName(null);
    };
    
    reader.readAsText(file);
  };

  const handleExtract = async () => {
    if (!text.trim()) return;
    setLoading(true);
    setResult(null);
    setProgress(null);

    // Parse custom labels (F2b)
    const customLabelsArray = customLabels
      .split(",")
      .map((l) => l.trim().toUpperCase())
      .filter((l) => l.length > 0);

    const entityTypesPayload = customLabelsArray.length > 0 ? null : (selectedTypes.length ? selectedTypes : null);
    const customLabelsPayload = customLabelsArray.length > 0 ? customLabelsArray : null;

    // Split text into chunks for large texts
    const chunks: string[] = [];
    const trimmed = text.trim();
    if (trimmed.length <= CHUNK_SIZE) {
      chunks.push(trimmed);
    } else {
      for (let i = 0; i < trimmed.length; i += CHUNK_SIZE) {
        // Try to split at sentence boundary (. ! ? \n) within last 200 chars
        let end = Math.min(i + CHUNK_SIZE, trimmed.length);
        if (end < trimmed.length) {
          const lookback = trimmed.substring(Math.max(end - 200, i), end);
          const lastSentence = Math.max(
            lookback.lastIndexOf(". "),
            lookback.lastIndexOf(".\n"),
            lookback.lastIndexOf("! "),
            lookback.lastIndexOf("? "),
          );
          if (lastSentence > 0) {
            end = Math.max(end - 200, i) + lastSentence + 1;
          }
        }
        chunks.push(trimmed.substring(i, end));
        // Move next start to actual end
        if (end > i + CHUNK_SIZE) break; // safety
        // Adjust next iteration start if we broke at a sentence
        if (end !== i + CHUNK_SIZE) {
          // Next chunk starts right after the sentence boundary
          i = end - CHUNK_SIZE; // will be incremented by CHUNK_SIZE in loop
        }
      }
    }

    const totalChunks = chunks.length;
    if (totalChunks > 1) {
      setProgress({ current: 0, total: totalChunks });
    }

    try {
      // Merged result across all chunks
      const mergedEntities: Record<string, Entity[]> = {};
      let lastProvider = provider;
      let lastError: string | undefined;

      for (let idx = 0; idx < chunks.length; idx++) {
        if (totalChunks > 1) {
          setProgress({ current: idx + 1, total: totalChunks });
        }

        const res = await fetch("/api/ner", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            text: chunks[idx],
            entity_types: entityTypesPayload,
            custom_labels: customLabelsPayload,
            enable_assertion: enableAssertion,
            provider,
          }),
        });
        const data: NerResult = await res.json();

        if (data.error) {
          lastError = data.error;
          continue;
        }
        if (data.provider) lastProvider = data.provider;

        // Merge entities: deduplicate by (type, text) pair
        for (const [type, entities] of Object.entries(data.entities)) {
          if (!mergedEntities[type]) mergedEntities[type] = [];
          for (const ent of entities) {
            const exists = mergedEntities[type].some(
              (e) => e.text.toLowerCase() === ent.text.toLowerCase()
            );
            if (!exists) {
              mergedEntities[type].push(ent);
            }
          }
        }
      }

      setResult({
        entities: mergedEntities,
        provider: lastProvider,
        error: lastError,
        custom_labels: customLabelsPayload || undefined,
        assertion_enabled: enableAssertion,
      });
    } catch (e) {
      setResult({ entities: {}, error: String(e) });
    } finally {
      setLoading(false);
      setProgress(null);
    }
  };

  const totalEntities = result
    ? Object.values(result.entities).reduce((sum, arr) => sum + arr.length, 0)
    : 0;

  // Build co-occurrence graph from NER results + original text
  const graphData = useMemo(() => {
    if (!result || !text) return { nodes: [], links: [] };

    // Collect all entities with their type
    const allEntities: { text: string; type: string }[] = [];
    for (const [type, entities] of Object.entries(result.entities)) {
      for (const ent of entities) {
        if (ent.text.trim()) allEntities.push({ text: ent.text, type });
      }
    }
    if (allEntities.length === 0) return { nodes: [], links: [] };

    // Split text into sentences
    const sentences = text.split(/[.!?\n]+/).filter((s) => s.trim().length > 10);

    // Build co-occurrence links: entities in same sentence
    const linkMap = new Map<string, number>();
    for (const sentence of sentences) {
      const lower = sentence.toLowerCase();
      const found = allEntities.filter((e) => lower.includes(e.text.toLowerCase()));
      for (let i = 0; i < found.length; i++) {
        for (let j = i + 1; j < found.length; j++) {
          if (found[i].text === found[j].text) continue;
          const key = [found[i].text, found[j].text].sort().join("|||");
          linkMap.set(key, (linkMap.get(key) || 0) + 1);
        }
      }
    }

    // Only keep entities that have at least one link
    const connectedEntities = new Set<string>();
    for (const key of linkMap.keys()) {
      const [a, b] = key.split("|||");
      connectedEntities.add(a);
      connectedEntities.add(b);
    }

    const nodes = allEntities
      .filter((e) => connectedEntities.has(e.text))
      .map((e) => {
        const style = ENTITY_COLORS[e.type] || { color: "#475569", bg: "#f1f5f9" };
        return { id: e.text, label: e.text, type: e.type, color: style.color };
      });

    // Deduplicate nodes by id
    const uniqueNodes = Array.from(new Map(nodes.map((n) => [n.id, n])).values());

    const links = Array.from(linkMap.entries()).map(([key, weight]) => {
      const [source, target] = key.split("|||");
      return { source, target, weight };
    });

    return { nodes: uniqueNodes, links };
  }, [result, text]);

  const paintNode = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const label = node.label || node.id;
    const fontSize = Math.max(12 / globalScale, 3);
    ctx.font = `600 ${fontSize}px Inter, sans-serif`;
    const textWidth = ctx.measureText(label).width;
    const padding = fontSize * 0.4;
    const boxWidth = textWidth + padding * 2;
    const boxHeight = fontSize + padding * 2;

    // Background pill
    ctx.fillStyle = node.color + "22";
    ctx.strokeStyle = node.color;
    ctx.lineWidth = 1.5 / globalScale;
    const r = boxHeight / 2;
    ctx.beginPath();
    ctx.roundRect(node.x - boxWidth / 2, node.y - boxHeight / 2, boxWidth, boxHeight, r);
    ctx.fill();
    ctx.stroke();

    // Label
    ctx.fillStyle = node.color;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(label, node.x, node.y);
  }, []);

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


            {/* Examples   
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
            </div>*/}
          </div>
          
          {/* Main Area */}
          <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
            {/* Text Input */}
            <div className="medical-card" style={{ padding: "1.25rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.625rem" }}>
                <label style={{ fontSize: "0.875rem", fontWeight: "600", color: "#0f172a" }}>
                  Input Text
                </label>
                <label style={{ 
                  fontSize: "0.8125rem", 
                  fontWeight: "600", 
                  color: "#3b82f6", 
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.375rem",
                  padding: "0.375rem 0.75rem",
                  borderRadius: "6px",
                  border: "1.5px solid #3b82f6",
                  background: "#eff6ff",
                }}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                  </svg>
                  Upload File
                  <input 
                    type="file" 
                    accept=".txt,.md,.csv,.pdf" 
                    onChange={handleFileUpload}
                    style={{ display: "none" }}
                  />
                </label>
              </div>
              {fileError && (
                <div style={{
                  fontSize: "0.8125rem",
                  color: "#dc2626",
                  background: "#fef2f2",
                  border: "1px solid #fecaca",
                  borderRadius: "8px",
                  padding: "0.75rem 1rem",
                  marginBottom: "0.625rem",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem",
                }}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#dc2626" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="8" x2="12" y2="12" />
                    <line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                  {fileError}
                </div>
              )}
              {fileName && !fileError && (
                <div style={{ 
                  fontSize: "0.75rem", 
                  color: "#059669", 
                  marginBottom: "0.5rem",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.375rem",
                }}>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                  </svg>
                  {fileName}
                </div>
              )}
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
              {/* Progress bar for chunked processing */}
              {progress && (
                <div style={{ marginTop: "0.75rem" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.375rem" }}>
                    <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
                      Traitement du chunk {progress.current}/{progress.total}
                    </span>
                    <span style={{ fontSize: "0.75rem", fontWeight: "600", color: "#fbbf24" }}>
                      {Math.round((progress.current / progress.total) * 100)}%
                    </span>
                  </div>
                  <div style={{
                    width: "100%", height: "6px", borderRadius: "3px",
                    background: "#e2e8f0", overflow: "hidden",
                  }}>
                    <div style={{
                      width: `${(progress.current / progress.total) * 100}%`,
                      height: "100%", borderRadius: "3px",
                      background: "linear-gradient(90deg, #fbbf24, #f59e0b)",
                      transition: "width 0.3s ease",
                    }} />
                  </div>
                </div>
              )}
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

                {/* View mode toggle */}
                <div style={{ display: "flex", gap: "0.5rem", justifyContent: "center" }}>
                  <button
                    onClick={() => setViewMode("entities")}
                    style={{
                      padding: "0.5rem 1.25rem", borderRadius: "8px", cursor: "pointer",
                      border: `1.5px solid ${viewMode === "entities" ? "#fbbf24" : "#e2e8f0"}`,
                      background: viewMode === "entities" ? "rgba(251,191,36,0.1)" : "white",
                      color: viewMode === "entities" ? "#b45309" : "#64748b",
                      fontWeight: viewMode === "entities" ? "600" : "400",
                      fontSize: "0.8125rem", display: "flex", alignItems: "center", gap: "0.375rem",
                    }}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="8" y1="6" x2="21" y2="6" /><line x1="8" y1="12" x2="21" y2="12" /><line x1="8" y1="18" x2="21" y2="18" />
                      <line x1="3" y1="6" x2="3.01" y2="6" /><line x1="3" y1="12" x2="3.01" y2="12" /><line x1="3" y1="18" x2="3.01" y2="18" />
                    </svg>
                    Entities
                  </button>
                  <button
                    onClick={() => setViewMode("graph")}
                    style={{
                      padding: "0.5rem 1.25rem", borderRadius: "8px", cursor: "pointer",
                      border: `1.5px solid ${viewMode === "graph" ? "#fbbf24" : "#e2e8f0"}`,
                      background: viewMode === "graph" ? "rgba(251,191,36,0.1)" : "white",
                      color: viewMode === "graph" ? "#b45309" : "#64748b",
                      fontWeight: viewMode === "graph" ? "600" : "400",
                      fontSize: "0.8125rem", display: "flex", alignItems: "center", gap: "0.375rem",
                    }}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="6" cy="6" r="3" /><circle cx="18" cy="6" r="3" /><circle cx="6" cy="18" r="3" /><circle cx="18" cy="18" r="3" />
                      <line x1="8.5" y1="7.5" x2="15.5" y2="16.5" /><line x1="15.5" y1="7.5" x2="8.5" y2="16.5" />
                    </svg>
                    Co-occurrence Graph
                  </button>
                </div>

                {/* Entities view */}
                {viewMode === "entities" && (
                  <>
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

                {/* Graph view */}
                {viewMode === "graph" && (
                  <div className="medical-card" style={{ padding: "1.25rem" }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.75rem" }}>
                      <h3 style={{ margin: 0, fontSize: "0.9375rem", fontWeight: "600", color: "#0f172a" }}>
                        Co-occurrence Graph
                      </h3>
                      <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
                        {graphData.nodes.length} nodes · {graphData.links.length} links
                      </span>
                    </div>
                    {graphData.nodes.length > 0 ? (
                      <>
                        {/* Legend */}
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem", marginBottom: "0.75rem" }}>
                          {ENTITY_TYPE_OPTIONS
                            .filter((t) => graphData.nodes.some((n: any) => n.type === t.value))
                            .map((t) => (
                              <div key={t.value} style={{ display: "flex", alignItems: "center", gap: "0.25rem", fontSize: "0.6875rem" }}>
                                <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: t.color }} />
                                <span style={{ color: "#64748b" }}>{t.label}</span>
                              </div>
                            ))}
                        </div>
                        <div style={{ border: "1px solid #e2e8f0", borderRadius: "8px", overflow: "hidden", background: "#fafbfc" }}>
                          <ForceGraph2D
                            ref={graphRef}
                            graphData={graphData}
                            width={700}
                            height={500}
                            nodeCanvasObject={paintNode}
                            nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D) => {
                              const fontSize = 12;
                              ctx.font = `600 ${fontSize}px Inter, sans-serif`;
                              const w = ctx.measureText(node.label || node.id).width + fontSize;
                              ctx.fillStyle = color;
                              ctx.fillRect(node.x - w / 2, node.y - fontSize, w, fontSize * 2);
                            }}
                            linkColor={() => "#cbd5e1"}
                            linkWidth={(link: any) => Math.min(link.weight || 1, 5)}
                            linkDirectionalParticles={0}
                            cooldownTicks={100}
                            d3AlphaDecay={0.04}
                            d3VelocityDecay={0.3}
                          />
                        </div>
                        <p style={{ fontSize: "0.6875rem", color: "#94a3b8", marginTop: "0.5rem", marginBottom: 0, textAlign: "center" }}>
                          Entities are linked when they co-occur in the same sentence. Drag to rearrange, scroll to zoom.
                        </p>
                      </>
                    ) : (
                      <div style={{ padding: "2rem", textAlign: "center", color: "#94a3b8", fontSize: "0.875rem" }}>
                        No co-occurrences found. Entities must appear together in the same sentence to form links.
                      </div>
                    )}
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
