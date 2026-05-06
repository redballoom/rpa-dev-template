@echo off
chcp 65001 >nul

REM ============================================
REM run.bat — 影刀 RPA 入口
REM 调用: run.bat <run_id>
REM 示例: run.bat 20260506_001
REM 结果保存在 runner_<run_id>.json (影刀读取)
REM ============================================

set RUN_ID=%~1
set REPO_PATH=D:\RPA_项目
set PROJECT=XXXX项目

REM 第一步: 切换 Git 分支
python "%REPO_PATH%\git_controller.py" --is_test True --repo_path "%REPO_PATH%"

REM 第二步: 执行业务逻辑 (结果写入 runner_%RUN_ID%.json)
python "%REPO_PATH%\runner.py" --run_id "%RUN_ID%" --repo_path "%REPO_PATH%" --project "%PROJECT%"
