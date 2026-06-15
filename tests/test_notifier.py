"""
tests/test_notifier.py — 通知模块测试
===================================
覆盖：
  - 飞书 webhook 为空时不发无效请求
  - 生产分支判断可由配置列表控制
  - 飞书错误卡片透出 AI 摘要
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import notifier


def test_feishu_post_skips_empty_webhook(monkeypatch):
    """未配置飞书 webhook 时应静默跳过，不请求空 URL"""
    called = []

    def fake_post(*args, **kwargs):
        called.append((args, kwargs))
        raise AssertionError("requests.post should not be called")

    monkeypatch.setattr(notifier, "FEISHU_WEBHOOK", "")
    monkeypatch.setattr(notifier.requests, "post", fake_post)

    assert notifier._feishu_post({"msg_type": "text"}) is True
    assert called == []


def test_production_branch_uses_configured_branch_list(monkeypatch):
    """生产分支名应来自配置，而不是只认 main"""
    monkeypatch.setattr(notifier, "PRODUCTION_BRANCHES", ["main", "release"])
    monkeypatch.setattr(notifier, "_get_current_branch", lambda repo_path=".": "release")

    assert notifier._is_production_env(".") is True


def test_execution_summary_includes_ai_summary(monkeypatch):
    """飞书异常卡片应展示 AI 摘要，方便人工快速判断"""
    posted = []

    def fake_post(data):
        posted.append(data)
        return True

    monkeypatch.setattr(notifier, "_feishu_post", fake_post)

    assert notifier.send_execution_summary(
        project="测试项目",
        run_id="ai-summary-001",
        total=1,
        success_count=0,
        warnings=[],
        errors=[{
            "task": {"name": "触发崩溃"},
            "message": "原始错误",
            "exc_category": "DATA_QUALITY",
            "code": "DATA_INVALID",
            "ai_summary": "AI 判断为输入文件缺失",
            "confidence": 0.9,
        }],
    ) is True

    card_text = "\n".join(
        element.get("content", "")
        for element in posted[0]["card"]["elements"]
    )
    assert "AI 判断为输入文件缺失" in card_text
