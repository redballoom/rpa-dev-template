"""
core/entry.py — 业务执行入口
=============================
统一输出协议（7 种状态码）：
  success | warning | retryable_error | pending_fix | failed | locked | fatal
"""
import json, os, traceback
from core.exceptions import BusinessException, SystemException
from core.notifier import send_execution_summary
from core.logger import RunLogger


def run_tasks(run_id, project="dev-template", tasks=None, context=None, repo_path="."):
    """
    执行任务列表，返回标准化结果 JSON。

    Args:
        run_id:    运行 ID（影刀生成）
        project:   项目名称
        tasks:     任务列表，来自 input_{run_id}.json
        context:   运行时上下文（operator/env/source/input_file 等）
        repo_path: 仓库路径（用于写 snapshot 和日志）
    """
    if tasks is None:
        tasks = []
    if context is None:
        context = {}
    context.setdefault("repo_path", repo_path)
    context.setdefault("project", project)
    fail_fast = _as_bool(context.get("fail_fast", True))

    logger = RunLogger(run_id, repo_path)
    logger.start(project, len(tasks))

    results, warnings, errors = [], [], []

    for task in tasks:
        logger.task_start(task)
        try:
            task_data = _process_single_task(task, project, context)
            result_item = {"task": task, "status": "ok"}
            if task_data is not None:
                result_item["data"] = task_data
            results.append(result_item)
            logger.task_end(task, "ok")
        except BusinessException as e:
            info = e.notify()
            warnings.append({
                "task": task, "message": info["message"], "context": info["context"],
                "category": info["category"], "code": info["code"],
                "retryable": info["retryable"],
                "suggested_action": info["suggested_action"],
            })
            results.append({"task": task, "status": "skipped", "reason": str(e)})
            logger.task_end(task, "skipped", str(e))
            logger.exception(info)
        except SystemException as e:
            info = e.notify(extra_payload={"run_id": run_id}, repo_path=repo_path)
            ai = info.get("ai_analysis") or {}
            errors.append({
                "task": task, "message": info["message"],
                "category": info["category"],
                "error_type": info.get("error_type", ""),
                "code": info.get("code", ""),
                "exc_category": info.get("exc_category", ""),
                "retryable": info.get("retryable", False),
                "issue_url": info.get("issue_url", ""),
                # AI 增强字段
                "confidence": ai.get("confidence", ""),
                "need_human_review": ai.get("need_human_review", False),
                "test_suggestion": ai.get("test_suggestion", ""),
            })
            results.append({"task": task, "status": "error", "reason": str(e)})
            logger.task_end(task, "error", str(e))
            logger.exception(info)
            if fail_fast and not _as_bool(task.get("continue_on_error", False)):
                break  # 默认保持系统异常中断；独立批任务可通过 context.fail_fast=false 继续。
        except Exception as e:
            # 兜底：未捕获异常 → 包装为 SystemException
            se = SystemException(
                message=str(e), project=project,
                payload={"raw_exception": traceback.format_exc()},
                action="执行任务 %s" % task.get("name", "?"),
                expected="正常完成", actual="未捕获异常: %s" % type(e).__name__,
                run_context=context,
            )
            info = se.notify(extra_payload={"run_id": run_id}, repo_path=repo_path)
            errors.append({
                "task": task, "message": info["message"],
                "category": "system",
                "error_type": info.get("error_type", ""),
                "code": info.get("code", ""),
                "exc_category": info.get("exc_category", ""),
                "retryable": False,
                "issue_url": info.get("issue_url", ""),
                # 兜底异常无 AI 分析
                "confidence": "",
                "need_human_review": True,
                "test_suggestion": "",
            })
            results.append({"task": task, "status": "error", "reason": str(e)})
            logger.task_end(task, "error (uncaught)", str(e))
            if fail_fast and not _as_bool(task.get("continue_on_error", False)):
                break

    success_count = sum(1 for r in results if r["status"] == "ok")
    total = len(tasks)

    # 飞书汇总通知
    send_execution_summary(
        project=project, run_id=run_id, total=total,
        success_count=success_count, warnings=warnings, errors=errors,
    )

    # ── 判定状态码 ──────────────────────────────────────────
    status, message = _determine_status(errors, warnings, success_count, total)

    # 结束日志
    logger.end(status, success_count, total)

    # ── 构建统一输出 ────────────────────────────────────────
    has_retryable = any(e.get("retryable") for e in errors)

    return {
        "status": status,
        "message": message,
        "data": {
            "run_id": run_id,
            "results": results,
            "warnings": warnings,
            "errors": errors,
            "retryable": has_retryable,
            "crash_snapshot_dir": "crash_snapshots/" if errors else "",
            "log_path": logger.log_path,
        },
    }


def _as_bool(value):
    """兼容影刀传入 bool 或字符串形式的开关。"""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() not in ("0", "false", "no", "off", "")
    return bool(value)


