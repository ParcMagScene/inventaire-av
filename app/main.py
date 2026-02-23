"""
main.py — Point d'entrée de l'application Inventaire AV.

Lancement :
    python -m app.main          (depuis inventaire-app/)
    python app/main.py          (depuis inventaire-app/)
"""
import sys
import os
from pathlib import Path

__version__ = "2.0.0"

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


def _detect_portable_mode() -> bool:
    """Détecte si on fonctionne en mode portable (clé USB).

    Indices :
      - Présence d'un fichier `.portable` à la racine
      - Présence d'un dossier `python_embed` au-dessus
    """
    marker = ROOT_DIR / ".portable"
    parent_embed = ROOT_DIR.parent / "python_embed"
    return marker.exists() or parent_embed.exists()


# ── Imports applicatifs ───────────────────────────────────
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

from app.core.database import init_db
from app.ui.main_window import MainWindow


def main():
    # Détection mode portable
    portable = _detect_portable_mode()
    if portable:
        print(f"  [USB] Mode portable détecté — données locales")

    # Initialiser la base de données (crée les tables + seed au 1er lancement)
    init_db()

    # Vérification d'intégrité (non bloquante)
    try:
        from app.core.integrity import verify_manifest
        ok, errors = verify_manifest(ROOT_DIR)
        if not ok and errors:
            print(f"  [⚠] Intégrité : {len(errors)} problème(s) détecté(s)")
            for e in errors[:5]:
                print(f"      • {e}")
    except Exception:
        pass  # Pas de manifeste = pas de vérification

    # ── Application Qt ────────────────────────────────────
    app = QApplication(sys.argv)
    app.setApplicationName("Inventaire AV")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("InventaireAV")

    # Icône
    icon_path = APP_DIR / "ui" / "icons" / "app_icon.svg"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Fenêtre principale
    window = MainWindow()
    if portable:
        window.setWindowTitle(f"Inventaire AV v{__version__} — Mode portable")
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
