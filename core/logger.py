"""
core/logger.py — 运行日志记录器
===============================
每次运行生成 logs/run_{run_id}.log，同时写文件和控制台。
"""
import os
import time
from datetime import datetime


class RunLogger:
    """单次运行的日志记录器，同时输出到文件和控制台"""

    def __init__(self, run_id: str, repo_path: str = "."):
        self.run_id = run_id
        log_dir = os.path.join(repo_path, "logs")
        os.makedirs(log_dir, exist_ok=True)
        self.log_path = os.path.join(log_dir, "run_%s.log" % run_id)
        self._start_time = None
        self._fh = None

    def _write(self, level: str, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        line = "[%s] [%s] %s" % (ts, level, msg)
        print(line)
        if self._fh:
            try:
                self._fh.write(line + "\n")
                self._fh.flush()
            except Exception:
                pass

    def start(self, project: str, task_count: int):
        self._start_time = time.time()
        self._fh = open(self.log_path, "w", encoding="utf-8")
        self._write("INFO", "========== 运行开始 ==========")
        self._write("INFO", "run_id: %s | project: %s | tasks: %d" % (self.run_id, project, task_count))

    def task_start(self, task: dict):
        tid = task.get("id", "?")
        name = task.get("name", "unnamed")
        self._write("TASK", "开始: [%s] %s" % (tid, name))

    def task_end(self, task: dict, status: str, detail: str = ""):
        tid = task.get("id", "?")
        name = task.get("name", "unnamed")
        msg = "完成: [%s] %s -> %s" % (tid, name, status)
        if detail:
            msg += " (%s)" % detail
        self._write("TASK", msg)

    def exception(self, exc_info: dict):
        cat = exc_info.get("category", "unknown")
        code = exc_info.get("code", "")
        msg = exc_info.get("message", "")
        self._write("WARN" if cat == "business" else "ERROR",
                    "异常[%s]: %s %s" % (cat, code, msg))

    def external_call(self, name: str, duration: float, success: bool = True):
        status = "OK" if success else "FAIL"
        self._write("EXT", "%s %s (%.1fs)" % (name, status, duration))

    def end(self, status: str, success: int, total: int):
        elapsed = time.time() - self._start_time if self._start_time else 0
        self._write("INFO", "========== 运行结束 ==========")
        self._write("INFO", "status: %s | 成功: %d/%d | 耗时: %.1fs" % (status, success, total, elapsed))
        if self._fh:
            try:
                self._fh.close()
            except Exception:
                pass
            self._fh = None

    def info(self, msg: str):
        self._write("INFO", msg)

    def warn(self, msg: str):
        self._write("WARN", msg)
