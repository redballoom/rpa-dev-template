"""Portable evidence summary contract tests (M2 / A17)."""
import json
from pathlib import Path

from tools.evidence import build_summary, validate_summary, write_summary


def _runner(status="success", warnings=None, errors=None):
    warnings = warnings or []
    errors = errors or []
    result_status = "error" if errors else ("skipped" if warnings else "ok")
    return {
        "status": status,
        "message": "private message must not be copied",
        "data": {
            "run_id": "A17-001",
            "results": [{
                "task": {"id": "customer-123", "name": "private", "payload": {"token": "secret"}},
                "status": result_status,
                "data": {"customer": "private output"},
            }],
            "warnings": warnings,
            "errors": errors,
            "retryable": False,
            "crash_snapshot_dir": "",
            "log_path": "private.log",
        },
    }


def _files(tmp_path):
    input_path = tmp_path / "input.json"
    input_path.write_text(json.dumps({
        "project": "private project",
        "tasks": [{"type": "demo", "payload": {"cookie": "cookie-value", "account": "buyer@example.com"}}],
        "context": {"token": "top-secret"},
    }), encoding="utf-8")
    runner_path = tmp_path / "runner.json"
    runner_path.write_text(json.dumps({"response": "private response"}), encoding="utf-8")
    return input_path, runner_path


def _build(tmp_path, monkeypatch, result):
    input_path, runner_path = _files(tmp_path)
    monkeypatch.setenv("RPA_PRODUCTION_ENTRYPOINT", "run.bat")
    monkeypatch.setenv("RPA_PYTHON_ENV", "system")
    return build_summary(
        result=result,
        repo_path=Path(__file__).resolve().parents[1],
        input_path=input_path,
        runner_path=runner_path,
        started_at="2026-09-05T00:00:00Z",
        finished_at="2026-09-05T00:00:01Z",
    )


def test_success_summary_records_version_entrypoint_counts_and_hashes(tmp_path, monkeypatch):
    summary = _build(tmp_path, monkeypatch, _runner())
    assert validate_summary(summary)["valid"] is True
    assert summary["run"]["status"] == "success"
    assert len(summary["run"]["commit"]) == 40
    assert isinstance(summary["run"]["working_tree_clean"], bool)
    assert summary["runtime"]["entrypoint"] == "run.bat"
    assert summary["runtime"]["interpreter"]["environment"] == "system"
    assert summary["counts"]["succeeded"] == 1
    assert len(summary["artifacts"]["input"]["sha256"]) == 64
    assert len(summary["artifacts"]["runner_output"]["sha256"]) == 64


def test_business_warning_is_grouped_without_message_or_task(tmp_path, monkeypatch):
    warning = {
        "task": {"payload": {"account": "private"}},
        "message": "customer data missing",
        "context": {"cookie": "secret"},
        "category": "business",
        "code": "DATA_EMPTY",
        "retryable": False,
    }
    summary = _build(tmp_path, monkeypatch, _runner("warning", warnings=[warning]))
    assert summary["counts"]["warnings"] == 1
    assert summary["issue_groups"] == [{
        "kind": "warning", "code": "DATA_EMPTY", "category": "business", "retryable": False, "count": 1,
    }]


def test_failure_is_grouped_without_traceback(tmp_path, monkeypatch):
    error = {
        "task": {"payload": {"api_key": "secret"}},
        "message": "private failure",
        "traceback": "private stack",
        "category": "system",
        "code": "NETWORK_TIMEOUT",
        "exc_category": "DEPENDENCY_FAILURE",
        "retryable": True,
    }
    summary = _build(tmp_path, monkeypatch, _runner("retryable_error", errors=[error]))
    assert summary["counts"]["errors"] == 1
    assert summary["issue_groups"][0]["category"] == "DEPENDENCY_FAILURE"
    assert summary["issue_groups"][0]["retryable"] is True


def test_tampered_summary_hash_is_rejected(tmp_path, monkeypatch):
    summary = _build(tmp_path, monkeypatch, _runner())
    summary["counts"]["succeeded"] = 99
    result = validate_summary(summary)
    assert result["valid"] is False
    assert "integrity hash mismatch" in result["errors"]


def test_sensitive_input_and_output_values_are_not_copied(tmp_path, monkeypatch):
    summary = _build(tmp_path, monkeypatch, _runner())
    serialized = json.dumps(summary, ensure_ascii=False).lower()
    for value in ["top-secret", "cookie-value", "buyer@example.com", "private response", "customer-123"]:
        assert value.lower() not in serialized


def test_summary_round_trip_and_checked_example(tmp_path, monkeypatch):
    input_path, runner_path = _files(tmp_path)
    monkeypatch.setenv("RPA_PRODUCTION_ENTRYPOINT", "runner.py")
    path = write_summary(
        result=_runner(),
        repo_path=Path(__file__).resolve().parents[1],
        output_dir=tmp_path,
        input_path=input_path,
        runner_path=runner_path,
        started_at="2026-09-05T00:00:00Z",
        finished_at="2026-09-05T00:00:01Z",
    )
    assert path == tmp_path / "evidence" / "runs" / "A17-001.summary.json"
    assert validate_summary(path)["valid"] is True
    example = Path(__file__).resolve().parents[1] / "docs" / "examples" / "evidence_summary_success.json"
    assert validate_summary(example)["valid"] is True
