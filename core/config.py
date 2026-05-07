"""
core/config.py — 项目配置集中管理
==================================
所有敏感信息（飞书 Webhook、Linear API Key / Team ID）统一在此管理。
影刀 RPA / Python 代码运行时从此模块导入，不再硬编码散落各处。
"""

# ── 飞书通知 ────────────────────────────────────────────────
FEISHU_WEBHOOK = (
    "https://open.feishu.cn/open-apis/bot/v2/hook/e4a52f76-64dd-45e0-872c-93c94a6474e7"
)

# ── Linear 工单 ─────────────────────────────────────────────
LINEAR_API_KEY = "lin_api_mcShEBr22zfPqDpyFrzo2W93FoHXo2DfI5VsJMar"
LINEAR_TEAM_ID = "06d60efd-fef2-4f56-95ff-c4c1fd6c05d3"
LINEAR_GRAPHQL_URL = "https://api.linear.app/graphql"
