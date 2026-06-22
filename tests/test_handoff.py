"""Tests for AI handoff lifecycle utilities."""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import handoff


def _patch_paths(monkeypatch, tmp_path):
    workflow = handoff.load_workflow()
    patched = dict(workflow)
    patched["handoff"] = {
        "current": str(tmp_path / "current.json"),
        "history_dir": str(tmp_path / "history"),
    }
    monkeypatch.setattr(handoff, "load_workflow", lambda: patched)
    return patched


def test_create_handoff_writes_current_file(monkeypatch, tmp_path):
    workflow = _patch_paths(monkeypatch, tmp_path)
    data = handoff.create_handoff("contract_review", project_path="C:/demo")
    current, _history = handoff.get_handoff_paths(workflow)
    assert current.exists()
    assert data["workspace"] == "contract_review"
    assert data["next_workspace"] == "minimal_implementation"
    assert data["project_path"] == "C:/demo"


def test_validate_rejects_unknown_workspace():
    workflow = handoff.load_workflow()
    data = {
        "workflow_schema_version": workflow["workflow_schema_version"],
        "workspace": "unknown",
        "status": "draft",
        "artifacts": [],
        "verification": [],
        "risks": [],
        "next_workspace": "",
        "requires_user_confirmation": True,
    }
    try:
        handoff.validate_handoff_data(data, workflow)
    except handoff.HandoffError as exc:
        assert "unknown workspace" in str(exc)
    else:
        raise AssertionError("expected HandoffError")


def test_archive_current_handoff(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    handoff.create_handoff("initialized")
    archived = handoff.archive_current_handoff(label="reviewed")
    assert archived.exists()
    assert archived.parent == tmp_path / "history"
    assert "initialized" in archived.name


def test_advance_handoff_creates_next_and_archives(monkeypatch, tmp_path):
    workflow = _patch_paths(monkeypatch, tmp_path)
    handoff.create_handoff("initialized", project_path="C:/demo", run_id="r1")
    advanced = handoff.advance_handoff()
    current, history_dir = handoff.get_handoff_paths(workflow)
    assert current.exists()
    assert advanced["workspace"] == "contract_review"
    assert advanced["next_workspace"] == "minimal_implementation"
    assert advanced["project_path"] == "C:/demo"
    assert advanced["run_id"] == "r1"
    assert list(Path(history_dir).glob("*.json"))


def test_cli_gates_outputs_gate_list(capsys):
    rc = handoff.main(["gates"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "contract_review" in captured.out
