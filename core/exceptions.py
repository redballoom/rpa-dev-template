"""
core/exceptions.py — 异常路由分流器
====================================
L1: BusinessException -> 飞书黄牌，跳过继续
L2: SystemException   -> 飞书红牌，强制退出
"""

import traceback
from typing import Optional
from core.notifier import send_business_alert, send_system_alert


class BusinessException(Exception):
    """业务规则异常（可接受，跳过继续）"""

    def __init__(self, message: str, project: str = "未命名项目",
                 context: Optional[dict] = None):
        super().__init__(message)
        self.project = project
        self.context = context or {}
        self.category = "business"

    def notify(self) -> bool:
        return send_business_alert(
            project=self.project,
            message=str(self),
            context=self.context,
        )


class SystemException(Exception):
    """系统 Bug 异常（需强制退出）"""

    def __init__(self, message: str, project: str = "未命名项目",
                 payload: Optional[dict] = None):
        super().__init__(message)
        self.project = project
        self.traceback_str = traceback.format_exc()
        self.payload = payload or {}
        self.category = "system"

    def notify(self, extra_payload: Optional[dict] = None) -> bool:
        merged = {**self.payload}
        if extra_payload:
            merged.update(extra_payload)
        return send_system_alert(
            project=self.project,
            message=str(self),
            traceback_str=self.traceback_str,
            payload=merged if merged else None,
        )
