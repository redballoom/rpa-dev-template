"""
runner.py — 影刀 CLI 入口 (BAT 模式)
======================================
影刀通过 BAT 调用此脚本，输出 JSON 状态文件供影刀读取。

BAT 示例:
    python runner.py --run_id 20260506_001 --repo_path D:/RPA_Project
    python runner.py --run_id 20260506_001 --repo_path D:/RPA_Project --project 物流项目

影刀内的 4 步编排:
    1. 生成 run_id
    2. 调用 BAT: python runner.py --run_id %run_id% --repo_path D:/RPA_Project
    3. 读取 runner_%run_id%.json
    4. IF 判断 status -> success | warning | failed
"""

import sys
import os
import json
import argparse
import traceback

# Windows GBK 兼容
try:
    if hasattr(sys.stdout, 'encoding') and sys.stdout.encoding and sys.stdout.encoding.upper() == "GBK":
        import io
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except AttributeError:
    pass


def _load_project_config(repo_path: str) -> dict:
    """
    合并读取配置（template 为基准，project.json 覆盖）:
      1. project.template.json  — 追踪版本控制，含 is_test_to_git_env
      2. project.json           — gitignored，含 API Key 等敏感信息
    """
    config = {}

    # 基准配置（模板，版本控制追踪）
    template_path = os.path.join(repo_path, "project.template.json")
    if os.path.exists(template_path):
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                config.update(json.load(f))
        except Exception as e:
            print(f"[runner] 警告: 读取 project.template.json 失败: {e}")

    # 覆盖配置（用户本地，含密钥，gitignored）
    override_path = os.path.join(repo_path, "project.json")
    if os.path.exists(override_path):
        try:
            with open(override_path, "r", encoding="utf-8") as f:
                config.update(json.load(f))
        except Exception as e:
            print(f"[runner] 警告: 读取 project.json 失败: {e}")

    return config


def _switch_git_env(repo_path: str, config: dict) -> None:
    """根据 project.json 的 is_test_to_git_env 切换 Git 分支"""
    is_test = config.get("is_test_to_git_env", False)
    target_branch = "fix/bug-test" if is_test else "main"

    try:
        import git_controller
        import importlib
        importlib.reload(git_controller)

        result = git_controller.switch_git_env(
            is_test=is_test,
            repo_path=repo_path,
        )
        if result.get("status") == "error":
            print(f"[runner] Git 切换警告 ({target_branch}): {result.get('msg')}")
        else:
            print(f"[runner] Git 分支已确认: {target_branch}")
    except Exception as e:
        print(f"[runner] Git 切换失败 (非阻断): {e}")


def execute(run_id: str, repo_path: str, project: str = "开发模板",
            tasks: list = None, output_dir: str = None) -> str:
    """
    影刀调用的唯一入口 (CLI)

    Returns:
        status.json 的绝对路径（影刀读取此文件判断结果）
    """
    # 1. 确保工作区在 sys.path
    if repo_path in sys.path:
        sys.path.remove(repo_path)
    sys.path.insert(0, repo_path)

    if output_dir is None:
        output_dir = repo_path
    os.makedirs(output_dir, exist_ok=True)
    status_file = os.path.join(output_dir, f"runner_{run_id}.json")

    try:
        # 2. 读取 project.json 配置
        config = _load_project_config(repo_path)
        project_name = project or config.get("project", "开发模板")

        # 3. 根据 is_test_to_git_env 切换 Git 分支
        _switch_git_env(repo_path, config)

        # 4. 导入业务入口，热重载
        import core.entry as entry_module
        import importlib
        importlib.reload(entry_module)

        # 5. 执行业务逻辑
        result_dict = entry_module.run_tasks(
            run_id=run_id,
            project=project_name,
            tasks=tasks,
            repo_path=repo_path,
        )

    except Exception as e:
        result_dict = {
            "status": "fatal",
            "message": f"Runner 崩溃: {e}",
            "data": {"run_id": run_id, "traceback": traceback.format_exc()}
        }

    # 4. 状态落盘 (JSON 握手文件)
    with open(status_file, "w", encoding="utf-8") as f:
        json.dump(result_dict, f, ensure_ascii=False, indent=2)

    print(f"[runner] 状态已写入: {status_file}")
    return status_file


# ========== CLI 入口 ==========
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="影刀 RPA -> Python 业务调度器")
    parser.add_argument("--run_id", type=str, required=True, help="本次运行 Trace ID")
    parser.add_argument("--repo_path", type=str, required=True, help="项目本地路径")
    parser.add_argument("--project", type=str, default="开发模板", help="项目名称")
    parser.add_argument("--output_dir", type=str, default="", help="结果输出目录（默认 repo_path）")

    args = parser.parse_args()

    # 示例任务（实际项目中可由影刀动态生成 JSON 文件传入）
    sample_tasks = [
        {"id": 1, "name": "正常任务"},
        {"id": 2, "name": "正常任务B"},
        # 取消注释下一行测试业务异常
        # {"id": -1, "name": "无效ID"},
        # 取消注释下一行测试系统异常
        # {"id": 0, "name": "触发崩溃"},
    ]

    status_path = execute(
        run_id=args.run_id,
        repo_path=args.repo_path,
        project=args.project,
        tasks=sample_tasks,
        output_dir=args.output_dir or args.repo_path,
    )

    # 标准输出也打印一份 JSON，影刀可捕获 stdout
    with open(status_path, "r", encoding="utf-8") as f:
        print(f.read())
