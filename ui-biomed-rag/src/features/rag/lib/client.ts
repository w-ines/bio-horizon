import { fetchJson } from "@/lib/fetch";

export type RagRequest = {
  query: string;
  files?: File[];
};

export type RagResponse = {
  answer: string;
  sources?: Array<{ title?: string; url?: string; snippet?: string }>; // optional
};

export async function askRag(request: RagRequest): Promise<RagResponse> {
  const hasFiles = Array.isArray(request.files) && request.files.length > 0;
  console.log(`[client] askRag called hasFiles=${hasFiles} query="${request.query}"`);

  if (!hasFiles) {
    // JSON request when no files attached
    console.log(`[client] sending JSON request to /api/ask`);
    return await fetchJson<RagResponse>("/api/ask", {
      method: "POST",
      body: JSON.stringify({ query: request.query }),
    });
  }

  // Multipart request when files are attached
  const formData = new FormData();
  formData.append("query", request.query);
  for (const file of request.files!) {
    formData.append("files", file);
  }
  console.log(`[client] sending multipart request to /api/ask with ${request.files!.length} file(s)`);

  const res = await fetch("/api/ask", {
    method: "POST",
    body: formData, // Let the browser set the Content-Type with boundary
  });

  const contentType = res.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");
  console.log(`[client] response status=${res.status} contentType="${contentType}" isJson=${isJson}`);
  
  if (!res.ok) {
    const payload = isJson ? await res.json().catch(() => undefined) : await res.text().catch(() => undefined);
    const message = typeof payload === "string" ? payload : JSON.stringify(payload || { error: res.statusText });
    console.error(`[client] request failed:`, message);
    throw new Error(message || `Request failed with status ${res.status}`);
  }

  if (!isJson) {
    const text = await res.text();
    console.error(`[client] Expected JSON response but got contentType="${contentType}" text="${text.substring(0, 200)}"`);
    throw new Error("Expected JSON response");
  }

  const data = await res.json();
  console.log(`[client] success:`, data);
  return data as RagResponse;
}

