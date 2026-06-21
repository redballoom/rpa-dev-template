"""
tests/test_notifier.py — 通知环境判断测试
========================================
覆盖：
  - context.env 优先于 Git 分支判断生产/测试环境
  - env 缺失时仍保留 Git 分支兜底
"""
import sys
import os
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core.notifier as notifier
from core.notifier import _is_production_env


def test_is_production_env_prefers_context_prod():
    """context.env=prod 时，即使 Git 分支未知也按生产处理"""
    with patch("core.notifier._get_current_branch", return_value="unknown"):
        assert _is_production_env(".", {"env": "prod"}) is True


def test_is_production_env_prefers_context_test():
    """context.env=test 时，即使在 main 分支也按测试处理"""
    with patch("core.notifier._get_current_branch", return_value="main"):
        assert _is_production_env(".", {"env": "test"}) is False


def test_is_production_env_falls_back_to_branch():
    """context.env 缺失时使用 Git 分支兜底"""
    with patch("core.notifier._get_current_branch", return_value="main"):
        assert _is_production_env(".", {}) is True
    with patch("core.notifier._get_current_branch", return_value="feature/demo"):
        assert _is_production_env(".", {}) is False


def test_feishu_post_skips_when_webhook_missing():
    """飞书 webhook 未配置时应明确跳过，不发起网络请求"""
    original = notifier.FEISHU_WEBHOOK
    try:
        notifier.FEISHU_WEBHOOK = ""
        with patch("core.notifier.requests.post") as mock_post:
            assert notifier._feishu_post({"msg_type": "text"}) is True
            mock_post.assert_not_called()
    finally:
        notifier.FEISHU_WEBHOOK = original


def test_linear_issue_skips_when_config_missing_in_prod():
    """生产环境但 Linear 关键配置缺失时明确跳过，避免空配置网络请求"""
    original_key = notifier.LINEAR_API_KEY
    original_team = notifier.LINEAR_TEAM_ID
    try:
        notifier.LINEAR_API_KEY = ""
        notifier.LINEAR_TEAM_ID = ""
        with patch("core.notifier.requests.post") as mock_post:
            result = notifier.create_linear_issue(
                error_msg="boom",
                trace="",
                payload_data={},
                repo_path=".",
                run_context={"env": "prod"},
            )
            assert result == {"success": False, "issue_url": ""}
            mock_post.assert_not_called()
    finally:
        notifier.LINEAR_API_KEY = original_key
        notifier.LINEAR_TEAM_ID = original_team
