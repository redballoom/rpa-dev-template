"""
tests/test_exceptions.py — 异常编码与分类测试
=============================================
覆盖：
  - BUSINESS_CODES / SYSTEM_CATEGORIES 完整性
  - BusinessException / SystemException 字段传递
  - 分类映射（AI 分类 → SYSTEM_CATEGORIES）
"""
import sys
import os
import json
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.exceptions import (
    BusinessException, SystemException,
    BUSINESS_CODES, SYSTEM_CATEGORIES,
)


MOCK_ISSUE_URL = "https://linear.app/rpa-workspace/issue/RPA-MOCK/test-issue"


def _mock_create_issue(*a, **kw):
    return {"success": True, "issue_url": MOCK_ISSUE_URL}


def _mock_analyze(*a, **kw):
    return {
        "root_cause": "mock根因", "suggested_fix": "mock修复",
        "severity": "high", "category": "LOGIC_DEFECT",
        "priority": "urgent", "summary": "mock摘要",
        "confidence": 0.8, "need_human_review": False, "test_suggestion": "",
    }


# ── 业务异常编码体系 ─────────────────────────────────────────

def test_business_codes_completeness():
    """业务编码 5 种完整性"""
    expected = {"DATA_EMPTY", "DATA_INVALID", "ORDER_NOT_FOUND",
                "DUPLICATE_RECORD", "RULE_BLOCKED"}
    assert set(BUSINESS_CODES.keys()) == expected


def test_system_categories_completeness():
    """系统分类 7 种完整性"""
    expected = {"UI_CHANGED", "DATA_QUALITY", "RULE_MISSING",
                "DEPENDENCY_FAILURE", "ENVIRONMENT_ISSUE",
                "LOGIC_DEFECT", "THIRD_PARTY_LIMIT"}
    assert set(SYSTEM_CATEGORIES.keys()) == expected


# ── BusinessException ──────────────────────────────────────────

def test_business_exception_defaults():
    """BusinessException 默认字段"""
    exc = BusinessException("测试", project="P1")
    info = exc.notify()
    assert info["category"] == "business"
    assert info["code"] == "DATA_INVALID"  # 默认 code
    assert info["retryable"] == False
    assert info["suggested_action"] == "跳过并记录"


def test_business_exception_custom_code():
    """BusinessException 自定义 code"""
    exc = BusinessException("重复", code="DUPLICATE_RECORD", retryable=True,
                            suggested_action="跳过")
    info = exc.notify()
    assert info["code"] == "DUPLICATE_RECORD"
    assert info["retryable"] == True
    assert info["suggested_action"] == "跳过"


# ── SystemException ────────────────────────────────────────────

@patch("core.ai_analyzer.analyze_crash", _mock_analyze)
@patch("core.exceptions.create_linear_issue", _mock_create_issue)
def test_system_exception_fields():
    """SystemException 字段传递验证"""
    exc = SystemException(
        message="Connection timeout", project="测试",
        action="调用外部API", expected="返回200", actual="ConnectionTimeout",
        code="NETWORK_TIMEOUT", exc_category="DEPENDENCY_FAILURE",
        retryable=True,
    )
    info = exc.notify(extra_payload={"run_id": "test"}, repo_path=".")
    assert info["category"] == "system"
    assert info["exc_category"] == "DEPENDENCY_FAILURE"
    assert info["code"] == "NETWORK_TIMEOUT"
    assert info["retryable"] == True
    assert info["issue_url"] == MOCK_ISSUE_URL
    assert info["fix_target"] == "python"


def test_system_exception_fix_target_inference():
    """fix_target 根据异常分类和消息自动推断，也允许显式覆盖"""
    cases = [
        ({"message": "Input file not found", "exc_category": "ENVIRONMENT_ISSUE"}, "rpa"),
        ({"message": "Element not found on page", "exc_category": "UI_CHANGED"}, "rpa"),
        ({"message": "Permission denied", "exc_category": "ENVIRONMENT_ISSUE"}, "python"),
        ({"message": "Rate limited by platform", "exc_category": "THIRD_PARTY_LIMIT"}, "python"),
        ({"message": "Network timeout", "exc_category": "DEPENDENCY_FAILURE"}, "python"),
        ({"message": "Rule missing", "exc_category": "RULE_MISSING"}, "python"),
        ({"message": "Bad data", "exc_category": "DATA_QUALITY"}, "python"),
        ({"message": "Division by zero", "exc_category": "LOGIC_DEFECT"}, "python"),
    ]
    for kwargs, expected in cases:
        assert SystemException(**kwargs).fix_target == expected

    exc = SystemException(
        message="File not found",
        exc_category="ENVIRONMENT_ISSUE",
        fix_target="upstream",
    )
    assert exc.fix_target == "upstream"


@patch("core.ai_analyzer.analyze_crash", _mock_analyze)
@patch("core.exceptions.create_linear_issue", _mock_create_issue)
def test_system_exception_fix_target_snapshot_and_notify(tmp_path):
    """fix_target 同时进入 crash snapshot 和 notify 返回值"""
    exc = SystemException(
        message="Input file not found",
        exc_category="ENVIRONMENT_ISSUE",
    )
    info = exc.notify(extra_payload={"run_id": "fix-target"}, repo_path=str(tmp_path))

    assert info["fix_target"] == "rpa"
    snapshot_path = tmp_path / "crash_snapshots" / "crash_fix-target.json"
    with open(snapshot_path, "r", encoding="utf-8") as f:
        snapshot = json.load(f)
    assert snapshot["fix_target"] == "rpa"


@patch("core.ai_analyzer.analyze_crash", _mock_analyze)
@patch("core.exceptions.create_linear_issue", _mock_create_issue)
def test_system_exception_defaults():
    """SystemException 默认字段"""
    exc = SystemException("测试错误", project="P1")
    info = exc.notify(extra_payload={"run_id": "test-defaults"}, repo_path=".")
    assert info["code"] == "LOGIC_DEFECT"  # 默认 code
    assert info["exc_category"] == "LOGIC_DEFECT"  # 默认 exc_category
    assert info["retryable"] == False


# ── 分类映射测试 ──────────────────────────────────────────────

def test_category_mapping_from_ai():
    """AI 旧分类 → SYSTEM_CATEGORIES 映射验证"""
    from core.ai_analyzer import _normalize_category, _LEGACY_CATEGORY_MAP
    # 旧 AI 分类映射
    assert _normalize_category("DATA_NON_STANDARD") == "DATA_QUALITY"
    assert _normalize_category("LOGIC_ERROR") == "LOGIC_DEFECT"
    assert _normalize_category("NETWORK_BLOCK") == "THIRD_PARTY_LIMIT"
    # 合法分类直通
    assert _normalize_category("UI_CHANGED") == "UI_CHANGED"
    assert _normalize_category("DEPENDENCY_FAILURE") == "DEPENDENCY_FAILURE"
    # 未知分类回退
    assert _normalize_category("some_unknown") == "LOGIC_DEFECT"


def test_legacy_map_values_are_valid():
    """_LEGACY_CATEGORY_MAP 的值必须都在 SYSTEM_CATEGORIES 中"""
    from core.ai_analyzer import _LEGACY_CATEGORY_MAP, _VALID_CATEGORIES
    for key, mapped in _LEGACY_CATEGORY_MAP.items():
        assert mapped in _VALID_CATEGORIES, \
            "映射 %s -> %s 中 %s 不在 SYSTEM_CATEGORIES" % (key, mapped, mapped)
