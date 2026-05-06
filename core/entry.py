"""
core/entry.py — 业务执行入口
=============================
异常路由:
  BusinessException -> L1 飞书通知，跳过继续
  SystemException   -> L2 飞书告警，强制退出
  其他 Exception     -> L2 飞书告警，强制退出
"""

from core.exceptions import BusinessException, SystemException


def run_tasks(run_id: str, project: str = "开发模板", tasks: list = None, **kwargs) -> dict:
    """
    核心业务入口

    Args:
        run_id: Trace ID（影刀传入）
        project: 项目名称
        tasks: 任务列表 [{"id": 1, "name": "..."}, ...]

    Returns:
        {"status": "success|warning|failed", "message": "...", "data": {...}}
    """
    if tasks is None:
        tasks = [{"id": 1, "name": "示例任务"}]

    print(f"[entry:{run_id}] 开始执行 ({project}), 共 {len(tasks)} 个任务")

    try:
        results = []
        for task in tasks:
            try:
                result = _process_single_task(task, project)
                results.append({"task": task, "status": "ok"})
            except BusinessException as e:
                e.notify()
                results.append({"task": task, "status": "skipped", "reason": str(e)})
                print(f"[entry:{run_id}] 跳过任务 {task.get('id')}: {e}")
            except SystemException as e:
                e.notify(extra_payload={"run_id": run_id})
                print(f"[entry:{run_id}] 系统异常，终止: {e}")
                return {
                    "status": "failed",
                    "message": f"系统异常: {e}",
                    "data": {"results": results, "failed_task": task}
                }

        all_ok = all(r["status"] == "ok" for r in results)
        return {
            "status": "success" if all_ok else "warning",
            "message": (f"处理完成: {sum(1 for r in results if r['status'] == 'ok')} ok, "
                       f"{sum(1 for r in results if r['status'] == 'skipped')} skipped"),
            "data": {"run_id": run_id, "results": results}
        }

    except Exception as e:
        se = SystemException(str(e), project=project, payload={"run_id": run_id})
        se.traceback_str = __import__("traceback").format_exc()
        se.notify()
        return {"status": "failed", "message": f"未捕获异常: {e}", "data": None}


def _process_single_task(task: dict, project: str) -> dict:
    """处理单个任务（示例逻辑，实际业务替换此函数）"""
    task_id = task.get("id", 0)
    if task_id < 0:
        raise BusinessException(f"任务 ID 无效: {task_id}", project=project,
                                context={"task_id": task_id, "reason": "ID 不能为负数"})
    if task_id == 0:
        raise SystemException("关键数据缺失: 任务 ID 为 0", project=project,
                              payload={"task_id": task_id, "severity": "critical"})
    return {"processed": task_id}


if __name__ == "__main__":
    # CLI 入口: python -m core.entry --run_id test001
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_id", default="cli_test")
    parser.add_argument("--project", default="开发模板")
    args = parser.parse_args()
    result = run_tasks(run_id=args.run_id, project=args.project)
    print(__import__("json").dumps(result, ensure_ascii=False, indent=2))
