@echo off
REM Lanzador de LoL Auto Queue (portable: usa la carpeta del script)
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if not errorlevel 1 (
    py -3.12 main.py
    if not errorlevel 1 exit /b 0
)
python main.py
if errorlevel 1 pause
