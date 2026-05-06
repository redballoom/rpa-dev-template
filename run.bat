@echo off
chcp 65001 >nul

REM ============================================
REM run.bat — 影刀 RPA 入口
REM 调用: run.bat <run_id>
REM 示例: run.bat 20260506_001
REM
REM 使用前先改这 3 个变量:
REM   REPO_PATH = 你的项目实际路径
REM   PYTHON    = 你的 Python 路径
REM   PROJECT   = 你的项目名称
REM ============================================

set RUN_ID=%~1
set REPO_PATH=D:\你的项目路径
set PYTHON=python
set PROJECT=你的项目名

REM 第一步: 切换 Git 分支
%PYTHON% "%REPO_PATH%\git_controller.py" --is_test True --repo_path "%REPO_PATH%"

REM 第二步: 执行业务逻辑 (结果写入 runner_%RUN_ID%.json)
%PYTHON% "%REPO_PATH%\runner.py" --run_id "%RUN_ID%" --repo_path "%REPO_PATH%" --project "%PROJECT%"
