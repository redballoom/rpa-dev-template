"""
git_controller.py — Git 动态路由调度器
=========================================
职能: 影刀专用，运行时动态切换 Git 分支，实现环境隔离。
位置: 项目根目录，保持稳定，不与业务代码频繁变动。

使用方式 (影刀内):
    1. 设置变量 is_test = True / False
    2. 调用 Python 模块 → git_controller.py → switch_git_env
    3. 传入参数: is_test, repo_path
    4. 判断返回值 status 是否为 "error"，是则飞书告警 + 停止流程
"""

import subprocess
import traceback
import os


def switch_git_env(is_test: bool, repo_path: str) -> dict:
    """
    影刀专用的 Git 环境路由调度器

    Args:
        is_test: True → 切换到测试分支 fix/bug-test
                 False → 切换到 main 并拉取最新
        repo_path: 本地仓库的绝对路径 (如 D:/RPA_Core_Logic)

    Returns:
        {"status": "success|error", "current_branch": "...", "msg": "..."}
    """
    # 约定：测试环境使用测试分支，生产环境强制锁定 main
    target_branch = "fix/bug-test" if is_test else "main"

    if not os.path.exists(os.path.join(repo_path, ".git")):
        return {
            "status": "error",
            "msg": f"致命错误: {repo_path} 不是一个有效的 Git 仓库！"
        }

    try:
        print(f"🔄 [系统调度] 准备将工作区切换至分支: {target_branch}")

        # 1. 强制清理：丢弃本地任何未提交的脏数据（防止 Checkout 卡死）
        subprocess.run(
            ["git", "-C", repo_path, "stash", "--include-untracked"],
            capture_output=True
        )

        # 2. 切到目标分支（如果分支不存在则创建）
        checkout_res = subprocess.run(
            ["git", "-C", repo_path, "checkout", target_branch],
            capture_output=True, text=True
        )
        if checkout_res.returncode != 0:
            # 分支不存在，从 main 创建
            subprocess.run(
                ["git", "-C", repo_path, "checkout", "-b", target_branch],
                check=True, capture_output=True, text=True
            )
            print(f"🆕 [系统调度] 分支 {target_branch} 不存在，已从 HEAD 创建")
        else:
            print(f"✅ [系统调度] 成功切换至 {target_branch}")

        # 3. 生产环境保鲜：main 分支强制拉取远端最新稳定版
        if not is_test:
            subprocess.run(
                ["git", "-C", repo_path, "pull", "origin", "main"],
                capture_output=True
            )

        return {
            "status": "success",
            "current_branch": target_branch,
            "msg": checkout_res.stdout
        }

    except subprocess.CalledProcessError as e:
        return {"status": "error", "msg": f"Git 底层命令失败: {e.stderr}"}
    except Exception as e:
        return {"status": "error", "msg": traceback.format_exc()}


# ── 单元测试 ──
if __name__ == "__main__":
    # 测试场景：切到测试分支
    result = switch_git_env(
        is_test=True,
        repo_path=os.path.dirname(os.path.abspath(__file__))
    )
    print(f"Result: {result}")
