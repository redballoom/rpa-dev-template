@echo off
setlocal

set "RUN_ID=%~1"
set "WORK_DIR=%~2"
set "INPUT_FILE=%~3"
set "REPO_PATH=%~dp0"
set "PROJECT=开发模板"
set "RPA_PRODUCTION_ENTRYPOINT=run.bat"
set "PROJECT_PYTHON=%REPO_PATH%.venv\Scripts\python.exe"

if not exist "%PROJECT_PYTHON%" (
  echo [run.bat] ERROR: project virtualenv not found: "%PROJECT_PYTHON%"
  echo Please run: py -3.12 -m venv .venv
  echo Then run: .venv\Scripts\python.exe -m pip install -r requirements.txt
  exit /b 7
)

set "PYTHON=%PROJECT_PYTHON%"
set "RPA_PYTHON_ENV=project_venv"

if "%RUN_ID%"=="" (
  echo [run.bat] ERROR: missing run_id
  echo Usage: run.bat {run_id} {work_dir} {input_file}
  exit /b 2
)

if "%WORK_DIR%"=="" (
  echo [run.bat] ERROR: missing work_dir
  echo Usage: run.bat {run_id} {work_dir} {input_file}
  exit /b 3
)

if not exist "%WORK_DIR%\." (
  echo [run.bat] ERROR: work_dir not found: "%WORK_DIR%"
  exit /b 4
)

if "%INPUT_FILE%"=="" (
  echo [run.bat] ERROR: missing input_file
  echo Usage: run.bat {run_id} {work_dir} {input_file}
  exit /b 5
)

if not exist "%INPUT_FILE%" (
  echo [run.bat] ERROR: input_file not found: "%INPUT_FILE%"
  exit /b 6
)

"%PYTHON%" "%REPO_PATH%runner.py" --run_id "%RUN_ID%" --repo_path "%REPO_PATH:~0,-1%" --work_dir "%WORK_DIR%" --input_file "%INPUT_FILE%" --project "%PROJECT%"
exit /b %ERRORLEVEL%
