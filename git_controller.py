"""
git_controller.py -- Git 动态路由调度器
=========================================
职能: 影刀专用，运行时动态切换 Git 分支，实现环境隔离。

增强功能:
  - 首次运行自动 git clone（无本地仓库时）
  - 日常运行切换分支 + 拉取最新
  - 支持多机部署（新机器自动拉取）
"""

import subprocess, traceback, os, sys

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
            track_res = subprocess.run(["git", "-C", repo_path, "checkout", "-b", target_branch, f"origin/{target_branch}"], capture_output=True, text=True)
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


if __name__ == "__main__":
    result = switch_git_env(is_test=True, repo_path=os.path.dirname(os.path.abspath(__file__)))
    print(f"Result: {result}")
    subprocess.run(["git", "-C", os.path.dirname(os.path.abspath(__file__)), "checkout", "main"], capture_output=True)
