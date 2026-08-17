"""
tests/test_routing.py — 全链路集成测试
======================================
覆盖：
  - 混合场景、retryable_error 端到端、crash snapshot 上下文
  - pending_fix 语义统一
  - runner 级别（输入缺失、配置校验）
  - warnings/errors category 字段稳定性
"""
import sys
import os
import json
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.entry import run_tasks
from core.exceptions import BusinessException, SystemException, BUSINESS_CODES, SYSTEM_CATEGORIES
from runner import _read_input_file, execute


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


# ── 混合场景 ────────────────────────────────────────────────────

@with_mocks
def test_mixed_business_and_system():
    """混合场景：业务异常 + 系统异常 → pending_fix"""
    result = run_tasks(
        run_id="route-001", project="测试",
        tasks=[
            {"id": 1, "name": "正常任务", "type": "template_demo"},
            {"id": -1, "name": "无效ID", "type": "template_demo"},
            {"id": 0, "name": "触发崩溃", "type": "template_demo"},
            {"id": 3, "name": "不会被执行", "type": "template_demo"}
        ]
    )
    assert result["status"] == "pending_fix"
    data = result["data"]
    assert len(data["warnings"]) == 1
    assert len(data["errors"]) == 1
    assert data["warnings"][0]["category"] == "business"
    assert data["errors"][0]["category"] == "system"


# ── retryable_error 端到端 ──────────────────────────────────────

@with_mocks
def test_retryable_error_e2e():
    """retryable_error 端到端：id=-2 → DEPENDENCY_FAILURE → retryable_error"""
    result = run_tasks(
        run_id="route-002", project="测试",
        tasks=[
            {"id": 1, "name": "正常任务", "type": "template_demo"},
            {"id": -2, "name": "网络超时", "type": "template_demo"},
            {"id": 3, "name": "不会被执行", "type": "template_demo"},
        ],
        context={"operator": "yingdao", "env": "prod", "source": "test"},
    )
    assert result["status"] == "retryable_error"
    assert "可重试" in result["message"]
    errors = result["data"]["errors"]
    assert len(errors) == 1
    assert errors[0]["code"] == "NETWORK_TIMEOUT"
    assert errors[0]["exc_category"] == "DEPENDENCY_FAILURE"
    assert errors[0]["retryable"] == True
    assert result["data"]["retryable"] == True
    # SystemException 中断后续任务
    task_ids = [r["task"]["id"] for r in result["data"]["results"]]
    assert 3 not in task_ids


# ── pending_fix 语义统一 ──────────────────────────────────────

@with_mocks
def test_pending_fix_without_issue():
    """工单创建失败仍返回 pending_fix"""
    with patch("core.exceptions.create_linear_issue",
               return_value={"success": False, "issue_url": ""}):
        result = run_tasks(
            run_id="route-003", project="测试",
            tasks=[{"id": 0, "name": "触发崩溃", "type": "template_demo"}]
        )
    assert result["status"] == "pending_fix"
    assert result["data"]["errors"][0]["issue_url"] == ""


# ── category 字段稳定性 ───────────────────────────────────────

@with_mocks
def test_category_fields_stability():
    """warnings 和 errors 中 category 字段稳定性"""
    result = run_tasks(
        run_id="route-004", project="测试",
        tasks=[
            {"id": -1, "name": "业务异常", "type": "template_demo"},
            {"id": 0, "name": "系统异常", "type": "template_demo"},
        ]
    )
    assert result["status"] == "pending_fix"
    for warn in result["data"]["warnings"]:
        assert "category" in warn
        assert warn["category"] == "business"
    for err in result["data"]["errors"]:
        assert "category" in err
        assert err["category"] == "system"


@with_mocks
def test_unknown_task_type_pending_fix():
    """未知非空 type 不能假成功，应进入待修复状态"""
    result = run_tasks(
        run_id="route-unknown-type", project="测试",
        tasks=[{
            "id": "task-unknown",
            "name": "未知任务类型",
            "type": "missing_handler",
            "payload": {},
        }]
    )
    assert result["status"] == "pending_fix"
    errors = result["data"]["errors"]
    assert len(errors) == 1
    assert errors[0]["code"] == "ROUTE_NOT_FOUND"
    assert errors[0]["exc_category"] == "RULE_MISSING"


@with_mocks
def test_missing_task_type_pending_fix():
    """缺失 type 违反输入契约，不能假成功"""
    result = run_tasks(
        run_id="route-missing-type", project="测试",
        tasks=[{"id": "task-missing", "name": "缺失任务类型", "payload": {}}]
    )
    assert result["status"] == "pending_fix"
    errors = result["data"]["errors"]
    assert len(errors) == 1
    assert errors[0]["code"] == "TASK_TYPE_MISSING"
    assert errors[0]["exc_category"] == "RULE_MISSING"


