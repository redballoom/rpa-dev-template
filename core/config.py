"""
core/config.py — 项目配置集中管理
==================================
加载顺序：project.template.json（默认值）→ project.json（覆盖）
深度合并策略：模板提供骨架，本地配置覆盖具体值。
"""
import json, os

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TEMPLATE_PATH = os.path.join(_PROJECT_ROOT, "project.template.json")
_PROJECT_JSON_PATH = os.path.join(_PROJECT_ROOT, "project.json")


def _deep_merge(base: dict, override: dict) -> dict:
    """深度合并两个字典，override 的值覆盖 base"""
    result = dict(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def _load_json_file(path: str) -> dict:
    """安全读取 JSON 文件，失败返回空字典"""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print("[config] WARN: %s read failed: %s" % (os.path.basename(path), e))
        return {}


def _load_merged_config() -> dict:
    """
    加载合并后的配置。
    1. 先读 project.template.json（默认值）
    2. 再读 project.json（覆盖）
    3. 深度合并（嵌套 dict 也合并）
    """
    base = _load_json_file(_TEMPLATE_PATH)
    override = _load_json_file(_PROJECT_JSON_PATH)
    if not base and not override:
        return {}
    if not override:
        return base
    if not base:
        return override
    return _deep_merge(base, override)


# ── 加载配置 ────────────────────────────────────────────────
_cfg = _load_merged_config()

# ── 项目名称 ────────────────────────────────────────────────
PROJECT = _cfg.get("project", "RPA")

# ── 飞书通知 ────────────────────────────────────────────────
FEISHU_WEBHOOK = _cfg.get("feishu_webhook", "")

# ── Linear 工单 ─────────────────────────────────────────────
_linear_cfg = _cfg.get("linear", {})
LINEAR_API_KEY = _linear_cfg.get("api_key", "")
LINEAR_TEAM_ID = _linear_cfg.get("team_id", "")
LINEAR_GRAPHQL_URL = "https://api.linear.app/graphql"
LINEAR_PROJECT_NAME = _linear_cfg.get("project_name", "")
LINEAR_PROJECT_ID = _linear_cfg.get("project_id", "")
LINEAR_ASSIGNEE_ID = _linear_cfg.get("assignee_id", "")

# ── AI 分析 (OpenAI-compatible) ─────────────────────────────
_ai_cfg = _cfg.get("ai", {})
AI_ENABLED = _ai_cfg.get("enabled", False)
AI_BASE_URL = _ai_cfg.get("base_url", "")
AI_API_KEY = _ai_cfg.get("api_key", "")
AI_MODEL = _ai_cfg.get("model", "")
_ai_api_format_raw = str(_ai_cfg.get("api_format", "chat_completions") or "").strip().lower().replace("-", "_")
AI_API_FORMAT = {
    "chat.completions": "chat_completions",
    "chat_completion": "chat_completions",
    "completions": "chat_completions",
    "response": "responses",
}.get(_ai_api_format_raw, _ai_api_format_raw)
AI_TIMEOUT = _ai_cfg.get("timeout", 15)
AI_API_FORMATS = ("chat_completions", "responses")

# ── 配置校验 ────────────────────────────────────────────────

# 关键字段定义：(config 变量名, 字段中文描述, 是否必须非空)
_REQUIRED_FIELDS = [
    ("PROJECT", "项目名称(project)", True),
    ("FEISHU_WEBHOOK", "飞书 Webhook(feishu_webhook)", False),
    ("LINEAR_API_KEY", "Linear API Key(linear.api_key)", False),
    ("LINEAR_TEAM_ID", "Linear Team ID(linear.team_id)", False),
]


def validate_config() -> dict:
    """
    运行前配置自检。

    Returns:
        dict: {
            "valid": bool,          # 是否通过校验
            "fatal": bool,          # 是否致命（必须字段缺失）
            "missing": list[str],   # 缺失的必须字段列表
            "warnings": list[str],  # 可选字段缺失警告
            "message": str,         # 汇总消息
        }
    """
    missing = []
    warnings = []
    for var_name, desc, required in _REQUIRED_FIELDS:
        value = globals().get(var_name, "")
        if not value:
            if required:
                missing.append("%s (%s)" % (desc, var_name))
            else:
                warnings.append("%s 未配置 (%s)" % (desc, var_name))
    # AI 启用但缺 API Key
    if AI_ENABLED and not AI_API_KEY:
        warnings.append("AI 分析已启用但 API Key 未配置 (AI_API_KEY)")
    if AI_ENABLED and not AI_BASE_URL:
        warnings.append("AI 分析已启用但 Base URL 未配置 (AI_BASE_URL)")
    if AI_ENABLED and not AI_MODEL:
        warnings.append("AI 分析已启用但模型未配置 (AI_MODEL)")
    if AI_ENABLED and AI_API_FORMAT not in AI_API_FORMATS:
        warnings.append(
            "AI API 格式不支持: %s，可选值: %s"
            % (AI_API_FORMAT, ", ".join(AI_API_FORMATS))
        )

    is_fatal = len(missing) > 0
    parts = []
    if missing:
        parts.append("致命缺失: %s" % "; ".join(missing))
    if warnings:
        parts.append("警告: %s" % "; ".join(warnings))
    message = " | ".join(parts) if parts else "配置校验通过"

    return {
        "valid": not is_fatal,
        "fatal": is_fatal,
        "missing": missing,
        "warnings": warnings,
        "message": message,
    }


# ── 启动诊断 ────────────────────────────────────────────────
if _cfg:
    src = []
    if os.path.exists(_TEMPLATE_PATH):
        src.append("template")
    if os.path.exists(_PROJECT_JSON_PATH):
        src.append("project.json")
    print("[config] OK: loaded from %s (project: %s)" % ("+".join(src), PROJECT))
    if AI_ENABLED and AI_API_KEY:
        print("[config] AI analysis: enabled (model: %s)" % AI_MODEL)
    elif AI_ENABLED and not AI_API_KEY:
        print("[config] AI analysis: enabled but no API key set")
    else:
        print("[config] AI analysis: disabled")
else:
    print("[config] WARN: no config found, using defaults")
