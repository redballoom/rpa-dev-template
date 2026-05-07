"""
core/config.py — 项目配置集中管理
==================================
优先从项目根目录的 project.json 读取配置（影刀生成），
读取失败时回退到本文件的硬编码默认值（开发/测试兜底）。

{"project":"物流追踪系统","feishu_webhook":"https://open.feishu.cn/...","linear":{"api_key":"lin_api_xxx","team_id":"xxx","project_name":"物流追踪","project_id":""}}
"""

import json
import os

# ── 定位 project.json ──────────────────────────────────────
# 从本文件向上两级找到项目根目录（core/config.py → 项目根）
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROJECT_JSON_PATH = os.path.join(_PROJECT_ROOT, "project.json")


def _load_project_config() -> dict:
    """
    从项目根目录读取 project.json。
    文件不存在或格式错误时返回空字典，由调用方使用硬编码默认值。
    """
    if not os.path.exists(_PROJECT_JSON_PATH):
        return {}
    try:
        with open(_PROJECT_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"[config] WARN: project.json read failed: {e}, using defaults")
        return {}


# ── 加载配置 ────────────────────────────────────────────────
_cfg = _load_project_config()

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


# ── 启动诊断 ────────────────────────────────────────────────
if _cfg:
    print(f"[config] OK: project.json loaded (project: {PROJECT})")
else:
    print(f"[config] WARN: project.json not found, using defaults")
