"""Template health checks for portability, handoff, and upgrade readiness."""
import json
import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_TEMPLATE_REPO = "https://github.com/redballoom/rpa-dev-template"
CANONICAL_SKILLS_REPO = "https://github.com/redballoom/rpa-dev-template-skills"
CANONICAL_SCHEMA_PREFIX = CANONICAL_TEMPLATE_REPO + "/schemas/"

REQUIRED_FILES = [
    "VERSION",
    "README.md",
    "AGENTS.md",
    "project.template.json",
    "runner.py",
    "run.bat",
    "core/entry.py",
    "docs/OPERATION_GUIDE.md",
    "docs/SHADOWBOT_INPUT_CONTRACT.md",
    "docs/ISSUE_FIX_WORKFLOW.md",
    ".rpa_ai/workflow.template.json",
    "schemas/workflow.schema.json",
    "schemas/handoff.schema.json",
    "schemas/input.schema.json",
    "tools/handoff.py",
]

JSON_FILES = [
    "project.template.json",
    ".rpa_ai/workflow.template.json",
    "schemas/workflow.schema.json",
    "schemas/handoff.schema.json",
    "schemas/input.schema.json",
]

GITIGNORE_PATTERNS = [
    "project.json",
    "runner_*.json",
    "/input_*.json",
    "logs/",
    "crash_snapshots/",
    "data/",
]


def _read_text(path):
    return path.read_text(encoding="utf-8")


def _load_json(relative_path):
    with (ROOT / relative_path).open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def _add_check(checks, name, ok, message):
    checks.append({"name": name, "ok": bool(ok), "message": message})


def _check_required_files(checks):
    missing = [item for item in REQUIRED_FILES if not (ROOT / item).exists()]
    _add_check(
        checks,
        "required_files",
        not missing,
        "all required files exist" if not missing else "missing: %s" % ", ".join(missing),
    )


def _check_json_files(checks):
    errors = []
    for item in JSON_FILES:
        try:
            _load_json(item)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append("%s: %s" % (item, exc))
    _add_check(
        checks,
        "json_parse",
        not errors,
        "json files parse successfully" if not errors else "; ".join(errors),
    )


def _check_version_alignment(checks):
    try:
        version = _read_text(ROOT / "VERSION").strip()
        workflow = _load_json(".rpa_ai/workflow.template.json")
    except (OSError, json.JSONDecodeError) as exc:
        _add_check(checks, "version_alignment", False, str(exc))
        return
    workflow_version = str(workflow.get("template_version", "")).strip()
    ok = bool(version) and version == workflow_version
    _add_check(
        checks,
        "version_alignment",
        ok,
        "VERSION matches workflow template" if ok else "VERSION=%s workflow=%s" % (version, workflow_version),
    )


def _check_workflow_shape(checks):
    try:
        workflow = _load_json(".rpa_ai/workflow.template.json")
    except (OSError, json.JSONDecodeError) as exc:
        _add_check(checks, "workflow_shape", False, str(exc))
        return
    gates = workflow.get("gates", [])
    gate_ids = [gate.get("id") for gate in gates if isinstance(gate, dict)]
    required = {"initialized", "contract_review", "minimal_implementation", "runtime_verification", "delivery"}
    ok = required.issubset(set(gate_ids)) and workflow.get("required_skills")
    _add_check(
        checks,
        "workflow_shape",
        ok,
        "workflow gates and required skills are present" if ok else "workflow gates or required skills incomplete",
    )


def _check_gitignore(checks):
    try:
        gitignore = _read_text(ROOT / ".gitignore")
    except OSError as exc:
        _add_check(checks, "gitignore_runtime_outputs", False, str(exc))
        return
    missing = [item for item in GITIGNORE_PATTERNS if item not in gitignore]
    _add_check(
        checks,
        "gitignore_runtime_outputs",
        not missing,
        "runtime outputs are ignored" if not missing else "missing ignore rules: %s" % ", ".join(missing),
    )


