"""
core/config.py — 项目配置集中管理
==================================
优先从项目根目录的 project.json 读取配置（影刀生成），
读取失败时回退到本文件的硬编码默认值（开发/测试兜底）。
"""
import json, os

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROJECT_JSON_PATH = os.path.join(_PROJECT_ROOT, "project.json")


def _load_project_config() -> dict:
    if not os.path.exists(_PROJECT_JSON_PATH):
        return {}
    try:
        with open(_PROJECT_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print("[config] WARN: project.json read failed: %s, using defaults" % e)
        return {}


_cfg = _load_project_config()

# ── Project ─────────────────────────────────────────────────
PROJECT = _cfg.get("project", "RPA")

# ── Feishu ──────────────────────────────────────────────────
FEISHU_WEBHOOK = _cfg.get("feishu_webhook", "")

# ── Linear ──────────────────────────────────────────────────
_linear_cfg = _cfg.get("linear", {})
LINEAR_API_KEY = _linear_cfg.get("api_key", "")
LINEAR_TEAM_ID = _linear_cfg.get("team_id", "")
LINEAR_GRAPHQL_URL = "https://api.linear.app/graphql"
LINEAR_PROJECT_NAME = _linear_cfg.get("project_name", "")
LINEAR_PROJECT_ID = _linear_cfg.get("project_id", "")

# ── AI Analysis (Volcengine Ark) ────────────────────────────
_ai_cfg = _cfg.get("ai", {})
AI_ENABLED = _ai_cfg.get("enabled", False)
AI_API_KEY = _ai_cfg.get("api_key", "")
AI_MODEL = _ai_cfg.get("model", "ep-20260509143138-njpgt")
AI_TIMEOUT = _ai_cfg.get("timeout", 15)

# ── Startup diagnostic ──────────────────────────────────────
if _cfg:
    print("[config] OK: project.json loaded (project: %s)" % PROJECT)
    if AI_ENABLED and AI_API_KEY:
        print("[config] AI analysis: enabled (model: %s)" % AI_MODEL)
    elif AI_ENABLED and not AI_API_KEY:
        print("[config] AI analysis: enabled but no API key set")
    else:
        print("[config] AI analysis: disabled")
else:
    print("[config] WARN: project.json not found, using defaults")
