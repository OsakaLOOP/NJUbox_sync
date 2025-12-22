@echo off
:: Set the project root path
set PROJECT_ROOT=C:\Scripts\NJUbox_sync

:: Activate venv if you use one, otherwise just call python
:: Make sure python is in PATH
python "%PROJECT_ROOT%\src\main.py" "%~1"