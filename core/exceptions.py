"""
core/exceptions.py — 异常路由分流器
====================================
L1: BusinessException -> 收集跳过，汇总通知
L2: SystemException   -> 创建 Linear 工单 + 收集，汇总通知

异常编码体系：
  业务编码: DATA_EMPTY / DATA_INVALID / ORDER_NOT_FOUND / DUPLICATE_RECORD / RULE_BLOCKED
  系统分类: UI_CHANGED / DATA_QUALITY / RULE_MISSING / DEPENDENCY_FAILURE / ENVIRONMENT_ISSUE / LOGIC_DEFECT / THIRD_PARTY_LIMIT
"""

import traceback, os, re, json
from datetime import datetime
from typing import Optional, Dict, Any
from core.notifier import create_linear_issue


def _parse_traceback(tb_str: str) -> Dict[str, Any]:
    result = {"error_type": "", "error_message": "", "file": "", "function": "",
              "line_no": "", "code_line": "", "frames": []}
    if not tb_str or tb_str == "NoneType: None":
        return result
    exc_match = re.search(
        r"(\w+Error|\w+Exception|AssertionError|KeyError|IndexError|"
        r"AttributeError|TypeError|ValueError|RuntimeError|ImportError|"
        r"FileNotFoundError|ZeroDivisionError|ConnectionError|TimeoutError|"
        r"json\.decoder\.JSONDecodeError|requests\.exceptions\.\w+):\s*(.*)", tb_str)
    if exc_match:
        result["error_type"] = exc_match.group(1)
        result["error_message"] = exc_match.group(2).strip()
    frames = re.findall(r'File "(.+?)", line (\d+), in (\w+)', tb_str)
    for f in frames:
        result["frames"].append({"file": f[0], "line": f[1], "function": f[2], "code": ""})
    if frames:
        last = frames[-1]
        result["file"] = last[0]; result["line_no"] = last[1]
        result["function"] = last[2]; result["code_line"] = ""
    return result


def _short_path(full_path: str) -> str:
    for marker in ["core" + os.sep, "commands" + os.sep, "tests" + os.sep]:
        idx = full_path.find(marker)
        if idx != -1: return full_path[idx:]
    return os.path.basename(full_path)


# ── 业务异常编码 ────────────────────────────────────────────
BUSINESS_CODES = {
    "DATA_EMPTY": "数据为空",
    "DATA_INVALID": "数据不合法",
    "ORDER_NOT_FOUND": "订单未找到",
    "DUPLICATE_RECORD": "重复记录",
    "RULE_BLOCKED": "规则阻断",
}

# ── 系统异常分类 ────────────────────────────────────────────
SYSTEM_CATEGORIES = {
    "UI_CHANGED": "页面结构变更",
    "DATA_QUALITY": "数据质量问题",
    "RULE_MISSING": "规则缺失",
    "DEPENDENCY_FAILURE": "依赖故障（可重试）",
    "ENVIRONMENT_ISSUE": "环境问题",
    "LOGIC_DEFECT": "逻辑缺陷",
    "THIRD_PARTY_LIMIT": "第三方限制",
}


class BusinessException(Exception):
    """
    业务规则异常（可接受，跳过继续）。

    新增字段:
      code:             业务编码，如 DATA_INVALID
      retryable:        是否可重试（默认 False）
      suggested_action: 建议动作，如 "跳过并记录"
    """

    def __init__(
        self,
        message: str,
        project: str = "",
        context: Optional[dict] = None,
        code: str = "",
        retryable: bool = False,
        suggested_action: str = "",
    ):
        super().__init__(message)
        self.project = project
        self.context = context or {}
        self.category = "business"
        self.code = code or "DATA_INVALID"
        self.retryable = retryable
        self.suggested_action = suggested_action or "跳过并记录"

    def notify(self) -> dict:
        """返回结构化信息供 entry.py 收集"""
        return {
            "category": "business",
            "message": str(self),
            "project": self.project,
            "context": self.context,
            "code": self.code,
            "retryable": self.retryable,
            "suggested_action": self.suggested_action,
        }


