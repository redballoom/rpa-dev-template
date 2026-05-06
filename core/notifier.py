"""
core/notifier.py — 消息通知层
================================
职能: L1 飞书通知（业务异常 + 系统告警）
      通过飞书自定义机器人 Webhook 发送消息。
"""

import requests
import json
import traceback as tb
import sys
from typing import Optional

# Windows GBK 编码兼容
if sys.stdout.encoding and sys.stdout.encoding.upper() == "GBK":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── 飞书 Webhook ──
FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/e4a52f76-64dd-45e0-872c-93c94a6474e7"


def send_business_alert(project: str, message: str, context: Optional[dict] = None) -> bool:
    """
    L1 业务异常通知 — 静默处理，仅通知统计

    触发场景:
        - 账号不符合要求
        - 数据校验不通过
        - 业务规则拦截
    """
    content = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"[{project}] 业务异常提醒"},
                "template": "yellow"
            },
            "elements": [
                {"tag": "markdown", "content": f"**异常信息**\n{message}"},
            ]
        }
    }

    if context:
        ctx_text = "\n".join([f"**{k}**: {json.dumps(v, ensure_ascii=False, indent=2) if isinstance(v, (dict, list)) else v}" for k, v in context.items()])
        content["card"]["elements"].append(
            {"tag": "markdown", "content": f"**上下文**\n{ctx_text}"}
        )

    return _post(content)


def send_system_alert(project: str, message: str, traceback_str: str = "",
                      payload: Optional[dict] = None) -> bool:
    """
    L2 系统异常通知 — 需人工介入，强制退出

    触发场景:
        - 网页结构变更导致 KeyError
        - DOM 元素找不到
        - 接口响应格式异常
    """
    trace = traceback_str or tb.format_exc()

    content = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"🚨 [{project}] 系统 Bug — 需人工介入"},
                "template": "red"
            },
            "elements": [
                {"tag": "markdown", "content": f"**异常信息**\n{message}"},
                {"tag": "markdown", "content": f"**堆栈追踪**\n```\n{trace[:2000]}\n```"},
            ]
        }
    }

    if payload:
        payload_text = json.dumps(payload, ensure_ascii=False, indent=2)
        content["card"]["elements"].append(
            {"tag": "markdown", "content": f"**毒性参数载荷**\n```\n{payload_text[:2000]}\n```"}
        )

    return _post(content)


def _post(data: dict) -> bool:
    """发送飞书消息"""
    try:
        resp = requests.post(
            FEISHU_WEBHOOK,
            json=data,
            timeout=10
        )
        result = resp.json()
        if result.get("code") != 0:
            print(f"[notifier] 飞书发送失败: {result.get('msg', '')}")
            return False
        print("[notifier] 飞书通知已发送")
        return True
    except Exception as e:
        print(f"[notifier] 飞书请求异常: {e}")
        return False


# ── 单元测试 ──
if __name__ == "__main__":
    print("=" * 40)
    print("测试 L1 业务异常通知...")
    send_business_alert(
        project="开发模板",
        message="账号 redballoom 未绑定海外仓，跳过处理",
        context={"account": "redballoom", "warehouse": "US_EAST", "rule": "必须绑定海外仓"}
    )

    print("=" * 40)
    print("测试 L2 系统异常通知...")
    try:
        1 / 0  # 故意制造异常
    except ZeroDivisionError:
        send_system_alert(
            project="开发模板",
            message="ZeroDivisionError in core/parser.py:192",
            payload={"item_id": "ORD-20260506-001", "url": "https://example.com/orders/001"}
        )
