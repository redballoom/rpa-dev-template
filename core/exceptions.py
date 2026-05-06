"""core/exceptions.py — 异常路由分流器

层级:
    BusinessException   → L1 飞书通知（业务规则异常）
    SystemException     → L2 Linear 工单（代码级 Bug）
"""

from typing import Any, Optional


class BusinessException(Exception):
    """业务规则异常 — 由飞书 L1 监控处理

    触发场景:
        - 账号不符合要求
        - 数据校验不通过
        - 业务逻辑前置条件不满足
    """

    def __init__(self, message: str, context: Optional[dict] = None):
        super().__init__(message)
        self.context = context or {}
        self.category = "business"

    def to_payload(self) -> dict:
        """转成飞书通知的标准载荷"""
        return {
            "type": "business_exception",
            "message": str(self),
            "context": self.context,
        }


class SystemException(Exception):
    """系统 Bug 异常 — 由 Linear L2 工单处理

    触发场景:
        - 网页结构变更导致 KeyError
        - DOM 元素找不到
        - 接口响应格式异常
    """

    def __init__(self, message: str, traceback_str: str = "",
                 payload: Optional[dict] = None):
        super().__init__(message)
        self.traceback = traceback_str
        self.payload = payload or {}
        self.category = "system"

    def to_payload(self) -> dict:
        """转成 Linear 工单的标准载荷"""
        return {
            "type": "system_bug",
            "message": str(self),
            "traceback": self.traceback,
            "payload": self.payload,
        }