def _determine_status(errors, warnings, success_count, total):
    """根据异常情况判定状态码和消息

    语义说明：
      pending_fix:  只要出现不可重试的系统异常 → 待修复
                   不再依赖 issue_url（工单创建可能失败），状态码由错误本身决定
      retryable_error: 系统异常且可重试
      failed:  保留给 runner 级别的崩溃（execute() 中使用），不在 run_tasks 中产生
    """
    if errors:
        has_non_retryable = any(not e.get("retryable") for e in errors)
        if not has_non_retryable:
            return "retryable_error", "可重试异常: %s" % errors[0]["message"]
        # 非可重试系统异常 → pending_fix（语义统一：待修复）
        first_non_retryable = next((e for e in errors if not e.get("retryable")), errors[0])
        return "pending_fix", "系统异常(待修复): %s" % first_non_retryable["message"]

    all_ok = success_count == total
    if all_ok:
        return "success", "处理完成"
    return "warning", "完成，%d 个任务被跳过" % len(warnings)


def _process_single_task(task, project, context=None):
    """
    处理单个任务。
    当前为模板示例：根据 task.id 模拟不同异常。
    实际业务模块应替换此函数内容。
    """
    tid = task.get("id", 0)
    tn = task.get("name", "unnamed")
    task_type = task.get("type", "")

    if not task_type:
        raise SystemException(
            message="Missing task type",
            project=project,
            payload={"id": tid, "name": tn, "task": task},
            action="校验任务路由字段",
            expected="tasks[].type 必填并对应已实现的 handler",
            actual="tasks[].type 为空",
            code="TASK_TYPE_MISSING",
            exc_category="RULE_MISSING",
            run_context=context or {},
        )

    if task_type == "calc_summary":
        return _process_calc_summary(task, context or {})

    if task_type and task_type != "template_demo":
        raise SystemException(
            message="Unsupported task type: %s" % task_type,
            project=project,
            payload={
                "id": tid,
                "name": tn,
                "type": task_type,
                "payload": task.get("payload") or {},
            },
            action="路由任务类型",
            expected="tasks[].type 对应已实现的 handler",
            actual="未找到 handler: %s" % task_type,
            code="ROUTE_NOT_FOUND",
            exc_category="RULE_MISSING",
            run_context=context or {},
        )

    # ── 示例：模拟不同异常场景 ──
    # type=template_demo 仅用于模板状态码演示。
    if tid and isinstance(tid, (int, float)) and tid == -2:
        # retryable 系统异常（如网络超时）
        raise SystemException(
            message="Connection timeout", project=project,
            payload={"id": tid, "name": tn},
            action="调用外部API", expected="返回200", actual="ConnectionTimeout",
            code="NETWORK_TIMEOUT", exc_category="DEPENDENCY_FAILURE",
            retryable=True, run_context=context or {},
        )
    if tid and isinstance(tid, (int, float)) and tid < 0:
        raise BusinessException(
            "Invalid ID: %d" % tid, project=project,
            context={"id": tid, "name": tn},
            code="DATA_INVALID",
            suggested_action="跳过此任务并记录",
        )
    if tid == 0:
        raise SystemException(
            message="task_id=0 invalid", project=project,
            payload={"id": tid, "name": tn},
            action="Execute [%s]" % tn, expected="positive task_id",
            actual="got task_id=0, abort",
            code="DATA_INVALID", exc_category="DATA_QUALITY",
            run_context=context or {},
        )
    return {"processed": tid}


def _process_calc_summary(task, context):
    payload = task.get("payload") or {}
    numbers = payload.get("numbers", [])
    if not isinstance(numbers, list) or not numbers:
        raise BusinessException(
            "payload.numbers is empty", project=context.get("project", "RPA"),
            context={"payload": payload}, code="DATA_EMPTY",
            suggested_action="请在输入文件的 payload.numbers 中传入数字列表",
        )

    try:
        values = [float(item) for item in numbers]
    except (TypeError, ValueError):
        raise BusinessException(
            "payload.numbers contains non-numeric value", project=context.get("project", "RPA"),
            context={"numbers": numbers}, code="DATA_INVALID",
            suggested_action="请确保 payload.numbers 中的值均为数字",
        )

    total = sum(values)
    summary = {
        "count": len(values),
        "sum": total,
        "average": total / len(values),
        "min": min(values),
        "max": max(values),
    }

    repo_path = context.get("repo_path") or "."
    output_file = payload.get("output_file") or "data/output/calc_result.json"
    output_path = output_file
    if not os.path.isabs(output_path):
        output_path = os.path.join(repo_path, output_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    result = dict(summary)
    result["output_file"] = output_file
    return result


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--run_id", default="cli_test")
    p.add_argument("--project", default="dev")
    a = p.parse_args()
    print(json.dumps(run_tasks(run_id=a.run_id, project=a.project), ensure_ascii=False, indent=2))
