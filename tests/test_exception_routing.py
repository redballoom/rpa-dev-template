"""
tests/test_exception_routing.py - 异常路由全链路测试
=====================================================
测试场景:
  1. 正常任务 -> success
  2. 业务异常 (BusinessException) -> L1 飞书通知, warning
  3. 系统异常 (SystemException)   -> L2 飞书告警, failed
"""

import sys
import os

# 把项目根目录加入 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.entry import run_tasks


def test_normal():
    print("=" * 60)
    print("[测试 1] 正常任务")
    result = run_tasks(
        run_id="test-001",
        project="开发模板测试",
        tasks=[{"id": 1, "name": "正常任务A"}, {"id": 2, "name": "正常任务B"}]
    )
    print(f"  status: {result['status']}")
    print(f"  message: {result['message']}")
    assert result["status"] == "success"
    print("  [PASS]\n")


def test_business_exception():
    print("=" * 60)
    print("[测试 2] 业务异常 (L1 飞书通知)")
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
    # 业务异常不应终止流程，整体状态应为 warning
    assert result["status"] == "warning"
    print("  [PASS]\n")


def test_system_exception():
    print("=" * 60)
    print("[测试 3] 系统异常 (L2 飞书告警 + 强制退出)")
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
    # 系统异常应终止流程，后续任务不执行
    assert result["status"] == "failed"
    data = result.get("data", {})
    results = data.get("results", [])
    print(f"  执行了 {len(results)} 个任务 (预期只有第1个)")
    assert len(results) == 1
    print("  [PASS]\n")


if __name__ == "__main__":
    test_normal()
    test_business_exception()
    test_system_exception()
    print("=" * 60)
    print("全部测试通过!")
