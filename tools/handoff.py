"""Manage AI workspace handoff files for the RPA template."""
import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".rpa_ai" / "workflow.template.json"
ALLOWED_STATUSES = {"draft", "ready_for_review", "approved", "blocked", "completed"}
STATUS_ALIASES = {
    "ready": "ready_for_review",
    "ready-for-review": "ready_for_review",
    "review": "ready_for_review",
    "reviewed": "ready_for_review",
    "verified": "completed",
    "delivered": "completed",
    "done": "completed",
    "complete": "completed",
}


class HandoffError(Exception):
    """Raised when a handoff file is invalid or cannot be advanced."""


def _load_json(path):
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def load_workflow():
    return _load_json(WORKFLOW_PATH)


def get_handoff_paths(workflow=None):
    workflow = workflow or load_workflow()
    handoff = workflow.get("handoff", {})
    current = ROOT / handoff.get("current", ".rpa_ai/handoff/current.json")
    history_dir = ROOT / handoff.get("history_dir", ".rpa_ai/handoff/history")
    return current, history_dir


def get_gate(workspace, workflow=None):
    workflow = workflow or load_workflow()
    for gate in workflow.get("gates", []):
        if gate.get("id") == workspace:
            return gate
    return None


def list_gate_ids(workflow=None):
    workflow = workflow or load_workflow()
    return [gate.get("id") for gate in workflow.get("gates", [])]


def create_handoff(workspace, status="draft", project_path="", run_id="", require_confirmation=True):
    workflow = load_workflow()
    gate = get_gate(workspace, workflow)
    if gate is None:
        raise HandoffError("unknown workspace: %s" % workspace)
    data = {
        "workflow_schema_version": workflow.get("workflow_schema_version", "1.0.0"),
        "workspace": workspace,
        "gate": workspace,
        "status": status,
        "project_path": project_path,
        "run_id": run_id,
        "decisions": [],
        "artifacts": [],
        "verification": [],
        "risks": [],
        "next_workspace": gate.get("next", ""),
        "requires_user_confirmation": require_confirmation,
        "created_at": _now(),
        "updated_at": _now(),
    }
    validate_handoff_data(data, workflow)
    current, _history_dir = get_handoff_paths(workflow)
    _write_json(current, data)
    return data


def load_current_handoff():
    workflow = load_workflow()
    current, _history_dir = get_handoff_paths(workflow)
    if not current.exists():
        raise HandoffError("handoff file does not exist: %s" % current)
    return _load_json(current)


def validate_current_handoff():
    workflow = load_workflow()
    data = load_current_handoff()
    validate_handoff_data(data, workflow)
    return data


def validate_handoff_data(data, workflow=None):
    workflow = workflow or load_workflow()
    errors = []
    required = [
        "workflow_schema_version",
        "workspace",
        "status",
        "artifacts",
        "verification",
        "risks",
        "next_workspace",
        "requires_user_confirmation",
    ]
    for key in required:
        if key not in data:
            errors.append("missing required field: %s" % key)

    string_fields = ["workflow_schema_version", "workspace", "status", "next_workspace"]
    optional_string_fields = ["gate", "project_path", "run_id"]
    list_fields = ["decisions", "artifacts", "verification", "risks"]
    for key in string_fields:
        if key in data and not isinstance(data[key], str):
            errors.append("%s must be a string" % key)
    for key in optional_string_fields:
        if key in data and data[key] is not None and not isinstance(data[key], str):
            errors.append("%s must be a string" % key)
    for key in list_fields:
        if key in data and not _is_string_list(data[key]):
            errors.append("%s must be a list of strings" % key)
    if "requires_user_confirmation" in data and not isinstance(data["requires_user_confirmation"], bool):
        errors.append("requires_user_confirmation must be a boolean")

    if data.get("status") not in ALLOWED_STATUSES:
        errors.append("invalid status: %s" % data.get("status"))

    gate_ids = set(list_gate_ids(workflow))
    workspace = data.get("workspace", "")
    if workspace and workspace not in gate_ids:
        errors.append("unknown workspace: %s" % workspace)
    next_workspace = data.get("next_workspace", "")
    if next_workspace and next_workspace not in gate_ids:
        errors.append("unknown next_workspace: %s" % next_workspace)

    expected_schema = workflow.get("workflow_schema_version")
    if data.get("workflow_schema_version") != expected_schema:
        errors.append(
            "workflow_schema_version mismatch: %s != %s"
            % (data.get("workflow_schema_version"), expected_schema)
        )

    if errors:
        raise HandoffError("; ".join(errors))
    return True


def archive_current_handoff(label=""):
    workflow = load_workflow()
    current, history_dir = get_handoff_paths(workflow)
    data = validate_current_handoff()
    history_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    workspace = data.get("workspace", "handoff")
    suffix = ("_%s" % _safe_slug(label)) if label else ""
    archived = history_dir / ("%s_%s%s.json" % (timestamp, _safe_slug(workspace), suffix))
    shutil.copy2(current, archived)
    return archived