class SystemException(Exception):
    """
    系统级异常（代码 Bug、外部服务故障等）。

    新增字段:
      code:           异常编码，如 LOGIC_DEFECT
      exc_category:   异常分类，如 UI_CHANGED / DEPENDENCY_FAILURE
      retryable:      是否可重试（DEPENDENCY_FAILURE → True）
      need_snapshot:  是否需要写 crash snapshot（默认 True）
      need_issue:     是否需要创建 Linear 工单（默认 True）
      run_context:    运行时上下文（operator/env/source/input_file 等）
    """

    def __init__(
        self,
        message: str,
        project: str = "",
        payload: Optional[dict] = None,
        action: str = "",
        expected: str = "",
        actual: str = "",
        rule_context: str = "",
        intent: str = "",
        screenshot_path: str = "",
        last_interacted_selectors: Optional[list] = None,
        code: str = "",
        exc_category: str = "",
        retryable: bool = False,
        need_snapshot: bool = True,
        need_issue: bool = True,
        run_context: Optional[dict] = None,
    ):
        super().__init__(message)
        self.project = project
        self.traceback_str = traceback.format_exc()
        self.payload = payload or {}
        self.category = "system"
        self.action = action
        self.expected = expected
        self.actual = actual or message
        self.rule_context = rule_context
        self.intent = intent
        self.screenshot_path = screenshot_path
        self.last_interacted_selectors = last_interacted_selectors or []
        # 异常编码体系
        self.code = code or "LOGIC_DEFECT"
        self.exc_category = exc_category or "LOGIC_DEFECT"
        self.retryable = retryable
        self.need_snapshot = need_snapshot
        self.need_issue = need_issue
        self.run_context = run_context or {}
        # 解析 traceback
        parsed = _parse_traceback(self.traceback_str)
        self.error_type = parsed["error_type"]
        self.error_file = _short_path(parsed["file"])
        self.error_function = parsed["function"]
        self.error_line = parsed["line_no"]
        self.error_code = parsed["code_line"]

    def _dump_snapshot(self, run_id: str, repo_path: str = ".") -> str:
        """
        写出 crash snapshot JSON，供 AI 分析。
        R3-7 增强：补充 operator/env/source/input_file/upstream_run_id 等上下文。
        """
        rc = self.run_context
        # screenshot_path 存在性校验
        ss_path = self.screenshot_path
        if ss_path and not os.path.exists(ss_path):
            ss_path = "(file not found: %s)" % ss_path
        # 原始异常信息
        cause_type = ""
        cause_message = ""
        if self.traceback_str and self.traceback_str != "NoneType: None":
            exc_match = re.search(r"(\w+Error|\w+Exception):\s*(.*)", self.traceback_str)
            if exc_match:
                cause_type = exc_match.group(1)
                cause_message = exc_match.group(2).strip()

        snapshot = {
            "snapshot_type": "crash",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "run_id": run_id,
            # ── 运行时上下文（R3-7 增强）──
            "step_name": rc.get("step_name", ""),
            "operator": rc.get("operator", ""),
            "env": rc.get("env", ""),
            "source": rc.get("source", ""),
            "input_file": rc.get("input_file", ""),
            "upstream_run_id": rc.get("upstream_run_id", ""),
            # ── 浏览器上下文 ──
            "page_url": rc.get("page_url", ""),
            "page_title": rc.get("page_title", ""),
            # ── 错误信息 ──
            "error_type": self.error_type,
            "message": str(self),
            "code": self.code,
            "exc_category": self.exc_category,
            "action": self.action,
            "expected": self.expected,
            "actual": self.actual,
            "traceback": self.traceback_str,
            "cause_type": cause_type,
            "cause_message": cause_message,
            "file": self.error_file,
            "function": self.error_function,
            "line": self.error_line,
            "code_line": self.error_code,
            "payload": self.payload,
            "project": self.project,
            "rule_context": self.rule_context,
            "intent": self.intent,
            "screenshot_path": ss_path,
            "last_interacted_selectors": self.last_interacted_selectors,
            "retryable": self.retryable,
        }
        snap_dir = os.path.join(repo_path, "crash_snapshots")
        os.makedirs(snap_dir, exist_ok=True)
        path = os.path.join(snap_dir, "crash_%s.json" % run_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)
        print("[exceptions] Snapshot: %s" % path)
        return path

    def notify(self, extra_payload: Optional[dict] = None, repo_path: str = ".") -> dict:
        """
        创建 Linear 工单 + 写 crash snapshot，返回结构化信息供 entry.py 收集。
        """
        merged = {**self.payload}
        if extra_payload:
            merged.update(extra_payload)
        run_id = extra_payload.get("run_id", "unknown") if extra_payload else "unknown"

        # 1. 写 crash snapshot（可关闭）
        snapshot_path = ""
        if self.need_snapshot:
            snapshot_path = self._dump_snapshot(run_id=run_id, repo_path=repo_path)

        # 2. AI 根因分析（可选，优雅降级）
        ai_result = None
        try:
            from core.ai_analyzer import analyze_crash
            snapshot_data = {
                "error_type": self.error_type, "message": str(self),
                "action": self.action, "expected": self.expected, "actual": self.actual,
                "traceback": self.traceback_str,
                "file": self.error_file, "function": self.error_function,
                "line": self.error_line, "code_line": self.error_code,
                "payload": merged, "project": self.project,
                "rule_context": self.rule_context, "intent": self.intent,
                "screenshot_path": self.screenshot_path,
                "last_interacted_selectors": self.last_interacted_selectors,
                "code": self.code, "exc_category": self.exc_category,
                "retryable": self.retryable,
                "cause_type": self.error_type,
                # 运行时上下文
                "operator": self.run_context.get("operator", ""),
                "env": self.run_context.get("env", ""),
                "source": self.run_context.get("source", ""),
                "step_name": self.run_context.get("step_name", ""),
                "input_file": self.run_context.get("input_file", ""),
                "upstream_run_id": self.run_context.get("upstream_run_id", ""),
                # 浏览器上下文
                "page_url": self.run_context.get("page_url", ""),
                "page_title": self.run_context.get("page_title", ""),
            }
            ai_result = analyze_crash(snapshot_data)
        except ImportError:
            print("[exceptions] ai_analyzer module not available, skipping AI analysis")
        except Exception as e:
            print("[exceptions] AI analysis error (non-blocking): %s" % e)

        # 3. 创建 Linear 工单（可关闭，如测试分支）
        issue_result = {"success": False, "issue_url": ""}
        if self.need_issue:
            issue_result = create_linear_issue(
                error_msg=str(self), trace=self.traceback_str,
                payload_data=merged if merged else {}, project=self.project,
                repo_path=repo_path,
                error_type=self.error_type, error_file=self.error_file,
                error_function=self.error_function, error_line=self.error_line,
                error_code=self.error_code, action=self.action,
                expected=self.expected, actual=self.actual,
                ai_analysis=ai_result,
            )

        if isinstance(issue_result, dict):
            return {
                "category": "system", "message": str(self), "project": self.project,
                "error_type": self.error_type, "error_file": self.error_file,
                "code": self.code, "exc_category": self.exc_category,
                "retryable": self.retryable,
                "issue_success": issue_result.get("success", False),
                "issue_url": issue_result.get("issue_url", ""),
                "ai_analysis": ai_result,
                "crash_snapshot_path": snapshot_path,
            }
        return {
            "category": "system", "message": str(self), "project": self.project,
            "error_type": self.error_type, "error_file": self.error_file,
            "code": self.code, "exc_category": self.exc_category,
            "retryable": self.retryable,
            "issue_success": bool(issue_result), "issue_url": "",
            "ai_analysis": ai_result,
            "crash_snapshot_path": snapshot_path,
        }
