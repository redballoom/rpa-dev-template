@echo off
chcp 65001 >nul

REM ============================================
REM run.bat — 影刀 RPA 入口
REM 调用: run.bat <run_id>
REM 示例: run.bat 20260506_001
REM
REM 使用前改：
REM   REPO_PATH = 项目根目录
REM   PYTHON    = Python 路径
REM   PROJECT   = 项目名
REM ============================================

set RUN_ID=%~1
set REPO_PATH=D:\CraftPJ\开发模板
set PYTHON=python
set PROJECT=开发模板

REM 执行业务逻辑 (结果写入 runner_%RUN_ID%.json)
%PYTHON% "%REPO_PATH%\runner.py" --run_id "%RUN_ID%" --repo_path "%REPO_PATH%" --project "%PROJECT%"