def close_current_handoff(
    status="ready_for_review",
    decisions=None,
    artifacts=None,
    verification=None,
    risks=None,
    next_workspace=None,
    project_path=None,
    run_id=None,
    require_confirmation=None,
):
    workflow = load_workflow()
    data = validate_current_handoff()
    data["status"] = normalize_status(status)
    _append_unique(data, "decisions", decisions or [])
    _append_unique(data, "artifacts", artifacts or [])
    _append_unique(data, "verification", verification or [])
    _append_unique(data, "risks", risks or [])
    if next_workspace is not None:
        if next_workspace and get_gate(next_workspace, workflow) is None:
            raise HandoffError("unknown next_workspace: %s" % next_workspace)
        data["next_workspace"] = next_workspace
    if project_path is not None:
        data["project_path"] = project_path
    if run_id is not None:
        data["run_id"] = run_id
    if require_confirmation is not None:
        data["requires_user_confirmation"] = require_confirmation
    data["updated_at"] = _now()
    validate_handoff_data(data, workflow)
    current, _history_dir = get_handoff_paths(workflow)
    _write_json(current, data)
    return data


def advance_handoff(next_workspace=None, archive=True):
    workflow = load_workflow()
    data = validate_current_handoff()
    current_workspace = data["workspace"]
    current_gate = get_gate(current_workspace, workflow)
    target = next_workspace or data.get("next_workspace") or (current_gate or {}).get("next", "")
    if not target:
        raise HandoffError("current workspace has no next workspace")
    if get_gate(target, workflow) is None:
        raise HandoffError("unknown next workspace: %s" % target)
    if archive:
        archive_current_handoff(label="before_%s" % target)
    return create_handoff(
        target,
        status="draft",
        project_path=data.get("project_path", ""),
        run_id=data.get("run_id", ""),
        require_confirmation=True,
    )


def _is_string_list(value):
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def normalize_status(status):
    normalized = str(status or "").strip()
    normalized = STATUS_ALIASES.get(normalized, normalized)
    normalized = STATUS_ALIASES.get(normalized.lower(), normalized)
    normalized = normalized.replace(" ", "_")
    return normalized


def _append_unique(data, key, values):
    current = data.setdefault(key, [])
    seen = set(current)
    for value in values:
        item = str(value).strip()
        if item and item not in seen:
            current.append(item)
            seen.add(item)


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_slug(value):
    chars = []
    for ch in str(value):
        if ch.isalnum() or ch in ("-", "_"):
            chars.append(ch)
        else:
            chars.append("-")
    return "".join(chars).strip("-") or "handoff"


def _print_result(status, data):
    print(json.dumps({"status": status, "data": data}, ensure_ascii=False, indent=2))


def build_parser():
    parser = argparse.ArgumentParser(description="Manage RPA AI handoff files")
    sub = parser.add_subparsers(dest="command", required=True)

    init_p = sub.add_parser("init", help="create .rpa_ai/handoff/current.json")
    init_p.add_argument("--workspace", default="initialized", help="workflow gate id")
    init_p.add_argument("--status", default="draft", help="handoff status")
    init_p.add_argument("--project-path", default="", help="project path to record")
    init_p.add_argument("--run-id", default="", help="run id to record")
    init_p.add_argument(
        "--no-confirmation",
        action="store_true",
        help="set requires_user_confirmation=false",
    )

    sub.add_parser("validate", help="validate current handoff")

    close_p = sub.add_parser("close", help="record gate decisions, artifacts, checks, and risks")
    close_p.add_argument("--status", default="ready_for_review", help="handoff status or known alias")
    close_p.add_argument("--decision", action="append", default=[], help="decision to append")
    close_p.add_argument("--artifact", action="append", default=[], help="artifact path or note to append")
    close_p.add_argument("--verification", action="append", default=[], help="verification result to append")
    close_p.add_argument("--risk", action="append", default=[], help="risk or follow-up to append")
    close_p.add_argument("--next", default=None, help="override next workflow gate")
    close_p.add_argument("--project-path", default=None, help="override recorded project path")
    close_p.add_argument("--run-id", default=None, help="override recorded run id")
    close_p.add_argument(
        "--no-confirmation",
        action="store_true",
        help="set requires_user_confirmation=false",
    )

    advance_p = sub.add_parser("advance", help="archive current handoff and create the next one")
    advance_p.add_argument("--next", default="", help="target workflow gate id")
    advance_p.add_argument("--no-archive", action="store_true", help="do not archive before advancing")

    archive_p = sub.add_parser("archive", help="archive current handoff")
    archive_p.add_argument("--label", default="", help="optional archive label")

    sub.add_parser("show", help="print current handoff")
    sub.add_parser("gates", help="print available workflow gates")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            data = create_handoff(
                args.workspace,
                status=args.status,
                project_path=args.project_path,
                run_id=args.run_id,
                require_confirmation=not args.no_confirmation,
            )
            _print_result("ok", data)
        elif args.command == "validate":
            data = validate_current_handoff()
            _print_result("ok", data)
        elif args.command == "close":
            data = close_current_handoff(
                status=args.status,
                decisions=args.decision,
                artifacts=args.artifact,
                verification=args.verification,
                risks=args.risk,
                next_workspace=args.next,
                project_path=args.project_path,
                run_id=args.run_id,
                require_confirmation=False if args.no_confirmation else None,
            )
            _print_result("ok", data)
        elif args.command == "advance":
            data = advance_handoff(next_workspace=args.next or None, archive=not args.no_archive)
            _print_result("ok", data)
        elif args.command == "archive":
            archived = archive_current_handoff(label=args.label)
            _print_result("ok", {"archived": str(archived)})
        elif args.command == "show":
            _print_result("ok", load_current_handoff())
        elif args.command == "gates":
            workflow = load_workflow()
            _print_result("ok", workflow.get("gates", []))
    except HandoffError as exc:
        _print_result("failed", {"error": str(exc)})
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
