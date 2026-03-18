@echo off
chcp 1252 >nul 2>&1
title Inventaire AV - Execution depuis USB
color 0B
cd /d "%~dp0"

set "USB_DIR=%cd%"
set "PYTHON_EXE=%USB_DIR%\python_embed\python\python.exe"
set "APP_DIR=%USB_DIR%\inventaire-app"

echo.
echo  Lancement d'Inventaire AV depuis USB...
echo.

if exist "%USB_DIR%\python_embed\python\get-pip.py" (
    echo  Installation de pip...
    "%PYTHON_EXE%" "%USB_DIR%\python_embed\python\get-pip.py" --no-warn-script-location >nul 2>&1
    del "%USB_DIR%\python_embed\python\get-pip.py" 2>nul
)

"%PYTHON_EXE%" -c "import PySide6" >nul 2>&1
if %errorlevel% neq 0 (
    echo  Installation des dependances...
    "%PYTHON_EXE%" -m pip install --no-index --find-links="%APP_DIR%\wheels" -r "%APP_DIR%\requirements.txt" --no-warn-script-location >nul 2>&1
)

cd /d "%APP_DIR%"
start "" "%PYTHON_EXE%" -m app.main
