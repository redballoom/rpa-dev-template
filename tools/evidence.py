"""Create and verify portable, sanitized run evidence summaries."""
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

try:
    from .delivery_version import delivery_version
except ImportError:  # python tools/evidence.py
    from delivery_version import delivery_version


SCHEMA_VERSION = 2
SUMMARY_RELATIVE_DIR = Path("evidence") / "runs"
ALLOWED_TOP_LEVEL_FIELDS = {
    "schema_version",
    "run",
    "runtime",
    "counts",
    "issue_groups",
    "artifacts",
    "integrity",
}
DENIED_SOURCE_FIELDS = {
    "account",
    "api_key",
    "authorization",
    "cookie",
    "credentials",
    "message",
    "name",
    "payload",
    "response",
    "secret",
    "session",
    "task",
    "token",
    "traceback",
}
ALLOWED_NESTED_FIELDS = {
    "run": {"run_id", "status", "started_at", "finished_at", "commit", "working_tree_clean", "delivery_tree_clean"},
    "runtime": {"entrypoint", "interpreter"},
    "interpreter": {"implementation", "version", "executable", "environment"},
    "counts": {"tasks_planned", "tasks_recorded", "succeeded", "skipped", "failed", "warnings", "errors"},
    "issue_group": {"kind", "code", "category", "retryable", "count"},
    "artifacts": {"input", "runner_output"},
    "artifact": {"present", "bytes", "sha256"},
    "integrity": {"algorithm", "sha256"},
}


