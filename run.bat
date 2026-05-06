@echo off

set RUN_ID=%~1
set REPO_PATH=D:\CraftPJ\开发模板
set PYTHON=python
set PROJECT=开发模板

%PYTHON% "%REPO_PATH%\runner.py" --run_id "%RUN_ID%" --repo_path "%REPO_PATH%" --project "%PROJECT%"
