"use client";

import { useState } from "react";

const PUBLICATION_TYPES = [
  "Clinical Trial",
  "Meta-Analysis",
  "Review",
  "Systematic Review",
  "RCT",
  "Case Reports",
  "Research Article",
];

const SPECIES_OPTIONS = ["Humans", "Mice", "Rats", "Escherichia coli"];

interface Article {
  pmid: string;
  title: string;
  abstract: string;
  journal: string;
  pub_date: string;
  authors: string[];
  mesh_terms: string[];
}

interface SearchResult {
  total: number;
  pmids: string[];
  articles: Article[];
  error?: string;
}

export default function PubMedPage() {
  const [query, setQuery] = useState("");
  const [maxResults, setMaxResults] = useState(10);
  const [mindate, setMindate] = useState("");
  const [maxdate, setMaxdate] = useState("");
  const [selectedPubTypes, setSelectedPubTypes] = useState<string[]>([]);
  const [journalsInput, setJournalsInput] = useState("");
  const [language, setLanguage] = useState("");
  const [selectedSpecies, setSelectedSpecies] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SearchResult | null>(null);
  const [expandedPmid, setExpandedPmid] = useState<string | null>(null);

  const togglePubType = (pt: string) =>
    setSelectedPubTypes((prev) =>
      prev.includes(pt) ? prev.filter((x) => x !== pt) : [...prev, pt]
    );

  const toggleSpecies = (sp: string) =>
    setSelectedSpecies((prev) =>
      prev.includes(sp) ? prev.filter((x) => x !== sp) : [...prev, sp]
    );

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setResult(null);

    const journals = journalsInput
      .split("\n")
      .map((j) => j.trim())
      .filter(Boolean);

    try {
      const res = await fetch("/api/pubmed", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          max_results: maxResults,
          mindate,
          maxdate,
          publication_types: selectedPubTypes.length ? selectedPubTypes : null,
          journals: journals.length ? journals : null,
          language: language || null,
          species: selectedSpecies.length ? selectedSpecies : null,
          fetch_details: true,
        }),
      });
      const data = await res.json();
      setResult(data);
    } catch (e) {
      setResult({ total: 0, pmids: [], articles: [], error: String(e) });
    } finally {
      setLoading(false);
    }
  };

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
            background: "rgba(167, 139, 250, 0.08)", display: "flex", alignItems: "center",
            justifyContent: "center", color: "#a78bfa",
          }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
          </div>
          <div>
            <h1 style={{ margin: 0, fontSize: "1.5rem", fontWeight: "700", color: "#0f172a" }}>
              PubMed Advanced Search
            </h1>
            <p style={{ margin: 0, fontSize: "0.875rem", color: "#64748b" }}>
              Search medical literature with advanced filters
            </p>
          </div>
        </div>
      </div>

      <div style={{ padding: "0 2rem 3rem", maxWidth: "1100px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: "1.5rem", alignItems: "start" }}>

          {/* Filters Panel */}
          <div className="medical-card" style={{ padding: "1.5rem", display: "flex", flexDirection: "column", gap: "1.25rem" }}>
            <h2 style={{ margin: 0, fontSize: "1rem", fontWeight: "600", color: "#0f172a" }}>
              Filters
            </h2>

            {/* Max Results */}
            <div>
              <label style={{ fontSize: "0.8125rem", fontWeight: "600", color: "#475569", display: "block", marginBottom: "0.375rem" }}>
                Max Results: {maxResults}
              </label>
              <input type="range" min={5} max={50} step={5} value={maxResults}
                onChange={(e) => setMaxResults(Number(e.target.value))}
                style={{ width: "100%", accentColor: "#a78bfa" }}
              />
            </div>

            {/* Date Range */}
            <div>
              <label style={{ fontSize: "0.8125rem", fontWeight: "600", color: "#475569", display: "block", marginBottom: "0.5rem" }}>
                Date Range
              </label>
              <div style={{ display: "flex", gap: "0.5rem" }}>
                <input className="medical-input" placeholder="From (YYYY)" value={mindate}
                  onChange={(e) => setMindate(e.target.value)}
                  style={{ fontSize: "0.8125rem", padding: "0.5rem 0.75rem" }}
                />
                <input className="medical-input" placeholder="To (YYYY)" value={maxdate}
                  onChange={(e) => setMaxdate(e.target.value)}
                  style={{ fontSize: "0.8125rem", padding: "0.5rem 0.75rem" }}
                />
              </div>
            </div>

            {/* Publication Types */}
            <div>
              <label style={{ fontSize: "0.8125rem", fontWeight: "600", color: "#475569", display: "block", marginBottom: "0.5rem" }}>
                Publication Types
              </label>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.375rem" }}>
                {PUBLICATION_TYPES.map((pt) => (
                  <button key={pt} onClick={() => togglePubType(pt)}
                    style={{
                      fontSize: "0.75rem", padding: "0.25rem 0.625rem", borderRadius: "9999px",
                      border: `1.5px solid ${selectedPubTypes.includes(pt) ? "#a78bfa" : "var(--medical-gray-200)"}`,
                      background: selectedPubTypes.includes(pt) ? "#ede9fe" : "transparent",
                      color: selectedPubTypes.includes(pt) ? "#a78bfa" : "#64748b",
                      cursor: "pointer", fontWeight: selectedPubTypes.includes(pt) ? "600" : "400",
                    }}>
                    {pt}
                  </button>
                ))}
              </div>
            </div>

            {/* Journals */}
            <div>
              <label style={{ fontSize: "0.8125rem", fontWeight: "600", color: "#475569", display: "block", marginBottom: "0.375rem" }}>
                Journals (one per line)
              </label>
              <textarea className="medical-input" rows={3} placeholder={"Nature\nScience\nCell"}
                value={journalsInput} onChange={(e) => setJournalsInput(e.target.value)}
                style={{ fontSize: "0.8125rem", resize: "vertical" }}
              />
            </div>

            {/* Language */}
            <div>
              <label style={{ fontSize: "0.8125rem", fontWeight: "600", color: "#475569", display: "block", marginBottom: "0.375rem" }}>
                Language
              </label>
              <select className="medical-input" value={language} onChange={(e) => setLanguage(e.target.value)}
                style={{ fontSize: "0.8125rem", padding: "0.5rem 0.75rem" }}>
                <option value="">All languages</option>
                <option value="eng">English</option>
                <option value="fre">French</option>
                <option value="ger">German</option>
                <option value="spa">Spanish</option>
              </select>
            </div>

            {/* Species */}
            <div>
              <label style={{ fontSize: "0.8125rem", fontWeight: "600", color: "#475569", display: "block", marginBottom: "0.5rem" }}>
                Species
              </label>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.375rem" }}>
                {SPECIES_OPTIONS.map((sp) => (
                  <button key={sp} onClick={() => toggleSpecies(sp)}
                    style={{
                      fontSize: "0.75rem", padding: "0.25rem 0.625rem", borderRadius: "9999px",
                      border: `1.5px solid ${selectedSpecies.includes(sp) ? "#a78bfa" : "var(--medical-gray-200)"}`,
                      background: selectedSpecies.includes(sp) ? "#ede9fe" : "transparent",
                      color: selectedSpecies.includes(sp) ? "#a78bfa" : "#64748b",
                      cursor: "pointer", fontWeight: selectedSpecies.includes(sp) ? "600" : "400",
                    }}>
                    {sp}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Search + Results */}
          <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
            {/* Search Bar */}
            <div className="medical-card" style={{ padding: "1.25rem" }}>
              <div style={{ display: "flex", gap: "0.75rem" }}>
                <input className="medical-input" placeholder='e.g. "CRISPR gene editing" or "cancer[MeSH] AND immunotherapy"'
                  value={query} onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                  style={{ flex: 1 }}
                />
                <button className="medical-button-primary" onClick={handleSearch} disabled={loading || !query.trim()}
                  style={{ padding: "0.75rem 1.5rem", whiteSpace: "nowrap", background: "#a78bfa", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  {loading ? (
                    <svg style={{ animation: "spin 1s linear infinite" }} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                    </svg>
                  ) : (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
                    </svg>
                  )}
                  {loading ? "Searching…" : "Search"}
                </button>
              </div>
            </div>

            {/* Results */}
            {result?.error && (
              <div className="medical-card" style={{ padding: "1.25rem", borderLeft: "4px solid var(--medical-error)" }}>
                <strong style={{ color: "var(--medical-error)" }}>Error:</strong> {result.error}
              </div>
            )}

            {result && !result.error && (
              <>
                {/* Stats */}
                <div style={{ display: "flex", gap: "1rem" }}>
                  {[
                    { label: "Total Results", value: result.total.toLocaleString() },
                    { label: "Fetched", value: result.articles.length },
                    { label: "PMIDs", value: result.pmids.length },
                  ].map((s) => (
                    <div key={s.label} className="medical-card" style={{ padding: "1rem 1.25rem", flex: 1, textAlign: "center" }}>
                      <div style={{ fontSize: "1.5rem", fontWeight: "700", color: "#a78bfa" }}>{s.value}</div>
                      <div style={{ fontSize: "0.75rem", color: "#64748b", marginTop: "2px" }}>{s.label}</div>
                    </div>
                  ))}
                </div>

                {/* Articles */}
                {result.articles.length > 0 ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                    {result.articles.map((article) => {
                      const isExpanded = expandedPmid === article.pmid;
                      return (
                        <div key={article.pmid} className="medical-card" style={{ padding: "1.25rem" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem" }}>
                            <div style={{ flex: 1 }}>
                              <h3 style={{ margin: "0 0 0.5rem 0", fontSize: "0.9375rem", fontWeight: "600", color: "#0f172a", lineHeight: "1.4" }}>
                                {article.title}
                              </h3>
                              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem", fontSize: "0.8125rem", color: "#64748b" }}>
                                <span>📰 {article.journal}</span>
                                {article.pub_date && <span>📅 {article.pub_date}</span>}
                                {article.authors?.length > 0 && (
                                  <span>👤 {article.authors.slice(0, 2).join(", ")}{article.authors.length > 2 ? " et al." : ""}</span>
                                )}
                                <a href={`https://pubmed.ncbi.nlm.nih.gov/${article.pmid}`} target="_blank" rel="noreferrer"
                                  style={{ color: "#a78bfa", fontWeight: "600", textDecoration: "none" }}>
                                  PMID: {article.pmid} ↗
                                </a>
                              </div>
                              {article.mesh_terms?.length > 0 && (
                                <div style={{ marginTop: "0.625rem", display: "flex", flexWrap: "wrap", gap: "0.25rem" }}>
                                  {article.mesh_terms.slice(0, 6).map((term) => (
                                    <span key={term} style={{
                                      fontSize: "0.6875rem", padding: "0.125rem 0.5rem", borderRadius: "9999px",
                                      background: "#ede9fe", color: "#a78bfa", fontWeight: "500",
                                    }}>{term}</span>
                                  ))}
                                </div>
                              )}
                            </div>
                            {article.abstract && (
                              <button onClick={() => setExpandedPmid(isExpanded ? null : article.pmid)}
                                style={{
                                  flexShrink: 0, fontSize: "0.75rem", padding: "0.375rem 0.75rem",
                                  borderRadius: "6px", border: "1.5px solid var(--medical-gray-200)",
                                  background: "transparent", cursor: "pointer", color: "#64748b",
                                }}>
                                {isExpanded ? "Hide" : "Abstract"}
                              </button>
                            )}
                          </div>
                          {isExpanded && article.abstract && (
                            <div style={{
                              marginTop: "1rem", paddingTop: "1rem", borderTop: "1px solid var(--medical-gray-200)",
                              fontSize: "0.875rem", color: "#475569", lineHeight: "1.7",
                            }}>
                              {article.abstract}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="medical-card" style={{ padding: "2rem", textAlign: "center", color: "#64748b" }}>
                    No articles found with current filters. Try broadening your search.
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