def utc_timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _canonical_bytes(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _artifact(path):
    if not path or not Path(path).is_file():
        return {"present": False, "bytes": 0, "sha256": ""}
    source = Path(path)
    return {
        "present": True,
        "bytes": source.stat().st_size,
        "sha256": _sha256_file(source),
    }


def _git_identity(repo_path):
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return {"commit": "", "working_tree_clean": False}
    value = completed.stdout.strip()
    commit = value if completed.returncode == 0 and re.fullmatch(r"[0-9a-fA-F]{40}", value) else ""
    if not commit:
        return {"commit": "", "working_tree_clean": False}
    try:
        status = subprocess.run(
            ["git", "-C", str(repo_path), "status", "--porcelain", "--untracked-files=all"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            check=False,
        )
        clean = status.returncode == 0 and not status.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        clean = False
    return {"commit": commit, "working_tree_clean": clean}


def _interpreter_identity(repo_path):
    executable = Path(sys.executable).resolve()
    root = Path(repo_path).resolve()
    try:
        executable_label = executable.relative_to(root).as_posix()
    except ValueError:
        executable_label = executable.name

    declared_environment = os.environ.get("RPA_PYTHON_ENV", "").strip()
    if declared_environment not in {"project_venv", "system"}:
        declared_environment = "virtualenv" if sys.prefix != getattr(sys, "base_prefix", sys.prefix) else "system"
    return {
        "implementation": platform.python_implementation(),
        "version": platform.python_version(),
        "executable": executable_label,
        "environment": declared_environment,
    }


def _count_results(result, input_data=None):
    data = result.get("data") if isinstance(result.get("data"), dict) else {}
    results = data.get("results") if isinstance(data.get("results"), list) else []
    warnings = data.get("warnings") if isinstance(data.get("warnings"), list) else []
    errors = data.get("errors") if isinstance(data.get("errors"), list) else []
    tasks = input_data.get("tasks") if isinstance(input_data, dict) else None
    return {
        "tasks_planned": len(tasks) if isinstance(tasks, list) else len(results),
        "tasks_recorded": len(results),
        "succeeded": sum(1 for item in results if isinstance(item, dict) and item.get("status") == "ok"),
        "skipped": sum(1 for item in results if isinstance(item, dict) and item.get("status") == "skipped"),
        "failed": sum(1 for item in results if isinstance(item, dict) and item.get("status") == "error"),
        "warnings": len(warnings),
        "errors": len(errors),
    }


def _group_issues(items, kind):
    counter = Counter()
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or "UNSPECIFIED")[:80]
        category = str(item.get("exc_category") or item.get("category") or kind)[:80]
        retryable = bool(item.get("retryable", False))
        counter[(code, category, retryable)] += 1
    return [
        {"kind": kind, "code": code, "category": category, "retryable": retryable, "count": count}
        for (code, category, retryable), count in sorted(counter.items())
    ]


def summary_path(output_dir, run_id):
    safe_run_id = re.sub(r"[^A-Za-z0-9._-]", "_", str(run_id)).strip("._") or "run"
    return Path(output_dir) / SUMMARY_RELATIVE_DIR / (safe_run_id + ".summary.json")


def build_summary(result, repo_path, input_path, runner_path, started_at, finished_at):
    data = result.get("data") if isinstance(result.get("data"), dict) else {}
    warnings = data.get("warnings") if isinstance(data.get("warnings"), list) else []
    errors = data.get("errors") if isinstance(data.get("errors"), list) else []
    input_data = None
    if input_path and Path(input_path).is_file():
        try:
            input_data = json.loads(Path(input_path).read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            input_data = None

    entrypoint = os.environ.get("RPA_PRODUCTION_ENTRYPOINT", "runner.py").strip() or "runner.py"
    version = delivery_version(repo_path)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "run": {
            "run_id": str(data.get("run_id") or ""),
            "status": str(result.get("status") or "fatal"),
            "started_at": started_at,
            "finished_at": finished_at,
            "commit": version["head"],
            "working_tree_clean": version["working_tree_clean"],
            "delivery_tree_clean": version["delivery_tree_clean"] if version["ok"] else False,
        },
        "runtime": {
            "entrypoint": entrypoint,
            "interpreter": _interpreter_identity(repo_path),
        },
        "counts": _count_results(result, input_data),
        "issue_groups": _group_issues(warnings, "warning") + _group_issues(errors, "error"),
        "artifacts": {
            "input": _artifact(input_path),
            "runner_output": _artifact(runner_path),
        },
    }
    summary["integrity"] = {
        "algorithm": "sha256",
        "sha256": hashlib.sha256(_canonical_bytes(summary)).hexdigest(),
    }
    return summary


def write_summary(result, repo_path, output_dir, input_path, runner_path, started_at, finished_at=None):
    finished_at = finished_at or utc_timestamp()
    destination = summary_path(output_dir, result.get("data", {}).get("run_id", "run"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    summary = build_summary(result, repo_path, input_path, runner_path, started_at, finished_at)
    destination.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destination


def validate_summary(summary_or_path):
    try:
        if isinstance(summary_or_path, (str, os.PathLike)):
            summary = json.loads(Path(summary_or_path).read_text(encoding="utf-8-sig"))
        else:
            summary = summary_or_path
    except (OSError, json.JSONDecodeError) as exc:
        return {"valid": False, "errors": ["summary cannot be read: %s" % exc]}

    errors = []
    if not isinstance(summary, dict):
        return {"valid": False, "errors": ["summary must be a JSON object"]}
    unexpected = sorted(set(summary) - ALLOWED_TOP_LEVEL_FIELDS)
    if unexpected:
        errors.append("unexpected top-level fields: %s" % ", ".join(unexpected))
    if summary.get("schema_version") not in (1, SCHEMA_VERSION):
        errors.append("unsupported schema_version")
    run = summary.get("run")
    if isinstance(run, dict):
        if summary.get("schema_version") == 2 and not isinstance(run.get("delivery_tree_clean"), bool):
            errors.append("delivery_tree_clean must be boolean for schema 2")
        if summary.get("schema_version") == 1 and "delivery_tree_clean" in run:
            errors.append("delivery_tree_clean is only available in schema 2")
    for field in ["run", "runtime", "counts", "issue_groups", "artifacts", "integrity"]:
        if field not in summary:
            errors.append("missing field: %s" % field)

    _check_allowed_fields(errors, summary.get("run"), "run")
    runtime = summary.get("runtime")
    _check_allowed_fields(errors, runtime, "runtime")
    _check_allowed_fields(errors, runtime.get("interpreter") if isinstance(runtime, dict) else None, "interpreter")
    _check_allowed_fields(errors, summary.get("counts"), "counts")
    issue_groups = summary.get("issue_groups")
    if not isinstance(issue_groups, list):
        errors.append("issue_groups must be an array")
    else:
        for item in issue_groups:
            _check_allowed_fields(errors, item, "issue_group")
    artifacts = summary.get("artifacts")
    _check_allowed_fields(errors, artifacts, "artifacts")
    if isinstance(artifacts, dict):
        _check_allowed_fields(errors, artifacts.get("input"), "artifact")
        _check_allowed_fields(errors, artifacts.get("runner_output"), "artifact")
    _check_allowed_fields(errors, summary.get("integrity"), "integrity")

    integrity = summary.get("integrity") if isinstance(summary.get("integrity"), dict) else {}
    expected = integrity.get("sha256", "")
    unsigned = dict(summary)
    unsigned.pop("integrity", None)
    actual = hashlib.sha256(_canonical_bytes(unsigned)).hexdigest()
    if integrity.get("algorithm") != "sha256" or not re.fullmatch(r"[0-9a-f]{64}", str(expected)):
        errors.append("invalid integrity metadata")
    elif expected != actual:
        errors.append("integrity hash mismatch")

    serialized_keys = {str(key).lower() for key in _walk_keys(summary)}
    leaked = sorted(serialized_keys & DENIED_SOURCE_FIELDS)
    if leaked:
        errors.append("denied fields present: %s" % ", ".join(leaked))
    return {"valid": not errors, "errors": errors, "sha256": actual}


def _check_allowed_fields(errors, value, kind):
    if not isinstance(value, dict):
        errors.append("%s must be an object" % kind)
        return
    unexpected = sorted(set(value) - ALLOWED_NESTED_FIELDS[kind])
    if unexpected:
        errors.append("unexpected %s fields: %s" % (kind, ", ".join(unexpected)))


def _walk_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Verify a portable RPA evidence summary")
    parser.add_argument("summary", help="evidence/runs/{run_id}.summary.json")
    args = parser.parse_args(argv)
    result = validate_summary(args.summary)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
