"""
commands/ — RPA 业务命令模块
============================
本目录存放可被影刀 RPA 调用的独立业务命令。
每个 .py 文件对应一个原子动作，暴露为纯函数，供 entry.py 路由分发。

目录结构（规划中）:
    commands/
        __init__.py        ← 本文件（模块入口）
        search.py          # 搜索指令
        submit.py          # 提交流程指令
        notify.py          # 通知指令
        ...

使用方式（影刀 Python 模块）:
    from commands import search
    result = search.run(keyword="SKU-998")
"""

# 命令路由表（按需扩展）
COMMAND_REGISTRY = {}

def register(name: str, func: callable):
    """注册命令，供 entry.py 动态调用"""
    COMMAND_REGISTRY[name] = func
