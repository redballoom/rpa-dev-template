"""Tests for shared path, atomic-write and redaction infrastructure."""
import json

import pytest

from core.infrastructure.files import PathPolicyError, atomic_write_json, resolve_project_path
from core.infrastructure.redaction import redact_sensitive


def test_resolve_project_path_accepts_output_child(tmp_path):
    path, relative = resolve_project_path(
        str(tmp_path), "data/output/result.json", allowed_dir="data/output"
    )
    assert path == (tmp_path / "data" / "output" / "result.json").resolve()
    assert relative == "data/output/result.json"


@pytest.mark.parametrize("value", ["../outside.json", "data/input/not-output.json"])
def test_resolve_project_path_rejects_escape(tmp_path, value):
    with pytest.raises(PathPolicyError):
        resolve_project_path(str(tmp_path), value, allowed_dir="data/output")


def test_atomic_write_json(tmp_path):
    target = tmp_path / "nested" / "result.json"
    atomic_write_json(target, {"ok": True})
    assert json.loads(target.read_text(encoding="utf-8")) == {"ok": True}
    assert list(target.parent.glob("*.tmp")) == []


def test_redact_sensitive_nested_values():
    source = {
        "api_key": "secret-key",
        "payload": {"cookie_value": "secret-cookie", "normal": "visible"},
        "items": [{"access_token": "secret-token"}],
    }
    result = redact_sensitive(source)
    assert result["api_key"] == "***REDACTED***"
    assert result["payload"]["cookie_value"] == "***REDACTED***"
    assert result["payload"]["normal"] == "visible"
    assert result["items"][0]["access_token"] == "***REDACTED***"
