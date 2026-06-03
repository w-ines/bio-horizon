"""
PDF storage — migrated from huggingsmolagent/tools/supabase_store.py.
Stores PDFs to Supabase storage with local fallback.
"""

import os
import pathlib

from fastapi import UploadFile
from dotenv import load_dotenv

load_dotenv()

# Local storage fallback directory
LOCAL_STORAGE_DIR = pathlib.Path(__file__).parent.parent.parent.parent / "local_storage" / "uploads"
LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Lazy Supabase client (initialized on first use)
_supabase = None
_supabase_available = None


def _get_supabase():
    """Lazy-init Supabase client."""
    global _supabase, _supabase_available
    if _supabase_available is not None:
        return _supabase, _supabase_available

    try:
        from storage.supabase_client import get_supabase_client
        _supabase = get_supabase_client()
        _supabase_available = True
        print("[store_pdf] Supabase client initialized successfully")
    except Exception as e:
        _supabase = None
        _supabase_available = False
        print(f"[store_pdf] ⚠️  Supabase not available: {e}")

    return _supabase, _supabase_available


def store_pdf(file: UploadFile) -> str:
    """
    Store PDF file. Tries Supabase first, falls back to local storage.

    Returns:
        URL of the stored file.
    """
    path = f"{file.filename}"
    file.file.seek(0)
    file_bytes = file.file.read()

    client, available = _get_supabase()

    # Try Supabase first
    if available and client:
        try:
            options = {
                "content-type": file.content_type or "application/octet-stream",
                "upsert": "true",
            }
            res = client.storage.from_("public-bucket").upload(path, file_bytes, options)
            print(f"[store_pdf] Uploaded to Supabase: {res}")
            url = os.getenv("SUPABASE_URL", "")
            return f"{url}/storage/v1/object/public/public-bucket/{file.filename}"
        except Exception as e:
            print(f"[store_pdf] ⚠️  Supabase upload failed: {e}")
            print("[store_pdf] Falling back to local storage...")

    # Fallback to local storage
    local_file_path = LOCAL_STORAGE_DIR / file.filename
    with open(local_file_path, "wb") as f:
        f.write(file_bytes)

    local_url = f"file://{local_file_path.absolute()}"
    print(f"[store_pdf] Stored locally: {local_url}")
    return local_url
