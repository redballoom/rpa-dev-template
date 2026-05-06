"""core/notifier.py — 飞书通知"""
import requests, json, traceback, sys
from typing import Optional

try:
    if hasattr(sys.stdout, "encoding") and sys.stdout.encoding and sys.stdout.encoding.upper() == "GBK":
        import io
        if hasattr(sys.stdout, "buffer"):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except AttributeError:
    pass

FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/e4a52f76-64dd-45e0-872c-93c94a6474e7"

def send_business_alert(project, message, context=None):
    content = {"msg_type": "interactive", "card": {
        "header": {"title": {"tag": "plain_text", "content": f"[{project}] 业务异常提醒"}, "template": "yellow"},
        "elements": [{"tag": "markdown", "content": f"**异常信息**\n{message}"}]}}
    if context:
        ctx = "\n".join([f"**{k}**: {v}" for k, v in context.items()])
        content["card"]["elements"].append({"tag": "markdown", "content": f"**上下文**\n{ctx}"})
    return _post(content)

def send_system_alert(project, message, traceback_str="", payload=None):
    trace = traceback_str or traceback.format_exc()
    content = {"msg_type": "interactive", "card": {
        "header": {"title": {"tag": "plain_text", "content": f"[{project}] 系统 Bug"}, "template": "red"},
        "elements": [
            {"tag": "markdown", "content": f"**异常信息**\n{message}"},
            {"tag": "markdown", "content": f"**堆栈追踪**\n```\n{trace[:2000]}\n```"}]}}
    if payload:
        content["card"]["elements"].append({"tag": "markdown", "content": f"**轿性参数载荷**\n```\n{json.dumps(payload, ensure_ascii=False)[:2000]}\n```"})
    return _post(content)

def _post(data):
    try:
        r = requests.post(FEISHU_WEBHOOK, json=data, timeout=10)
        result = r.json()
        if result.get("code") != 0:
            print(f"[notifier] 飞书失败: {result.get('msg', '')}")
            return False
        print("[notifier] 已发送")
        return True
    except Exception as e:
        print(f"[notifier] 异常: {e}")
        return False
