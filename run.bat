@echo off

set RUN_ID=%~1
set WORK_DIR=%~2
set INPUT_FILE=%~3
set REPO_PATH=%~dp0
set PYTHON=python
set PROJECT=开发模板

%PYTHON% "%REPO_PATH%runner.py" --run_id "%RUN_ID%" --repo_path "%REPO_PATH:~0,-1%" --work_dir "%WORK_DIR%" --input_file "%INPUT_FILE%" --project "%PROJECT%"
