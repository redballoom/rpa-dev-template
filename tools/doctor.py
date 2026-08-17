"""Template health checks for portability and runtime readiness."""
import json
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
    "schemas/input.schema.json",
    "schemas/output.schema.json",
]

JSON_FILES = [
    "project.template.json",
    "schemas/input.schema.json",
    "schemas/output.schema.json",
]

GITIGNORE_PATTERNS = [
    "/project.json",
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


def _check_version(checks):
    try:
        version = _read_text(ROOT / "VERSION").strip()
    except OSError as exc:
        _add_check(checks, "version", False, str(exc))
        return
    _add_check(checks, "version", bool(version), "VERSION is declared" if version else "VERSION is empty")


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
    scanned = ["README.md", "AGENTS.md", "project.template.json"]
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


def _check_example_inputs(checks):
    examples_dir = ROOT / "docs" / "examples"
    examples = sorted(examples_dir.glob("input_*.json")) if examples_dir.exists() else []
    errors = []
    for path in examples:
        try:
            json.loads(path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as exc:
            errors.append("%s: %s" % (path.name, exc))
    ok = bool(examples) and not errors
    message = "example input files are present and parse successfully" if ok else (
        "; ".join(errors) if errors else "docs/examples has no input_*.json files"
    )
    _add_check(checks, "example_inputs", ok, message)


def _check_canonical_repositories(checks):
    errors = []
    for schema_name in ["input.schema.json", "output.schema.json"]:
        schema_path = "schemas/" + schema_name
        schema = _load_json(schema_path)
        expected_id = CANONICAL_SCHEMA_PREFIX + schema_name
        if schema.get("$id") != expected_id:
            errors.append("%s $id=%s" % (schema_path, schema.get("$id")))

    combined = ""
    for item in ["README.md", "AGENTS.md", "docs/OPERATION_GUIDE.md"]:
        path = ROOT / item
        if path.exists():
            combined += _read_text(path)
    if CANONICAL_SKILLS_REPO not in combined:
        errors.append("canonical skills repository is not documented")

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
    _check_version(checks)
    _check_gitignore(checks)
    _check_portability(checks)
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
