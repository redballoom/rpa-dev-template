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


def test_example_inputs_match_runtime_contract():
    from runner import _validate_input_contract

    for path in sorted((doctor.ROOT / "docs" / "examples").glob("input_*.json")):
        relative_path = path.relative_to(doctor.ROOT).as_posix()
        assert _validate_input_contract(doctor._load_json(relative_path)) == [], path.name


def test_input_schema_repository_is_canonical():
    schema = doctor._load_json("schemas/input.schema.json")
    assert schema["$id"] == doctor.CANONICAL_SCHEMA_PREFIX + "input.schema.json"
    assert "schema_version" in schema["required"]
    assert schema["properties"]["schema_version"]["const"] == "1.0"


def test_output_schema_repository_is_canonical():
    schema = doctor._load_json("schemas/output.schema.json")
    assert schema["$id"] == doctor.CANONICAL_SCHEMA_PREFIX + "output.schema.json"
    assert "fatal" in schema["properties"]["status"]["enum"]
    assert "failed" not in schema["properties"]["status"]["enum"]
    assert "run_id" in schema["properties"]["data"]["required"]


def test_evidence_schema_and_runtime_entrypoint_are_canonical():
    schema = doctor._load_json("schemas/evidence-summary.schema.json")
    assert schema["$id"] == doctor.CANONICAL_SCHEMA_PREFIX + "evidence-summary.schema.json"
    checks = {item["name"]: item for item in doctor.run_checks()["checks"]}
    assert checks["runtime_entrypoint"]["ok"] is True


def test_runtime_template_has_no_agent_workflow_dependency():
    assert not (doctor.ROOT / ".rpa_ai" / "workflow.template.json").exists()
    assert not (doctor.ROOT / "tools" / "handoff.py").exists()
