"""core/entry.py — 业务执行入口"""
import json, traceback
from core.exceptions import BusinessException, SystemException

def run_tasks(run_id, project="开发模板", tasks=None, **kwargs):
    if tasks is None:
        tasks = [{"id": 1, "name": "示例"}]
    print(f"[entry:{run_id}] 开始执行 ({project}), 共 {len(tasks)} 个任务")
    try:
        results = []
        for task in tasks:
            try:
                _process_single_task(task, project)
                results.append({"task": task, "status": "ok"})
            except BusinessException as e:
                e.notify()
                results.append({"task": task, "status": "skipped", "reason": str(e)})
            except SystemException as e:
                e.notify(extra_payload={"run_id": run_id})
                return {"status": "failed", "message": f"系统异常: {e}", "data": {"results": results, "failed_task": task}}
        all_ok = all(r["status"] == "ok" for r in results)
        return {"status": "success" if all_ok else "warning", "message": "处理完成", "data": {"run_id": run_id, "results": results}}
    except Exception as e:
        se = SystemException(str(e), project=project, payload={"run_id": run_id})
        se.traceback_str = traceback.format_exc()
        se.notify()
        return {"status": "failed", "message": f"未捕获: {e}", "data": None}

def _process_single_task(task, project):
    tid = task.get("id", 0)
    if tid < 0:
        raise BusinessException(f"ID无效: {tid}", project=project, context={"task_id": tid})
    if tid == 0:
        raise SystemException("ID为0", project=project, payload={"task_id": tid})
    return {"processed": tid}

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--run_id", default="cli_test")
    p.add_argument("--project", default="开发模板")
    a = p.parse_args()
    print(json.dumps(run_tasks(run_id=a.run_id, project=a.project), ensure_ascii=False))
