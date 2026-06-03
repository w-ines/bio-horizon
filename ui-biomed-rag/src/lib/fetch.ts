// Small wrapper around fetch with sane defaults and error handling.

export type JsonBody = Record<string, unknown>;

export async function fetchJson<T>(input: RequestInfo | URL, init?: RequestInit): Promise<T> {
  const res = await fetch(input, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    ...init,
  });

  const contentType = res.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");

  if (!res.ok) {
    const errorPayload = isJson ? await res.json().catch(() => undefined) : await res.text().catch(() => undefined);
    const message = typeof errorPayload === "string" ? errorPayload : JSON.stringify(errorPayload || { error: res.statusText });
    throw new Error(message || `Request failed with status ${res.status}`);
  }

  if (!isJson) {
    throw new Error("Expected JSON response");
  }

  return (await res.json()) as T;
}


