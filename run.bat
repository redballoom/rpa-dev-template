@echo off
setlocal

set RUN_ID=%~1
set WORK_DIR=%~2
set INPUT_FILE=%~3
set REPO_PATH=%~dp0
set PYTHON=python
set PROJECT=开发模板

if "%RUN_ID%"=="" (
  echo [run.bat] ERROR: missing run_id
  echo Usage: run.bat {run_id} {work_dir} {input_file}
  exit /b 2
)

if not "%INPUT_FILE%"=="" if not exist "%INPUT_FILE%" (
  echo [run.bat] ERROR: input_file not found: "%INPUT_FILE%"
  exit /b 3
)

%PYTHON% "%REPO_PATH%runner.py" --run_id "%RUN_ID%" --repo_path "%REPO_PATH:~0,-1%" --work_dir "%WORK_DIR%" --input_file "%INPUT_FILE%" --project "%PROJECT%"
exit /b %ERRORLEVEL%
