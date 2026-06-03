/**
 * Get the backend API base URL.
 * Defaults to http://localhost:8000 if not configured.
 * 
 * Note: Uses NEXT_PUBLIC_ prefix for client-side access.
 */
export function getApiUrl(): string {
  return process.env.NEXT_PUBLIC_BACKEND_API_URL || "http://localhost:8000";
}

/**
 * Get the backend RAG endpoint URL (server-side only).
 * Used for server-side API routes.
 */
export function getRagUrl(): string {
  return process.env.BACKEND_API_URL || "http://localhost:8000/ask";
}
