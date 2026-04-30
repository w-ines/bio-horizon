"""Unified /ask endpoint — delegates to Deep Agent with optional file uploads."""

import os
import json
import uuid
import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

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
    return store_pdf, parse_pdf, index_documents, compute_file_hash, check_existing_document


def _build_deep_agent_stream(query: str, conversation_id: str = None):
    """Return an async generator that streams Deep Agent events."""

    async def _events():
        import queue
        import threading

        event_queue = queue.Queue()
        final_answer = None

        def stream_callback(event):
            event_queue.put(event)

        def run_agent():
            nonlocal final_answer
            try:
                from deepagents.agents.main_agent import create_biomedical_agent

                agent = create_biomedical_agent(
                    conversation_id=conversation_id,
                    stream_callback=stream_callback,
                )

                result = agent.invoke({"input": query})
                final_answer = result.get("output", str(result)) if isinstance(result, dict) else str(result)
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                print(f"[ask] Agent error: {e}\n{tb}")
                event_queue.put({"type": "error", "content": f"Agent error: {e}"})
                final_answer = f"An error occurred while processing your request: {e}"
            finally:
                event_queue.put({"type": "done"})

        agent_thread = threading.Thread(target=run_agent)
        agent_thread.start()

        yield json.dumps({"step": "🚀 Starting Deep Agent..."}, ensure_ascii=False) + "\n"

        while True:
            try:
                event = event_queue.get(timeout=0.1)

                if event["type"] == "done":
                    break
                elif event["type"] in ("thought", "action", "error"):
                    yield json.dumps({"step": event["content"]}, ensure_ascii=False) + "\n"
                elif event["type"] == "observation":
                    step_data = {"step": event["content"]}
                    if "preview" in event:
                        step_data["preview"] = event["preview"]
                    yield json.dumps(step_data, ensure_ascii=False) + "\n"
                elif event["type"] == "answer":
                    pass

            except queue.Empty:
                await asyncio.sleep(0.05)
                continue

        agent_thread.join()

        if final_answer:
            print(f"[ask] LLM final response: {final_answer}")
            print(f"[ask] Checking for URLs in response...")
            import re
            urls = re.findall(r'\[([^\]]+)\]\((https?://[^)]+)\)', final_answer)
            if urls:
                for text, url in urls:
                    print(f"[ask] Found markdown link: [{text}]({url})")
            yield json.dumps({"response": final_answer, "canHandle": True}, ensure_ascii=False) + "\n"
        else:
            yield json.dumps({"response": "No response generated", "canHandle": False}, ensure_ascii=False) + "\n"

    return _events()


async def _process_uploads(files) -> list[dict]:
    """Process uploaded files: store, parse, index. Returns upload context list."""
    store_pdf, parse_pdf, index_documents, compute_file_hash, check_existing_document = _get_upload_tools()

    uploaded_context = []
    for f in files:
        print(f"[ask] processing file name={getattr(f, 'filename', None)}")

        file_content = await f.read()
        await f.seek(0)

        file_hash = compute_file_hash(file_content)
        print(f"[ask] computed file_hash={file_hash[:16]}...")

        existing = check_existing_document(file_hash)

        if existing:
            print(f"[ask] ⚠️  File already indexed! doc_id={existing['doc_id']}, chunks={existing['chunk_count']}")
            uploaded_context.append({
                "filename": f.filename,
                "doc_id": existing["doc_id"],
                "chunks": existing["chunk_count"],
                "reused": True,
            })
            continue

        file_url = store_pdf(f)
        print(f"[ask] stored file_url={file_url}")
        documents = parse_pdf(f)
        print(f"[ask] parsed documents_count={len(documents) if isinstance(documents, list) else 'n/a'}")
        doc_id = str(uuid.uuid4())
        stored = index_documents(
            documents,
            base_metadata={
                "source": file_url,
                "filename": f.filename,
                "doc_id": doc_id,
                "file_hash": file_hash,
            },
        )
        print(f"[ask] indexed doc_id={doc_id} stored={stored}")
        uploaded_context.append({
            "filename": f.filename,
            "doc_id": doc_id,
            "chunks": stored,
            "reused": False,
        })
    return uploaded_context


@router.post("")
async def ask(request: Request):
    """
    Unified Ask endpoint:
    - If files are attached: upload+index them first, then pass query to agent
    - If no files: directly pass query to agent

    Returns streaming NDJSON response from Deep Agent.
    """
    content_type = request.headers.get("content-type", "")
    is_multipart = "multipart/form-data" in content_type
    is_json = "application/json" in content_type
    print(f"[ask] called content_type={content_type} is_multipart={is_multipart} is_json={is_json}")

    try:
        query = ""
        conversation_id = None
        uploaded_context = []

        # STEP 1: Handle file uploads if present
        if is_multipart:
            form = await request.form()
            query = (form.get("query") or "").strip()
            conversation_id = (form.get("conversation_id") or "").strip() or None
            files = form.getlist("files")
            print(f"[ask] multipart received query='{query[:80] if query else ''}' conversation_id={conversation_id} files_count={len(files) if files else 0}")

            if files:
                print(f"[ask] processing {len(files)} file(s)")
                uploaded_context = await _process_uploads(files)
                print(f"[ask] upload complete. {len(uploaded_context)} file(s) processed")
        else:
            body = await request.json() if is_json else {}
            query = (body.get("query") if isinstance(body, dict) else None) or ""
            conversation_id = (body.get("conversation_id") if isinstance(body, dict) else None) or None
            print(f"[ask] json body parsed query='{query[:120] if query else ''}' conversation_id={conversation_id}")

        # If files were uploaded but no query, return upload success
        if not query and uploaded_context:
            return JSONResponse({
                "answer": f"✅ {len(uploaded_context)} file(s) uploaded and indexed successfully. You can now ask questions about them.",
                "uploaded_files": uploaded_context,
                "status": "success"
            }, status_code=200)

        if not query:
            return JSONResponse({"answer": "Please provide a query."}, status_code=400)

        # STEP 2: Build context message if files were uploaded
        agent_query = query
        if uploaded_context:
            filenames = [ctx["filename"] for ctx in uploaded_context]
            doc_ids = [ctx["doc_id"] for ctx in uploaded_context]
            total_chunks = sum(ctx["chunks"] for ctx in uploaded_context)
            doc_id_param = doc_ids[0] if len(doc_ids) == 1 else None

            agent_query = query + f"""

[CONTEXT: User uploaded {len(uploaded_context)} file(s): {', '.join(filenames)}]
[Total chunks indexed: {total_chunks}]

The uploaded document(s) are now in the vector database. Use the retrieve_knowledge tool to access the content.
{f'Document ID: {doc_id_param}' if doc_id_param else ''}
"""

        print(f"[ask] delegating to agent with query (length={len(agent_query)})")

        # STEP 3: Stream Deep Agent response
        return StreamingResponse(
            _build_deep_agent_stream(agent_query, conversation_id),
            media_type="application/x-ndjson",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except Exception as e:
        print("[ask] error:", e)
        import traceback
        traceback.print_exc()
        return JSONResponse({"answer": "Error processing request.", "error": str(e)}, status_code=500)
