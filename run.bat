@echo off

set RUN_ID=%~1
set REPO_PATH=%~dp0
set INPUT_FILE=%~2
set PYTHON=python

%PYTHON% "%REPO_PATH%runner.py" --run_id "%RUN_ID%" --repo_path "%REPO_PATH:~0,-1%" --input_file "%INPUT_FILE%"
