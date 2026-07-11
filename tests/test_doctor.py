"""Tests for template doctor checks."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import doctor


def test_doctor_checks_pass_for_template():
    result = doctor.run_checks()
    assert result["status"] == "ok"
    assert result["checks"]
    failed = [item for item in result["checks"] if not item["ok"]]
    assert failed == []


def test_template_version_is_declared():
    version = (doctor.ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert version


def test_doctor_checks_example_inputs():
    result = doctor.run_checks()
    checks = {item["name"]: item for item in result["checks"]}
    assert checks["example_inputs"]["ok"] is True


def test_input_schema_repository_is_canonical():
    schema = doctor._load_json("schemas/input.schema.json")
    assert schema["$id"] == doctor.CANONICAL_SCHEMA_PREFIX + "input.schema.json"


def test_runtime_template_has_no_agent_workflow_dependency():
    assert not (doctor.ROOT / ".rpa_ai" / "workflow.template.json").exists()
    assert not (doctor.ROOT / "tools" / "handoff.py").exists()
