"use client";

import { useEffect, useState, useCallback, useRef, useMemo } from "react";
import dynamic from "next/dynamic";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
});

interface Article {
  pmid: string;
  title: string;
  journal: string;
  pub_date: string;
  authors: string[];
  pmc_id?: string;
  doi?: string;
  pubmed_url?: string;
  pdf_url?: string;
}

interface Job {
  job_id: string;
  query: string;
  status: string;
  created_at: string;
  entities_extracted: number;
}

interface Node {
  id: string;
  label: string;
  type: string;
  frequency: number;
  degree: number;
  sources?: string[];
  source_count?: number;
  job_ids?: string[];
}

interface Link {
  source: string;
  target: string;
  weight: number;
  relation_type: string;
  sources?: string[];
  source_count?: number;
  job_ids?: string[];
}

interface GraphData {
  nodes: Node[];
  links: Link[];
  stats: {
    total_nodes: number;
    total_edges: number;
    filtered: boolean;
    job_ids_filter?: string[] | null;
  };
}

const RELATION_COLORS: Record<string, string> = {
  activates:       "#16a34a",
  inhibits:        "#dc2626",
  converts:        "#7c3aed",
  causes:          "#ea580c",
  treats:          "#2563eb",
  associated_with: "#0891b2",
  interacts_with:  "#db2777",
  located_in:      "#92400e",
  binds:           "#4f46e5",
  predisposes:     "#ca8a04",
  cotreatment:     "#65a30d",
  expressed_in:    "#0e7490",
};

const ENTITY_COLORS: Record<string, string> = {
  DRUG:    "#72C4BE",
  DISEASE: "#F07068",
  SYMPTOM: "#F0A347",
  GENE:    "#A8CC60",
  PROTEIN: "#C3B7DA",
  ANATOMY: "#6B9FBD",
  UNKNOWN: "#F5F580",
};

