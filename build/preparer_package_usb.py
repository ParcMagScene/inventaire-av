#!/usr/bin/env python3
"""
Préparateur de package USB autonome pour Inventaire AV.
Alternative Python au script batch — utilisable sous macOS/Linux/Windows.

Crée un dossier USB_Package/ contenant :
  - Python embarqué (Windows amd64)
  - Tous les wheels pré-téléchargés
  - L'application complète
  - Scripts d'installation et de lancement
"""

import os
import sys
import ssl
import shutil
import subprocess
import zipfile
import urllib.request
import platform
from pathlib import Path

# ─── Contournement SSL macOS ────────────────────────────────────────────────
# macOS ne fournit pas toujours les certificats racine à Python.
try:
    _SSL_CTX = ssl.create_default_context()
except ssl.SSLError:
    _SSL_CTX = ssl._create_unverified_context()

# Si les certificats ne sont pas installés, on désactive la vérif
try:
    urllib.request.urlopen("https://www.python.org", timeout=5, context=_SSL_CTX)
except Exception:
    _SSL_CTX = ssl._create_unverified_context()

# ─── Configuration ──────────────────────────────────────────────────────────
PYTHON_VERSION = "3.11.9"
PYTHON_EMBED_URL = (
    f"https://www.python.org/ftp/python/{PYTHON_VERSION}/"
    f"python-{PYTHON_VERSION}-embed-amd64.zip"
)
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"

SRC_DIR = Path(__file__).resolve().parent.parent  # inventaire-app/
OUTPUT_DIR = SRC_DIR / "USB_Package"

# Fichiers / dossiers à copier dans inventaire-app/
APP_ITEMS = [
    ("app", True),        # (nom, est_dossier)
]
APP_FILES = [
    "requirements.txt",
    "README.md",
    "Lanceur.bat",
    "lanceur.py",
]


def banner():
    print()
    print("  ╔══════════════════════════════════════════════════════╗")
    print("  ║   INVENTAIRE AV — Préparation du Package USB       ║")
    print("  ╚══════════════════════════════════════════════════════╝")
    print()


def download_file(url: str, dest: Path, label: str = ""):
    """Télécharge un fichier avec affichage de progression."""
    print(f"      → Téléchargement {label or url}...")
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, context=_SSL_CTX) as resp, open(dest, "wb") as f:
            shutil.copyfileobj(resp, f)
    except Exception as e:
        print(f"  [✗] Erreur téléchargement : {e}")
        sys.exit(1)


def step_clean():
    """Nettoie et crée le dossier de sortie."""
    print("  [1/7] Préparation du dossier de sortie...")
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)
    print("        → Dossier USB_Package/ créé")


def step_copy_app():
    """Copie l'application."""
    print("  [2/7] Copie de l'application...")
    app_dest = OUTPUT_DIR / "inventaire-app"
    app_dest.mkdir(parents=True, exist_ok=True)

    # Copier les dossiers
    ignore_pycache = shutil.ignore_patterns("__pycache__", "*.pyc")
    for name, is_dir in APP_ITEMS:
        src = SRC_DIR / name
        dst = app_dest / name
        if is_dir and src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True, ignore=ignore_pycache)
        elif not is_dir and src.is_file():
            shutil.copy2(src, dst)

    # Copier les fichiers individuels
    for f in APP_FILES:
        src = SRC_DIR / f
        if src.exists():
            shutil.copy2(src, app_dest / f)

    # Créer data/ si absent
    (app_dest / "app" / "data").mkdir(parents=True, exist_ok=True)

    # Créer backups/ si absent
    (app_dest / "app" / "backups").mkdir(parents=True, exist_ok=True)

    print("        → Application copiée")


