import json
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.entry import run_tasks
from core.exceptions import SystemException


def _mock_send_summary(*args, **kwargs):
    return True


def _write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


@patch("core.entry.send_execution_summary", _mock_send_summary)
def test_filter_records_success(tmp_path):
    repo_path = str(tmp_path)
    input_file = tmp_path / "data" / "input" / "records.json"
    output_file = "data/output/filtered_records.json"
    _write_json(str(input_file), {
        "records": [
            {"id": "a", "status": "ready"},
            {"id": "b", "status": "skip"},
            {"id": "c", "status": "ready"},
        ]
    })

    result = run_tasks(
        run_id="filter-success",
        project="测试",
        repo_path=repo_path,
        tasks=[{
            "id": "filter-001",
            "name": "筛选 ready 记录",
            "type": "filter_records",
            "payload": {
                "input_file": "data/input/records.json",
                "output_file": output_file,
                "status_field": "status",
                "match_value": "ready",
            },
        }],
    )

    assert result["status"] == "success"
    data = result["data"]["results"][0]["data"]
    assert data["total_count"] == 3
    assert data["matched_count"] == 2
    assert data["skipped_count"] == 1

    output_path = tmp_path / output_file
    with open(output_path, "r", encoding="utf-8") as f:
        output = json.load(f)
    assert [item["id"] for item in output["records"]] == ["a", "c"]


@patch("core.entry.send_execution_summary", _mock_send_summary)
def test_filter_records_empty_records_warning(tmp_path):
    repo_path = str(tmp_path)
    input_file = tmp_path / "data" / "input" / "records.json"
    _write_json(str(input_file), {"records": []})

    result = run_tasks(
        run_id="filter-empty",
        project="测试",
        repo_path=repo_path,
        tasks=[{
            "id": "filter-empty",
            "name": "空数据",
            "type": "filter_records",
            "payload": {"input_file": "data/input/records.json"},
        }],
    )

    assert result["status"] == "warning"
    assert result["data"]["warnings"][0]["code"] == "DATA_EMPTY"


def test_filter_records_missing_file_system_exception(tmp_path):
    from core.handlers.record_filter import process_filter_records

    try:
        process_filter_records(
            {
                "id": "filter-missing",
                "name": "缺失输入文件",
                "type": "filter_records",
                "payload": {"input_file": "data/input/missing.json"},
            },
            {"repo_path": str(tmp_path), "project": "测试"},
        )
    except SystemException as exc:
        assert exc.code == "INPUT_FILE_MISSING"
        assert exc.exc_category == "ENVIRONMENT_ISSUE"
    else:
        raise AssertionError("expected SystemException")
