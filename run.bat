@echo off

set RUN_ID=%~1
set REPO_PATH=%~dp0
set PYTHON=python
set PROJECT=dev-template

%PYTHON% "%REPO_PATH%runner.py" --run_id "%RUN_ID%" --repo_path "%REPO_PATH:~0,-1%" --project "%PROJECT%"
