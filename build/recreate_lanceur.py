#!/usr/bin/env python3
"""Recrée les Lanceur.bat en CRLF + cp1252."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

LANCEUR_BAT = (
    "@echo off\n"
    "chcp 1252 >nul 2>&1\n"
    "title Inventaire AV - Lanceur\n"
    "color 0B\n"
    "\n"
    "echo.\n"
    "echo  ========================================================\n"
    "echo     INVENTAIRE AV - Lanceur\n"
    "echo  ========================================================\n"
    "echo.\n"
    "\n"
    'cd /d "%~dp0"\n'
    'set "APP_ROOT=%cd%"\n'
    "\n"
    "echo [1/4] Verification de Python...\n"
    "\n"
    'if exist "%APP_ROOT%\\python\\python.exe" (\n'
    '    set "PYTHON_EXE=%APP_ROOT%\\python\\python.exe"\n'
    "    echo        - Python embarque trouve.\n"
    "    goto :python_ok\n"
    ")\n"
    "\n"
    "where python >nul 2>&1\n"
    "if %errorlevel%==0 (\n"
    '    set "PYTHON_EXE=python"\n'
    "    echo        - Python systeme trouve.\n"
    "    goto :python_ok\n"
    ")\n"
    "\n"
    "where python3 >nul 2>&1\n"
    "if %errorlevel%==0 (\n"
    '    set "PYTHON_EXE=python3"\n'
    "    echo        - Python3 systeme trouve.\n"
    "    goto :python_ok\n"
    ")\n"
    "\n"
    "echo.\n"
    "echo  [ERREUR] Python non installe ou introuvable.\n"
    "echo           Installez Python 3.10+ depuis https://www.python.org\n"
    'echo           Cochez "Add Python to PATH" lors de l installation.\n'
    "echo.\n"
    "pause\n"
    "exit /b 1\n"
    "\n"
    ":python_ok\n"
    "\n"
    "echo [2/4] Environnement virtuel...\n"
    "\n"
    'if not exist "%APP_ROOT%\\venv\\Scripts\\python.exe" (\n'
    "    echo        - Creation de l environnement virtuel...\n"
    '    "%PYTHON_EXE%" -m venv "%APP_ROOT%\\venv"\n'
    "    if %errorlevel% neq 0 (\n"
    "        echo  [ERREUR] Impossible de creer le venv.\n"
    "        pause\n"
    "        exit /b 1\n"
    "    )\n"
    "    echo        - Environnement virtuel cree.\n"
    ") else (\n"
    "    echo        - Environnement virtuel existant.\n"
    ")\n"
    "\n"
    'set "VENV_PYTHON=%APP_ROOT%\\venv\\Scripts\\python.exe"\n'
    'set "VENV_PIP=%APP_ROOT%\\venv\\Scripts\\pip.exe"\n'
    "\n"
    "echo [3/4] Dependances...\n"
    "\n"
    '"%VENV_PYTHON%" -c "import PySide6" >nul 2>&1\n'
    "if %errorlevel% neq 0 (\n"
    "    echo        - Installation des dependances...\n"
    "\n"
    '    if exist "%APP_ROOT%\\wheels" (\n'
    "        echo        - Mode offline detecte\n"
    '        "%VENV_PIP%" install --no-index --find-links="%APP_ROOT%\\wheels" -r "%APP_ROOT%\\requirements.txt" >nul 2>&1\n'
    "    ) else (\n"
    "        echo        - Telechargement depuis Internet...\n"
    '        "%VENV_PIP%" install --upgrade pip >nul 2>&1\n'
    '        "%VENV_PIP%" install -r "%APP_ROOT%\\requirements.txt"\n'
    "    )\n"
    "\n"
    "    if %errorlevel% neq 0 (\n"
    "        echo.\n"
    "        echo  [ERREUR] Installation des dependances echouee.\n"
    "        pause\n"
    "        exit /b 1\n"
    "    )\n"
    "    echo        - Dependances installees.\n"
    ") else (\n"
    "    echo        - Dependances deja installees.\n"
    ")\n"
    "\n"
    "echo [4/4] Lancement...\n"
    "echo.\n"
    "\n"
    '"%VENV_PYTHON%" -m app.main\n'
    "\n"
    "if %errorlevel% neq 0 (\n"
    "    echo.\n"
    "    echo  [ERREUR] L application s est terminee avec une erreur.\n"
    "    echo.\n"
    "    pause\n"
    ")\n"
)


def write_crlf(path: Path, content: str):
    content = content.replace("\r\n", "\n").replace("\n", "\r\n")
    with open(path, "wb") as f:
        f.write(content.encode("cp1252", errors="replace"))


targets = [
    ROOT / "Lanceur.bat",
    ROOT / "USB_Package" / "inventaire-app" / "Lanceur.bat",
]

for t in targets:
    if t.parent.exists():
        write_crlf(t, LANCEUR_BAT)
        print(f"OK: {t.relative_to(ROOT)}")
    else:
        print(f"SKIP: {t}")

print("Done.")
