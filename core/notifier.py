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

from core.config import (
    FEISHU_WEBHOOK,
    LINEAR_API_KEY,
    LINEAR_TEAM_ID,
    LINEAR_GRAPHQL_URL,
    LINEAR_PROJECT_NAME,
    LINEAR_PROJECT_ID,
)


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


def _get_current_commit(repo_path: str = ".") -> str:
    """获取当前 Git 短 commit hash，读失败时返回 'unknown'"""
    try:
        import subprocess
        res = subprocess.run(
            ["git", "-C", repo_path, "rev-parse", "--short", "HEAD"],
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


def _linear_request(query: str, variables: dict = None) -> Optional[dict]:
    """Linear GraphQL 请求封装，返回 data 层或 None"""
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
            print(f"[notifier] ❌ GraphQL 错误: {result['errors']}")
            return None
        return result.get("data")
    except Exception as e:
        print(f"[notifier] ❌ Linear 请求异常: {e}")
        return None


# ── Linear 项目管理 ──────────────────────────────────────────

def _ensure_linear_project() -> Optional[str]:
    """
    确保 Linear Project 存在，返回 project_id。

    逻辑：
    1. 如果 config 中已配置 LINEAR_PROJECT_ID，直接使用
    2. 否则按 LINEAR_PROJECT_NAME 查询
    3. 查不到则自动创建
    """
    # 1. 优先使用已知的 project_id
    if LINEAR_PROJECT_ID:
        return LINEAR_PROJECT_ID

    # 2. 按名称查找
    query = """
    query FindProject($name: String!) {
      projects(filter: {name: {eq: $name}}) {
        nodes {
          id
          name
          state
        }
      }
    }
    """
    data = _linear_request(query, {"name": LINEAR_PROJECT_NAME})
    if data:
        nodes = data.get("projects", {}).get("nodes", [])
        if nodes:
            project_id = nodes[0]["id"]
            print(f"[notifier] 📂 已找到 Linear 项目: {nodes[0]['name']} ({project_id})")
            return project_id

    # 3. 项目不存在，自动创建
    print(f"[notifier] 📂 项目 [{LINEAR_PROJECT_NAME}] 不存在，自动创建...")
    mutation = """
    mutation CreateProject($name: String!, $teamIds: [String!]!) {
      projectCreate(input: {name: $name, teamIds: $teamIds}) {
        success
        project {
          id
          name
        }
      }
    }
    """
    data = _linear_request(mutation, {"name": LINEAR_PROJECT_NAME, "teamIds": [LINEAR_TEAM_ID]})
    if data and data.get("projectCreate", {}).get("success"):
        project = data["projectCreate"]["project"]
        project_id = project["id"]
        print(f"[notifier] 📂 ✅ 项目创建成功: {project['name']} ({project_id})")
        return project_id

    print("[notifier] ❌ Linear 项目查找/创建失败，工单将不关联项目")
    return None


# ── Linear：系统 Bug 工单（L2）───────────────────────────────

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
) -> bool:
    """
    将 Python 系统 Bug 推送为 Linear 工单，并关联到对应项目。

    流程：
    1. 检查分支（测试环境跳过）
    2. 检查/创建 Linear Project
    3. 创建 Issue 并关联 Project

    Args:
        error_msg:      报错信息摘要
        trace:          traceback 堆栈
        payload_data:   触发时的入参载荷
        project:        项目名称
        repo_path:      仓库路径
        error_type:     异常类型
        error_file:     出错文件
        error_function: 出错函数名
        error_line:     出错行号
        error_code:     出错代码行
        action:         触发动作：正在做什么时出错
        expected:       预期结果：系统本来应该怎样
        actual:         实际结果：这次失败造成了什么

    Returns:
        bool: 工单是否创建成功
    """
    # 测试分支不创建工单
    if repo_path and not _is_production_env(repo_path):
        branch = _get_current_branch(repo_path)
        print(f"[notifier] INFO: branch [{branch}] is test env, skip Linear issue")
        return True

    project_id = _ensure_linear_project()

    # ── 工单标题 ─────────────────────────────────────────────
    # 优先级：action > error_type + file > error_msg
    if action and error_type:
        title = f"[Bug] {action} 失败 - {error_type}"
    elif error_type and error_file:
        short_file = error_file.replace("\\", "/")
        title = f"[Bug] {error_type} in {short_file}:{error_function}()"
    elif error_type:
        title = f"[Bug] {error_type}: {error_msg.split(chr(10))[0][:60]}"
    else:
        title = f"[Bug] {error_msg.split(':')[0][:60]}"

    # ── 工单描述 ─────────────────────────────────────────────
    branch = _get_current_branch(repo_path)
    commit = _get_current_commit(repo_path)

    parts = []

    # 1. 业务上下文（最重要的定位信息，放在最前面）
    if action or expected or actual:
        parts.append("## 业务上下文")
        ctx_lines = ["| 项目 | 内容 |", "|------|------|"]
        if action:
            ctx_lines.append(f"| **触发动作** | {action} |")
        if expected:
            ctx_lines.append(f"| **预期结果** | {expected} |")
        if actual:
            ctx_lines.append(f"| **实际结果** | {actual} |")
        parts.append("\n".join(ctx_lines))

    # 2. 错误摘要
    parts.append("\n## 错误摘要")
    summary_lines = ["| 项目 | 值 |", "|------|------|"]
    summary_lines.append(f"| 异常类型 | `{error_type or 'Unknown'}` |")
    summary_lines.append(f"| 出错文件 | `{error_file or 'Unknown'}` |")
    summary_lines.append(f"| 出错函数 | `{error_function or 'Unknown'}` |")
    if error_line:
        summary_lines.append(f"| 行号 | L{error_line} |")
    summary_lines.append(f"| 所属项目 | {project} |")
    summary_lines.append(f"| 环境 | `{branch}@{commit}` |")
    parts.append("\n".join(summary_lines))

    # 3. 出错代码
    if error_code:
        parts.append(
            f"\n## 出错代码\n```python\n# {error_file} L{error_line}\n{error_code}\n```"
        )

    # 4. 报错信息
    parts.append(f"\n## 报错信息\n```\n{error_msg}\n```")

    # 5. 堆栈追踪（折叠）
    parts.append(
        "\n## 堆栈追踪\n<details>\n\n```python\n{}\n```\n\n</details>".format(
            trace or "无堆栈信息（手动 raise 的异常，无真实栈帧）"
        )
    )

    # 6. 输入参数
    if payload_data:
        parts.append(
            "\n## 输入参数\n```json\n{}\n```".format(
                json.dumps(payload_data, ensure_ascii=False, indent=2)
            )
        )

    description = "\n".join(parts)

    # 创建 Issue 并关联 Project
    mutation = """
    mutation IssueCreate($title: String!, $description: String!, $teamId: String!, $projectId: String) {
      issueCreate(input: {title: $title, description: $description, teamId: $teamId, projectId: $projectId}) {
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
            proj_info = f" (项目: {LINEAR_PROJECT_NAME})" if project_id else ""
            print(f"[notifier] ✅ Linear 工单创建成功{proj_info}: {issue_url}")
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
