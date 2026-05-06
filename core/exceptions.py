"""
core/exceptions.py — 异常路由分流器
====================================
层级:
    BusinessException → L1 飞书通知（业务规则异常，静默处理）
    SystemException   → L2 飞书告警（代码级 Bug，强制退出）
"""

from typing import Any, Optional
from core.notifier import send_business_alert, send_system_alert


class BusinessException(Exception):
    """业务规则异常 — L1 飞书通知，流程继续

    触发场景:
        - 账号不符合要求
        - 数据校验不通过
        - 业务逻辑前置条件不满足
    """

    def __init__(self, message: str, project: str = "未命名项目",
                 context: Optional[dict] = None):
        super().__init__(message)
        self.project = project
        self.context = context or {}
        self.category = "business"

    def notify(self) -> bool:
        """发送 L1 飞书业务通知"""
        return send_business_alert(
            project=self.project,
            message=str(self),
            context=self.context,
        )


class SystemException(Exception):
    """系统 Bug 异常 — L2 飞书告警，强制退出流程

    触发场景:
        - 网页结构变更导致 KeyError
        - DOM 元素找不到
        - 接口响应格式异常
    """

    def __init__(self, message: str, project: str = "未命名项目",
                 payload: Optional[dict] = None):
        super().__init__(message)
        self.project = project
        # 自动捕获当前堆栈
        import traceback
        self.traceback_str = traceback.format_exc()
        self.payload = payload or {}
        self.category = "system"

    def notify(self, extra_payload: Optional[dict] = None) -> bool:
        """发送 L2 飞书系统告警"""
        merged_payload = {**self.payload}
        if extra_payload:
            merged_payload.update(extra_payload)

        return send_system_alert(
            project=self.project,
            message=str(self),
            traceback_str=self.traceback_str,
            payload=merged_payload if merged_payload else None,
        )
