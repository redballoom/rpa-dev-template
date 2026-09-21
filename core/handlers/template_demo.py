"""Status-code demo handler. Replace or remove it in a real business project."""
from core.exceptions import BusinessException, SystemException


def process_template_demo(task, context):
    tid = task.get("id", 0)
    name = task.get("name", "unnamed")
    project = context.get("project", "RPA")
    if tid and isinstance(tid, (int, float)) and tid == -2:
        raise SystemException(
            message="Connection timeout", project=project,
            payload={"id": tid, "name": name}, action="调用外部API",
            expected="返回200", actual="ConnectionTimeout",
            code="NETWORK_TIMEOUT", exc_category="DEPENDENCY_FAILURE",
            retryable=True, run_context=context,
        )
    if tid and isinstance(tid, (int, float)) and tid < 0:
        raise BusinessException(
            "Invalid ID: %d" % tid, project=project,
            context={"id": tid, "name": name}, code="DATA_INVALID",
            suggested_action="跳过此任务并记录",
        )
    if tid == 0:
        raise SystemException(
            message="task_id=0 invalid", project=project,
            payload={"id": tid, "name": name},
            action="Execute [%s]" % name, expected="positive task_id",
            actual="got task_id=0, abort", code="DATA_INVALID",
            exc_category="DATA_QUALITY", run_context=context,
        )
    return {"processed": tid}


__all__ = ["process_template_demo"]
