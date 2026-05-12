"""
tests/test_ai_analyzer.py — AI 分析模块测试
=============================================
覆盖：
  - _normalize_category 分类归一化
  - _extract_json JSON 解析与字段填充
  - 分类映射覆盖度
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ai_analyzer import _normalize_category, _extract_json, _VALID_CATEGORIES


# ── _normalize_category 测试 ───────────────────────────────────

def test_normalize_valid_categories():
    """SYSTEM_CATEGORIES 中的分类直通"""
    for cat in _VALID_CATEGORIES:
        assert _normalize_category(cat) == cat, \
            "合法分类 %s 应该直通" % cat


def test_normalize_legacy_categories():
    """旧 AI 分类映射到 SYSTEM_CATEGORIES"""
    assert _normalize_category("DATA_NON_STANDARD") == "DATA_QUALITY"
    assert _normalize_category("LOGIC_ERROR") == "LOGIC_DEFECT"
    assert _normalize_category("NETWORK_BLOCK") == "THIRD_PARTY_LIMIT"


def test_normalize_legacy_keywords():
    """旧关键词映射"""
    assert _normalize_category("validation") == "DATA_QUALITY"
    assert _normalize_category("network") == "THIRD_PARTY_LIMIT"
    assert _normalize_category("data") == "DATA_QUALITY"
    assert _normalize_category("logic") == "LOGIC_DEFECT"
    assert _normalize_category("config") == "LOGIC_DEFECT"
    assert _normalize_category("ui") == "UI_CHANGED"
    assert _normalize_category("unknown") == "LOGIC_DEFECT"


def test_normalize_unknown_fallback():
    """未知分类回退到 LOGIC_DEFECT"""
    assert _normalize_category("totally_new_category") == "LOGIC_DEFECT"
    assert _normalize_category("") == "LOGIC_DEFECT"


# ── _extract_json 测试 ─────────────────────────────────────────

def test_extract_json_valid_full():
    """完整 JSON 解析（含新字段）"""
    raw = '{"root_cause":"原因","suggested_fix":"修复","severity":"high",'\
          '"category":"UI_CHANGED","priority":"urgent","summary":"摘要",'\
          '"confidence":0.85,"need_human_review":true,"test_suggestion":"建议测试"}'
    result = _extract_json(raw)
    assert result is not None
    assert result["category"] == "UI_CHANGED"
    assert result["confidence"] == 0.85
    assert result["need_human_review"] == True
    assert result["test_suggestion"] == "建议测试"


def test_extract_json_missing_optional():
    """缺少可选字段时自动填充默认值"""
    raw = '{"root_cause":"原因","suggested_fix":"修复","severity":"medium",'\
          '"category":"LOGIC_DEFECT","priority":"low","summary":"摘要"}'
    result = _extract_json(raw)
    assert result is not None
    assert result["confidence"] == 0.5  # 默认
    assert result["need_human_review"] == False  # 默认
    assert result["test_suggestion"] == ""  # 默认


def test_extract_json_category_mapping():
    """JSON 中旧分类自动映射"""
    raw = '{"root_cause":"原因","suggested_fix":"修复","severity":"high",'\
          '"category":"DATA_NON_STANDARD","priority":"medium","summary":"摘要"}'
    result = _extract_json(raw)
    assert result is not None
    assert result["category"] == "DATA_QUALITY"


def test_extract_json_confidence_clamp():
    """confidence 超出范围自动裁剪"""
    raw = '{"root_cause":"原因","suggested_fix":"修复","severity":"high",'\
          '"category":"LOGIC_DEFECT","priority":"medium","summary":"摘要",'\
          '"confidence":2.5}'
    result = _extract_json(raw)
    assert result is not None
    assert result["confidence"] == 1.0  # clamped


def test_extract_json_confidence_negative():
    """confidence 负数裁剪为 0"""
    raw = '{"root_cause":"原因","suggested_fix":"修复","severity":"high",'\
          '"category":"LOGIC_DEFECT","priority":"medium","summary":"摘要",'\
          '"confidence":-0.5}'
    result = _extract_json(raw)
    assert result is not None
    assert result["confidence"] == 0.0


def test_extract_json_incomplete():
    """缺少必需字段返回 None"""
    raw = '{"root_cause":"原因","severity":"high"}'
    result = _extract_json(raw)
    assert result is None


def test_extract_json_invalid():
    """非法 JSON 返回 None"""
    result = _extract_json("not json at all")
    assert result is None


def test_extract_json_markdown_fenced():
    """Markdown 代码块包裹的 JSON"""
    raw = '```json\n{"root_cause":"原因","suggested_fix":"修复","severity":"high","category":"UI_CHANGED","priority":"urgent","summary":"摘要"}\n```'
    result = _extract_json(raw)
    assert result is not None
    assert result["category"] == "UI_CHANGED"


# ── 覆盖度验证 ─────────────────────────────────────────────────

def test_valid_categories_matches_system():
    """_VALID_CATEGORIES 必须与 SYSTEM_CATEGORIES 完全一致"""
    from core.exceptions import SYSTEM_CATEGORIES
    assert _VALID_CATEGORIES == set(SYSTEM_CATEGORIES.keys())
