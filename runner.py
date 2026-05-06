"""
runner.py — 业务热重载调度器
================================
职能: 影刀通过此模块调用业务代码，利用 importlib.reload 解决
      Python 内存缓存旧代码的问题（Git 分支切换后生效）。

使用方式 (影刀内):
    1. git_controller 成功切换分支后
    2. 调用 Python 模块 → runner.py → execute_core_logic
    3. 传入参数: repo_path, run_id, task_data
"""

import sys
import importlib
import os


def execute_core_logic(repo_path: str, run_id: str, **kwargs) -> dict:
    """
    热重载最新代码并执行核心业务

    Args:
        repo_path: 项目仓库的本地绝对路径
        run_id:    本次运行的唯一 ID（用于 Trace ID 校验）
        **kwargs:  传递给业务入口的额外参数

    Returns:
        {"status": "success|failed", "message": "...", "data": {...}}
    """
    # 确保仓库路径在系统环境变量中
    if repo_path not in sys.path:
        sys.path.append(repo_path)

    # 强制移除已缓存的核心模块，确保从硬盘重新加载
    for mod_name in list(sys.modules.keys()):
        if mod_name.startswith("core."):
            del sys.modules[mod_name]

    # 导入业务入口模块
    import core.entry

    # 💥 极度关键：强制 Python 丢弃内存旧版本
    #    读取刚刚被 Git 切换过来的硬盘新文件
    importlib.reload(core.entry)

    # 将控制权移交给业务代码，传入 run_id 做 Trace ID
    return core.entry.run_tasks(run_id=run_id, **kwargs)