export function KnowledgeGraphViewer() {
  const [graphData, setGraphData] = useState<GraphData>({
    nodes: [],
    links: [],
    stats: { total_nodes: 0, total_edges: 0, filtered: false },
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [selectedArticles, setSelectedArticles] = useState<Article[]>([]);
  const [articlesLoading, setArticlesLoading] = useState(false);
  const [showAllRelations, setShowAllRelations] = useState(false);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJobIds, setSelectedJobIds] = useState<Set<string>>(new Set());
  const [filters, setFilters] = useState({
    entityType: "",
    maxNodes: 100,
    minFrequency: 1,
  });

  const fgRef = useRef<any>(null);

  // Fetch available jobs on mount
  useEffect(() => {
    async function fetchJobs() {
      try {
        const res = await fetch("http://localhost:8000/jobs");
        const data = await res.json();
        const completedJobs = (data.jobs || data || []).filter(
          (j: Job) => j.status === "completed" || j.status === "running"
        );
        setJobs(completedJobs);
      } catch {
        setJobs([]);
      }
    }
    fetchJobs();
  }, []);

  const toggleJobId = (jobId: string) => {
    setSelectedJobIds((prev) => {
      const next = new Set(prev);
      if (next.has(jobId)) {
        next.delete(jobId);
      } else {
        next.add(jobId);
      }
      return next;
    });
  };

  const fetchArticles = useCallback(async (pmids: string[]) => {
    if (!pmids.length) {
      setSelectedArticles([]);
      return;
    }
    setArticlesLoading(true);
    try {
      const response = await fetch(
        `http://localhost:8000/kg/articles?pmids=${pmids.slice(0, 10).join(",")}&limit=10`
      );
      const data = await response.json();
      setSelectedArticles(data.articles || []);
    } catch {
      setSelectedArticles([]);
    } finally {
      setArticlesLoading(false);
    }
  }, []);

  const fetchGraphData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      if (filters.entityType) params.append("entity_type", filters.entityType);
      params.append("max_nodes", filters.maxNodes.toString());
      params.append("min_frequency", filters.minFrequency.toString());
      if (selectedJobIds.size > 0) {
        params.append("job_ids", Array.from(selectedJobIds).join(","));
      }

      const response = await fetch(
        `http://localhost:8000/kg/graph?${params.toString()}`
      );
      const data = await response.json();

      if ('error' in data) {
        setError(data.error);
        setGraphData({ nodes: [], links: [], stats: { total_nodes: 0, total_edges: 0, filtered: false } });
      } else {
        setGraphData(data as GraphData);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch graph data");
      setGraphData({ nodes: [], links: [], stats: { total_nodes: 0, total_edges: 0, filtered: false } });
    } finally {
      setLoading(false);
    }
  }, [filters, selectedJobIds]);

  useEffect(() => {
    fetchGraphData();
  }, [fetchGraphData]);

  const handleNodeClick = useCallback((node: any) => {
    setSelectedNode(node);
    setSelectedArticles([]);
    setShowAllRelations(false);
    // Fetch source articles for this node
    if (node.sources && node.sources.length > 0) {
      fetchArticles(node.sources);
    }
    // Center on node
    if (fgRef.current) {
      fgRef.current.centerAt(node.x, node.y, 1000);
      fgRef.current.zoom(2, 1000);
    }
  }, [fetchArticles]);

  const getNodeColor = (node: Node) => {
    return ENTITY_COLORS[node.type] || ENTITY_COLORS.UNKNOWN;
  };

  const getNodeSize = (node: Node) => {
    // Screen-pixel radius (frequency-based). Used for both physics and canvas.
    return Math.min(48, Math.max(22, 22 + (node.frequency || 1) * 2));
  };

  const getLinkWidth = (link: Link) => {
    // Width based on weight (min 1, max 5)
    return Math.min(5, Math.max(1, link.weight * 0.5));
  };

  const mergedGraphData = useMemo((): GraphData => {
    if (!graphData?.links) return graphData;
    const linkMap = new Map<string, any>();
    for (const link of graphData.links) {
      const src = typeof link.source === "object" ? (link.source as any).id : link.source;
      const tgt = typeof link.target === "object" ? (link.target as any).id : link.target;
      const key = [src, tgt].sort().join("|||");
      if (linkMap.has(key)) {
        const existing = linkMap.get(key)!;
        const types: string[] = existing._relationTypes;
        const rel = link.relation_type || "";
        if (rel && !types.includes(rel)) {
          types.push(rel);
          existing.relation_type = types.join("+");
        }
        existing.weight = Math.max(existing.weight, link.weight);
      } else {
        const rel = link.relation_type || "";
        linkMap.set(key, { ...link, _relationTypes: rel ? [rel] : [] });
      }
    }
    return { ...graphData, links: Array.from(linkMap.values()) as Link[] };
  }, [graphData]);

  const getLinkColor = (link: any): string => {
    const rel: string = link.relation_type || "";
    if (rel.includes("+")) return "#94a3b8";
    return RELATION_COLORS[rel] || "#94a3b8";
  };

  const getNodeRadiusPx = (node: any, ctx: CanvasRenderingContext2D, globalScale: number): number => {
    const FONT_PX = 11;
    const fontSize = FONT_PX / globalScale;
    ctx.font = `600 ${fontSize}px Sans-Serif`;
    const textWidthPx = ctx.measureText(node.label || "").width * globalScale;
    const freqBonusPx = Math.min(25, (node.frequency || 1) * 2);
    return Math.max(22 + freqBonusPx, textWidthPx / 2 + 10);
  };

  const selectedNodeRelations = useMemo(() => {
    if (!selectedNode || !mergedGraphData?.links) return [];
    const nodeId = selectedNode.id;
    return mergedGraphData.links.flatMap((l: any) => {
      const src = typeof l.source === "object" ? l.source.id : l.source;
      const tgt = typeof l.target === "object" ? l.target.id : l.target;
      const srcLabel = typeof l.source === "object" ? (l.source.label || l.source.id) : l.source;
      const tgtLabel = typeof l.target === "object" ? (l.target.label || l.target.id) : l.target;
      if (src === nodeId) return [{ subject: selectedNode.label, relation: l.relation_type || "", object: tgtLabel }];
      if (tgt === nodeId) return [{ subject: srcLabel, relation: l.relation_type || "", object: selectedNode.label }];
      return [];
    });
  }, [selectedNode, mergedGraphData]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen" style={{ background: "var(--background)" }}>
        <div className="text-center">
          <div style={{
            width: "48px",
            height: "48px",
            border: "3px solid var(--medical-gray-200)",
            borderTop: "3px solid var(--medical-primary)",
            borderRadius: "50%",
            animation: "spin 1s linear infinite",
            margin: "0 auto 1rem"
          }}></div>
          <p style={{ color: "var(--medical-gray-600)", fontSize: "0.9375rem" }}>Loading medical graph...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen" style={{ background: "var(--background)" }}>
        <div className="medical-card" style={{ padding: "2rem", maxWidth: "28rem", background: "#fef2f2", borderColor: "#fecaca" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1rem" }}>
            <div style={{
              width: "40px",
              height: "40px",
              background: "var(--medical-error)",
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0
            }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            </div>
            <h3 style={{ fontSize: "1.125rem", fontWeight: "600", color: "#991b1b", margin: 0 }}>Loading Error</h3>
          </div>
          <p style={{ color: "#dc2626", fontSize: "0.875rem", marginBottom: "1.5rem" }}>{error}</p>
          <button
            onClick={fetchGraphData}
            className="medical-button-primary"
            style={{ width: "100%", background: "var(--medical-error)" }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen" style={{ background: "var(--background)" }}>
      {/* Header */}
      <div className="medical-card" style={{ 
        borderRadius: 0, 
        borderLeft: "none", 
        borderRight: "none", 
        borderTop: "none",
        borderBottom: "4px solid var(--medical-primary)",
        padding: "1.5rem 2rem"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "0.5rem" }}>
          <div style={{
            width: "48px",
            height: "48px",
            background: "linear-gradient(135deg, var(--medical-primary) 0%, var(--medical-secondary) 100%)",
            borderRadius: "12px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 4px 6px -1px rgba(0, 102, 204, 0.2)"
          }}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3" />
              <circle cx="6" cy="6" r="2" />
              <circle cx="18" cy="6" r="2" />
              <circle cx="6" cy="18" r="2" />
              <circle cx="18" cy="18" r="2" />
              <line x1="9" y1="12" x2="6" y2="9" />
              <line x1="15" y1="12" x2="18" y2="9" />
              <line x1="9" y1="12" x2="6" y2="15" />
              <line x1="15" y1="12" x2="18" y2="15" />
            </svg>
          </div>
          <div>
            <h1 style={{ fontSize: "1.75rem", fontWeight: "700", color: "var(--medical-gray-900)", margin: 0, letterSpacing: "-0.025em" }}>
              Medical Knowledge Graph
            </h1>
            <p style={{ fontSize: "0.875rem", color: "var(--medical-gray-600)", margin: "0.25rem 0 0 0" }}>
              {graphData?.stats?.total_nodes || 0} entities • {graphData?.stats?.total_edges || 0} relationships
            </p>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="medical-card" style={{ 
        borderRadius: 0, 
        borderLeft: "none", 
        borderRight: "none", 
        borderTop: "none",
        borderBottom: "1px solid var(--medical-gray-200)",
        padding: "1rem 2rem",
        display: "flex",
        gap: "1.5rem",
        alignItems: "center",
        flexWrap: "wrap"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <label style={{ fontSize: "0.875rem", fontWeight: "600", color: "var(--medical-gray-700)" }}>Entity Type:</label>
          <select
            value={filters.entityType}
            onChange={(e) => setFilters({ ...filters, entityType: e.target.value })}
            style={{
              border: "2px solid var(--medical-gray-200)",
              borderRadius: "6px",
              padding: "0.375rem 0.75rem",
              fontSize: "0.875rem",
              background: "white",
              color: "var(--foreground)",
              cursor: "pointer"
            }}
          >
            <option value="">All</option>
            <option value="DRUG">Drug</option>
            <option value="DISEASE">Disease</option>
            <option value="SYMPTOM">Symptom</option>
            <option value="GENE">Gene</option>
            <option value="PROTEIN">Protein</option>
            <option value="ANATOMY">Anatomy</option>
          </select>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <label style={{ fontSize: "0.875rem", fontWeight: "600", color: "var(--medical-gray-700)" }}>Max Nodes:</label>
          <input
            type="number"
            value={filters.maxNodes}
            onChange={(e) => setFilters({ ...filters, maxNodes: parseInt(e.target.value) || 100 })}
            style={{
              border: "2px solid var(--medical-gray-200)",
              borderRadius: "6px",
              padding: "0.375rem 0.75rem",
              fontSize: "0.875rem",
              width: "5rem",
              background: "white",
              color: "var(--foreground)"
            }}
            min="10"
            max="500"
          />
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <label style={{ fontSize: "0.875rem", fontWeight: "600", color: "var(--medical-gray-700)" }}>Min Frequency:</label>
          <input
            type="number"
            value={filters.minFrequency}
            onChange={(e) => setFilters({ ...filters, minFrequency: parseInt(e.target.value) || 1 })}
            style={{
              border: "2px solid var(--medical-gray-200)",
              borderRadius: "6px",
              padding: "0.375rem 0.75rem",
              fontSize: "0.875rem",
              width: "5rem",
              background: "white",
              color: "var(--foreground)"
            }}
            min="1"
            max="10"
          />
        </div>

        <button
          onClick={fetchGraphData}
          className="medical-button-primary"
          style={{ marginLeft: "auto", padding: "0.5rem 1rem", fontSize: "0.875rem" }}
        >
          Refresh
        </button>
      </div>

      {/* Job Filter */}
      {jobs.length > 0 && (
        <div className="medical-card" style={{
          borderRadius: 0,
          borderLeft: "none",
          borderRight: "none",
          borderTop: "none",
          borderBottom: "1px solid var(--medical-gray-200)",
          padding: "0.75rem 2rem",
          display: "flex",
          gap: "1rem",
          alignItems: "center",
          flexWrap: "wrap",
          fontSize: "0.8125rem"
        }}>
          <span style={{ fontWeight: "600", color: "var(--medical-gray-700)", whiteSpace: "nowrap" }}>Filter by Job:</span>
          {jobs.map((job) => (
            <label
              key={job.job_id}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.375rem",
                cursor: "pointer",
                padding: "0.25rem 0.625rem",
                borderRadius: "6px",
                border: selectedJobIds.has(job.job_id)
                  ? "2px solid var(--medical-primary)"
                  : "2px solid var(--medical-gray-200)",
                background: selectedJobIds.has(job.job_id)
                  ? "rgba(0, 102, 204, 0.05)"
                  : "white",
                transition: "all 0.15s ease",
              }}
            >
              <input
                type="checkbox"
                checked={selectedJobIds.has(job.job_id)}
                onChange={() => toggleJobId(job.job_id)}
                style={{ accentColor: "var(--medical-primary)" }}
              />
              <span style={{ fontWeight: "500", color: "var(--medical-gray-800)" }}>
                {job.query}
              </span>
              <span style={{ color: "var(--medical-gray-500)", fontSize: "0.6875rem" }}>
                ({job.entities_extracted} ent.)
              </span>
              {job.status === "running" && (
                <span style={{ color: "#f59e0b", fontSize: "0.6875rem", fontWeight: "600" }}>Running</span>
              )}
            </label>
          ))}
          {selectedJobIds.size > 0 && (
            <button
              onClick={() => setSelectedJobIds(new Set())}
              style={{
                background: "none",
                border: "1px solid var(--medical-gray-300)",
                borderRadius: "4px",
                padding: "0.25rem 0.5rem",
                fontSize: "0.75rem",
                color: "var(--medical-gray-600)",
                cursor: "pointer",
              }}
            >
              Clear filter
            </button>
          )}
        </div>
      )}

      {/* Legend */}
      <div className="medical-card" style={{
        borderRadius: 0,
        borderLeft: "none",
        borderRight: "none",
        borderTop: "none",
        borderBottom: "1px solid var(--medical-gray-200)",
        padding: "0.5rem 2rem",
        display: "flex",
        flexDirection: "column",
        gap: "0.4rem",
        fontSize: "0.8125rem"
      }}>
        {/* Entity types row */}
        <div style={{ display: "flex", gap: "1.25rem", alignItems: "center", flexWrap: "wrap" }}>
          <span style={{ fontWeight: "600", color: "var(--medical-gray-700)", minWidth: "4.5rem" }}>Entities:</span>
          {Object.entries(ENTITY_COLORS).map(([type, color]) => {
            const labels: Record<string, string> = {
              DRUG: "Drug", DISEASE: "Disease", SYMPTOM: "Symptom",
              GENE: "Gene", PROTEIN: "Protein", ANATOMY: "Anatomy", UNKNOWN: "Unknown"
            };
            return (
              <div key={type} style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
                <div style={{ width: "12px", height: "12px", borderRadius: "50%", backgroundColor: color, boxShadow: "0 1px 2px rgba(0,0,0,0.1)" }}></div>
                <span style={{ color: "var(--medical-gray-600)" }}>{labels[type] || type}</span>
              </div>
            );
          })}
        </div>
        {/* Relation types row — only shows types present in current graph */}
        {mergedGraphData?.links?.length > 0 && (
          <div style={{ display: "flex", gap: "1rem", alignItems: "center", flexWrap: "wrap" }}>
            <span style={{ fontWeight: "600", color: "var(--medical-gray-700)", minWidth: "4.5rem" }}>Relations:</span>
            {Object.entries(RELATION_COLORS)
              .filter(([rel]) =>
                mergedGraphData.links.some((l: any) => {
                  const r: string = l.relation_type || "";
                  return r === rel || r.split("+").includes(rel);
                })
              )
              .map(([rel, color]) => (
                <div key={rel} style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
                  <svg width="22" height="8" viewBox="0 0 22 8" style={{ flexShrink: 0 }}>
                    <line x1="0" y1="4" x2="15" y2="4" stroke={color} strokeWidth="2"/>
                    <polygon points="15,1 22,4 15,7" fill={color}/>
                  </svg>
                  <span style={{ color: "var(--medical-gray-600)", fontSize: "0.75rem" }}>
                    {rel.replace(/_/g, " ")}
                  </span>
                </div>
              ))}
            <span style={{ color: "var(--medical-gray-400)", fontSize: "0.7rem", marginLeft: "0.5rem" }}>
              (zoom in to see labels on arrows)
            </span>
          </div>
        )}
      </div>

      {/* Graph Container */}
      <div className="flex-1 relative">
        {!graphData || !graphData.nodes || graphData.nodes.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="medical-card" style={{ padding: "2rem", textAlign: "center", maxWidth: "28rem" }}>
              <div style={{
                width: "64px",
                height: "64px",
                background: "var(--medical-gray-100)",
                borderRadius: "50%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                margin: "0 auto 1rem"
              }}>
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--medical-gray-400)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="16" x2="12" y2="12" />
                  <line x1="12" y1="8" x2="12.01" y2="8" />
                </svg>
              </div>
              <p style={{ color: "var(--medical-gray-700)", marginBottom: "0.5rem", fontSize: "1rem", fontWeight: "600" }}>No entities in the graph</p>
              <p style={{ fontSize: "0.875rem", color: "var(--medical-gray-600)" }}>
                Import documents or PubMed articles to populate the knowledge graph
              </p>
            </div>
          </div>
        ) : (
          <ForceGraph2D
            ref={fgRef}
            graphData={mergedGraphData}
            nodeLabel={(node: any) => `${node.label} (${node.type})\nFrequency: ${node.frequency}`}
            nodeColor={(node: any) => getNodeColor(node)}
            nodeVal={(node: any) => (getNodeSize(node) / 4) ** 2}
            linkWidth={(link: any) => getLinkWidth(link)}
            linkColor={(link: any) => getLinkColor(link)}
            linkDirectionalParticles={2}
            linkDirectionalParticleWidth={2}
            linkDirectionalParticleColor={(link: any) => getLinkColor(link)}
            linkCanvasObjectMode={() => "after"}
            linkCanvasObject={(link: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
              if (globalScale < 1.5) return;
              const start = link.source;
              const end = link.target;
              if (!start || !end || typeof start.x !== "number") return;
              const midX = (start.x + end.x) / 2;
              const midY = (start.y + end.y) / 2;
              const label = (link.relation_type || "").replace(/_/g, " ");
              if (!label) return;
              const fontSize = Math.max(2, 8 / globalScale);
              ctx.font = `${fontSize}px Sans-Serif`;
              const textWidth = ctx.measureText(label).width;
              const padding = fontSize * 0.35;
              ctx.fillStyle = "rgba(255,255,255,0.88)";
              ctx.fillRect(midX - textWidth / 2 - padding, midY - fontSize / 2 - padding, textWidth + padding * 2, fontSize + padding * 2);
              ctx.textAlign = "center";
              ctx.textBaseline = "middle";
              ctx.fillStyle = getLinkColor(link);
              ctx.fillText(label, midX, midY);
            }}
            onNodeClick={handleNodeClick}
            backgroundColor="#f9fafb"
            nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
              const radius = getNodeRadiusPx(node, ctx, globalScale) / globalScale;
              const fontSize = 11 / globalScale;
              ctx.font = `600 ${fontSize}px Sans-Serif`;

              ctx.beginPath();
              ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
              ctx.fillStyle = getNodeColor(node);
              ctx.fill();
              ctx.strokeStyle = "rgba(255,255,255,0.55)";
              ctx.lineWidth = 0.8 / globalScale;
              ctx.stroke();

              ctx.textAlign = "center";
              ctx.textBaseline = "middle";
              ctx.fillStyle = "#1f2937";
              ctx.fillText(node.label, node.x, node.y);
            }}
            nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D, globalScale: number) => {
              const radius = getNodeRadiusPx(node, ctx, globalScale) / globalScale;
              ctx.fillStyle = color;
              ctx.beginPath();
              ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
              ctx.fill();
            }}
          />
        )}
      </div>

      {/* Selected Node Details + Source Articles */}
      {selectedNode && (
        <div className="medical-card animate-slideInRight" style={{
          position: "absolute",
          top: "1.5rem",
          right: "1.5rem",
          bottom: "1.5rem",
          padding: "0",
          width: "24rem",
          boxShadow: "var(--card-shadow-lg)",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}>
          {/* Header */}
          <div style={{ padding: "1.25rem 1.5rem", borderBottom: "1px solid var(--medical-gray-200)", flexShrink: 0 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", marginBottom: "0.75rem" }}>
              <h3 style={{ fontSize: "1.125rem", fontWeight: "600", color: "var(--medical-gray-900)", margin: 0 }}>{selectedNode.label}</h3>
              <button
                onClick={() => { setSelectedNode(null); setSelectedArticles([]); }}
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--medical-gray-400)",
                  cursor: "pointer",
                  padding: "0.25rem",
                  fontSize: "1.25rem",
                  lineHeight: 1
                }}
              >
                ✕
              </button>
            </div>
            <div style={{ display: "flex", gap: "1rem", fontSize: "0.8125rem" }}>
              <span
                style={{
                  backgroundColor: getNodeColor(selectedNode),
                  color: "white",
                  padding: "0.125rem 0.5rem",
                  borderRadius: "4px",
                  fontWeight: "600",
                  fontSize: "0.75rem",
                }}
              >
                {selectedNode.type}
              </span>
              <span style={{ color: "var(--medical-gray-600)" }}>
                Freq: <strong style={{ color: "var(--medical-gray-900)" }}>{selectedNode.frequency}</strong>
              </span>
              <span style={{ color: "var(--medical-gray-600)" }}>
                Links: <strong style={{ color: "var(--medical-gray-900)" }}>{selectedNode.degree}</strong>
              </span>
            </div>
          </div>

          {/* Relations */}
          {selectedNodeRelations.length > 0 && (
            <div style={{ padding: "0.75rem 1.5rem", borderBottom: "1px solid var(--medical-gray-200)", flexShrink: 0 }}>
              <h4 style={{ fontSize: "0.8125rem", fontWeight: "600", color: "var(--medical-gray-700)", margin: "0 0 0.5rem 0", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                Relations Extracted
                <span style={{ background: "var(--medical-primary)", color: "white", borderRadius: "999px", padding: "0.075rem 0.45rem", fontSize: "0.7rem", fontWeight: "700" }}>
                  {selectedNodeRelations.length}
                </span>
              </h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {(showAllRelations ? selectedNodeRelations : selectedNodeRelations.slice(0, 4)).map((rel, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: "0.35rem", fontSize: "0.75rem", flexWrap: "nowrap", minWidth: 0 }}>
                    <span title={rel.subject} style={{ padding: "0.15rem 0.4rem", border: "1px solid var(--medical-gray-200)", borderRadius: "4px", color: "var(--medical-gray-700)", background: "#f9fafb", minWidth: 0, flex: "1 1 0", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", cursor: "default" }}>{rel.subject}</span>
                    <span style={{ padding: "0.15rem 0.4rem", borderRadius: "4px", background: getLinkColor({ relation_type: rel.relation }), color: "white", fontWeight: "600", fontSize: "0.6875rem", whiteSpace: "nowrap", flexShrink: 0 }}>{rel.relation.replace(/_/g, " ")}</span>
                    <span style={{ color: "var(--medical-gray-400)", flexShrink: 0 }}>→</span>
                    <span title={rel.object} style={{ padding: "0.15rem 0.4rem", border: "1px solid var(--medical-gray-200)", borderRadius: "4px", color: "var(--medical-gray-700)", background: "#f9fafb", minWidth: 0, flex: "1 1 0", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", cursor: "default" }}>{rel.object}</span>
                  </div>
                ))}
                {selectedNodeRelations.length > 4 && (
                  <button
                    onClick={() => setShowAllRelations(!showAllRelations)}
                    style={{
                      marginTop: "0.25rem",
                      background: "none",
                      border: "1px solid var(--medical-gray-300)",
                      borderRadius: "6px",
                      padding: "0.3rem 0.75rem",
                      fontSize: "0.75rem",
                      color: "var(--medical-primary)",
                      cursor: "pointer",
                      fontWeight: "600",
                      alignSelf: "flex-start",
                    }}
                  >
                    {showAllRelations
                      ? "Show less"
                      : `Show ${selectedNodeRelations.length - 4} more`}
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Source Articles */}
          <div style={{ padding: "1rem 1.5rem 0.5rem", flexShrink: 0 }}>
            <h4 style={{ fontSize: "0.875rem", fontWeight: "600", color: "var(--medical-gray-700)", margin: 0 }}>
              Source Articles
              {selectedNode.source_count ? ` (${selectedNode.source_count})` : ""}
            </h4>
          </div>

          <div style={{ flex: 1, overflowY: "auto", padding: "0 1.5rem 1.5rem" }}>
            {articlesLoading ? (
              <p style={{ fontSize: "0.8125rem", color: "var(--medical-gray-500)", padding: "1rem 0" }}>Loading articles...</p>
            ) : selectedArticles.length === 0 ? (
              <p style={{ fontSize: "0.8125rem", color: "var(--medical-gray-500)", padding: "1rem 0" }}>
                {selectedNode.sources && selectedNode.sources.length > 0
                  ? "Articles not found in database. Re-run ingestion to populate."
                  : "No source articles linked."}
              </p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", paddingTop: "0.5rem" }}>
                {selectedArticles.map((article) => (
                  <div
                    key={article.pmid}
                    style={{
                      padding: "0.75rem",
                      border: "1px solid var(--medical-gray-200)",
                      borderRadius: "8px",
                      fontSize: "0.8125rem",
                      background: "var(--medical-gray-50, #f9fafb)",
                    }}
                  >
                    <p style={{
                      fontWeight: "600",
                      color: "var(--medical-gray-900)",
                      margin: "0 0 0.375rem 0",
                      lineHeight: "1.3",
                      display: "-webkit-box",
                      WebkitLineClamp: 3,
                      WebkitBoxOrient: "vertical" as const,
                      overflow: "hidden",
                    }}>
                      {article.title || "Untitled"}
                    </p>
                    <p style={{ color: "var(--medical-gray-500)", margin: "0 0 0.5rem 0", fontSize: "0.75rem" }}>
                      {article.journal}{article.pub_date ? ` - ${article.pub_date}` : ""}
                    </p>
                    <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                      {article.pubmed_url && (
                        <a
                          href={article.pubmed_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "0.25rem",
                            padding: "0.25rem 0.5rem",
                            borderRadius: "4px",
                            fontSize: "0.6875rem",
                            fontWeight: "600",
                            textDecoration: "none",
                            color: "#0066cc",
                            background: "#e0f2fe",
                          }}
                        >
                          PubMed
                        </a>
                      )}
                      {article.pdf_url && (
                        <a
                          href={article.pdf_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "0.25rem",
                            padding: "0.25rem 0.5rem",
                            borderRadius: "4px",
                            fontSize: "0.6875rem",
                            fontWeight: "600",
                            textDecoration: "none",
                            color: "#dc2626",
                            background: "#fef2f2",
                          }}
                        >
                          PDF
                        </a>
                      )}
                      {article.doi && (
                        <a
                          href={`https://doi.org/${article.doi}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "0.25rem",
                            padding: "0.25rem 0.5rem",
                            borderRadius: "4px",
                            fontSize: "0.6875rem",
                            fontWeight: "600",
                            textDecoration: "none",
                            color: "#059669",
                            background: "#ecfdf5",
                          }}
                        >
                          DOI
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
