"""PDF upload endpoint."""

import os
import uuid

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse
import httpx

router = APIRouter()


def _get_upload_tools():
    """Lazy-import document processing tools from deepagents."""
    from deepagents.tools.document.store_pdf import store_pdf
    from deepagents.tools.document.pdf_loader import parse_pdf
    from deepagents.tools.document.vector_store import (
        index_documents,
        compute_file_hash,
        check_existing_document,
    )
    from deepagents.tools.document.summarizer import summarize
    return store_pdf, parse_pdf, index_documents, compute_file_hash, check_existing_document, summarize


@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        store_pdf, parse_pdf, index_documents, compute_file_hash, check_existing_document, summarize = _get_upload_tools()
    except ImportError:
        return JSONResponse({"error": "Upload tools not available (deepagents.tools.document not found)"}, status_code=501)

    print("[upload] /upload called")
    print("filename", file.filename, "content_type", file.content_type)

    # Read file content for hashing
    file_content = await file.read()
    await file.seek(0)  # Reset file pointer for subsequent reads

    # Compute file hash for deduplication
    file_hash = compute_file_hash(file_content)
    print(f"[upload] computed file_hash={file_hash[:16]}...")

    # Check if this file already exists
    existing = check_existing_document(file_hash)

    if existing:
        print(f"[upload] ⚠️  File already indexed! doc_id={existing['doc_id']}, chunks={existing['chunk_count']}")
        return {
            "file_url": existing.get("source", ""),
            "doc_id": existing["doc_id"],
            "chunks_indexed": existing["chunk_count"],
            "summary": f"File '{file.filename}' was already indexed. Reusing existing document.",
            "reused": True
        }

    # New file - proceed with storage and indexing
    # 1. Save in supabase storage
    file_url = store_pdf(file)
    print("[upload] stored file_url", file_url)

    # 2. Text Extraction
    documents = parse_pdf(file)
    try:
        print("[upload] documents_count", len(documents))
    except Exception:
        print("[upload] documents_count unavailable")

    # 3. Vector Supabase Indexation
    doc_id = str(uuid.uuid4())
    print("[upload] doc_id", doc_id)
    stored = index_documents(
        documents,
        base_metadata={
            "source": file_url,
            "filename": file.filename,
            "doc_id": doc_id,
            "file_hash": file_hash
        },
    )
    print("[upload] indexed stored=", stored)

    # 4. Summarization
    summary = summarize(documents)
    print("[upload] summary generated length=", (len(summary) if isinstance(summary, str) else "n/a"))

    # 5. notify n8n webhook
    webhook_url = os.getenv("N8N_WEBHOOK_URL")
    if webhook_url:
        print("webhook_url", webhook_url)
        try:
            payload = {
                "doc_id": doc_id,
                "file_url": file_url,
                "filename": file.filename,
                "chunks_indexed": stored,
                "summary": summary,
            }
            print("payload", payload)

            # non-blocking fire-and-forget
            verify = os.getenv("N8N_WEBHOOK_VERIFY", "true").lower() != "false"
            with httpx.Client(timeout=5.0, verify=verify) as client:
                client.post(webhook_url, json=payload)
        except Exception as e:
            print("n8n webhook notify failed:", e)

    return {"file_url": file_url, "doc_id": doc_id, "chunks_indexed": stored, "summary": summary}
