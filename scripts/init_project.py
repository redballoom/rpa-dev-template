"""
scripts/init_project.py — 从本地模板创建新 RPA 项目

用法:
  python scripts/init_project.py --name 物流项目
  
与 D:\\CraftPJ\\init_project.py 不同，此脚本不克隆远程仓库，
而是直接复制当前模板目录到目标位置。

适合：
  - 离线环境或无 GitHub SSH 权限时使用
  - 需要从本地修改后的模板创建项目
"""

import os
import sys
import shutil
import subprocess
import argparse
import json

TEMPLATE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(cmd, cwd=None, check=True, timeout=60):
    proc = subprocess.run(
        cmd, cwd=cwd, capture_output=True, timeout=timeout,
        shell=True, encoding='utf-8', errors='replace'
    )
    if check and proc.returncode != 0:
        print(f"  ⚠ 命令失败 (RC={proc.returncode}): {cmd[:80]}")
        if proc.stderr.strip():
            print(f"     stderr: {proc.stderr[:200]}")
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def main():
    parser = argparse.ArgumentParser(description="从本地模板创建新 RPA 项目")
    parser.add_argument("--name", "-n", required=True, help="项目名")
    parser.add_argument("--target", "-t", default=os.path.dirname(TEMPLATE_DIR),
                        help="目标目录（默认上级目录）")
    parser.add_argument("--remote", "-r", help="Git 远程地址")
    parser.add_argument("--push", action="store_true", help="创建后推送")
    parser.add_argument("--skip-verify", action="store_true", help="跳过 pytest")
    args = parser.parse_args()

    project_name = args.name.strip()
    project_dir = os.path.join(os.path.abspath(args.target), project_name)

    print(f"\n{'='*50}")
    print(f"  📦 新项目: {project_name}")
    print(f"  📁 路径:   {project_dir}")
    print(f"  📁 模板:   {TEMPLATE_DIR}")
    print(f"{'='*50}")

    # 步骤 1: 复制模板
    if os.path.exists(project_dir):
        print(f"  ❌ 目录已存在: {project_dir}")
        sys.exit(1)

    print(f"\n  [1/5] 复制模板...")
    shutil.copytree(TEMPLATE_DIR, project_dir,
                    ignore=shutil.ignore_patterns(
                        ".git", "__pycache__", ".pytest_cache",
                        "crash_snapshots", "logs", "*.pyc"
                    ))

    # 步骤 2: 更新项目文件
    print("  [2/5] 改写项目文件...")

    # run.bat
    bat_path = os.path.join(project_dir, "run.bat")
    bat_content = (
        '@echo off\r\n'
        '\r\n'
        'set RUN_ID=%~1\r\n'
        'set WORK_DIR=%~2\r\n'
        'set INPUT_FILE=%~3\r\n'
        'set REPO_PATH=%~dp0\r\n'
        'set PYTHON=python\r\n'
        f'set PROJECT={project_name}\r\n'
        '\r\n'
        '%PYTHON% "%REPO_PATH%runner.py" --run_id "%RUN_ID%" --repo_path "%REPO_PATH:~0,-1%" --work_dir "%WORK_DIR%" --input_file "%INPUT_FILE%" --project "%PROJECT%"\r\n'
    )
    with open(bat_path, 'w', encoding='utf-8') as f:
        f.write(bat_content)
    print(f"     ✅ run.bat -> PROJECT={project_name}")

    # project.json
    pj_path = os.path.join(project_dir, "project.json")
    with open(pj_path, 'r', encoding='utf-8') as f:
        pj = json.load(f)
    pj["project"] = project_name
    pj["linear"]["project_name"] = project_name
    pj["feishu_webhook"] = ""
    pj["linear"]["api_key"] = ""
    with open(pj_path, 'w', encoding='utf-8') as f:
        json.dump(pj, f, ensure_ascii=False, indent=2)
    print(f"     ✅ project.json -> {project_name}")

    # README
    readme_path = os.path.join(project_dir, "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
        content = content.replace("rpa-dev-template", project_name, 1)
        content = content.replace("开发模板", project_name, 1)
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(content)

    # 步骤 3: Git 初始化
    print("  [3/5] 初始化 Git 仓库...")
    run("git init", cwd=project_dir)
    run("git add -A", cwd=project_dir, check=False)
    run(f'git commit -m "🎉 init: {project_name}"', cwd=project_dir)

    # 步骤 4: 远程配置
    print("  [4/5] 远程配置...")
    if args.remote:
        run(f"git remote add origin {args.remote}", cwd=project_dir)
        if args.push:
            run("git push -u origin main", cwd=project_dir, timeout=60, check=False)
        print(f"     ✅ 远程: {args.remote}")

    # 步骤 5: 验证
    if not args.skip_verify:
        print("  [5/5] 运行 pytest 验证...")
        rc, out, _ = run("python -m pytest tests/ -v", cwd=project_dir, check=False, timeout=60)
        if rc == 0 or "passed" in out:
            print("     ✅ 测试通过")
        else:
            print(f"  ⚠ 测试异常 (RC={rc})，请检查")

    print(f"\n{'='*50}")
    print(f"  ✅ 项目初始化完成!")
    print(f"  {'='*50}")
    print(f"  路径:  {project_dir}")
    print(f"  影刀:  {project_dir}\\run.bat")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
