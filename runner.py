"""
runner.py — 影刀 RPA 调度入口
==============================
影刀通过 run.bat 调用此文件，传入 input_{run_id}.json。
runner.py 读取输入 → 调用 core.entry.run_tasks() → 输出 runner_{run_id}.json。

职责边界：
  影刀：组织输入参数 → 调用 run.bat → 读取结果 JSON → 按 status 分支
  Python：加载配置 → 读取输入 → 执行业务 → 异常分类 → 输出结果 → 写日志 → 通知
"""
import sys, os, json, argparse, traceback

try:
    if hasattr(sys.stdout, 'encoding') and sys.stdout.encoding and sys.stdout.encoding.upper() == "GBK":
        import io
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except AttributeError:
    pass


class _FileLock:
    def __init__(self, lock_path):
        self.lock_path = lock_path
        self._acquired = False

    def try_acquire(self, timeout=10):
        import time
        deadline = time.time() + max(timeout, 0)
        tried = False
        while not tried or time.time() < deadline:
            tried = True
            if self._try_lock():
                self._acquired = True
                return True
            if timeout <= 0:
                break
            time.sleep(0.5)
        return False

    def _try_lock(self):
        try:
            my_pid = os.getpid()
            if os.path.exists(self.lock_path):
                with open(self.lock_path, "r") as f:
                    content = f.read().strip()
                if content:
                    try:
                        pid = int(content)
                        if self._is_pid_alive(pid):
                            return False
                    except ValueError:
                        pass
            with open(self.lock_path, "w") as f:
                f.write(str(my_pid))
            with open(self.lock_path, "r") as f:
                return f.read().strip() == str(my_pid)
        except Exception:
            return False

    def _is_pid_alive(self, pid):
        try:
            if os.name == "nt":
                import ctypes
                h = ctypes.windll.kernel32.OpenProcess(0x0400, False, pid)
                if h:
                    ctypes.windll.kernel32.CloseHandle(h)
                    return True
                return False
            else:
                os.kill(pid, 0)
                return True
        except (OSError, AttributeError):
            return False

    def release(self):
        if self._acquired and os.path.exists(self.lock_path):
            try:
                os.remove(self.lock_path)
            except (OSError, PermissionError):
                pass
        self._acquired = False


def _read_input_file(input_path: str):
    """
    读取标准输入文件 input_{run_id}.json。
    返回 dict 或 None（文件不存在/格式非法）。
    """
    if not os.path.exists(input_path):
        print("[runner] ERROR: input file not found: %s" % input_path)
        return None
    try:
        # 兼容 Windows/PowerShell 可能写出的 UTF-8 BOM
        with open(input_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        # 基本校验
        if not isinstance(data, dict):
            print("[runner] ERROR: input file is not a JSON object")
            return None
        return data
    except (json.JSONDecodeError, IOError) as e:
        print("[runner] ERROR: input file parse failed: %s" % e)
        return None


def execute(run_id, repo_path, input_file=None, output_dir=None, work_dir=None, project_override=None):
    """
    主执行函数。

    Args:
        run_id:     运行 ID（影刀生成）
        repo_path:  仓库路径
        input_file: 输入文件路径（input_{run_id}.json）
        output_dir: 输出目录（默认 = repo_path）
    """
    if repo_path in sys.path:
        sys.path.remove(repo_path)
    sys.path.insert(0, repo_path)
    if output_dir is None:
        output_dir = repo_path
    os.makedirs(output_dir, exist_ok=True)
    sf = os.path.join(output_dir, "runner_%s.json" % run_id)

    # ── 并发锁 ──────────────────────────────────────────────
    lock = _FileLock(os.path.join(repo_path, ".runner.lock"))
    if not lock.try_acquire(timeout=0):
        rd = {"status": "locked", "message": "Locked: %s" % repo_path,
              "data": {"run_id": run_id, "retryable": True,
                       "log_path": "", "crash_snapshot_dir": "",
                       "results": [], "warnings": [], "errors": []}}
        with open(sf, "w", encoding="utf-8") as f:
            json.dump(rd, f, ensure_ascii=False, indent=2)
        print("[runner] !! Locked: %s" % repo_path)
        return sf

    try:
        # ── 读取输入 ────────────────────────────────────────
        project = project_override or "dev-template"
        tasks = []
        context = {}

        if input_file:
            input_data = _read_input_file(input_file)
            if input_data is None:
                # 输入文件不存在或非法 → fatal
                rd = {"status": "fatal", "message": "Input file invalid: %s" % input_file,
                      "data": {"run_id": run_id, "retryable": False,
                               "log_path": "", "crash_snapshot_dir": "",
                               "results": [], "warnings": [], "errors": []}}
                with open(sf, "w", encoding="utf-8") as f:
                    json.dump(rd, f, ensure_ascii=False, indent=2)
                return sf
            project = input_data.get("project", project)
            tasks = input_data.get("tasks", [])
            context = input_data.get("context", {})
        if work_dir:
            context.setdefault("work_dir", work_dir)

        # ── 配置统一从 core.config 加载 ────────────────────
        from core.config import PROJECT
        if not input_file:
            project = project_override or project or PROJECT

        # ── 运行前配置自检 ───────────────────────────────
        from core.config import validate_config
        config_check = validate_config()
        if config_check["fatal"]:
            rd = {"status": "fatal",
                  "message": "配置校验失败: %s" % config_check["message"],
                  "data": {"run_id": run_id, "retryable": False,
                           "log_path": "", "crash_snapshot_dir": "",
                           "results": [], "warnings": [], "errors": [],
                           "config_check": config_check}}
            with open(sf, "w", encoding="utf-8") as f:
                json.dump(rd, f, ensure_ascii=False, indent=2)
            return sf

        # ── 执行业务 ────────────────────────────────────────
        import core.entry as em
        import importlib
        importlib.reload(em)
        rd = em.run_tasks(run_id=run_id, project=project, tasks=tasks,
                          context=context, repo_path=repo_path)

    except Exception as e:
        rd = {"status": "fatal", "message": "Runner crash: %s" % e,
              "data": {"run_id": run_id, "retryable": False,
                       "log_path": "", "crash_snapshot_dir": "",
                       "results": [], "warnings": [], "errors": [],
                       "traceback": traceback.format_exc()}}
    finally:
        lock.release()

    with open(sf, "w", encoding="utf-8") as f:
        json.dump(rd, f, ensure_ascii=False, indent=2)
    print("[runner] Status: %s" % sf)
    return sf


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Yingdao RPA -> Python scheduler")
    p.add_argument("--run_id", required=True, help="运行 ID（影刀生成）")
    p.add_argument("--repo_path", required=True, help="仓库绝对路径")
    p.add_argument("--input_file", default="", help="输入文件路径 input_{run_id}.json")
    p.add_argument("--output_dir", default="", help="输出目录（默认=repo_path）")
    p.add_argument("--work_dir", default="", help="影刀本次运行工作目录")
    p.add_argument("--project", default="", help="影刀或 run.bat 传入的项目名")
    a = p.parse_args()
    st = execute(
        run_id=a.run_id,
        repo_path=a.repo_path,
        input_file=a.input_file or None,
        output_dir=a.output_dir or a.repo_path,
        work_dir=a.work_dir or None,
        project_override=a.project or None,
    )
    with open(st, "r", encoding="utf-8") as f:
        print(f.read())
