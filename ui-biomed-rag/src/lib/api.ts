/**
 * API client for BioHorizon backend.
 * Provides typed functions to call all backend endpoints.
 */

import { fetchJson } from "./fetch";
import { getApiUrl } from "./env";

const API_BASE = getApiUrl();

// =============================================================================
// Types
// =============================================================================

export interface Snapshot {
  week_label: string;
  node_count: number;
  edge_count: number;
  entity_types: Record<string, number>;
}

export interface SnapshotsList {
  snapshots: string[];
  current_week: string;
  total_count: number;
}

export interface EntityNode {
  id: string;
  label: string;
  entity_type: string;
  frequency: number;
}

export interface EntityEdge {
  source: EntityNode;
  target: EntityNode;
  old_weight?: number;
  new_weight?: number;
  delta?: number;
}

export interface SnapshotComparison {
  week_new: string;
  week_old: string;
  weeks_ago?: number;
  summary: {
    total_new_nodes: number;
    total_new_edges: number;
    total_weight_increased: number;
    total_disappeared_nodes: number;
    total_disappeared_edges: number;
  };
  new_nodes: EntityNode[];
  new_edges: EntityEdge[];
  weight_increased: EntityEdge[];
  disappeared_nodes?: EntityNode[];
  disappeared_edges?: EntityEdge[];
  note?: string;
}

export interface Signal {
  id: number;
  week_label: string;
  signal_type: "emerging" | "accelerating" | "declining" | "contradictory";
  entity_a: string;
  entity_b: string;
  emergence_score: number;
  velocity: number;
  source_diversity: number;
  consensus_positive?: number;
  consensus_negative?: number;
  consensus_hypothetical?: number;
  consensus_label?: "confirmed" | "contradictory" | "preliminary";
  pmids: string[];
  details: Record<string, unknown>;
  created_at: string;
}

export interface SignalsList {
  signals: Signal[];
  message?: string;
  available_endpoints?: Record<string, string>;
}

// =============================================================================
// Signals API
// =============================================================================

/**
 * List all available KG snapshots.
 */
export async function listSnapshots(): Promise<SnapshotsList> {
  return fetchJson<SnapshotsList>(`${API_BASE}/signals/snapshots`);
}

/**
 * Get metadata about a specific snapshot.
 */
export async function getSnapshot(weekLabel: string): Promise<Snapshot> {
  return fetchJson<Snapshot>(`${API_BASE}/signals/snapshots/${weekLabel}`);
}

/**
 * Compare two snapshots to detect changes.
 */
export async function compareSnapshots(
  weekNew: string,
  weekOld: string
): Promise<SnapshotComparison> {
  const params = new URLSearchParams({ week_new: weekNew, week_old: weekOld });
  return fetchJson<SnapshotComparison>(`${API_BASE}/signals/compare?${params}`);
}

/**
 * Compare current week vs N weeks ago.
 */
export async function compareCurrentVsPast(
  weeksAgo: number = 4
): Promise<SnapshotComparison> {
  const params = new URLSearchParams({ weeks_ago: weeksAgo.toString() });
  return fetchJson<SnapshotComparison>(
    `${API_BASE}/signals/compare/current?${params}`
  );
}

/**
 * List detected signals (Phase 2 - currently returns stub).
 */
export async function listSignals(params?: {
  week?: string;
  signal_type?: string;
  min_score?: number;
}): Promise<SignalsList> {
  const searchParams = new URLSearchParams();
  if (params?.week) searchParams.set("week", params.week);
  if (params?.signal_type) searchParams.set("signal_type", params.signal_type);
  if (params?.min_score !== undefined)
    searchParams.set("min_score", params.min_score.toString());

  const url = searchParams.toString()
    ? `${API_BASE}/signals/?${searchParams}`
    : `${API_BASE}/signals/`;

  return fetchJson<SignalsList>(url);
}

/**
 * Get a specific signal by ID (Phase 2 - not yet implemented).
 */
export async function getSignal(signalId: number): Promise<Signal> {
  return fetchJson<Signal>(`${API_BASE}/signals/${signalId}`);
}

/**
 * Get consensus score for a relation (Phase 5 - not yet implemented).
 */
export async function getConsensus(
  entityA: string,
  entityB: string
): Promise<{
  consensus_positive: number;
  consensus_negative: number;
  consensus_hypothetical: number;
  consensus_label: string;
}> {
  return fetchJson(
    `${API_BASE}/signals/consensus/${encodeURIComponent(
      entityA
    )}/${encodeURIComponent(entityB)}`
  );
}
