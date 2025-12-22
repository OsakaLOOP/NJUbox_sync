@echo off
:: Set the project root path to the directory where this script is located
set "PROJECT_ROOT=%~dp0"
python "%PROJECT_ROOT%src\main.py" "%~1"
