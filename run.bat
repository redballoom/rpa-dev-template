@echo off
chcp 65001 >nul

REM ============================================
REM run.bat — 影刀 RPA 入口
REM 调用: run.bat <run_id> <repo_path> [project]
REM
REM 示例:
REM   run.bat 20260506_001 D:\RPA_项目 物流项目
REM   run.bat 20260506_001 D:\RPA_项目
REM
REM 参数:
REM   %1 = run_id     (必填) Trace ID
REM   %2 = repo_path  (必填) 项目根目录
REM   %3 = project    (选填) 项目名，默认取目录名
REM ============================================

set RUN_ID=%~1
set REPO_PATH=%~2
set PROJECT=%~3

if "%PROJECT%"=="" (
    for %%i in ("%REPO_PATH%") do set PROJECT=%%~ni
)

REM 第一步: 切换 Git 分支
python "%REPO_PATH%\git_controller.py" --is_test True --repo_path "%REPO_PATH%"

REM 第二步: 执行业务逻辑 (结果写入 runner_%RUN_ID%.json)
python "%REPO_PATH%\runner.py" --run_id "%RUN_ID%" --repo_path "%REPO_PATH%" --project "%PROJECT%"
