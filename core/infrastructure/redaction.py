"""Best-effort redaction before diagnostics leave the local runtime."""
from typing import Any


_SENSITIVE_MARKERS = (
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "password",
    "secret",
    "token",
    "webhook",
)


def redact_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            normalized = str(key).strip().lower()
            result[key] = "***REDACTED***" if any(
                marker in normalized for marker in _SENSITIVE_MARKERS
            ) else redact_sensitive(item)
        return result
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_sensitive(item) for item in value)
    return value
