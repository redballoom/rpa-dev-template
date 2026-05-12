"""
core/ai_analyzer.py - AI crash analysis with business context awareness

Upgraded from "Debugger" to "Architect" role:
- Analyzes code traceback + business intent + UI context
- 分类体系统一到 SYSTEM_CATEGORIES（7 种）：
    UI_CHANGED / DATA_QUALITY / RULE_MISSING / DEPENDENCY_FAILURE /
    ENVIRONMENT_ISSUE / LOGIC_DEFECT / THIRD_PARTY_LIMIT
- Graceful fallback: no API key / timeout / error -> skip
"""
import json as _json
import requests
from typing import Optional
from core.config import AI_ENABLED, AI_API_KEY, AI_MODEL, AI_TIMEOUT

ARK_API_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

# ── 分类体系：与 exceptions.SYSTEM_CATEGORIES 完全对齐 ─────────
from core.exceptions import SYSTEM_CATEGORIES

# AI 输出合法分类集合
_VALID_CATEGORIES = set(SYSTEM_CATEGORIES.keys())

# 旧分类 → SYSTEM_CATEGORIES 映射（兼容历史 AI 输出和早期版本）
_LEGACY_CATEGORY_MAP = {
    # 旧 AI 分类（v2 遗留）
    "DATA_NON_STANDARD": "DATA_QUALITY",
    "LOGIC_ERROR": "LOGIC_DEFECT",
    "NETWORK_BLOCK": "THIRD_PARTY_LIMIT",
    # 旧模糊关键词（v1 遗留）
    "validation": "DATA_QUALITY",
    "network": "THIRD_PARTY_LIMIT",
    "data": "DATA_QUALITY",
    "logic": "LOGIC_DEFECT",
    "config": "LOGIC_DEFECT",
    "ui": "UI_CHANGED",
    "unknown": "LOGIC_DEFECT",
}

_SYSTEM_PROMPT = """You are a senior cross-border e-commerce RPA architect analyzing an automation failure.
Your role: combine code traceback, business intent, input data, and UI context
to classify the issue into one of:
  - UI_CHANGED: page layout changed, element selectors need recapturing
  - DATA_QUALITY: input data violates business rules or has quality issues
  - RULE_MISSING: business rule is not configured or missing
  - DEPENDENCY_FAILURE: external service / network dependency failed (retryable)
  - ENVIRONMENT_ISSUE: runtime environment problem (path, config, permission)
  - LOGIC_DEFECT: Python script logic defect or bug
  - THIRD_PARTY_LIMIT: platform rate-limiting, CAPTCHA, or firewall
Prefer suggesting fixes at the Python/data layer over selector changes.
Return ONLY valid JSON in this exact format (no markdown fences, no extra text):
{
  "root_cause": "detailed explanation in Chinese or English",
  "suggested_fix": "specific actionable fix suggestion",
  "severity": "critical|high|medium|low",
  "category": "UI_CHANGED|DATA_QUALITY|RULE_MISSING|DEPENDENCY_FAILURE|ENVIRONMENT_ISSUE|LOGIC_DEFECT|THIRD_PARTY_LIMIT",
  "priority": "urgent|high|medium|low",
  "confidence": 0.0-1.0,
  "need_human_review": true|false,
  "test_suggestion": "suggested test case to verify the fix",
  "summary": "one-line summary suitable for issue title"
}"""


def analyze_crash(snapshot: dict) -> Optional[dict]:
    if not AI_ENABLED or not AI_API_KEY:
        print("[ai_analyzer] AI disabled or no API key, skipping")
        return None
    prompt = _build_prompt(snapshot)
    try:
        resp = requests.post(
            ARK_API_URL,
            headers={
                "Authorization": "Bearer " + AI_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "model": AI_MODEL,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
            },
            timeout=AI_TIMEOUT,
        )
        if resp.status_code != 200:
            print("[ai_analyzer] API error: %d %s" % (resp.status_code, resp.text[:200]))
            return None
        result = resp.json()
        raw = result["choices"][0]["message"]["content"]
        return _extract_json(raw)
    except requests.Timeout:
        print("[ai_analyzer] Timeout (%ds), skipping" % AI_TIMEOUT)
        return None
    except Exception as e:
        print("[ai_analyzer] Failed (non-blocking): %s" % e)
        return None


def _normalize_category(cat: str) -> str:
    """将 AI 输出的分类归一化到 SYSTEM_CATEGORIES，未命中则回退到 LOGIC_DEFECT"""
    if cat in _VALID_CATEGORIES:
        return cat
    mapped = _LEGACY_CATEGORY_MAP.get(cat)
    if mapped:
        print("[ai_analyzer] Mapped category '%s' -> '%s'" % (cat, mapped))
        return mapped
    print("[ai_analyzer] Unknown category '%s', fallback to LOGIC_DEFECT" % cat)
    return "LOGIC_DEFECT"


