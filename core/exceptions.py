"""
core/exceptions.py — 异常路由分流器
====================================
L1: BusinessException -> 收集跳过，汇总后通过飞书一次性通知
L2: SystemException   -> 创建 Linear 工单 + 收集，汇总后通过飞书通知

通知策略：批量汇总模式
    不再逐个即时发送飞书消息，而是在 entry.py 中收集所有异常，
    执行完毕后由 send_execution_summary() 一次性汇总发送。
"""

import traceback
import os
import re
from typing import Optional, Dict, Any
from core.notifier import create_linear_issue


def _parse_traceback(tb_str: str) -> Dict[str, Any]:
    """
    从 traceback 文本中提取结构化信息：
    - 最后一个报错帧的文件路径、函数名、行号、代码行
    - 异常类型和异常消息
    """
    result = {
        "error_type": "",
        "error_message": "",
        "file": "",
        "function": "",
        "line_no": "",
        "code_line": "",
        "frames": [],
    }

    if not tb_str or tb_str == "NoneType: None":
        return result

    # 提取异常类型行
    exc_match = re.search(
        r"(\w+Error|\w+Exception|AssertionError|KeyError|IndexError|"
        r"AttributeError|TypeError|ValueError|RuntimeError|ImportError|"
        r"FileNotFoundError|ZeroDivisionError|ConnectionError|TimeoutError|"
        r"json\.decoder\.JSONDecodeError|requests\.exceptions\.\w+):\s*(.*)",
        tb_str,
    )
    if exc_match:
        result["error_type"] = exc_match.group(1)
        result["error_message"] = exc_match.group(2).strip()

    # 提取所有栈帧
    frame_pattern = r'File "(.+?)", line (\d+), in (\w+)\s*\n\s*(.+)'
    frames = re.findall(frame_pattern, tb_str)
    for f in frames:
        result["frames"].append({
            "file": f[0], "line": f[1],
            "function": f[2], "code": f[3].strip(),
        })

    if frames:
        last = frames[-1]
        result["file"] = last[0]
        result["line_no"] = last[1]
        result["function"] = last[2]
        result["code_line"] = last[3].strip()

    return result


def _short_path(full_path: str) -> str:
    """将绝对路径缩短为项目相对路径，方便阅读"""
    for marker in ["core" + os.sep, "commands" + os.sep, "tests" + os.sep]:
        idx = full_path.find(marker)
        if idx != -1:
            return full_path[idx:]
    return os.path.basename(full_path)


class BusinessException(Exception):
    """业务规则异常（可接受，跳过继续）"""

    def __init__(
        self,
        message: str,
        project: str = "未命名项目",
        context: Optional[dict] = None,
    ):
        super().__init__(message)
        self.project = project
        self.context = context or {}
        self.category = "business"

    def notify(self) -> dict:
        """
        返回结构化信息供 entry.py 收集，不再直接发飞书。
        飞书通知由 send_execution_summary() 汇总发送。
        """
        return {
            "category": "business",
            "message": str(self),
            "project": self.project,
            "context": self.context,
        }


class SystemException(Exception):
    """
    系统 Bug 异常（需强制退出，推送 Linear 工单）。

    用法示例::

        # 场景1：在业务处理中抛出
        raise SystemException(
            message="无法连接数据库",
            project="物流追踪",
            action="查询物流单号 HK2025050001 的最新状态",
            expected="返回物流状态 JSON",
            actual="ConnectionError: 连接超时 (30s)",
            payload={"tracking_no": "HK2025050001"},
        )

        # 场景2：捕获真实异常后包装
        try:
            result = api_call()
        except requests.Timeout as e:
            raise SystemException(
                message=str(e),
                project="物流追踪",
                action="调用物流 API 查询运单",
                expected="HTTP 200 + JSON 响应",
                actual=f"requests.Timeout: {e}",
                payload={"url": url, "timeout": 30},
            )
    """

    def __init__(
        self,
        message: str,
        project: str = "未命名项目",
        payload: Optional[dict] = None,
        # 业务上下文（让工单具备直接定位能力）
        action: str = "",      # 触发动作：正在做什么时出错
        expected: str = "",    # 预期结果：系统本来应该怎样
        actual: str = "",      # 实际结果：这次失败造成了什么
    ):
        super().__init__(message)
        self.project = project
        self.traceback_str = traceback.format_exc()
        self.payload = payload or {}
        self.category = "system"

        # 业务上下文
        self.action = action
        self.expected = expected
        self.actual = actual or message  # actual 默认用 message 兜底

        # 自动解析 traceback
        parsed = _parse_traceback(self.traceback_str)
        self.error_type = parsed["error_type"]
        self.error_file = _short_path(parsed["file"])
        self.error_function = parsed["function"]
        self.error_line = parsed["line_no"]
        self.error_code = parsed["code_line"]

    def notify(self, extra_payload: Optional[dict] = None, repo_path: str = ".") -> dict:
        """
        创建 Linear 工单，并返回结构化信息供 entry.py 收集。
        飞书通知由 send_execution_summary() 汇总发送。
        """
        merged = {**self.payload}
        if extra_payload:
            merged.update(extra_payload)

        # 创建 Linear 工单（测试环境会跳过）
        issue_url = ""
        issue_success = create_linear_issue(
            error_msg=str(self),
            trace=self.traceback_str,
            payload_data=merged if merged else {},
            project=self.project,
            repo_path=repo_path,
            error_type=self.error_type,
            error_file=self.error_file,
            error_function=self.error_function,
            error_line=self.error_line,
            error_code=self.error_code,
            action=self.action,
            expected=self.expected,
            actual=self.actual,
        )

        return {
            "category": "system",
            "message": str(self),
            "project": self.project,
            "error_type": self.error_type,
            "error_file": self.error_file,
            "issue_success": issue_success,
            "issue_url": issue_url,
        }
