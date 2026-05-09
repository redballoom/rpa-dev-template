"""core/entry.py - Business execution entry"""
import json, traceback
from core.exceptions import BusinessException, SystemException
from core.notifier import send_execution_summary


def run_tasks(run_id, project="dev-template", tasks=None, repo_path=".", **kwargs):
    if tasks is None: tasks = [{"id": 1, "name": "sample"}]
    print("[entry:%s] Starting (%s), %d tasks" % (run_id, project, len(tasks)))
    results, warnings, errors = [], [], []
    for task in tasks:
        try:
            _process_single_task(task, project)
            results.append({"task": task, "status": "ok"})
        except BusinessException as e:
            info = e.notify()
            warnings.append({"task": task, "message": info["message"], "context": info["context"]})
            results.append({"task": task, "status": "skipped", "reason": str(e)})
        except SystemException as e:
            info = e.notify(extra_payload={"run_id": run_id}, repo_path=repo_path)
            errors.append({"task": task, "message": info["message"],
                           "error_type": info.get("error_type", ""),
                           "issue_url": info.get("issue_url", "")})
            results.append({"task": task, "status": "error", "reason": str(e)})
            break
    success_count = sum(1 for r in results if r["status"] == "ok")
    send_execution_summary(project=project, run_id=run_id, total=len(tasks),
                           success_count=success_count, warnings=warnings, errors=errors)
    if errors:
        has_pending = any(e.get("issue_url") for e in errors)
        return {"status": "pending_fix" if has_pending else "failed",
                "message": "%s" % errors[0]["message"],
                "data": {"run_id": run_id, "results": results, "errors": errors,
                         "warnings": warnings, "crash_snapshot_dir": "crash_snapshots/"}}
    all_ok = success_count == len(tasks)
    return {"status": "success" if all_ok else "warning",
            "message": "Done" if all_ok else "Done, %d skipped" % len(warnings),
            "data": {"run_id": run_id, "results": results, "warnings": warnings}}


def _process_single_task(task, project):
    tid = task.get("id", 0); tn = task.get("name", "unnamed")
    if tid < 0: raise BusinessException("Invalid ID: %d" % tid, project=project, context={"id": tid, "name": tn})
    if tid == 0: raise SystemException(message="task_id=0 invalid", project=project, payload={"id": tid, "name": tn},
        action="Execute [%s]" % tn, expected="positive task_id", actual="got task_id=0, abort")
    return {"processed": tid}


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--run_id", default="cli_test"); p.add_argument("--project", default="dev")
    a = p.parse_args()
    print(json.dumps(run_tasks(run_id=a.run_id, project=a.project), ensure_ascii=False))
