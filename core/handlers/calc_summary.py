"""Small runnable handler showing the recommended task contract."""
from core.exceptions import BusinessException
from core.infrastructure.files import PathPolicyError, atomic_write_json, resolve_project_path


def process_calc_summary(task, context):
    payload = task.get("payload") or {}
    numbers = payload.get("numbers", [])
    project = context.get("project", "RPA")
    if not isinstance(numbers, list) or not numbers:
        raise BusinessException(
            "payload.numbers is empty", project=project,
            context={"payload": payload}, code="DATA_EMPTY",
            suggested_action="请在输入文件的 payload.numbers 中传入数字列表",
        )

    try:
        values = [float(item) for item in numbers]
    except (TypeError, ValueError):
        raise BusinessException(
            "payload.numbers contains non-numeric value", project=project,
            context={"numbers": numbers}, code="DATA_INVALID",
            suggested_action="请确保 payload.numbers 中的值均为数字",
        )

    summary = {
        "count": len(values),
        "sum": sum(values),
        "average": sum(values) / len(values),
        "min": min(values),
        "max": max(values),
    }
    run_id = context.get("run_id", "unknown")
    output_file = payload.get("output_file") or "data/output/calc_summary_%s.json" % run_id
    try:
        output_path, output_rel = resolve_project_path(
            context.get("repo_path") or ".",
            output_file,
            allowed_dir="data/output",
        )
    except PathPolicyError as exc:
        raise BusinessException(
            str(exc), project=project,
            context={"output_file": output_file}, code="DATA_INVALID",
            suggested_action="请将 output_file 设置在 data/output/ 目录内",
        )

    atomic_write_json(output_path, summary)
    result = dict(summary)
    result["output_file"] = output_rel
    return result


__all__ = ["process_calc_summary"]
