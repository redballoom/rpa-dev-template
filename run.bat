@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ============================================================
REM run.bat — 影刀 RPA 统一入口
REM 调用: run.bat 20260506_001
REM 参数: %1 = run_id (Trace ID, 影刀生成)
REM ============================================================

set RUN_ID=%~1
set REPO_PATH=D:\RPA_物流项目
set PROJECT=物流项目

if "%RUN_ID%"=="" (
    echo [ERROR] 缺少 run_id 参数
    echo 用法: run.bat ^<run_id^>
    exit /b 1
)

echo ============================================
echo  RPA 调度入口
echo  项目 : %PROJECT%
echo  RunID: %RUN_ID%
echo  时间 : %DATE% %TIME%
echo ============================================

REM ── 第一步：切换 Git 环境 ──
echo [1/2] 切换 Git 分支...
python "%REPO_PATH%\git_controller.py" --is_test True --repo_path "%REPO_PATH%"
if errorlevel 1 (
    echo [失败] Git 切换出错，终止流程
    exit /b 1
)
echo [OK] Git 环境就绪

REM ── 第二步：执行业务逻辑 ──
echo [2/2] 运行 RPA 业务逻辑...
python "%REPO_PATH%\runner.py" --run_id "%RUN_ID%" --repo_path "%REPO_PATH%" --project "%PROJECT%"

REM ── 读取结果 JSON ──
set STATUS_FILE=%REPO_PATH%\runner_%RUN_ID%.json
if exist "%STATUS_FILE%" (
    REM 解析 status 字段决定退出码
    findstr /C:"""status"": ""success""" "%STATUS_FILE%" >nul 2>&1
    if !errorlevel! equ 0 (
        echo.
        echo [结果] success — RPA 正常完成
        exit /b 0
    )
    findstr /C:"""status"": ""warning""" "%STATUS_FILE%" >nul 2>&1
    if !errorlevel! equ 0 (
        echo.
        echo [结果] warning — 有业务异常被跳过
        exit /b 0
    )
    findstr /C:"""status"": ""failed""" "%STATUS_FILE%" >nul 2>&1
    if !errorlevel! equ 0 (
        echo.
        echo [结果] failed — 系统 Bug 已上报飞书 L2
        exit /b 2
    )
    findstr /C:"""status"": ""fatal""" "%STATUS_FILE%" >nul 2>&1
    if !errorlevel! equ 0 (
        echo.
        echo [结果] fatal — Runner 自身崩溃
        exit /b 3
    )
) else (
    echo [WARN] 未找到状态文件: %STATUS_FILE%
)

endlocal
