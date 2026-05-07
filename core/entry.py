"""core/entry.py — 业务执行入口"""
import json, traceback
from core.exceptions import BusinessException, SystemException
from core.notifier import send_execution_summary


def run_tasks(run_id, project="开发模板", tasks=None, repo_path=".", **kwargs):
    """
    业务执行入口（被 runner 调用）。

    通知策略：批量汇总模式
        - 不再逐个发送飞书消息
        - BusinessException 收集到 warnings 列表
        - SystemException 创建 Linear 工单 + 收集到 errors 列表
        - 执行完毕后由 send_execution_summary() 一次性发送飞书汇总

    Returns:
        dict: {"status": "success|warning|failed", "message": ..., "data": ...}
    """
    if tasks is None:
        tasks = [{"id": 1, "name": "示例"}]
    print(f"[entry:{run_id}] 开始执行 ({project}), 共 {len(tasks)} 个任务")

    results = []
    warnings = []  # 收集 BusinessException 信息
    errors = []    # 收集 SystemException 信息

    for task in tasks:
        try:
            _process_single_task(task, project)
            results.append({"task": task, "status": "ok"})
        except BusinessException as e:
            # 收集业务异常信息，不发送飞书
            info = e.notify()
            warnings.append({
                "task": task,
                "message": info["message"],
                "context": info["context"],
            })
            results.append({"task": task, "status": "skipped", "reason": str(e)})
        except SystemException as e:
            # 创建 Linear 工单 + 收集异常信息
            info = e.notify(extra_payload={"run_id": run_id}, repo_path=repo_path)
            errors.append({
                "task": task,
                "message": info["message"],
                "error_type": info.get("error_type", ""),
                "issue_url": info.get("issue_url", ""),
            })
            results.append({"task": task, "status": "error", "reason": str(e)})
            # SystemException 中断后续任务
            break

    # ── 统计 ──
    success_count = sum(1 for r in results if r["status"] == "ok")

    # ── 汇总飞书通知 ──
    send_execution_summary(
        project=project,
        run_id=run_id,
        total=len(tasks),
        success_count=success_count,
        warnings=warnings,
        errors=errors,
    )

    # ── 返回状态 ──
    if errors:
        return {
            "status": "failed",
            "message": f"系统异常中断: {errors[0]['message']}",
            "data": {
                "run_id": run_id,
                "results": results,
                "errors": errors,
                "warnings": warnings,
            },
        }

    all_ok = success_count == len(tasks)
    return {
        "status": "success" if all_ok else "warning",
        "message": "处理完成" if all_ok else f"完成，{len(warnings)} 个任务被跳过",
        "data": {
            "run_id": run_id,
            "results": results,
            "warnings": warnings,
        },
    }


def _process_single_task(task, project):
    """示例业务处理（实际业务模块替换此处）"""
    tid = task.get("id", 0)
    task_name = task.get("name", "未命名")
    if tid < 0:
        raise BusinessException(
            f"ID无效: {tid}",
            project=project,
            context={"task_id": tid, "task_name": task_name},
        )
    if tid == 0:
        raise SystemException(
            message=f"task_id=0 不合法",
            project=project,
            payload={"task_id": tid, "task_name": task_name},
            action=f"执行任务 [{task_name}]（处理阶段）",
            expected="task_id 应为正整数，<0 走业务异常跳过",
            actual=f"收到 task_id=0，触发系统异常，流程中断",
        )
    return {"processed": tid}


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--run_id", default="cli_test")
    p.add_argument("--project", default="开发模板")
    a = p.parse_args()
    print(json.dumps(run_tasks(run_id=a.run_id, project=a.project), ensure_ascii=False))
