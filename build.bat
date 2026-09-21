@echo off
REM Build local del .exe con PyInstaller (Windows) en entorno aislado.
REM Uso: doble clic o "build.bat" desde la carpeta del proyecto
setlocal
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no esta en el PATH.
    pause
    exit /b 1
)

if not exist .venv (
    echo [0/3] Creando entorno virtual...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] No se pudo crear .venv.
        pause
        exit /b 1
    )
)

echo [1/3] Instalando dependencias en .venv...
.venv\Scripts\python -m pip install -r requirements-dev.txt
if errorlevel 1 (
    echo [ERROR] Fallo instalando dependencias.
    pause
    exit /b 1
)

echo [2/3] Generando EXE...
.venv\Scripts\pyinstaller --noconfirm --clean LoLAutoQueue.spec

echo [3/3] Listo. Tu ejecutable esta en: dist\LoLAutoQueue.exe
