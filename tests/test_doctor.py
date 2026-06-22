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


def test_workflow_template_version_matches_version_file():
    version = (doctor.ROOT / "VERSION").read_text(encoding="utf-8").strip()
    workflow = doctor._load_json(".rpa_ai/workflow.template.json")
    assert workflow["template_version"] == version


def test_workflow_has_required_gates():
    workflow = doctor._load_json(".rpa_ai/workflow.template.json")
    gate_ids = {gate["id"] for gate in workflow["gates"]}
    assert "initialized" in gate_ids
    assert "contract_review" in gate_ids
    assert "minimal_implementation" in gate_ids
    assert "runtime_verification" in gate_ids
    assert "delivery" in gate_ids
