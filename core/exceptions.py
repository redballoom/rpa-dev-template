"""
core/exceptions.py - Exception router with crash snapshot support
L1: BusinessException -> collect, Feishu summary
L2: SystemException -> Linear issue + crash snapshot
"""

import traceback, os, re, json
from datetime import datetime
from typing import Optional, Dict, Any
from core.notifier import create_linear_issue


def _parse_traceback(tb_str: str) -> Dict[str, Any]:
    result = {"error_type": "", "error_message": "", "file": "", "function": "",
              "line_no": "", "code_line": "", "frames": []}
    if not tb_str or tb_str == "NoneType: None":
        return result
    exc_match = re.search(
        r"(\w+Error|\w+Exception|AssertionError|KeyError|IndexError|"
        r"AttributeError|TypeError|ValueError|RuntimeError|ImportError|"
        r"FileNotFoundError|ZeroDivisionError|ConnectionError|TimeoutError|"
        r"json\.decoder\.JSONDecodeError|requests\.exceptions\.\w+):\s*(.*)", tb_str)
    if exc_match:
        result["error_type"] = exc_match.group(1)
        result["error_message"] = exc_match.group(2).strip()
    frames = re.findall(r'File "(.+?)", line (\d+), in (\w+)\s*
\s*(.+)', tb_str)
    for f in frames:
        result["frames"].append({"file": f[0], "line": f[1], "function": f[2], "code": f[3].strip()})
    if frames:
        last = frames[-1]
        result["file"] = last[0]; result["line_no"] = last[1]
        result["function"] = last[2]; result["code_line"] = last[3].strip()
    return result


def _short_path(full_path: str) -> str:
    for marker in ["core" + os.sep, "commands" + os.sep, "tests" + os.sep]:
        idx = full_path.find(marker)
        if idx != -1: return full_path[idx:]
    return os.path.basename(full_path)


class BusinessException(Exception):
    def __init__(self, message: str, project: str = "", context: Optional[dict] = None):
        super().__init__(message)
        self.project = project; self.context = context or {}; self.category = "business"
    def notify(self) -> dict:
        return {"category": "business", "message": str(self), "project": self.project, "context": self.context}


class SystemException(Exception):
    def __init__(self, message: str, project: str = "", payload: Optional[dict] = None,
                 action: str = "", expected: str = "", actual: str = ""):
        super().__init__(message)
        self.project = project; self.traceback_str = traceback.format_exc()
        self.payload = payload or {}; self.category = "system"
        self.action = action; self.expected = expected; self.actual = actual or message
        parsed = _parse_traceback(self.traceback_str)
        self.error_type = parsed["error_type"]; self.error_file = _short_path(parsed["file"])
        self.error_function = parsed["function"]; self.error_line = parsed["line_no"]
        self.error_code = parsed["code_line"]

    def _dump_snapshot(self, run_id: str, repo_path: str = ".") -> str:
        snapshot = {
            "snapshot_type": "crash", "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "run_id": run_id, "error_type": self.error_type, "message": str(self),
            "action": self.action, "expected": self.expected, "actual": self.actual,
            "traceback": self.traceback_str,
            "file": self.error_file, "function": self.error_function,
            "line": self.error_line, "code": self.error_code,
            "payload": self.payload, "project": self.project,
        }
        snap_dir = os.path.join(repo_path, "crash_snapshots")
        os.makedirs(snap_dir, exist_ok=True)
        path = os.path.join(snap_dir, "crash_%s.json" % run_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)
        print("[exceptions] Snapshot:", path)
        return path

    def notify(self, extra_payload: Optional[dict] = None, repo_path: str = ".") -> dict:
        merged = {**self.payload}
        if extra_payload: merged.update(extra_payload)
        run_id = extra_payload.get("run_id", "unknown") if extra_payload else "unknown"
        self._dump_snapshot(run_id=run_id, repo_path=repo_path)
        ir = create_linear_issue(error_msg=str(self), trace=self.traceback_str,
            payload_data=merged if merged else {}, project=self.project, repo_path=repo_path,
            error_type=self.error_type, error_file=self.error_file,
            error_function=self.error_function, error_line=self.error_line,
            error_code=self.error_code, action=self.action, expected=self.expected, actual=self.actual)
        if isinstance(ir, dict):
            return {"category": "system", "message": str(self), "project": self.project,
                    "error_type": self.error_type, "error_file": self.error_file,
                    "issue_success": ir.get("success", False), "issue_url": ir.get("issue_url", "")}
        return {"category": "system", "message": str(self), "project": self.project,
                "error_type": self.error_type, "error_file": self.error_file,
                "issue_success": bool(ir), "issue_url": ""}
