import json
import os

from core.exceptions import BusinessException, SystemException


def _resolve_path(repo_path, path):
    if os.path.isabs(path):
        return path
    return os.path.join(repo_path, path)


def process_filter_records(task, context):
    """Filter JSON records by field value and write a stable output summary.

    Business path:
      1. Validate payload.
      2. Read a JSON file containing `records`.
      3. Keep records where `status_field` equals `match_value`.
      4. Write filtered records to `payload.output_file`.
      5. Return a compact results[].data summary.
    """
    payload = task.get("payload") or {}
    repo_path = context.get("repo_path") or "."
    project = context.get("project", "RPA")

    input_file = payload.get("input_file")
    if not input_file:
        raise BusinessException(
            "payload.input_file is required",
            project=project,
            context={"payload": payload},
            code="DATA_EMPTY",
            suggested_action="请在 payload.input_file 中传入 JSON 输入文件路径",
        )

    status_field = payload.get("status_field") or "status"
    match_value = payload.get("match_value") or "ready"
    output_file = payload.get("output_file") or "data/output/filtered_records.json"

    input_path = _resolve_path(repo_path, input_file)
    output_path = _resolve_path(repo_path, output_file)

    if not os.path.exists(input_path):
        raise SystemException(
            message="Input file not found: %s" % input_file,
            project=project,
            payload=payload,
            action="读取记录筛选输入文件",
            expected="输入文件存在且可读取",
            actual="文件不存在: %s" % input_file,
            code="INPUT_FILE_MISSING",
            exc_category="ENVIRONMENT_ISSUE",
            run_context=context,
        )

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            source = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemException(
            message="Failed to read JSON input: %s" % input_file,
            project=project,
            payload={"input_file": input_file, "error": str(exc)},
            action="解析记录筛选输入文件",
            expected="输入文件是 UTF-8 JSON",
            actual=str(exc),
            code="INPUT_FILE_INVALID",
            exc_category="DATA_QUALITY",
            run_context=context,
        )

    if not isinstance(source, dict):
        raise BusinessException(
            "input JSON root must be an object",
            project=project,
            context={"input_file": input_file},
            code="DATA_INVALID",
            suggested_action="请确认输入 JSON 顶层是对象，并包含 records 数组",
        )

    records = source.get("records")
    if not isinstance(records, list) or not records:
        raise BusinessException(
            "input records is empty",
            project=project,
            context={"input_file": input_file},
            code="DATA_EMPTY",
            suggested_action="请确认输入 JSON 中包含非空 records 数组",
        )

    if any(not isinstance(item, dict) for item in records):
        raise BusinessException(
            "records item must be an object",
            project=project,
            context={"input_file": input_file},
            code="DATA_INVALID",
            suggested_action="请确认 records 数组中的每条记录都是对象",
        )

    matched = [item for item in records if item.get(status_field) == match_value]
    result = {"records": matched}

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return {
        "input_file": input_file,
        "output_file": output_file,
        "status_field": status_field,
        "match_value": match_value,
        "total_count": len(records),
        "matched_count": len(matched),
        "skipped_count": len(records) - len(matched),
    }
