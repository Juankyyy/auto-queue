@echo off
REM Build local del .exe con PyInstaller (Windows)
REM Uso: doble clic o "build.bat" desde la carpeta del proyecto

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no esta en el PATH.
    pause
    exit /b 1
)

echo [1/3] Instalando dependencias...
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

echo [2/3] Generando EXE...
pyinstaller --noconfirm LoLAutoQueue.spec

echo [3/3] Listo. Tu ejecutable esta en: dist\LoLAutoQueue.exe
pause
