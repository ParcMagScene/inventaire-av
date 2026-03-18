@echo off
chcp 1252 >nul 2>&1
title Inventaire AV - Lanceur
color 0B

echo.
echo  ========================================================
echo     INVENTAIRE AV - Lanceur
echo  ========================================================
echo.

cd /d "%~dp0"
set "APP_ROOT=%cd%"

echo [1/4] Verification de Python...

if exist "%APP_ROOT%\python\python.exe" (
    set "PYTHON_EXE=%APP_ROOT%\python\python.exe"
    echo        - Python embarque trouve.
    goto :python_ok
)

where python >nul 2>&1
if %errorlevel%==0 (
    set "PYTHON_EXE=python"
    echo        - Python systeme trouve.
    goto :python_ok
)

where python3 >nul 2>&1
if %errorlevel%==0 (
    set "PYTHON_EXE=python3"
    echo        - Python3 systeme trouve.
    goto :python_ok
)

echo.
echo  [ERREUR] Python non installe ou introuvable.
echo           Installez Python 3.10+ depuis https://www.python.org
echo           Cochez "Add Python to PATH" lors de l installation.
echo.
pause
exit /b 1

:python_ok

echo [2/4] Environnement virtuel...

if not exist "%APP_ROOT%\venv\Scripts\python.exe" (
    echo        - Creation de l environnement virtuel...
    "%PYTHON_EXE%" -m venv "%APP_ROOT%\venv"
    if %errorlevel% neq 0 (
        echo  [ERREUR] Impossible de creer le venv.
        pause
        exit /b 1
    )
    echo        - Environnement virtuel cree.
) else (
    echo        - Environnement virtuel existant.
)

set "VENV_PYTHON=%APP_ROOT%\venv\Scripts\python.exe"
set "VENV_PIP=%APP_ROOT%\venv\Scripts\pip.exe"

echo [3/4] Dependances...

"%VENV_PYTHON%" -c "import PySide6" >nul 2>&1
if %errorlevel% neq 0 (
    echo        - Installation des dependances...

    if exist "%APP_ROOT%\wheels" (
        echo        - Mode offline detecte
        "%VENV_PIP%" install --no-index --find-links="%APP_ROOT%\wheels" -r "%APP_ROOT%\requirements.txt" >nul 2>&1
    ) else (
        echo        - Telechargement depuis Internet...
        "%VENV_PIP%" install --upgrade pip >nul 2>&1
        "%VENV_PIP%" install -r "%APP_ROOT%\requirements.txt"
    )

    if %errorlevel% neq 0 (
        echo.
        echo  [ERREUR] Installation des dependances echouee.
        pause
        exit /b 1
    )
    echo        - Dependances installees.
) else (
    echo        - Dependances deja installees.
)

echo [4/4] Lancement...
echo.

"%VENV_PYTHON%" -m app.main

if %errorlevel% neq 0 (
    echo.
    echo  [ERREUR] L application s est terminee avec une erreur.
    echo.
    pause
)
