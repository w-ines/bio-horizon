import "../../../../scripts/polyfills";

import { NextRequest, NextResponse } from "next/server";
import { getRagUrl } from "@/lib/env";
import { Agent, setGlobalDispatcher } from "undici";

// Configure undici with extended timeouts for long-running agent operations
const agent = new Agent({
  headersTimeout: 10 * 60 * 1000, // 10 minutes
  bodyTimeout: 10 * 60 * 1000,    // 10 minutes
  connectTimeout: 30 * 1000,      // 30 seconds
});
setGlobalDispatcher(agent);

export async function POST(req: NextRequest) {
  try {
    const contentType = req.headers.get("content-type") || "";
    const isMultipart = contentType.includes("multipart/form-data");
    const isJson = contentType.includes("application/json");
    console.log(`[next-api] /api/ask called contentType=${contentType} isMultipart=${isMultipart} isJson=${isJson}`);
    
    // Create AbortController with 10 minute timeout for slow LLM responses
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10 * 60 * 1000); // 10 minutes
    
    if (isJson) {
      const body = await req.json().catch(() => ({}));
      // Always forward JSON to backend /ask
      const backendUrl = getRagUrl();
      console.log(`[next-api] forwarding JSON to ${backendUrl}`);
      const backendResponse = await fetch(backendUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);
      const backendContentType = backendResponse.headers.get("content-type") || "";
      const backendIsJson = backendContentType.includes("application/json");
      const backendIsNdjson = backendContentType.includes("application/x-ndjson");

      if (!backendResponse.ok) {
        const payload = backendIsJson ? await backendResponse.json().catch(() => undefined) : await backendResponse.text().catch(() => undefined);
        console.log(`[next-api] backend error:`, payload);
        return NextResponse.json(
          { error: typeof payload === "string" ? payload : payload || backendResponse.statusText },
          { status: backendResponse.status }
        );
      }

      // Handle NDJSON streaming response (web search)
      if (backendIsNdjson) {
        console.log(`[next-api] streaming NDJSON response from backend`);
        const reader = backendResponse.body?.getReader();
        if (!reader) {
          throw new Error("No reader available from backend");
        }

        const stream = new ReadableStream({
          async start(controller) {
            const decoder = new TextDecoder();
            try {
              while (true) {
                const { done, value } = await reader.read();
                if (done) {
                  console.log(`[next-api] NDJSON stream completed`);
                  controller.close();
                  break;
                }
                
                const chunk = decoder.decode(value, { stream: true });
                console.log(`[next-api] NDJSON chunk: ${chunk.substring(0, 100)}...`);
                controller.enqueue(new TextEncoder().encode(chunk));
              }
            } catch (error) {
              console.error(`[next-api] NDJSON stream error:`, error);
              controller.error(error);
            }
          },
        });

        return new NextResponse(stream, {
          headers: {
            "Content-Type": "application/x-ndjson",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
          },
        });
      }

      if (backendIsJson) {
        const data = await backendResponse.json();
        console.log(`[next-api] returning json data:`, data);
        return NextResponse.json(data);
      }

      const text = await backendResponse.text();
      console.log(`[next-api] backend returned non-json text:`, text);
      return new NextResponse(text, { headers: { "content-type": "text/plain" } });
    }
    
    // Handle multipart form data (file uploads) - with streaming NDJSON support
    if (isMultipart) {
      const formData = await req.formData();
      const backendUrl = getRagUrl();
      console.log(`[next-api] forwarding multipart to ${backendUrl}`);
      
      // Create new controller for multipart requests
      const multipartController = new AbortController();
      const multipartTimeoutId = setTimeout(() => multipartController.abort(), 10 * 60 * 1000);
      
      const backendResponse = await fetch(backendUrl, {
        method: "POST",
        body: formData as unknown as BodyInit,
        signal: multipartController.signal,
      });

      clearTimeout(multipartTimeoutId);
      const backendContentType = backendResponse.headers.get("content-type") || "";
      const backendIsJson = backendContentType.includes("application/json");
      const backendIsNdjson = backendContentType.includes("application/x-ndjson");

      if (!backendResponse.ok) {
        const payload = backendIsJson ? await backendResponse.json().catch(() => undefined) : await backendResponse.text().catch(() => undefined);
        console.log(`[next-api] backend error:`, payload);
        return NextResponse.json(
          { error: typeof payload === "string" ? payload : payload || backendResponse.statusText },
          { status: backendResponse.status }
        );
      }

      // Handle NDJSON streaming response (RAG with files)
      if (backendIsNdjson) {
        console.log(`[next-api] streaming NDJSON response from backend`);
        const reader = backendResponse.body?.getReader();
        if (!reader) {
          throw new Error("No reader available from backend");
        }

        const stream = new ReadableStream({
          async start(controller) {
            const decoder = new TextDecoder();
            try {
              while (true) {
                const { done, value } = await reader.read();
                if (done) {
                  console.log(`[next-api] NDJSON stream completed`);
                  controller.close();
                  break;
                }
                
                const chunk = decoder.decode(value, { stream: true });
                console.log(`[next-api] NDJSON chunk: ${chunk.substring(0, 100)}...`);
                controller.enqueue(new TextEncoder().encode(chunk));
              }
            } catch (error) {
              console.error(`[next-api] NDJSON stream error:`, error);
              controller.error(error);
            }
          },
        });

        return new NextResponse(stream, {
          headers: {
            "Content-Type": "application/x-ndjson",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
          },
        });
      }

      if (backendIsJson) {
        const data = await backendResponse.json();
        console.log(`[next-api] returning json data:`, data);
        return NextResponse.json(data);
      }

      const text = await backendResponse.text();
      return new NextResponse(text, { headers: { "content-type": "text/plain" } });
    }

    // Fallback: stream raw body
    const backendUrl = getRagUrl();
    console.log(`[next-api] forwarding raw body to ${backendUrl}`);
    
    // Create new controller for raw body requests
    const rawController = new AbortController();
    const rawTimeoutId = setTimeout(() => rawController.abort(), 10 * 60 * 1000);
    
    const backendResponse = await fetch(backendUrl, {
      method: "POST",
      headers: { "content-type": contentType },
      body: req.body as unknown as BodyInit,
      signal: rawController.signal,
    });

    clearTimeout(rawTimeoutId);
    const backendContentType = backendResponse.headers.get("content-type") || "";
    const backendIsJson = backendContentType.includes("application/json");

    if (!backendResponse.ok) {
      const payload = backendIsJson ? await backendResponse.json().catch(() => undefined) : await backendResponse.text().catch(() => undefined);
      console.log(`[next-api] backend error:`, payload);
      return NextResponse.json(
        { error: typeof payload === "string" ? payload : payload || backendResponse.statusText },
        { status: backendResponse.status }
      );
    }

    if (backendIsJson) {
      const data = await backendResponse.json();
      return NextResponse.json(data);
    }

    const text = await backendResponse.text();
    return new NextResponse(text, { headers: { "content-type": "text/plain" } });
  } catch (error) {
    console.error(`[next-api] error:`, error);
    return NextResponse.json({ error: (error as Error).message || "Unknown error" }, { status: 500 });
  }
}

// proxies to your backend RAG/scraping service