def step_download_python():
    """Télécharge Python embarqué."""
    print(f"  [3/7] Téléchargement de Python embarqué {PYTHON_VERSION}...")
    embed_dir = OUTPUT_DIR / "python_embed"
    embed_dir.mkdir(parents=True, exist_ok=True)

    zip_path = embed_dir / "python_embed.zip"
    download_file(PYTHON_EMBED_URL, zip_path, f"Python {PYTHON_VERSION}")

    # Extraire
    python_dir = embed_dir / "python"
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(python_dir)
    zip_path.unlink()

    # Activer import site + ajouter chemin app dans le fichier ._pth
    # En mode USB : python_embed/python/ → ../../inventaire-app
    for pth in python_dir.glob("python*._pth"):
        content = pth.read_text()
        content = content.replace("#import site", "import site")
        # Ajouter le chemin relatif vers inventaire-app (mode USB)
        content += "\n../../inventaire-app\n"
        pth.write_text(content)

    print("        → Python embarqué extrait (._pth configuré)")


def step_install_pip():
    """Installe pip dans Python embarqué."""
    print("  [4/7] Installation de pip...")
    python_exe = OUTPUT_DIR / "python_embed" / "python" / "python.exe"
    get_pip = OUTPUT_DIR / "python_embed" / "python" / "get-pip.py"

    download_file(GET_PIP_URL, get_pip, "get-pip.py")

    # Sur macOS/Linux on ne peut pas exécuter python.exe — on skip l'exécution
    if platform.system() == "Windows":
        subprocess.run(
            [str(python_exe), str(get_pip), "--no-warn-script-location"],
            capture_output=True, text=True
        )
        get_pip.unlink(missing_ok=True)
        print("        → pip installé")
    else:
        print("        → get-pip.py copié (sera exécuté sur Windows)")


