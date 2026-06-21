"""
tests/test_entry.py — entry 模块测试
====================================
覆盖：
  - _determine_status 状态码判定逻辑
  - run_tasks 输出字段完整性
  - BusinessException / SystemException 端到端
"""
import sys
import os
import json
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.entry import run_tasks, _determine_status


MOCK_ISSUE_URL = "https://linear.app/rpa-workspace/issue/RPA-MOCK/test-issue"

MOCK_AI_RESULT = {
    "root_cause": "mock根因分析",
    "suggested_fix": "mock修复建议",
    "severity": "high",
    "category": "LOGIC_DEFECT",
    "priority": "urgent",
    "summary": "mock异常摘要",
    "confidence": 0.9,
    "need_human_review": False,
    "test_suggestion": "",
}


def _mock_create_issue(*a, **kw):
    return {"success": True, "issue_url": MOCK_ISSUE_URL}


def _mock_analyze(*a, **kw):
    return MOCK_AI_RESULT


def _mock_send_summary(*a, **kw):
    return True


def with_mocks(func):
    @patch("core.entry.send_execution_summary", _mock_send_summary)
    @patch("core.ai_analyzer.analyze_crash", _mock_analyze)
    @patch("core.exceptions.create_linear_issue", _mock_create_issue)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


# ── _determine_status 单元测试 ─────────────────────────────────

def test_determine_status_success():
    """全部成功"""
    status, msg = _determine_status([], [], 2, 2)
    assert status == "success"


def test_determine_status_warning():
    """有跳过但无错误"""
    status, msg = _determine_status([], [{}], 1, 2)
    assert status == "warning"


def test_determine_status_retryable_error():
    """可重试异常"""
    errors = [{"retryable": True, "message": "timeout"}]
    status, msg = _determine_status(errors, [], 0, 1)
    assert status == "retryable_error"
    assert "timeout" in msg


def test_determine_status_mixed_errors_prefers_pending_fix():
    """多个系统异常混合时，不可重试错误优先进入 pending_fix"""
    errors = [
        {"retryable": True, "message": "timeout"},
        {"retryable": False, "message": "logic bug"},
    ]
    status, msg = _determine_status(errors, [], 0, 2)
    assert status == "pending_fix"
    assert "logic bug" in msg


def test_determine_status_pending_fix():
    """不可重试系统异常 → pending_fix"""
    errors = [{"retryable": False, "message": "crash"}]
    status, msg = _determine_status(errors, [], 0, 1)
    assert status == "pending_fix"
    assert "crash" in msg


# ── run_tasks 端到端 ───────────────────────────────────────────

@with_mocks
def test_run_tasks_success():
    """正常任务 → success"""
    result = run_tasks(
        run_id="entry-001", project="测试",
        tasks=[
            {"id": 1, "name": "正常任务A", "type": "template_demo"},
            {"id": 2, "name": "正常任务B", "type": "template_demo"},
        ]
    )
    assert result["status"] == "success"
    assert result["data"]["retryable"] == False


@with_mocks
def test_run_tasks_business_exception():
    """业务异常 → warning"""
    result = run_tasks(
        run_id="entry-002", project="测试",
        tasks=[
            {"id": 1, "name": "正常任务", "type": "template_demo"},
            {"id": -1, "name": "无效ID任务", "type": "template_demo"},
            {"id": 3, "name": "正常任务C", "type": "template_demo"}
        ]
    )
    assert result["status"] == "warning"
    warnings = result["data"]["warnings"]
    assert len(warnings) == 1
    assert warnings[0]["code"] == "DATA_INVALID"
    assert warnings[0]["category"] == "business"


@with_mocks
def test_run_tasks_system_exception():
    """系统异常 → pending_fix，中断后续"""
    result = run_tasks(
        run_id="entry-003", project="测试",
        tasks=[
            {"id": 1, "name": "正常任务", "type": "template_demo"},
            {"id": 0, "name": "触发崩溃", "type": "template_demo"},
            {"id": 3, "name": "不会被执行", "type": "template_demo"}
        ]
    )
    assert result["status"] == "pending_fix"
    errors = result["data"]["errors"]
    assert len(errors) == 1
    assert errors[0]["exc_category"] == "DATA_QUALITY"
    assert errors[0]["category"] == "system"
    # 第3个任务不应执行
    task_ids = [r["task"]["id"] for r in result["data"]["results"]]
    assert 3 not in task_ids


@with_mocks
def test_run_tasks_system_exception_continue_when_fail_fast_false():
    """context.fail_fast=false 时，独立批任务可在系统异常后继续"""
    result = run_tasks(
        run_id="entry-003-continue", project="测试",
        tasks=[
            {"id": 1, "name": "正常任务", "type": "template_demo"},
            {"id": 0, "name": "触发崩溃", "type": "template_demo"},
            {"id": 3, "name": "继续执行", "type": "template_demo"},
        ],
        context={"fail_fast": False},
    )
    assert result["status"] == "pending_fix"
    task_ids = [r["task"]["id"] for r in result["data"]["results"]]
    assert task_ids == [1, 0, 3]


@with_mocks
def test_run_tasks_task_continue_on_error():
    """单个任务声明 continue_on_error 时，默认 fail_fast 下也可继续"""
    result = run_tasks(
        run_id="entry-003-task-continue", project="测试",
        tasks=[
            {"id": 0, "name": "触发崩溃", "type": "template_demo", "continue_on_error": True},
            {"id": 3, "name": "继续执行", "type": "template_demo"},
        ],
    )
    assert result["status"] == "pending_fix"
    task_ids = [r["task"]["id"] for r in result["data"]["results"]]
    assert task_ids == [0, 3]


@with_mocks
def test_run_tasks_output_structure():
    """输出字段完整性"""
    result = run_tasks(
        run_id="entry-004", project="测试",
        tasks=[{"id": 1, "name": "正常任务", "type": "template_demo"}]
    )
    for key in ["status", "message", "data"]:
        assert key in result
    data = result["data"]
    for key in ["run_id", "results", "warnings", "errors", "retryable", "log_path", "crash_snapshot_dir"]:
        assert key in data
