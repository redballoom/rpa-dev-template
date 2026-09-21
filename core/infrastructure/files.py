"""Safe project-relative paths and atomic JSON writes."""
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Tuple


class PathPolicyError(ValueError):
    """Raised when a business path escapes its declared project directory."""


def resolve_project_path(
    repo_path: str,
    path_value: str,
    *,
    allowed_dir: str,
) -> Tuple[Path, str]:
    """Resolve a path and ensure it remains under ``repo_path/allowed_dir``."""
    root = Path(repo_path).resolve()
    allowed_root = (root / allowed_dir).resolve()
    raw = Path(path_value)
    candidate = raw.resolve() if raw.is_absolute() else (root / raw).resolve()

    try:
        candidate.relative_to(allowed_root)
    except ValueError as exc:
        raise PathPolicyError(
            "path must stay under %s: %s" % (allowed_dir.replace("\\", "/"), path_value)
        ) from exc

    return candidate, candidate.relative_to(root).as_posix()


def atomic_write_json(path: Path, data: Any) -> None:
    """Write JSON beside its destination and atomically replace the target."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = ""
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".tmp",
            prefix=path.name + ".",
            dir=str(path.parent),
            delete=False,
        ) as handle:
            temp_name = handle.name
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.remove(temp_name)
