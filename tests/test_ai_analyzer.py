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

from core.ai_analyzer import (
    _VALID_CATEGORIES,
    _build_api_url,
    _build_request_payload,
    _extract_json,
    _extract_response_text,
    _normalize_api_format,
    _normalize_category,
)


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


# ── OpenAI-compatible 协议适配 ──────────────────────────────

def test_normalize_api_format_aliases():
    assert _normalize_api_format("chat_completions") == "chat_completions"
    assert _normalize_api_format("completions") == "chat_completions"
    assert _normalize_api_format("responses") == "responses"
    assert _normalize_api_format("response") == "responses"


def test_build_api_url_from_root_or_full_endpoint():
    assert _build_api_url("https://api.openai.com/v1", "chat_completions") == \
        "https://api.openai.com/v1/chat/completions"
    assert _build_api_url("https://proxy.example/v1/", "responses") == \
        "https://proxy.example/v1/responses"
    assert _build_api_url("https://proxy.example/v1/chat/completions", "responses") == \
        "https://proxy.example/v1/responses"


def test_build_request_payload_for_both_formats():
    chat = _build_request_payload("chat_completions", "model-a", "system", "user")
    assert chat["messages"][0] == {"role": "system", "content": "system"}
    assert chat["messages"][1] == {"role": "user", "content": "user"}
    responses = _build_request_payload("responses", "model-b", "system", "user")
    assert responses == {"model": "model-b", "instructions": "system", "input": "user"}


def test_extract_response_text_chat_completions():
    result = {"choices": [{"message": {"content": "chat result"}}]}
    assert _extract_response_text(result) == "chat result"


def test_extract_response_text_responses_output_text():
    assert _extract_response_text({"output_text": "response result"}) == "response result"


def test_extract_response_text_responses_nested_output():
    result = {
        "output": [
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": "part 1"},
                    {"type": "output_text", "text": "part 2"},
                ],
            }
        ]
    }
    assert _extract_response_text(result) == "part 1part 2"


class _FakeResponse:
    status_code = 200
    text = ""

    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


def _analysis_json():
    return (
        '{"root_cause":"cause","suggested_fix":"fix","severity":"medium",'
        '"category":"LOGIC_DEFECT","priority":"medium","summary":"summary"}'
    )


def test_analyze_crash_chat_completions_request(monkeypatch):
    import core.ai_analyzer as analyzer
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["json"] = kwargs["json"]
        return _FakeResponse({"choices": [{"message": {"content": _analysis_json()}}]})

    monkeypatch.setattr(analyzer, "AI_ENABLED", True)
    monkeypatch.setattr(analyzer, "AI_BASE_URL", "https://proxy.example/v1")
    monkeypatch.setattr(analyzer, "AI_API_KEY", "test-key")
    monkeypatch.setattr(analyzer, "AI_MODEL", "test-model")
    monkeypatch.setattr(analyzer, "AI_API_FORMAT", "chat_completions")
    monkeypatch.setattr(analyzer.requests, "post", fake_post)

    result = analyzer.analyze_crash({"message": "failure"})
    assert result["category"] == "LOGIC_DEFECT"
    assert captured["url"] == "https://proxy.example/v1/chat/completions"
    assert captured["json"]["messages"][1]["role"] == "user"


def test_analyze_crash_responses_request(monkeypatch):
    import core.ai_analyzer as analyzer
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["json"] = kwargs["json"]
        return _FakeResponse({"output_text": _analysis_json()})

    monkeypatch.setattr(analyzer, "AI_ENABLED", True)
    monkeypatch.setattr(analyzer, "AI_BASE_URL", "https://proxy.example/v1/")
    monkeypatch.setattr(analyzer, "AI_API_KEY", "test-key")
    monkeypatch.setattr(analyzer, "AI_MODEL", "test-model")
    monkeypatch.setattr(analyzer, "AI_API_FORMAT", "responses")
    monkeypatch.setattr(analyzer.requests, "post", fake_post)

    result = analyzer.analyze_crash({"message": "failure"})
    assert result["category"] == "LOGIC_DEFECT"
    assert captured["url"] == "https://proxy.example/v1/responses"
    assert captured["json"]["input"]
    assert captured["json"]["instructions"]
