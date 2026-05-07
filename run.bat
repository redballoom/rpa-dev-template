@echo off
chcp 65001 >nul 2>&1

REM ==========================================
REM  影刀 RPA 调用入口 (BAT 模式)
REM  参数1: run_id (影刀生成的 UUID)
REM  工作目录: 由影刀设置为项目路径 (glv['code_pj_path'])
REM ==========================================

REM 影刀传入的 run_id
set RUN_ID=%~1

REM 工作目录即项目路径（影刀在高级设置中指定工作目录）
set REPO_PATH=%cd%

REM 项目名称（按需修改，或通过第二个参数传入）
if "%~2"=="" (
    set PROJECT=RPA
) else (
    set PROJECT=%~2
)

python "%REPO_PATH%\runner.py" --run_id "%RUN_ID%" --repo_path "%REPO_PATH%" --project "%PROJECT%"
