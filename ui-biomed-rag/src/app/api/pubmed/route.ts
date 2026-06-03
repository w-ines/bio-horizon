import { NextRequest, NextResponse } from "next/server";

function backendBaseUrl(): string {
  const askUrl = process.env.BACKEND_API_URL || "http://localhost:8000/ask";
  return askUrl.replace(/\/ask$/, "");
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const url = `${backendBaseUrl()}/pubmed/search`;

    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status });
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error("[api/pubmed] error:", error);
    return NextResponse.json(
      { error: (error as Error).message || "Unknown error", pmids: [], articles: [], total: 0 },
      { status: 500 }
    );
  }
}