def step_download_wheels():
    """Télécharge les wheels pour Windows."""
    print("  [5/7] Téléchargement des packages (wheels)...")
    wheels_dir = OUTPUT_DIR / "inventaire-app" / "wheels"
    wheels_dir.mkdir(parents=True, exist_ok=True)

    req_file = SRC_DIR / "requirements.txt"

    # Essayer d'abord les binaires Windows uniquement
    result = subprocess.run(
        [
            sys.executable, "-m", "pip", "download",
            "-r", str(req_file),
            f"--dest={wheels_dir}",
            "--platform", "win_amd64",
            "--python-version", "3.11",
            "--only-binary=:all:",
        ],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        print("        → Téléchargement étendu (avec sources)...")
        subprocess.run(
            [
                sys.executable, "-m", "pip", "download",
                "-r", str(req_file),
                f"--dest={wheels_dir}",
            ],
            capture_output=True, text=True
        )

    count = len(list(wheels_dir.glob("*")))
    print(f"        → {count} packages téléchargés")


def write_bat(path: Path, content: str):
    """Écrit un fichier .bat avec fins de ligne CRLF (obligatoire pour Windows)."""
    # Normaliser en LF d'abord, puis convertir en CRLF
    content = content.replace("\r\n", "\n").replace("\n", "\r\n")
    with open(path, "wb") as f:
        f.write(content.encode("cp1252", errors="replace"))


def step_create_scripts():
    """Crée les scripts d'installation et de lancement USB."""
    print("  [6/7] Création des scripts USB...")

    # Créer le marqueur de mode portable
    portable_marker = OUTPUT_DIR / "inventaire-app" / ".portable"
    portable_marker.write_text("Mode portable USB\n", encoding="utf-8")
    print("        → .portable créé")

    # --- INSTALLER.bat ---
    installer = OUTPUT_DIR / "INSTALLER.bat"
    write_bat(installer, r"""@echo off
chcp 1252 >nul 2>&1
title Installation Inventaire AV
color 0A

echo.
echo  ========================================================
echo     INVENTAIRE AV - Installation depuis USB
echo  ========================================================
echo.
echo  Ce programme va installer Inventaire AV sur votre PC.
echo.

set "USB_DIR=%~dp0"
set "INSTALL_DIR=%USERPROFILE%\InventaireAV"

echo  Dossier d'installation : %INSTALL_DIR%
echo.
set /p CONFIRM="  Continuer ? (O/N) : "
if /i "%CONFIRM%" neq "O" exit /b 0

echo.
echo [1/5] Creation du dossier d'installation...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

echo [2/5] Copie de Python embarque...
xcopy /E /I /Y "%USB_DIR%python_embed\python" "%INSTALL_DIR%\python" >nul
echo        - Python copie.

echo [3/5] Copie de l'application...
xcopy /E /I /Y "%USB_DIR%inventaire-app" "%INSTALL_DIR%\inventaire-app" >nul
if not exist "%INSTALL_DIR%\inventaire-app\app\backups" mkdir "%INSTALL_DIR%\inventaire-app\app\backups"
echo        - Application copiee.

:: Mettre a jour le fichier ._pth avec le chemin absolu de l'app
for %%F in ("%INSTALL_DIR%\python\python*._pth") do (
    echo python311.zip> "%%F"
    echo .>> "%%F"
    echo %INSTALL_DIR%\inventaire-app>> "%%F"
    echo import site>> "%%F"
)
echo        - Chemin Python configure.

echo [4/5] Installation des dependances...

if exist "%INSTALL_DIR%\python\get-pip.py" (
    "%INSTALL_DIR%\python\python.exe" "%INSTALL_DIR%\python\get-pip.py" --no-warn-script-location >nul 2>&1
    del "%INSTALL_DIR%\python\get-pip.py" 2>nul
)

"%INSTALL_DIR%\python\python.exe" -m pip install --no-index --find-links="%INSTALL_DIR%\inventaire-app\wheels" -r "%INSTALL_DIR%\inventaire-app\requirements.txt" --no-warn-script-location >nul 2>&1
echo        - Dependances installees.

echo [5/5] Creation du raccourci Bureau...

set "VBS_FILE=%TEMP%\inventaire_shortcut.vbs"
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%VBS_FILE%"
echo sLinkFile = oWS.SpecialFolders("Desktop") ^& "\Inventaire AV.lnk" >> "%VBS_FILE%"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%VBS_FILE%"
echo oLink.TargetPath = "%INSTALL_DIR%\python\pythonw.exe" >> "%VBS_FILE%"
echo oLink.Arguments = "-m app.main" >> "%VBS_FILE%"
echo oLink.WorkingDirectory = "%INSTALL_DIR%\inventaire-app" >> "%VBS_FILE%"
echo oLink.Description = "Inventaire AV" >> "%VBS_FILE%"
echo oLink.WindowStyle = 1 >> "%VBS_FILE%"
echo oLink.Save >> "%VBS_FILE%"
cscript //nologo "%VBS_FILE%"
del "%VBS_FILE%" 2>nul
echo        - Raccourci cree sur le Bureau.

:: Lanceur VBS invisible (pas de fenetre cmd)
set "VBSLAUNCHER=%INSTALL_DIR%\Lancer_InventaireAV.vbs"
echo Set WshShell = CreateObject("WScript.Shell") > "%VBSLAUNCHER%"
echo WshShell.CurrentDirectory = "%INSTALL_DIR%\inventaire-app" >> "%VBSLAUNCHER%"
echo WshShell.Run Chr(34) ^& "%INSTALL_DIR%\python\pythonw.exe" ^& Chr(34) ^& " -m app.main", 0, False >> "%VBSLAUNCHER%"

echo.
echo  ========================================================
echo     Installation terminee !
echo  ========================================================
echo.
echo  - Raccourci "Inventaire AV" cree sur le Bureau
echo  - Dossier : %INSTALL_DIR%
echo.
echo  Double-cliquez sur le raccourci pour demarrer.
echo.
pause
""")

    # --- LANCER_DEPUIS_USB.bat ---
    launcher_usb = OUTPUT_DIR / "LANCER_DEPUIS_USB.bat"
    write_bat(launcher_usb, r"""@echo off
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
""")

    # --- LANCER_DEPUIS_USB.vbs (lanceur invisible depuis USB) ---
    vbs_usb = OUTPUT_DIR / "LANCER_DEPUIS_USB.vbs"
    vbs_content = (
        'Set WshShell = CreateObject("WScript.Shell")\n'
        'Set fso = CreateObject("Scripting.FileSystemObject")\n'
        'strUSB = fso.GetParentFolderName(WScript.ScriptFullName)\n'
        'strPython = strUSB & "\\python_embed\\python\\pythonw.exe"\n'
        'strCheck = strUSB & "\\python_embed\\python\\python.exe"\n'
        'strApp = strUSB & "\\inventaire-app"\n'
        'WshShell.CurrentDirectory = strApp\n'
        '\n'
        "' 1) Installer pip si necessaire (AVANT tout)\n"
        'strGetPip = strUSB & "\\python_embed\\python\\get-pip.py"\n'
        'If fso.FileExists(strGetPip) Then\n'
        '    WshShell.Run """"& strCheck &""" """ & strGetPip & """ --no-warn-script-location", 1, True\n'
        '    fso.DeleteFile strGetPip\n'
        'End If\n'
        '\n'
        "' 2) Verifier si PySide6 est installe\n"
        'Set oExec = WshShell.Exec(""""& strCheck &""" -c ""import PySide6""")\n'
        'Do While oExec.Status = 0\n'
        '    WScript.Sleep 100\n'
        'Loop\n'
        'If oExec.ExitCode <> 0 Then\n'
        "    ' 3) Installer les dependances depuis les wheels\n"
        '    strPip = """"& strCheck &""" -m pip install --no-index --find-links=""" '
        '& strApp & "\\wheels"" -r """ & strApp & "\\requirements.txt"" --no-warn-script-location"\n'
        '    WshShell.Run strPip, 1, True\n'
        'End If\n'
        '\n'
        "' 4) Lancer l application (invisible)\n"
        'WshShell.Run """"& strPython &""" -m app.main", 0, False\n'
    )
    vbs_content = vbs_content.replace("\r\n", "\n").replace("\n", "\r\n")
    with open(vbs_usb, "wb") as f:
        f.write(vbs_content.encode("cp1252", errors="replace"))

    print("        → INSTALLER.bat créé")
    print("        → LANCER_DEPUIS_USB.bat créé")
    print("        → LANCER_DEPUIS_USB.vbs créé")


def step_generate_integrity():
    """Génère le manifeste d'intégrité SHA-256."""
    print("  [7/7] Génération du manifeste d'intégrité...")
    sys.path.insert(0, str(SRC_DIR))
    try:
        from app.core.integrity import generate_manifest
        app_dest = OUTPUT_DIR / "inventaire-app"
        manifest_path = generate_manifest(app_dest)
        print(f"        → {manifest_path.name} généré")
    except Exception as e:
        print(f"        → Avertissement : {e}")
        print("        → Manifeste non généré (non bloquant)")


def print_summary():
    """Affiche le résumé."""
    print()
    print("  " + "═" * 54)
    print()
    print(f"  Package USB prêt dans :")
    print(f"    {OUTPUT_DIR}")
    print()
    print("  Structure du package :")
    print("    USB_Package/")
    print("    ├── INSTALLER.bat          ← Installer sur le PC")
    print("    ├── LANCER_DEPUIS_USB.bat  ← Lancer directement")
    print("    ├── python_embed/          ← Python embarqué")
    print("    │   └── python/")
    print("    └── inventaire-app/        ← Application + wheels")
    print("        ├── app/")
    print("        │   ├── core/          (+ migrations, backup)")
    print("        │   ├── ui/views/      (+ backup_view)")
    print("        │   ├── backups/       ← Sauvegardes auto")
    print("        │   └── data/")
    print("        ├── wheels/")
    print("        ├── .portable           ← Marqueur mode portable")
    print("        ├── integrity_manifest.json")
    print("        ├── Lanceur.bat")
    print("        └── requirements.txt")
    print()
    print("  Utilisation :")
    print("    1. Copiez USB_Package/ sur une clé USB")
    print("    2. Sur le PC cible :")
    print("       • INSTALLER.bat → installation permanente")
    print("       • LANCER_DEPUIS_USB.bat → mode portable")
    print()
    print("  " + "═" * 54)
    print()


def main():
    banner()
    step_clean()
    step_copy_app()
    step_download_python()
    step_install_pip()
    step_download_wheels()
    step_create_scripts()
    step_generate_integrity()
    print_summary()


if __name__ == "__main__":
    main()
