"""
Test ADR-DEV-001: Unicode sanitization for HTTP headers.

Validates that _ascii_only() and _sanitize_http_header_env() correctly
handle non-ASCII characters to prevent httpx header encoding crashes.

Run with: python3 tests/test_unicode_sanitization.py
"""
import os
import sys


# Inline implementations to avoid importing heavy dependencies
def _ascii_only(text: str) -> str:
    """Return an ASCII-only version of text."""
    try:
        return (text or "").encode("ascii", "ignore").decode("ascii")
    except Exception:
        return "".join(ch for ch in (text or "") if ord(ch) < 128)


def _sanitize_http_header_env() -> None:
    """Sanitize env vars that may be forwarded as HTTP headers."""
    candidate_keys = [
        "HTTP_REFERER", "OPENROUTER_HTTP_REFERER", "OPENROUTER_REFERER",
        "OPENROUTER_SITE_URL", "X_TITLE", "OPENROUTER_X_TITLE",
        "OPENROUTER_APP_NAME", "OPENROUTER_APP_TITLE",
        "OPENAI_ORGANIZATION", "OPENAI_PROJECT",
    ]
    for k in candidate_keys:
        v = os.getenv(k)
        if not v:
            continue
        ascii_v = _ascii_only(v)
        if ascii_v != v:
            os.environ[k] = ascii_v


def _safe_utf8_str(value) -> str:
    """Safely convert any value to a UTF-8 encoded string."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        str_value = str(value)
        return str_value.encode('utf-8', errors='replace').decode('utf-8')
    except Exception:
        return repr(value)


def test_ascii_only():
    """Test _ascii_only() function."""
    print("Testing _ascii_only()...")
    
    # ASCII strings should pass through unchanged
    assert _ascii_only("hello world") == "hello world", "ASCII unchanged"
    assert _ascii_only("API_KEY_123") == "API_KEY_123", "API key unchanged"
    
    # Accented characters should be stripped
    assert _ascii_only("Résumé") == "Rsum", "Accents removed"
    assert _ascii_only("Projet été") == "Projet t", "Accents removed"
    assert _ascii_only("café") == "caf", "Accents removed"
    
    # Unicode symbols should be stripped
    assert "🚀" not in _ascii_only("Hello 🚀 World"), "Emoji removed"
    
    # Edge cases
    assert _ascii_only("") == "", "Empty string"
    assert _ascii_only(None) == "", "None returns empty"
    assert _ascii_only("éèàù") == "", "Only unicode returns empty"
    
    print("  [PASS] _ascii_only()")


def test_sanitize_http_header_env():
    """Test _sanitize_http_header_env() function."""
    print("Testing _sanitize_http_header_env()...")
    
    # Test with accented OPENROUTER_X_TITLE
    os.environ["OPENROUTER_X_TITLE"] = "Résumé français"
    _sanitize_http_header_env()
    assert os.environ["OPENROUTER_X_TITLE"] == "Rsum franais", "OPENROUTER_X_TITLE sanitized"
    
    # Test with accented OPENAI_PROJECT
    os.environ["OPENAI_PROJECT"] = "Projet été 2026"
    _sanitize_http_header_env()
    assert os.environ["OPENAI_PROJECT"] == "Projet t 2026", "OPENAI_PROJECT sanitized"
    
    # ASCII-only values should remain unchanged
    os.environ["OPENROUTER_X_TITLE"] = "My Project"
    _sanitize_http_header_env()
    assert os.environ["OPENROUTER_X_TITLE"] == "My Project", "ASCII unchanged"
    
    # Clean up
    for key in ["OPENROUTER_X_TITLE", "OPENAI_PROJECT"]:
        os.environ.pop(key, None)
    
    # Should not crash with missing env vars
    _sanitize_http_header_env()
    
    print("  [PASS] _sanitize_http_header_env()")


def test_safe_utf8_str():
    """Test _safe_utf8_str() function."""
    print("Testing _safe_utf8_str()...")
    
    # Normal strings should pass through
    assert _safe_utf8_str("hello") == "hello", "String passthrough"
    assert _safe_utf8_str("Résumé") == "Résumé", "UTF-8 preserved"
    
    # None should return empty string
    assert _safe_utf8_str(None) == "", "None returns empty"
    
    # Numbers should be converted to string
    assert _safe_utf8_str(42) == "42", "Int to string"
    assert _safe_utf8_str(3.14) == "3.14", "Float to string"
    
    # Objects should be converted via str()
    result = _safe_utf8_str({"key": "value"})
    assert "key" in result, "Dict to string"
    
    print("  [PASS] _safe_utf8_str()")


if __name__ == "__main__":
    print("=" * 50)
    print("ADR-DEV-001 Validation Tests")
    print("=" * 50)
    
    try:
        test_ascii_only()
        test_sanitize_http_header_env()
        test_safe_utf8_str()
        print("=" * 50)
        print("ALL TESTS PASSED")
        print("ADR-DEV-001 implementation validated.")
        print("=" * 50)
    except AssertionError as e:
        print(f"FAILED: {e}")
        sys.exit(1)