def _check_portability(checks):
    scanned = [
        "README.md",
        "AGENTS.md",
        "project.template.json",
        ".rpa_ai/workflow.template.json",
    ]
    hits = []
    local_path_pattern = re.compile(r"[A-Za-z]:\\Users\\|C:\\Users\\redballoon", re.IGNORECASE)
    for item in scanned:
        path = ROOT / item
        if path.exists() and local_path_pattern.search(_read_text(path)):
            hits.append(item)
    _add_check(
        checks,
        "portable_paths",
        not hits,
        "no local absolute user paths in template control files" if not hits else "local paths found in: %s" % ", ".join(hits),
    )


def _check_docs_link_workflow(checks):
    try:
        readme = _read_text(ROOT / "README.md")
        agents = _read_text(ROOT / "AGENTS.md")
    except OSError as exc:
        _add_check(checks, "workflow_docs_linked", False, str(exc))
        return
    needed = [".rpa_ai/workflow.template.json", "tools/doctor.py", "tools/handoff.py", "schemas/"]
    missing = [item for item in needed if item not in readme + agents]
    _add_check(
        checks,
        "workflow_docs_linked",
        not missing,
        "workflow productization files are documented" if not missing else "missing doc references: %s" % ", ".join(missing),
    )


def _check_example_inputs(checks):
    examples_dir = ROOT / "docs" / "examples"
    if not examples_dir.exists():
        _add_check(checks, "example_inputs", False, "docs/examples is missing")
        return
    examples = sorted(examples_dir.glob("input_*.json"))
    if not examples:
        _add_check(checks, "example_inputs", False, "docs/examples has no input_*.json files")
        return
    errors = []
    for path in examples:
        try:
            json.loads(path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as exc:
            errors.append("%s: %s" % (path.name, exc))
    _add_check(
        checks,
        "example_inputs",
        not errors,
        "example input files are present and parse successfully" if not errors else "; ".join(errors),
    )


def _check_canonical_repositories(checks):
    errors = []
    try:
        workflow = _load_json(".rpa_ai/workflow.template.json")
    except (OSError, json.JSONDecodeError) as exc:
        _add_check(checks, "canonical_repositories", False, str(exc))
        return

    if workflow.get("template_repo") != CANONICAL_TEMPLATE_REPO:
        errors.append("template_repo=%s" % workflow.get("template_repo"))
    if workflow.get("skills_repo") != CANONICAL_SKILLS_REPO:
        errors.append("skills_repo=%s" % workflow.get("skills_repo"))

    for schema_name in ["workflow.schema.json", "handoff.schema.json", "input.schema.json"]:
        rel_path = "schemas/%s" % schema_name
        try:
            schema = _load_json(rel_path)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append("%s: %s" % (rel_path, exc))
            continue
        expected_id = CANONICAL_SCHEMA_PREFIX + schema_name
        if schema.get("$id") != expected_id:
            errors.append("%s $id=%s" % (rel_path, schema.get("$id")))

    polluted_skill_links = []
    skill_link_pattern = re.compile(
        r"https://github\.com/redballoom/(?!rpa-dev-template-skills\b)[^\s`)\"']+-skills\b"
    )
    for item in ["README.md", "AGENTS.md", "docs/OPERATION_GUIDE.md"]:
        path = ROOT / item
        if not path.exists():
            continue
        text = _read_text(path)
        if CANONICAL_SKILLS_REPO not in text:
            errors.append("%s missing canonical skills repo" % item)
        polluted_skill_links.extend("%s: %s" % (item, link) for link in skill_link_pattern.findall(text))
    errors.extend(polluted_skill_links)

    _add_check(
        checks,
        "canonical_repositories",
        not errors,
        "template and skills repository references are canonical" if not errors else "; ".join(errors),
    )


def run_checks():
    checks = []
    _check_required_files(checks)
    _check_json_files(checks)
    _check_version_alignment(checks)
    _check_workflow_shape(checks)
    _check_gitignore(checks)
    _check_portability(checks)
    _check_docs_link_workflow(checks)
    _check_example_inputs(checks)
    _check_canonical_repositories(checks)
    ok = all(item["ok"] for item in checks)
    return {
        "status": "ok" if ok else "failed",
        "template_root": str(ROOT),
        "python": sys.version.split()[0],
        "checks": checks,
    }


def main():
    result = run_checks()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