# ── crash snapshot 上下文 ──────────────────────────────────────

@with_mocks
def test_crash_snapshot_context():
    """crash snapshot 包含完整上下文字段"""
    result = run_tasks(
        run_id="route-005", project="测试",
        tasks=[{"id": 0, "name": "触发崩溃", "type": "template_demo"}],
        context={"operator": "yingdao", "env": "prod", "source": "test",
                 "input_file": "input_route-005.json"},
    )
    snap_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "crash_snapshots", "crash_route-005.json"
    )
    assert os.path.exists(snap_path), "snapshot 文件不存在: %s" % snap_path
    with open(snap_path, "r", encoding="utf-8") as f:
        snapshot = json.load(f)
    assert snapshot["operator"] == "yingdao"
    assert snapshot["env"] == "prod"
    assert snapshot["source"] == "test"
    assert snapshot["input_file"] == "input_route-005.json"
    assert snapshot["code"] == "DATA_INVALID"
    assert snapshot["exc_category"] == "DATA_QUALITY"
    assert snapshot["snapshot_type"] == "crash"
    assert snapshot["run_id"] == "route-005"


# ── runner 级别 ─────────────────────────────────────────────────

def test_input_file_missing():
    """输入文件不存在 → fatal"""
    sf = execute(
        run_id="route-006",
        repo_path=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        input_file="nonexistent_input.json",
    )
    with open(sf, "r", encoding="utf-8") as f:
        result = json.load(f)
    assert result["status"] == "fatal"
    assert "Input file" in result["message"]
    try:
        os.remove(sf)
    except OSError:
        pass


def test_input_file_with_empty_tasks_is_fatal():
    """显式输入文件没有任务时必须失败，不能把 0 个任务判为 success。"""
    repo_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_path = os.path.join(repo_path, "input_route_empty.json")
    output_path = os.path.join(repo_path, "runner_route-empty-001.json")
    try:
        with open(input_path, "w", encoding="utf-8") as f:
            json.dump(
                {"project": "空任务测试", "tasks": [], "context": {"env": "test"}},
                f,
                ensure_ascii=False,
                indent=2,
            )
        sf = execute(
            run_id="route-empty-001",
            repo_path=repo_path,
            input_file=input_path,
        )
        with open(sf, "r", encoding="utf-8") as f:
            result = json.load(f)
        assert result["status"] == "fatal"
        assert result["data"]["run_id"] == "route-empty-001"
        assert "non-empty list" in result["message"]
    finally:
        for path in [input_path, output_path]:
            try:
                os.remove(path)
            except OSError:
                pass


def test_input_file_with_utf8_bom():
    """UTF-8 BOM 输入文件也应被正确读取"""
    repo_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_path = os.path.join(repo_path, "input_route_bom.json")
    payload = {
        "run_id": "route-bom-from-input-should-be-ignored",
        "project": "BOM测试",
        "tasks": [{"id": 1, "name": "正常任务", "type": "template_demo"}],
        "context": {"operator": "pytest", "env": "test", "source": "bom"},
    }
    try:
        with open(input_path, "w", encoding="utf-8-sig") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        sf = execute(
            run_id="route-bom-001",
            repo_path=repo_path,
            input_file=input_path,
        )
        with open(sf, "r", encoding="utf-8") as f:
            result = json.load(f)
        assert result["status"] == "success"
        assert result["data"]["run_id"] == "route-bom-001"
    finally:
        for path in [input_path, os.path.join(repo_path, "runner_route-bom-001.json")]:
            try:
                os.remove(path)
            except OSError:
                pass


def test_exception_codes():
    """异常编码体系完整性"""
    assert "DATA_INVALID" in BUSINESS_CODES
    assert "DATA_EMPTY" in BUSINESS_CODES
    assert "ORDER_NOT_FOUND" in BUSINESS_CODES
    assert "DUPLICATE_RECORD" in BUSINESS_CODES
    assert "RULE_BLOCKED" in BUSINESS_CODES
    assert "UI_CHANGED" in SYSTEM_CATEGORIES
    assert "DATA_QUALITY" in SYSTEM_CATEGORIES
    assert "DEPENDENCY_FAILURE" in SYSTEM_CATEGORIES
    assert "ENVIRONMENT_ISSUE" in SYSTEM_CATEGORIES
    assert "LOGIC_DEFECT" in SYSTEM_CATEGORIES
    assert "THIRD_PARTY_LIMIT" in SYSTEM_CATEGORIES
