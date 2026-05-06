"""
core/entry.py — 业务执行入口（被 runner.py 调用）
===================================================
异常路由规则:
    BusinessException → L1 飞书通知 + 跳过当前任务
    SystemException   → L2 飞书告警 + 强制退出
    其他 Exception     → L2 飞书告警 + 强制退出
"""

from core.exceptions import BusinessException, SystemException


def run_tasks(run_id: str, **kwargs) -> dict:
    """
    业务执行入口

    Args:
        run_id: 本次运行唯一 ID（Trace ID）
        **kwargs: 影刀传入的额外参数

    Returns:
        {"status": "success|warning|failed", "message": "...", "data": {...}}
    """
    project = kwargs.get("project", "开发模板")
    print(f"[entry:{run_id}] 开始执行 ({project})")

    try:
        # ── 你的业务逻辑从这里开始 ──
        # 模拟处理一个任务列表
        tasks = kwargs.get("tasks", [{"id": 1, "name": "示例任务"}])

        results = []
        for task in tasks:
            try:
                result = _process_single_task(task, project)
                results.append({"task": task, "status": "ok"})
            except BusinessException as e:
                # L1: 业务异常 → 飞书通知，跳过继续
                e.notify()
                results.append({"task": task, "status": "skipped", "reason": str(e)})
                print(f"[entry:{run_id}] 跳过任务 {task.get('id')}: {e}")
            except SystemException as e:
                # L2: 系统 Bug → 飞书告警，强制退出
                e.notify(extra_payload={"run_id": run_id})
                print(f"[entry:{run_id}] 系统异常，终止: {e}")
                return {
                    "status": "failed",
                    "message": f"系统异常: {e}",
                    "data": {"results": results, "failed_task": task}
                }

        # 判断整体状态
        all_ok = all(r["status"] == "ok" for r in results)
        return {
            "status": "success" if all_ok else "warning",
            "message": f"处理完成: {sum(1 for r in results if r['status'] == 'ok')} ok, "
                       f"{sum(1 for r in results if r['status'] == 'skipped')} skipped",
            "data": {"run_id": run_id, "results": results}
        }

    except Exception as e:
        # 未捕获的异常 → 当系统异常处理
        se = SystemException(str(e), project=project, payload={"run_id": run_id})
        se.traceback_str = __import__("traceback").format_exc()
        se.notify()
        return {"status": "failed", "message": f"未捕获异常: {e}", "data": None}


def _process_single_task(task: dict, project: str) -> dict:
    """处理单个任务（示例）"""
    task_id = task.get("id", 0)

    # 模拟: id 为负数 → 业务异常（可接受，跳过）
    if task_id < 0:
        raise BusinessException(
            f"任务 ID 无效: {task_id}",
            project=project,
            context={"task_id": task_id, "reason": "ID 不能为负数"}
        )

    # 模拟: id 为 0 → 系统异常（需强制退出）
    if task_id == 0:
        raise SystemException(
            "关键数据缺失: 任务 ID 为 0",
            project=project,
            payload={"task_id": task_id, "severity": "critical"}
        )

    return {"processed": task_id}