def _extract_json(text: str) -> Optional[dict]:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        start = 1
        if lines[-1].strip().startswith("```"):
            end = -1
        else:
            end = len(lines)
        text = "\n".join(lines[start:end]).strip()
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end != -1:
        text = text[brace_start : brace_end + 1]
    try:
        data = _json.loads(text)
        # 必需字段校验（新增 confidence / need_human_review / test_suggestion 可选）
        required = ["root_cause", "suggested_fix", "severity", "category", "priority", "summary"]
        if not all(k in data for k in required):
            missing = [k for k in required if k not in data]
            print("[ai_analyzer] Incomplete JSON: missing keys: %s" % missing)
            return None
        # 分类归一化
        data["category"] = _normalize_category(data["category"])
        # 填充可选字段默认值
        data.setdefault("confidence", 0.5)
        data.setdefault("need_human_review", False)
        data.setdefault("test_suggestion", "")
        # confidence 范围校验
        try:
            data["confidence"] = max(0.0, min(1.0, float(data["confidence"])))
        except (ValueError, TypeError):
            data["confidence"] = 0.5
        # need_human_review 布尔校验
        if not isinstance(data["need_human_review"], bool):
            data["need_human_review"] = bool(data["need_human_review"])
        print("[ai_analyzer] Analysis: severity=%(severity)s category=%(category)s "
              "priority=%(priority)s confidence=%(confidence)s" % data)
        return data
    except _json.JSONDecodeError as e:
        print("[ai_analyzer] Parse error: %s" % e)
        return None


def _build_prompt(snapshot: dict) -> str:
    tb = (snapshot.get("traceback") or "")[:2000]
    payload = snapshot.get("payload") or {}
    pstr = _json.dumps(payload, ensure_ascii=False, indent=2) if payload else "{}"
    selectors = snapshot.get("last_interacted_selectors") or []
    sstr = _json.dumps(selectors, ensure_ascii=False)
    parts = []

    # ── 运行时上下文（R3-7 增强）──
    has_ctx = any(snapshot.get(k) for k in ["operator", "env", "source", "step_name", "input_file"])
    if has_ctx:
        parts.append("## Runtime Context")
        if snapshot.get("operator"):
            parts.append("- Operator: %s" % snapshot["operator"])
        if snapshot.get("env"):
            parts.append("- Environment: %s" % snapshot["env"])
        if snapshot.get("source"):
            parts.append("- Source: %s" % snapshot["source"])
        if snapshot.get("step_name"):
            parts.append("- Step: %s" % snapshot["step_name"])
        if snapshot.get("input_file"):
            parts.append("- Input File: %s" % snapshot["input_file"])
        if snapshot.get("upstream_run_id"):
            parts.append("- Upstream Run: %s" % snapshot["upstream_run_id"])
        parts.append("")

    parts.append("## Business Intent")
    parts.append("- Intent: %s" % snapshot.get("intent", "N/A"))
    parts.append("- Rule Context: %s" % snapshot.get("rule_context", "N/A"))
    if snapshot.get("code"):
        parts.append("- Exception Code: %s" % snapshot["code"])
    if snapshot.get("exc_category"):
        parts.append("- Exception Category: %s" % snapshot["exc_category"])
    parts.append("")

    parts.append("## Technical Context")
    parts.append("- Error: %s" % snapshot.get("error_type", "Unknown"))
    parts.append("- Message: %s" % snapshot.get("message", "N/A"))
    parts.append("- Action: %s" % snapshot.get("action", "N/A"))
    parts.append("- File: %s / Function: %s / Line: %s" % (
        snapshot.get("file", "N/A"),
        snapshot.get("function", "N/A"),
        snapshot.get("line", "N/A"),
    ))
    parts.append("- Code: %s" % snapshot.get("code_line", snapshot.get("code", "N/A")))
    parts.append("- Project: %s" % snapshot.get("project", "N/A"))
    parts.append("- Retryable: %s" % snapshot.get("retryable", False))
    parts.append("")
    parts.append("```traceback")
    parts.append(tb[:1000])
    parts.append("```")
    parts.append("")

    parts.append("## Visual & UI")
    parts.append("- Screenshot (local): %s" % snapshot.get("screenshot_path", "N/A"))
    parts.append("- Last Interacted Selectors: %s" % (sstr if sstr != "[]" else "N/A"))
    if snapshot.get("page_url"):
        parts.append("- Page URL: %s" % snapshot["page_url"])
    if snapshot.get("page_title"):
        parts.append("- Page Title: %s" % snapshot["page_title"])
    parts.append("")

    parts.append("## Expectation vs Reality")
    parts.append("- Expected: %s" % snapshot.get("expected", "N/A"))
    parts.append("- Actual: %s" % snapshot.get("actual", "N/A"))
    parts.append("")

    parts.append("## Input Payload")
    parts.append("```json")
    parts.append(pstr)
    parts.append("```")

    return "\n".join(parts)
