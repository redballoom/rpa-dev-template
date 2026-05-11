"""
tests/test_exception_routing.py - 异常路由全链路测试
=====================================================
测试场景:
  1. 正常任务            -> success（静默，不发飞书）
  2. 业务异常            -> warning（跳过继续，飞书汇总1条）
  3. 系统异常            -> failed（中断后续，飞书汇总1条 + Linear 工单）
  4. 混合场景            -> 多种异常共存，飞书汇总1条
"""

import sys
import os

# 把项目根目录加入 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.entry import run_tasks


def test_normal():
    """全部成功 → status=success，不发飞书"""
    print("=" * 60)
    print("[测试 1] 正常任务（全部成功，静默无通知）")
    result = run_tasks(
        run_id="test-001",
        project="开发模板测试",
        tasks=[{"id": 1, "name": "正常任务A"}, {"id": 2, "name": "正常任务B"}]
    )
    print(f"  status: {result['status']}")
    print(f"  message: {result['message']}")
    assert result["status"] == "success"
    # 成功时 data 里没有 errors 字段
    assert result["data"].get("warnings", []) == []
    assert result["data"].get("errors", []) == []
    print("  [PASS]\n")


def test_business_exception():
    """业务异常 → warning，跳过继续，后续任务仍执行"""
    print("=" * 60)
    print("[测试 2] 业务异常（跳过继续，飞书汇总1条黄色卡片）")
    result = run_tasks(
        run_id="test-002",
        project="开发模板测试",
        tasks=[
            {"id": 1, "name": "正常任务"},
            {"id": -1, "name": "无效ID任务"},   # 触发 BusinessException
            {"id": 3, "name": "正常任务C"}
        ]
    )
    print(f"  status: {result['status']}")
    print(f"  message: {result['message']}")
    # 业务异常不终止流程，3个任务都执行了
    assert result["status"] == "warning"
    results = result["data"]["results"]
    assert len(results) == 3
    assert results[1]["status"] == "skipped"
    # 有1条警告
    warnings = result["data"]["warnings"]
    assert len(warnings) == 1
    assert "Invalid ID" in warnings[0]["message"]
    print("  [PASS]\n")


def test_system_exception():
    """系统异常 → failed，中断后续任务，创建 Linear 工单"""
    print("=" * 60)
    print("[测试 3] 系统异常（中断 + AI 分析 + Linear 工单 + 飞书红色卡片）")
    result = run_tasks(
        run_id="test-003",
        project="开发模板测试",
        tasks=[
            {"id": 1, "name": "正常任务"},
            {"id": 0, "name": "触发崩溃"},     # 触发 SystemException
            {"id": 3, "name": "不会被执行"}
        ]
    )
    print(f"  status: {result['status']}")
    print(f"  message: {result['message']}")
    assert result["status"] == "pending_fix"
    data = result.get("data", {})
    results = data.get("results", [])
    # SystemException 中断，只执行了第1个（正常）+ 第2个（异常）
    assert len(results) == 2
    assert results[0]["status"] == "ok"
    assert results[1]["status"] == "error"
    # 有1条系统异常
    errors = data.get("errors", [])
    assert len(errors) == 1
    print("  [PASS]\n")


def test_mixed():
    """混合场景：业务异常 + 系统异常"""
    print("=" * 60)
    print("[测试 4] 混合场景（业务跳过 + 系统中断 + AI 分析）")
    result = run_tasks(
        run_id="test-004",
        project="开发模板测试",
        tasks=[
            {"id": 1, "name": "正常任务"},
            {"id": -1, "name": "无效ID"},       # BusinessException
            {"id": 0, "name": "触发崩溃"},       # SystemException → 中断
            {"id": 3, "name": "不会被执行"}
        ]
    )
    print(f"  status: {result['status']}")
    print(f"  message: {result['message']}")
    assert result["status"] == "pending_fix"
    data = result["data"]
    # 执行了3个：正常 + 跳过 + 异常
    results = data["results"]
    assert len(results) == 3
    assert results[0]["status"] == "ok"
    assert results[1]["status"] == "skipped"
    assert results[2]["status"] == "error"
    # 1条警告 + 1条异常
    assert len(data["warnings"]) == 1
    assert len(data["errors"]) == 1
    print("  [PASS]\n")


if __name__ == "__main__":
    test_normal()
    test_business_exception()
    test_system_exception()
    test_mixed()
    print("=" * 60)
    print("全部测试通过!")
