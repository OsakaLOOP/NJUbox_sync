@echo off
:: Set the project root path to the directory where this script is located
set "PROJECT_ROOT=%~dp0"
:: Remove trailing backslash if present (though %~dp0 usually has it)
:: It's safer to just point to PROJECT_ROOT without assuming C:\Scripts...

:: Activate venv if you use one, otherwise just call python
:: Make sure python is in PATH
python "%PROJECT_ROOT%src\main.py" "%~1"
