"""
core/exceptions.py — 异常路由分流器
====================================
L1: BusinessException -> 飞书黄牌，跳过继续
L2: SystemException   -> Linear 工单，强制退出
"""

import traceback
from typing import Optional
from core.notifier import send_business_alert, create_linear_issue


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

    def notify(self) -> bool:
        """触发飞书 L1 黄牌通知"""
        return send_business_alert(
            project=self.project,
            message=str(self),
            context=self.context,
        )


class SystemException(Exception):
    """系统 Bug 异常（需强制退出）"""

    def __init__(
        self,
        message: str,
        project: str = "未命名项目",
        payload: Optional[dict] = None,
    ):
        super().__init__(message)
        self.project = project
        self.traceback_str = traceback.format_exc()
        self.payload = payload or {}
        self.category = "system"

    def notify(self, extra_payload: Optional[dict] = None, repo_path: str = ".") -> bool:
        """
        触发 Linear 工单创建（不再走飞书红牌）。

        Args:
            extra_payload: 额外的上下文数据，会合并进 payload 一并写入工单描述
            repo_path:    仓库路径，用于判断当前分支是否为生产环境
        """
        merged = {**self.payload}
        if extra_payload:
            merged.update(extra_payload)

        return create_linear_issue(
            error_msg=str(self),
            trace=self.traceback_str,
            payload_data=merged if merged else {},
            project=self.project,
            repo_path=repo_path,
        )
