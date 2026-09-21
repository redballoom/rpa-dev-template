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
from functools import wraps
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.entry import run_tasks
from core.exceptions import BusinessException, SystemException, BUSINESS_CODES, SYSTEM_CATEGORIES
from runner import _read_input_file, execute
from tools.evidence import summary_path, validate_summary


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


def _remove_run_artifacts(repo_path, run_id, *extra_paths):
    paths = [
        os.path.join(repo_path, "runner_%s.json" % run_id),
        str(summary_path(repo_path, run_id)),
        *extra_paths,
    ]
    for path in paths:
        try:
            os.remove(path)
        except OSError:
            pass


def _mock_create_issue(*a, **kw):
    return {"success": True, "issue_url": MOCK_ISSUE_URL}


def _mock_analyze(*a, **kw):
    return MOCK_AI_RESULT


def _mock_send_summary(*a, **kw):
    return True


def with_mocks(func):
    @wraps(func)
    @patch("core.entry.send_execution_summary", _mock_send_summary)
    @patch("core.ai_analyzer.analyze_crash", _mock_analyze)
    @patch("core.exceptions.create_linear_issue", _mock_create_issue)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
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
def test_input_context_cannot_override_trusted_repo_path(tmp_path):
    output = tmp_path / "repo" / "data" / "output" / "safe.json"
    result = run_tasks(
        run_id="trusted-path-001",
        project="测试",
        repo_path=str(tmp_path / "repo"),
        context={"repo_path": str(tmp_path / "attacker")},
        tasks=[{
            "id": "calc-safe",
            "name": "安全路径",
            "type": "calc_summary",
            "payload": {"numbers": [1, 2], "output_file": "data/output/safe.json"},
        }],
    )
    assert result["status"] == "success"
    assert output.exists()
    assert not (tmp_path / "attacker" / "data" / "output" / "safe.json").exists()


@with_mocks
def test_calc_summary_rejects_output_path_escape(tmp_path):
    result = run_tasks(
        run_id="path-escape-001",
        project="测试",
        repo_path=str(tmp_path),
        tasks=[{
            "id": "calc-escape",
            "name": "越界输出",
            "type": "calc_summary",
            "payload": {"numbers": [1], "output_file": "outside.json"},
        }],
    )
    assert result["status"] == "warning"
    assert result["data"]["warnings"][0]["code"] == "DATA_INVALID"
    assert not (tmp_path / "outside.json").exists()


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
    repo_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sf = execute(
        run_id="route-006",
        repo_path=repo_path,
        input_file="nonexistent_input.json",
    )
    with open(sf, "r", encoding="utf-8") as f:
        result = json.load(f)
    assert result["status"] == "fatal"
    assert "Input file" in result["message"]
    assert validate_summary(os.path.join(repo_path, result["data"]["evidence_summary_path"]))["valid"] is True
    _remove_run_artifacts(repo_path, "route-006")


def test_input_file_with_empty_tasks_is_fatal():
    """显式输入文件没有任务时必须失败，不能把 0 个任务判为 success。"""
    repo_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_path = os.path.join(repo_path, "input_route_empty.json")
    output_path = os.path.join(repo_path, "runner_route-empty-001.json")
    try:
        with open(input_path, "w", encoding="utf-8") as f:
            json.dump(
                {"schema_version": "1.0", "project": "空任务测试", "tasks": [], "context": {"env": "test"}},
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
        assert "Input file invalid" in result["message"]
    finally:
        _remove_run_artifacts(repo_path, "route-empty-001", input_path, output_path)


def test_input_file_with_utf8_bom():
    """UTF-8 BOM 输入文件也应被正确读取"""
    repo_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_path = os.path.join(repo_path, "input_route_bom.json")
    payload = {
        "schema_version": "1.0",
        "run_id": "route-bom-from-input-should-be-ignored",
        "project": "BOM测试",
        "tasks": [{"id": 1, "name": "正常任务", "type": "template_demo", "payload": {}}],
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
        evidence_path = os.path.join(repo_path, result["data"]["evidence_summary_path"])
        assert validate_summary(evidence_path)["valid"] is True
    finally:
        _remove_run_artifacts(repo_path, "route-bom-001", input_path)


def test_missing_input_file_argument_is_fatal():
    """生产契约要求独立输入文件，不能把空任务运行判为成功。"""
    repo_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sf = execute(run_id="route-no-input-001", repo_path=repo_path)
    try:
        with open(sf, "r", encoding="utf-8") as f:
            result = json.load(f)
        assert result["status"] == "fatal"
        assert result["message"] == "Input file is required"
    finally:
        _remove_run_artifacts(repo_path, "route-no-input-001")


def test_unsupported_input_schema_version_is_fatal():
    repo_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_path = os.path.join(repo_path, "input_route_bad_schema.json")
    try:
        with open(input_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "schema_version": "0.9",
                    "project": "旧契约",
                    "tasks": [{"id": "t1", "name": "测试", "type": "template_demo", "payload": {}}],
                },
                f,
                ensure_ascii=False,
            )
        sf = execute(
            run_id="route-bad-schema-001",
            repo_path=repo_path,
            input_file=input_path,
        )
        with open(sf, "r", encoding="utf-8") as f:
            result = json.load(f)
        assert result["status"] == "fatal"
        assert "Input file invalid" in result["message"]
    finally:
        _remove_run_artifacts(repo_path, "route-bad-schema-001", input_path)


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
