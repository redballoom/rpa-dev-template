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
