"""
core/ai_analyzer.py — AI crash analysis using Volcengine Ark API (chat/completions)

Integrates at core/exceptions.py → SystemException.notify()
after _dump_snapshot(), before create_linear_issue().

Graceful fallback: no API key / timeout / error → skip, keep current behavior.
"""
import json
import requests
from typing import Optional, Dict, Any
from core.config import AI_ENABLED, AI_API_KEY, AI_MODEL, AI_TIMEOUT

ARK_API_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

_SYSTEM_PROMPT = (
    "You are a senior Python debugger analyzing an RPA automation crash. "
    "Given the error context, provide root cause analysis and fix suggestions. "
    "Return ONLY valid JSON in this exact format (no markdown fences, no extra text):\n"
    '{\n'
    '  "root_cause": "detailed explanation of what went wrong",\n'
    '  "suggested_fix": "specific code fix or configuration change",\n'
    '  "severity": "critical|high|medium|low",\n'
    '  "category": "validation|network|data|logic|config|unknown",\n'
    '  "priority": "urgent|high|medium|low",\n'
    '  "summary": "one-line summary suitable for issue title"\n'
    '}'
)


def analyze_crash(snapshot: dict) -> Optional[dict]:
    """Analyze crash snapshot via Volcengine Ark chat/completions API."""
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
        print("[ai_analyzer] Timeout (%ds), skipping AI analysis" % AI_TIMEOUT)
        return None
    except Exception as e:
        print("[ai_analyzer] Failed (non-blocking): %s" % e)
        return None


def _extract_json(text: str) -> Optional[dict]:
    """Extract JSON from model response, handling markdown fences."""
    text = text.strip()
    # Remove markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        start = 1
        if lines[-1].strip().startswith("```"):
            end = -1
        else:
            end = len(lines)
        text = "\n".join(lines[start:end]).strip()
    # Remove leading/trailing non-JSON content
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end != -1:
        text = text[brace_start : brace_end + 1]
    try:
        data = json.loads(text)
        required = ["root_cause", "suggested_fix", "severity", "category", "priority", "summary"]
        if all(k in data for k in required):
            print("[ai_analyzer] Analysis: severity=%(severity)s category=%(category)s priority=%(priority)s" % data)
            return data
        print("[ai_analyzer] Incomplete JSON: missing keys")
        return None
    except json.JSONDecodeError as e:
        print("[ai_analyzer] Parse error: %s" % e)
        return None


def _build_prompt(snapshot: dict) -> str:
    """Build analysis prompt from crash snapshot data."""
    tb = (snapshot.get("traceback") or "")[:2000]
    payload = snapshot.get("payload") or {}
    pstr = json.dumps(payload, ensure_ascii=False, indent=2) if payload else "{}"
    parts = []
    parts.append("## Crash Context")
    parts.append("- Error: %s" % snapshot.get("error_type", "Unknown"))
    parts.append("- Message: %s" % snapshot.get("message", "N/A"))
    parts.append("- Action: %s" % snapshot.get("action", "N/A"))
    parts.append("- Expected: %s" % snapshot.get("expected", "N/A"))
    parts.append("- Actual: %s" % snapshot.get("actual", "N/A"))
    parts.append("- File: %s / Function: %s / Line: %s" % (
        snapshot.get("file", "N/A"),
        snapshot.get("function", "N/A"),
        snapshot.get("line", "N/A"),
    ))
    parts.append("- Code: %s" % snapshot.get("code", "N/A"))
    parts.append("- Project: %s" % snapshot.get("project", "N/A"))
    parts.append("")
    parts.append("## Traceback")
    parts.append("```")
    parts.append(tb)
    parts.append("```")
    parts.append("")
    parts.append("## Input Payload")
    parts.append("```json")
    parts.append(pstr)
    parts.append("```")
    return "\n".join(parts)
