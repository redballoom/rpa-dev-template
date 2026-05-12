"""
core/entry.py — 业务执行入口
=============================
统一输出协议（7 种状态码）：
  success | warning | retryable_error | pending_fix | failed | locked | fatal
"""
import json, traceback
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

    logger = RunLogger(run_id, repo_path)
    logger.start(project, len(tasks))

    results, warnings, errors = [], [], []

    for task in tasks:
        logger.task_start(task)
        try:
            _process_single_task(task, project, context)
            results.append({"task": task, "status": "ok"})
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
            break  # SystemException 中断后续任务
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


def _determine_status(errors, warnings, success_count, total):
    """根据异常情况判定状态码和消息

    语义说明：
      pending_fix:  只要出现不可重试的系统异常 → 待修复
                   不再依赖 issue_url（工单创建可能失败），状态码由错误本身决定
      retryable_error: 系统异常且可重试
      failed:  保留给 runner 级别的崩溃（execute() 中使用），不在 run_tasks 中产生
    """
    if errors:
        has_retryable = any(e.get("retryable") for e in errors)
        if has_retryable:
            return "retryable_error", "可重试异常: %s" % errors[0]["message"]
        # 非可重试系统异常 → pending_fix（语义统一：待修复）
        return "pending_fix", "系统异常(待修复): %s" % errors[0]["message"]

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
    rule_context = task.get("rule_context", "")
    intent = task.get("intent", "")

    # ── 示例：模拟不同异常场景 ──
    if tid and isinstance(tid, (int, float)) and tid == -2:
        # retryable 系统异常（如网络超时）
        raise SystemException(
            message="Connection timeout", project=project,
            payload={"id": tid, "name": tn},
            action="调用外部API", expected="返回200", actual="ConnectionTimeout",
            rule_context=rule_context, intent=intent,
            code="NETWORK_TIMEOUT", exc_category="DEPENDENCY_FAILURE",
            retryable=True, run_context=context or {},
        )
    if tid and isinstance(tid, (int, float)) and tid < 0:
        raise BusinessException(
            "Invalid ID: %d" % tid, project=project,
            context={"id": tid, "name": tn, "rule_context": rule_context, "intent": intent},
            code="DATA_INVALID",
            suggested_action="跳过此任务并记录",
        )
    if tid == 0:
        raise SystemException(
            message="task_id=0 invalid", project=project,
            payload={"id": tid, "name": tn},
            action="Execute [%s]" % tn, expected="positive task_id",
            actual="got task_id=0, abort",
            rule_context=rule_context, intent=intent,
            code="DATA_INVALID", exc_category="DATA_QUALITY",
            run_context=context or {},
        )
    return {"processed": tid}


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--run_id", default="cli_test")
    p.add_argument("--project", default="dev")
    a = p.parse_args()
    print(json.dumps(run_tasks(run_id=a.run_id, project=a.project), ensure_ascii=False, indent=2))
