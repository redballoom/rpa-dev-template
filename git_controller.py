"""
git_controller.py — Git 部署辅助工具 (CLI 模式)
=================================================
职能: 部署期环境准备工具，不在任务执行链路中自动调用。

用途：
  1. 首次部署：git clone 项目仓库
  2. 切换分支：main（生产）/ fix/bug-test（测试）
  3. 影刀启动前手动调用（非运行时自动触发）

调用方式 (影刀内 BAT / 手动):
    python git_controller.py --is_test True --repo_path D:/RPA_Project
    python git_controller.py --is_test False --repo_path D:/RPA_Project --git_url git@github.com:user/repo.git

注意：任务执行时（runner.py）不会自动调用此模块。
"""

import subprocess
import traceback
import os
import sys
import argparse
import json

# Windows GBK 编码兼容
try:
    if hasattr(sys.stdout, 'encoding') and sys.stdout.encoding and sys.stdout.encoding.upper() == "GBK":
        import io
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except AttributeError:
    pass


def switch_git_env(is_test: bool, repo_path: str, git_url: str = "") -> dict:
    """
    影刀专用 Git 环境路由调度器 (带自动初始化)

    Args:
        is_test: True -> fix/bug-test, False -> main
        repo_path: 本地仓库绝对路径
        git_url: 远程仓库 URL，首次部署时用于 git clone

    Returns:
        {"status": "success|error", "current_branch": "...", "msg": "..."}
    """
    target_branch = "fix/bug-test" if is_test else "main"
    repo_dir_exists = os.path.isdir(repo_path)
    git_dir_exists = os.path.isdir(os.path.join(repo_path, ".git"))

    # -- 情况 A: 仓库不存在 -> git clone
    if not repo_dir_exists:
        if not git_url:
            return {"status": "error", "msg": "仓库不存在且未提供 git_url"}
        print("[系统调度] 首次部署: git clone")
        try:
            os.makedirs(os.path.dirname(repo_path), exist_ok=True)
            subprocess.run(["git", "clone", git_url, repo_path], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            return {"status": "error", "msg": f"git clone 失败: {e.stderr}"}

    # -- 情况 B: 目录存在但 .git 丢失
    elif not git_dir_exists:
        if os.listdir(repo_path):
            return {"status": "error", "msg": "目录存在但 .git 丢失，且非空目录"}
        if not git_url:
            return {"status": "error", "msg": "空目录需要 git_url"}
        try:
            subprocess.run(["git", "clone", git_url, repo_path], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            return {"status": "error", "msg": f"git clone 失败: {e.stderr}"}

    # -- 情况 C: 仓库已存在 -> 常规切换
    try:
        print(f"[系统调度] 准备切换至分支: {target_branch}")
        subprocess.run(["git", "-C", repo_path, "stash", "--include-untracked"], capture_output=True)
        subprocess.run(["git", "-C", repo_path, "fetch", "--all", "--prune"], capture_output=True)

        checkout_res = subprocess.run(["git", "-C", repo_path, "checkout", target_branch], capture_output=True, text=True)
        if checkout_res.returncode != 0:
            track_res = subprocess.run(
                ["git", "-C", repo_path, "checkout", "-b", target_branch, f"origin/{target_branch}"],
                capture_output=True, text=True
            )
            if track_res.returncode != 0:
                subprocess.run(["git", "-C", repo_path, "checkout", "-b", target_branch], check=True, capture_output=True, text=True)
                print(f"[系统调度] 分支 {target_branch} 从本地 HEAD 创建")
            else:
                print(f"[系统调度] 从 origin/{target_branch} 跟踪创建")
        else:
            print(f"[系统调度] 成功切换至 {target_branch}")

        subprocess.run(["git", "-C", repo_path, "pull", "origin", target_branch], capture_output=True)
        return {"status": "success", "current_branch": target_branch, "msg": checkout_res.stdout}
    except subprocess.CalledProcessError as e:
        return {"status": "error", "msg": f"Git 失败: {e.stderr}"}
    except Exception as e:
        return {"status": "error", "msg": traceback.format_exc()}


# ========== CLI 入口 ==========
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="影刀 Git 环境路由调度器")
    parser.add_argument("--is_test", type=lambda x: x.lower() == "true", required=True,
                        help="True=fix/bug-test, False=main")
    parser.add_argument("--repo_path", type=str, required=True,
                        help="本地仓库绝对路径")
    parser.add_argument("--git_url", type=str, default="",
                        help="远程仓库 URL（首次部署必需）")
    parser.add_argument("--output", type=str, default="",
                        help="结果输出到 JSON 文件（可选）")

    args = parser.parse_args()

    result = switch_git_env(
        is_test=args.is_test,
        repo_path=args.repo_path,
        git_url=args.git_url
    )

    # 输出 JSON
    output = json.dumps(result, ensure_ascii=False, indent=2)
    print(output)

    # 可选: 写入文件供影刀直接读
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
