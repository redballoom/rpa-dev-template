"""core/notifier.py — 告警通知（飞书 + Linear 双通道）"""
import requests
import json
import traceback
import sys
from typing import Optional, Dict, Any

try:
    if hasattr(sys.stdout, "encoding") and sys.stdout.encoding and sys.stdout.encoding.upper() == "GBK":
        import io
        if hasattr(sys.stdout, "buffer"):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except AttributeError:
    pass

from core.config import FEISHU_WEBHOOK, LINEAR_API_KEY, LINEAR_TEAM_ID, LINEAR_GRAPHQL_URL


# ── 飞书：业务异常黄牌（L1）───────────────────────────────────

def send_business_alert(project: str, message: str, context: Optional[Dict[str, Any]] = None) -> bool:
    """
    飞书 L1 业务异常提醒（黄牌）。
    BusinessException 触发，跳过继续执行。
    """
    content = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"[{project}] 业务异常提醒"},
                "template": "yellow",
            },
            "elements": [{"tag": "markdown", "content": f"**异常信息**\n{message}"}],
        },
    }
    if context:
        ctx = "\n".join([f"**{k}**: {v}" for k, v in context.items()])
        content["card"]["elements"].append({"tag": "markdown", "content": f"**上下文**\n{ctx}"})
    return _feishu_post(content)


# ── 工具函数 ────────────────────────────────────────────────

def _get_current_branch(repo_path: str = ".") -> str:
    """获取当前 Git 分支名称，读失败时返回 'unknown'"""
    try:
        import subprocess
        res = subprocess.run(
            ["git", "-C", repo_path, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return res.stdout.strip()
    except Exception:
        return "unknown"


def _is_production_env(repo_path: str = ".") -> bool:
    """
    检查当前 Git 分支是否为生产环境（main）。
    测试环境（fix/bug-test）不创建工单，避免污染 Linear。
    """
    return _get_current_branch(repo_path) == "main"


# ── Linear：系统 Bug 工单（L2）───────────────────────────────

def create_linear_issue(
    error_msg: str,
    trace: str,
    payload_data: Dict[str, Any],
    project: str = "RPA",
    repo_path: str = ".",
) -> bool:
    """
    将 Python 系统 Bug 推送为 Linear 工单。

    路由目标：SystemException 触发时调用（不再走飞书红牌）。

    Args:
        error_msg:  报错信息摘要（用于工单标题）
        trace:      traceback.format_exc() 堆栈
        payload_data: 触发时的入参载荷
        project:    项目名称（用于标题前缀）

    Returns:
        bool: 工单是否创建成功
    """
    # 测试分支（fix/bug-test）不创建工单，仅打印提示
    if repo_path and not _is_production_env(repo_path):
        branch = _get_current_branch(repo_path)
        print(f"[notifier] ℹ️ 当前分支 [{branch}] 为测试环境，跳过 Linear 工单创建")
        return True

    title = f"🐛 [RPA Bug] {error_msg.split(':')[0]}"
    description = (
        f"**报错信息:**\n{error_msg}\n\n"
        f"**报错堆栈:**\n```python\n{trace}\n```\n\n"
        f"**输入参数载荷:**\n```json\n{json.dumps(payload_data, ensure_ascii=False, indent=2)}\n```"
    )

    mutation = """
    mutation IssueCreate($title: String!, $description: String!, $teamId: String!) {
      issueCreate(input: {title: $title, description: $description, teamId: $teamId}) {
        success
        issue {
          id
          title
          url
        }
      }
    }
    """

    variables = {
        "title": title,
        "description": description,
        "teamId": LINEAR_TEAM_ID,
    }

    try:
        response = requests.post(
            LINEAR_GRAPHQL_URL,
            headers={
                "Authorization": LINEAR_API_KEY,
                "Content-Type": "application/json",
            },
            json={"query": mutation, "variables": variables},
            timeout=15,
        )
        result = response.json()

        if result.get("data", {}).get("issueCreate", {}).get("success"):
            issue_url = result["data"]["issueCreate"]["issue"]["url"]
            print(f"[notifier] ✅ Linear 工单创建成功: {issue_url}")
            return True
        else:
            print(f"[notifier] ❌ Linear 工单创建失败: {result}")
            return False

    except Exception as e:
        print(f"[notifier] ❌ Linear 请求异常: {e}")
        return False


# ── 内部工具 ────────────────────────────────────────────────

def _feishu_post(data: dict) -> bool:
    try:
        r = requests.post(FEISHU_WEBHOOK, json=data, timeout=10)
        result = r.json()
        if result.get("code") != 0:
            print(f"[notifier] 飞书发送失败: {result.get('msg', '')}")
            return False
        print("[notifier] ✅ 飞书通知已发送")
        return True
    except Exception as e:
        print(f"[notifier] 飞书请求异常: {e}")
        return False
