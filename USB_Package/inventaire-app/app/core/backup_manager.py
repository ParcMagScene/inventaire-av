"""
backup_manager.py — Système de sauvegarde et restauration.

- Sauvegarde manuelle (ZIP : base SQLite + config)
- Sauvegarde automatique au lancement (rotation)
- Restauration depuis un ZIP avec vérification d'intégrité
"""
import json
import os
import shutil
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Tuple, List

BASE_DIR = Path(__file__).resolve().parent.parent
BACKUP_DIR = BASE_DIR / "backups"
MAX_AUTO_BACKUPS = 5


def _ensure_backup_dir():
    """Crée le dossier backups/ s'il n'existe pas."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def _db_path() -> Path:
    """Résout le chemin de la base de données."""
    env = os.environ.get("INVENTAIRE_DB_PATH")
    if env:
        return Path(env)
    return BASE_DIR / "data" / "inventaire.db"


def _config_dir() -> Path:
    return BASE_DIR / "config"


# ═══════════════════════════════════════════════════════════
#  Sauvegarde
# ═══════════════════════════════════════════════════════════

def create_backup(dest_path: str | Path | None = None) -> Path:
    """Crée une sauvegarde ZIP contenant la base SQLite + les fichiers config.

    Args:
        dest_path: Chemin du fichier ZIP de destination (optionnel).
                   Si None, crée dans backups/ avec un nom horodaté.

    Returns:
        Chemin du fichier ZIP créé.
    """
    _ensure_backup_dir()

    if dest_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_path = BACKUP_DIR / f"backup_{ts}.zip"
    else:
        dest_path = Path(dest_path)

    db_file = _db_path()
    config = _config_dir()

    with zipfile.ZipFile(dest_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Base de données
        if db_file.exists():
            zf.write(db_file, "data/inventaire.db")

        # Fichiers de configuration
        if config.exists():
            for f in config.rglob("*"):
                if f.is_file() and "__pycache__" not in str(f):
                    arcname = f"config/{f.relative_to(config)}"
                    zf.write(f, arcname)

        # Métadonnées de la sauvegarde
        meta = {
            "created_at": datetime.now().isoformat(),
            "db_exists": db_file.exists(),
            "version": _get_app_version(),
        }
        zf.writestr("backup_meta.json", json.dumps(meta, indent=2, ensure_ascii=False))

    return dest_path


def auto_backup():
    """Sauvegarde automatique avec rotation (max MAX_AUTO_BACKUPS)."""
    _ensure_backup_dir()

    db_file = _db_path()
    if not db_file.exists():
        return  # Rien à sauvegarder

    # Créer la sauvegarde
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"auto_{ts}.zip"
    create_backup(backup_path)

    # Rotation : supprimer les plus anciennes
    auto_backups = sorted(
        [f for f in BACKUP_DIR.glob("auto_*.zip") if f.is_file()],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    for old in auto_backups[MAX_AUTO_BACKUPS:]:
        old.unlink(missing_ok=True)


# ═══════════════════════════════════════════════════════════
#  Restauration
# ═══════════════════════════════════════════════════════════

def verify_backup(zip_path: str | Path) -> Tuple[bool, str]:
    """Vérifie l'intégrité d'un fichier de sauvegarde.

    Returns:
        (ok, message)
    """
    zip_path = Path(zip_path)
    if not zip_path.exists():
        return False, "Le fichier n'existe pas."

    if not zipfile.is_zipfile(zip_path):
        return False, "Le fichier n'est pas un ZIP valide."

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()

            # Vérifier la présence de la base
            if "data/inventaire.db" not in names:
                return False, "La sauvegarde ne contient pas de base de données."

            # Vérifier les métadonnées
            if "backup_meta.json" in names:
                meta = json.loads(zf.read("backup_meta.json"))
                created = meta.get("created_at", "inconnu")
                version = meta.get("version", "inconnue")
                return True, f"Sauvegarde du {created} (version {version})"

            return True, "Sauvegarde valide (pas de métadonnées)."
    except zipfile.BadZipFile:
        return False, "Le fichier ZIP est corrompu."
    except Exception as e:
        return False, f"Erreur de vérification : {e}"


def restore_backup(zip_path: str | Path) -> Tuple[bool, str]:
    """Restaure une sauvegarde depuis un fichier ZIP.

    Crée une sauvegarde de sécurité avant la restauration.

    Returns:
        (ok, message)
    """
    zip_path = Path(zip_path)

    # 1) Vérifier l'intégrité
    ok, msg = verify_backup(zip_path)
    if not ok:
        return False, msg

    # 2) Sauvegarde de sécurité avant restauration
    try:
        safety_path = BACKUP_DIR / f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        create_backup(safety_path)
    except Exception:
        pass  # On continue même si la sauvegarde de sécurité échoue

    # 3) Extraire
    try:
        db_file = _db_path()
        config = _config_dir()

        with zipfile.ZipFile(zip_path, "r") as zf:
            # Restaurer la base de données
            if "data/inventaire.db" in zf.namelist():
                db_file.parent.mkdir(parents=True, exist_ok=True)
                with zf.open("data/inventaire.db") as src, open(db_file, "wb") as dst:
                    shutil.copyfileobj(src, dst)

            # Restaurer la configuration
            for name in zf.namelist():
                if name.startswith("config/") and not name.endswith("/"):
                    rel = name[len("config/"):]
                    dest = config / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(name) as src, open(dest, "wb") as dst:
                        shutil.copyfileobj(src, dst)

        # 4) Vérifier que la base restaurée est utilisable
        with sqlite3.connect(str(db_file)) as conn:
            conn.execute("SELECT COUNT(*) FROM articles")

        return True, "Restauration effectuée avec succès."

    except Exception as e:
        return False, f"Erreur lors de la restauration : {e}"


def list_backups() -> List[dict]:
    """Liste les sauvegardes disponibles dans backups/."""
    _ensure_backup_dir()
    result = []
    for f in sorted(BACKUP_DIR.glob("*.zip"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            size_mb = f.stat().st_size / (1024 * 1024)
            info = {
                "path": str(f),
                "name": f.name,
                "size": f"{size_mb:.2f} Mo",
                "date": datetime.fromtimestamp(f.stat().st_mtime).strftime("%d/%m/%Y %H:%M"),
                "is_auto": f.name.startswith("auto_"),
            }
            result.append(info)
        except Exception:
            continue
    return result


def _get_app_version() -> str:
    try:
        from app.main import __version__
        return __version__
    except Exception:
        return "2.0.0"
