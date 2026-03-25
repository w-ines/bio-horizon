"""
Application configuration and environment setup.
Centralizes all env var loading and app-wide settings.
"""

import os
import sys
import io
import json
import logging

from dotenv import load_dotenv

load_dotenv()


# =============================================================================
# UTF-8 / Encoding setup
# =============================================================================

def setup_encoding():
    """Set environment variables and reconfigure stdout/stderr for UTF-8."""
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("LANG", "C.UTF-8")
    os.environ.setdefault("LC_ALL", "C.UTF-8")
    os.environ.setdefault("SMOLAGENTS_VERBOSITY", "0")
    os.environ.setdefault("RICH_FORCE_TERMINAL", "false")
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


def patch_json_ascii():
    """Monkey-patch json.dumps to always use ensure_ascii=False."""
    _original_dumps = json.dumps

    def utf8_dumps(*args, **kwargs):
        kwargs["ensure_ascii"] = False
        return _original_dumps(*args, **kwargs)

    json.dumps = utf8_dumps


# =============================================================================
# Logging setup
# =============================================================================

def setup_huggingface_token():
    """Configure Hugging Face token for OpenMed model access (optional)."""
    hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
    if hf_token:
        try:
            from huggingface_hub import login
            login(token=hf_token, add_to_git_credential=False)
            logging.info("✓ Hugging Face token configured for OpenMed models")
        except ImportError:
            logging.debug("huggingface_hub not installed, skipping HF login")
        except Exception as e:
            logging.warning(f"Failed to configure HF token: {e}")


def setup_logging():
    """Configure logging levels and silence noisy loggers."""
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
    for noisy in ("openai", "httpx", "httpcore", "rquest", "primp", "cookie_store"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


# =============================================================================
# CORS settings
# =============================================================================

def get_cors_origins() -> list[str]:
    """Return list of allowed CORS origins from environment."""
    raw = os.getenv("CORS_ORIGINS", "http://localhost:3000")
    return [o.strip() for o in raw.split(",") if o.strip()]
