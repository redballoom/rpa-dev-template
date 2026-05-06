@echo off
chcp 65001 >nul

REM ============================================
REM run.bat — Yingdao RPA Entry
REM Usage : run.bat <run_id>
REM Example: run.bat 20260506_001
REM
REM Before use, set:
REM   REPO_PATH = project root (NO Chinese chars!)
REM   PYTHON    = python.exe path
REM   PROJECT   = project name
REM ============================================

set RUN_ID=%~1
set REPO_PATH=D:\CraftPJ\dev-template
set PYTHON=python
set PROJECT=dev-template

REM Execute business logic (output: runner_%RUN_ID%.json)
%PYTHON% "%REPO_PATH%\runner.py" --run_id "%RUN_ID%" --repo_path "%REPO_PATH%" --project "%PROJECT%"
