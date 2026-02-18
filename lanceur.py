#!/usr/bin/env python3
"""
Lanceur cross-platform pour Inventaire AV.
Gère automatiquement :
  - Détection de Python
  - Création de l'environnement virtuel
  - Installation des dépendances (online ou offline via wheels/)
  - Lancement de l'application
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent
VENV_DIR = APP_ROOT / "venv"
WHEELS_DIR = APP_ROOT / "wheels"
REQUIREMENTS = APP_ROOT / "requirements.txt"

IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    VENV_PYTHON = VENV_DIR / "Scripts" / "python.exe"
    VENV_PIP = VENV_DIR / "Scripts" / "pip.exe"
else:
    VENV_PYTHON = VENV_DIR / "bin" / "python"
    VENV_PIP = VENV_DIR / "bin" / "pip"


def print_header():
    print()
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║         INVENTAIRE AV  —  Lanceur           ║")
    print("  ╚══════════════════════════════════════════════╝")
    print()


def find_python() -> str:
    """Trouve l'exécutable Python disponible."""
    # Python embarqué local
    embedded = APP_ROOT / "python" / ("python.exe" if IS_WINDOWS else "python3")
    if embedded.exists():
        print("  [✓] Python embarqué trouvé")
        return str(embedded)

    # Python système
    for cmd in ("python3", "python"):
        try:
            result = subprocess.run(
                [cmd, "--version"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                version = result.stdout.strip() or result.stderr.strip()
                print(f"  [✓] {version} trouvé ({cmd})")
                return cmd
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue

    print("  [✗] Python introuvable !")
    print("      Installez Python 3.10+ : https://www.python.org")
    sys.exit(1)


def ensure_venv(python_exe: str):
    """Crée le venv si nécessaire."""
    if VENV_PYTHON.exists():
        print("  [✓] Environnement virtuel existant")
        return

    print("  [~] Création de l'environnement virtuel...")
    result = subprocess.run(
        [python_exe, "-m", "venv", str(VENV_DIR)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  [✗] Erreur : {result.stderr}")
        sys.exit(1)
    print("  [✓] Environnement virtuel créé")


def install_dependencies():
    """Installe les dépendances si nécessaire."""
    # Test rapide : PySide6 installé ?
    result = subprocess.run(
        [str(VENV_PYTHON), "-c", "import PySide6"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("  [✓] Dépendances déjà installées")
        return

    print("  [~] Installation des dépendances...")

    if WHEELS_DIR.exists() and any(WHEELS_DIR.glob("*.whl")):
        # Mode offline
        print("      → Mode offline (dossier wheels/)")
        cmd = [
            str(VENV_PIP), "install",
            "--no-index",
            f"--find-links={WHEELS_DIR}",
            "-r", str(REQUIREMENTS)
        ]
    else:
        # Mode online
        print("      → Téléchargement depuis Internet...")
        # Upgrade pip d'abord
        subprocess.run(
            [str(VENV_PIP), "install", "--upgrade", "pip"],
            capture_output=True, text=True
        )
        cmd = [str(VENV_PIP), "install", "-r", str(REQUIREMENTS)]

    result = subprocess.run(cmd, capture_output=False, text=True)
    if result.returncode != 0:
        print("  [✗] Erreur lors de l'installation des dépendances")
        sys.exit(1)

    print("  [✓] Dépendances installées")


def launch_app():
    """Lance l'application."""
    print("  [►] Lancement de l'application...")
    print()

    os.chdir(str(APP_ROOT))
    result = subprocess.run(
        [str(VENV_PYTHON), "-m", "app.main"],
        cwd=str(APP_ROOT)
    )
    return result.returncode


def main():
    print_header()

    print("  [1/4] Détection de Python")
    python_exe = find_python()

    print("  [2/4] Environnement virtuel")
    ensure_venv(python_exe)

    print("  [3/4] Dépendances")
    install_dependencies()

    print("  [4/4] Lancement")
    code = launch_app()

    if code != 0:
        print(f"\n  [!] Application terminée avec code {code}")
        if IS_WINDOWS:
            input("\n  Appuyez sur Entrée pour fermer...")
        sys.exit(code)


if __name__ == "__main__":
    main()
