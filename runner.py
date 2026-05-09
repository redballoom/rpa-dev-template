"""
runner.py - Yingdao RPA CLI entry (BAT mode)
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


def _load_config(repo_path):
    config = {}
    for fn in ["project.template.json", "project.json"]:
        fp = os.path.join(repo_path, fn)
        if os.path.exists(fp):
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    config.update(json.load(f))
            except Exception as e:
                print("[runner] warning: %s: %s" % (fn, e))
    return config


def _switch_git(repo_path, config):
    is_test = config.get("is_test_to_git_env", False)
    target = "fix/bug-test" if is_test else "main"
    try:
        import git_controller
        import importlib
        importlib.reload(git_controller)
        r = git_controller.switch_git_env(is_test=is_test, repo_path=repo_path)
        if r.get("status") == "error":
            print("[runner] Git warning (%s): %s" % (target, r.get("msg")))
        else:
            print("[runner] Git: %s" % target)
    except Exception as e:
        print("[runner] Git failed (non-blocking): %s" % e)


def execute(run_id, repo_path, project="dev-template", tasks=None, output_dir=None):
    if repo_path in sys.path:
        sys.path.remove(repo_path)
    sys.path.insert(0, repo_path)
    if output_dir is None:
        output_dir = repo_path
    os.makedirs(output_dir, exist_ok=True)
    sf = os.path.join(output_dir, "runner_%s.json" % run_id)

    lock = _FileLock(os.path.join(repo_path, ".runner.lock"))
    if not lock.try_acquire(timeout=0):
        rd = {"status": "locked", "message": "Locked: %s" % repo_path, "data": {"run_id": run_id}}
        with open(sf, "w", encoding="utf-8") as f:
            json.dump(rd, f, ensure_ascii=False, indent=2)
        print("[runner] !! Locked: %s" % repo_path)
        return sf

    try:
        cfg = _load_config(repo_path)
        pn = project or cfg.get("project", "dev-template")
        _switch_git(repo_path, cfg)
        import core.entry as em
        import importlib
        importlib.reload(em)
        rd = em.run_tasks(run_id=run_id, project=pn, tasks=tasks, repo_path=repo_path)
    except Exception as e:
        rd = {"status": "fatal", "message": "Runner crash: %s" % e,
              "data": {"run_id": run_id, "traceback": traceback.format_exc()}}
    finally:
        lock.release()

    with open(sf, "w", encoding="utf-8") as f:
        json.dump(rd, f, ensure_ascii=False, indent=2)
    print("[runner] Status: %s" % sf)
    return sf


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Yingdao RPA -> Python scheduler")
    p.add_argument("--run_id", required=True)
    p.add_argument("--repo_path", required=True)
    p.add_argument("--project", default="dev-template")
    p.add_argument("--output_dir", default="")
    a = p.parse_args()
    st = execute(run_id=a.run_id, repo_path=a.repo_path, project=a.project,
                 tasks=[{"id": 1, "name": "normal"}, {"id": 2, "name": "normal-B"}],
                 output_dir=a.output_dir or a.repo_path)
    with open(st, "r", encoding="utf-8") as f:
        print(f.read())
