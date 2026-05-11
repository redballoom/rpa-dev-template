"""core/notifier.py — 告警通知（飞书 + Linear 双通道 + AI 分析增强）"""
import requests
import json
import traceback
import sys
from typing import Optional, Dict, Any, List

try:
    if hasattr(sys.stdout, "encoding") and sys.stdout.encoding and sys.stdout.encoding.upper() == "GBK":
        import io
        if hasattr(sys.stdout, "buffer"):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except AttributeError:
    pass

from core.config import (
    FEISHU_WEBHOOK,
    LINEAR_API_KEY,
    LINEAR_TEAM_ID,
    LINEAR_GRAPHQL_URL,
    LINEAR_PROJECT_NAME,
    LINEAR_PROJECT_ID,
)


# ════════════════════════════════════════════════════════════════
#  飞书通知：批量汇总模式（L1 警告 + L2 异常 合并发送）
# ════════════════════════════════════════════════════════════════

def send_execution_summary(
    project: str,
    run_id: str,
    total: int,
    success_count: int,
    warnings: List[Dict[str, Any]],
    errors: List[Dict[str, Any]],
) -> bool:
    """
    飞书执行汇总通知（一次说完，不再逐个轰炸）。
    """
    if not warnings and not errors:
        print("[notifier] 全部成功 (%d/%d)，跳过飞书通知" % (success_count, total))
        return True

    warn_count = len(warnings)
    err_count = len(errors)
    has_error = err_count > 0

    title = (
        "🔴 [%s] 执行中断 %s" % (project, run_id)
        if has_error
        else "📊 [%s] 执行报告 %s" % (project, run_id)
    )
    template = "red" if has_error else "yellow"

    stat_parts = ["✅ 成功 %d/%d" % (success_count, total)]
    if warn_count:
        stat_parts.append("⚠️ 跳过 %d" % warn_count)
    if err_count:
        stat_parts.append("🔴 异常 %d" % err_count)
    stat_line = "  ".join(stat_parts)

    elements = [{"tag": "markdown", "content": stat_line}]

    if errors:
        err_lines = []
        for err in errors:
            task_name = err.get("task", {}).get("name", "未知任务")
            msg = err.get("message", "未知错误")[:80]
            error_type = err.get("error_type", "")
            issue_url = err.get("issue_url", "")
            line = "**· 任务[%s]** → %s: %s" % (task_name, error_type, msg)
            if issue_url:
                line += "\n  → [查看工单](%s)" % issue_url
            err_lines.append(line)
        elements.append({
            "tag": "markdown",
            "content": "**🔴 异常明细**\n" + "\n".join(err_lines),
        })

    if warnings:
        warn_lines = []
        for w in warnings:
            task_name = w.get("task", {}).get("name", "未知任务")
            msg = w.get("message", "")[:80]
            warn_lines.append("**· 任务[%s]** → %s" % (task_name, msg))
        elements.append({
            "tag": "markdown",
            "content": "**⚠️ 跳过明细**\n" + "\n".join(warn_lines),
        })

    content = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": template,
            },
            "elements": elements,
        },
    }
    return _feishu_post(content)


# ── 工具函数 ────────────────────────────────────────────────

