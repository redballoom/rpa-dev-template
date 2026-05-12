"""
tests/test_config.py — 配置模块测试
=================================
覆盖：
  - 配置加载与合并
  - validate_config() 校验逻辑
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_config_loaded():
    """配置至少能加载（不抛异常）"""
    from core import config
    # 默认模板有 project 字段
    assert hasattr(config, "PROJECT")
    assert hasattr(config, "AI_ENABLED")
    assert hasattr(config, "AI_API_KEY")


def test_validate_config_default():
    """默认模板配置校验：PROJECT 有默认值所以不 fatal"""
    from core.config import validate_config
    result = validate_config()
    # 默认 project.template.json 有 project="开发模板"
    assert result["fatal"] == False
    assert "valid" in result
    assert "missing" in result
    assert "warnings" in result
    assert "message" in result


def test_validate_config_fields():
    """validate_config 返回结构完整性"""
    from core.config import validate_config
    result = validate_config()
    assert isinstance(result["valid"], bool)
    assert isinstance(result["fatal"], bool)
    assert isinstance(result["missing"], list)
    assert isinstance(result["warnings"], list)
    assert isinstance(result["message"], str)


def test_validate_config_missing_field():
    """模拟缺失必须字段 → fatal=True"""
    import core.config as cfg
    original = cfg.PROJECT
    try:
        cfg.PROJECT = ""
        result = cfg.validate_config()
        assert result["fatal"] == True
        assert len(result["missing"]) > 0
        assert "project" in result["message"].lower() or "项目名称" in result["message"]
    finally:
        cfg.PROJECT = original


def test_validate_config_ai_warning():
    """AI 启用但缺 API Key → 产生警告"""
    import core.config as cfg
    original_enabled = cfg.AI_ENABLED
    original_key = cfg.AI_API_KEY
    try:
        cfg.AI_ENABLED = True
        cfg.AI_API_KEY = ""
        result = cfg.validate_config()
        assert any("API Key" in w for w in result["warnings"])
    finally:
        cfg.AI_ENABLED = original_enabled
        cfg.AI_API_KEY = original_key
