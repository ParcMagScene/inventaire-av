"""
main.py — Point d'entrée de l'application Inventaire AV.

Lancement :
    python -m app.main          (depuis inventaire-app/)
    python app/main.py          (depuis inventaire-app/)
"""
import sys
import os
from pathlib import Path

# ── Résolution robuste du chemin ──────────────────────────
# Fonctionne que l'on lance via `python -m app.main`, `python app/main.py`
# ou depuis un EXE PyInstaller (sys._MEIPASS).
if getattr(sys, "frozen", False):
    # Mode PyInstaller
    APP_DIR = Path(sys._MEIPASS) / "app"
    ROOT_DIR = Path(sys._MEIPASS)
else:
    APP_DIR = Path(__file__).resolve().parent
    ROOT_DIR = APP_DIR.parent

# Garantir que le dossier racine est dans sys.path
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# ── Imports applicatifs ───────────────────────────────────
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

from app.core.database import init_db
from app.ui.main_window import MainWindow


def main():
    # Initialiser la base de données (crée les tables + seed au 1er lancement)
    init_db()

    # ── Application Qt ────────────────────────────────────
    app = QApplication(sys.argv)
    app.setApplicationName("Inventaire AV")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("InventaireAV")

    # Icône
    icon_path = APP_DIR / "ui" / "icons" / "app_icon.svg"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Fenêtre principale
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