def _get_current_branch(repo_path: str = ".") -> str:
    try:
        import subprocess
        res = subprocess.run(
            ["git", "-C", repo_path, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, check=True, timeout=5,
        )
        return res.stdout.strip()
    except Exception:
        return "unknown"


def _get_current_commit(repo_path: str = ".") -> str:
    try:
        import subprocess
        res = subprocess.run(
            ["git", "-C", repo_path, "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True, timeout=5,
        )
        return res.stdout.strip()
    except Exception:
        return "unknown"


def _is_production_env(repo_path: str = ".") -> bool:
    return _get_current_branch(repo_path) == "main"


def _linear_request(query: str, variables: dict = None) -> Optional[dict]:
    try:
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        response = requests.post(
            LINEAR_GRAPHQL_URL,
            headers={
                "Authorization": LINEAR_API_KEY,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=15,
        )
        result = response.json()
        if "errors" in result:
            print("[notifier] ❌ GraphQL 错误: %s" % result["errors"])
            return None
        return result.get("data")
    except Exception as e:
        print("[notifier] ❌ Linear 请求异常: %s" % e)
        return None


# ── Linear 项目管理 ──────────────────────────────────────────

def _ensure_linear_project() -> Optional[str]:
    if LINEAR_PROJECT_ID:
        return LINEAR_PROJECT_ID

    query = """
    query FindProject($name: String!) {
      projects(filter: {name: {eq: $name}}) {
        nodes { id name state }
      }
    }
    """
    data = _linear_request(query, {"name": LINEAR_PROJECT_NAME})
    if data:
        nodes = data.get("projects", {}).get("nodes", [])
        if nodes:
            print("[notifier] 📂 已找到 Linear 项目: %s (%s)" % (nodes[0]["name"], nodes[0]["id"]))
            return nodes[0]["id"]

    print("[notifier] 📂 项目 [%s] 不存在，自动创建..." % LINEAR_PROJECT_NAME)
    mutation = """
    mutation CreateProject($name: String!, $teamIds: [String!]!) {
      projectCreate(input: {name: $name, teamIds: $teamIds}) {
        success
        project { id name }
      }
    }
    """
    data = _linear_request(mutation, {"name": LINEAR_PROJECT_NAME, "teamIds": [LINEAR_TEAM_ID]})
    if data and data.get("projectCreate", {}).get("success"):
        project = data["projectCreate"]["project"]
        print("[notifier] 📂 ✅ 项目创建成功: %s (%s)" % (project["name"], project["id"]))
        return project["id"]

    print("[notifier] ❌ Linear 项目查找/创建失败，工单将不关联项目")
    return None


# ── Linear：系统 Bug 工单（L2 + AI 增强）────────────────────

def create_linear_issue(
    error_msg: str,
    trace: str,
    payload_data: Dict[str, Any],
    project: str = "RPA",
    repo_path: str = ".",
    error_type: str = "",
    error_file: str = "",
    error_function: str = "",
    error_line: str = "",
    error_code: str = "",
    action: str = "",
    expected: str = "",
    actual: str = "",
    ai_analysis: Optional[dict] = None,
) -> Any:
    """
    创建 Linear 工单，支持 AI 分析增强。

    Args:
        ai_analysis: Optional dict from ai_analyzer.analyze_crash().
                     If present, enriches title + description with AI insights.
    """
    # 测试分支不创建工单
    if repo_path and not _is_production_env(repo_path):
        branch = _get_current_branch(repo_path)
        print("[notifier] INFO: branch [%s] is test env, skip Linear issue" % branch)
        return {"success": True, "issue_url": ""}

    project_id = _ensure_linear_project()

    # ── 工单标题 ─────────────────────────────────────────────
    # AI analysis overrides default title generation
    if ai_analysis and ai_analysis.get("summary"):
        title = "[Bug] %s" % ai_analysis["summary"]
    elif action and error_type:
        title = "[Bug] %s 失败 - %s" % (action, error_type)
    elif error_type and error_file:
        short_file = error_file.replace("\\", "/")
        title = "[Bug] %s in %s:%s()" % (error_type, short_file, error_function)
    elif error_type:
        title = "[Bug] %s: %s" % (error_type, error_msg.split(chr(10))[0][:60])
    else:
        title = "[Bug] %s" % error_msg.split(":")[0][:60]

    # ── 工单描述 ─────────────────────────────────────────────
    branch = _get_current_branch(repo_path)
    commit = _get_current_commit(repo_path)

    parts = []

    # 1. 业务上下文
    if action or expected or actual:
        parts.append("## 业务上下文")
        ctx_lines = ["| 项目 | 内容 |", "|------|------|"]
        if action:
            ctx_lines.append("| **触发动作** | %s |" % action)
        if expected:
            ctx_lines.append("| **预期结果** | %s |" % expected)
        if actual:
            ctx_lines.append("| **实际结果** | %s |" % actual)
        parts.append("\n".join(ctx_lines))

    # 2. 错误摘要
    parts.append("\n## 错误摘要")
    summary_lines = ["| 项目 | 值 |", "|------|------|"]
    summary_lines.append("| 异常类型 | `%s` |" % (error_type or "Unknown"))
    summary_lines.append("| 出错文件 | `%s` |" % (error_file or "Unknown"))
    summary_lines.append("| 出错函数 | `%s` |" % (error_function or "Unknown"))
    if error_line:
        summary_lines.append("| 行号 | L%s |" % error_line)
    summary_lines.append("| 所属项目 | %s |" % project)
    summary_lines.append("| 环境 | `%s@%s` |" % (branch, commit))
    parts.append("\n".join(summary_lines))

    # 3. 出错代码
    if error_code:
        parts.append("\n## 出错代码\n```python\n# %s L%s\n%s\n```" % (error_file, error_line, error_code))

    # 4. AI 分析（核心增强）
    if ai_analysis:
        ai_lines = ["## 🤖 AI 根因分析"]
        ai_lines.append("\n### 严重度")
        ai_lines.append("| 维度 | 评估 |")
        ai_lines.append("|------|------|")
        ai_lines.append("| 严重级别 | `%s` |" % ai_analysis.get("severity", "unknown"))
        ai_lines.append("| 优先级 | `%s` |" % ai_analysis.get("priority", "unknown"))
        ai_lines.append("| 异常类别 | `%s` |" % ai_analysis.get("category", "unknown"))
        ai_lines.append("\n### 根因分析")
        ai_lines.append(ai_analysis.get("root_cause", "N/A"))
        ai_lines.append("\n### 修复建议")
        ai_lines.append("```python")
        ai_lines.append(ai_analysis.get("suggested_fix", "N/A"))
        ai_lines.append("```")
        parts.append("\n".join(ai_lines))

    # 5. 报错信息
    parts.append("\n## 报错信息\n```\n%s\n```" % error_msg)

    # 6. 堆栈追踪
    parts.append(
        "\n## 堆栈追踪\n<details>\n\n```python\n%s\n```\n\n</details>" % (
            trace or "无堆栈信息（手动 raise 的异常，无真实栈帧）"
        )
    )

    # 7. 输入参数
    if payload_data:
        parts.append(
            "\n## 输入参数\n```json\n%s\n```" % json.dumps(payload_data, ensure_ascii=False, indent=2)
        )

    description = "\n".join(parts)

    # ── 创建 Issue ──────────────────────────────────────────
    mutation = """
    mutation IssueCreate($title: String!, $description: String!, $teamId: String!, $projectId: String) {
      issueCreate(input: {title: $title, description: $description, teamId: $teamId, projectId: $projectId}) {
        success
        issue { id title url }
      }
    }
    """
    variables = {
        "title": title,
        "description": description,
        "teamId": LINEAR_TEAM_ID,
        "projectId": project_id,
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
            print("[notifier] ✅ Linear 工单创建成功: %s" % issue_url)
            return {"success": True, "issue_url": issue_url}
        else:
            print("[notifier] ❌ Linear 工单创建失败: %s" % result)
            return {"success": False, "issue_url": ""}
    except Exception as e:
        print("[notifier] ❌ Linear 请求异常: %s" % e)
        return {"success": False, "issue_url": ""}


# ── 内部工具 ────────────────────────────────────────────────

def _feishu_post(data: dict) -> bool:
    try:
        r = requests.post(FEISHU_WEBHOOK, json=data, timeout=10)
        result = r.json()
        if result.get("code") != 0:
            print("[notifier] 飞书发送失败: %s" % result.get("msg", ""))
            return False
        print("[notifier] ✅ 飞书通知已发送")
        return True
    except Exception as e:
        print("[notifier] 飞书请求异常: %s" % e)
        return False
