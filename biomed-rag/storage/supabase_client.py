from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()


"""Centralized Supabase client factory.

All modules that need Supabase should import get_supabase_client() from here.
This avoids code duplication and centralizes error handling.
"""


class SupabaseNotConfigured(RuntimeError):
    """Raised when SUPABASE_URL or SUPABASE_KEY are missing."""
    pass


def get_supabase_client() -> Any:
    """Return a Supabase client suitable for server-side operations.

    Prefers SUPABASE_SERVICE_ROLE_KEY (bypasses RLS) when available,
    falls back to SUPABASE_KEY (anon key).

    Raises:
        SupabaseNotConfigured: If SUPABASE_URL or key env vars are missing.
    """
    from supabase import create_client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

    if not url or not key:
        raise SupabaseNotConfigured(
            "Missing SUPABASE_URL or SUPABASE_KEY/SUPABASE_SERVICE_ROLE_KEY. "
            "Set these in your .env file."
        )

    return create_client(url, key)
