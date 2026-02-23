"""
integrity.py — Vérification d'intégrité SHA-256 pour l'application et la base.

Fournit :
  - Calcul du hash SHA-256 d'un fichier ou d'un répertoire
  - Génération d'un manifeste d'intégrité
  - Vérification d'un manifeste existant
"""
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Fichiers à exclure du hachage
_EXCLUDE = {
    "__pycache__", ".pyc", ".pyo", ".DS_Store",
    "Thumbs.db", "desktop.ini", ".git",
}

# Nom du fichier manifeste
MANIFEST_NAME = "integrity_manifest.json"


def sha256_file(path: Path | str) -> str:
    """Calcule le SHA-256 d'un fichier."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    """Calcule le SHA-256 de données en mémoire."""
    return hashlib.sha256(data).hexdigest()


def _should_include(path: Path) -> bool:
    """Détermine si un fichier/dossier doit être inclus dans le manifeste."""
    for part in path.parts:
        if part in _EXCLUDE:
            return False
        if any(part.endswith(ext) for ext in (".pyc", ".pyo")):
            return False
    return True


def scan_directory(root: Path, relative_to: Path | None = None) -> Dict[str, str]:
    """
    Scanne un répertoire et retourne un dict {chemin_relatif: sha256}.
    
    Args:
        root: Répertoire racine à scanner.
        relative_to: Référence pour les chemins relatifs (défaut: root).
    """
    if relative_to is None:
        relative_to = root

    result: Dict[str, str] = {}
    root = Path(root)

    if not root.exists():
        return result

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if not _should_include(path.relative_to(relative_to)):
            continue
        rel = str(path.relative_to(relative_to)).replace("\\", "/")
        result[rel] = sha256_file(path)

    return result


def generate_manifest(app_dir: Path, output_path: Path | None = None) -> Path:
    """
    Génère un manifeste d'intégrité JSON pour l'application.

    Args:
        app_dir: Racine de l'application (contient app/, requirements.txt, etc.)
        output_path: Chemin de sortie (défaut: app_dir/integrity_manifest.json)

    Returns:
        Le chemin du manifeste généré.
    """
    app_dir = Path(app_dir)
    if output_path is None:
        output_path = app_dir / MANIFEST_NAME

    # Scanner les fichiers de l'application
    hashes = scan_directory(app_dir / "app", relative_to=app_dir)

    # Ajouter requirements.txt et lanceur.py s'ils existent
    for extra in ("requirements.txt", "lanceur.py"):
        fp = app_dir / extra
        if fp.exists():
            hashes[extra] = sha256_file(fp)

    # Calculer le hash global (trié par clé)
    combined = "".join(f"{k}:{v}" for k, v in sorted(hashes.items()))
    global_hash = sha256_bytes(combined.encode("utf-8"))

    manifest = {
        "version": "2.0.0",
        "generated_at": datetime.now().isoformat(),
        "global_hash": global_hash,
        "file_count": len(hashes),
        "files": hashes,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    return output_path


def verify_manifest(app_dir: Path, manifest_path: Path | None = None) -> Tuple[bool, List[str]]:
    """
    Vérifie l'intégrité de l'application par rapport à un manifeste.

    Args:
        app_dir: Racine de l'application.
        manifest_path: Chemin du manifeste (défaut: app_dir/integrity_manifest.json).

    Returns:
        (is_valid, errors) — is_valid est True si tout est OK.
    """
    app_dir = Path(app_dir)
    if manifest_path is None:
        manifest_path = app_dir / MANIFEST_NAME

    errors: List[str] = []

    if not manifest_path.exists():
        return False, ["Manifeste d'intégrité introuvable."]

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    expected_files: Dict[str, str] = manifest.get("files", {})

    # Vérifier chaque fichier du manifeste
    for rel_path, expected_hash in expected_files.items():
        full_path = app_dir / rel_path
        if not full_path.exists():
            errors.append(f"MANQUANT : {rel_path}")
            continue
        actual_hash = sha256_file(full_path)
        if actual_hash != expected_hash:
            errors.append(f"MODIFIÉ  : {rel_path}")

    # Vérifier le hash global
    current_hashes = {}
    for rel_path in expected_files:
        full_path = app_dir / rel_path
        if full_path.exists():
            current_hashes[rel_path] = sha256_file(full_path)
        else:
            current_hashes[rel_path] = "MISSING"

    combined = "".join(f"{k}:{v}" for k, v in sorted(current_hashes.items()))
    current_global = sha256_bytes(combined.encode("utf-8"))
    expected_global = manifest.get("global_hash", "")

    if current_global != expected_global:
        if not errors:
            errors.append("Hash global différent (fichiers potentiellement modifiés).")

    is_valid = len(errors) == 0
    return is_valid, errors


def verify_database(db_path: Path) -> Dict[str, str]:
    """
    Retourne des informations d'intégrité basiques sur la base SQLite.

    Args:
        db_path: Chemin de la base de données.

    Returns:
        Dict avec taille, hash, date de modification.
    """
    db_path = Path(db_path)
    if not db_path.exists():
        return {"status": "absent", "path": str(db_path)}

    stat = db_path.stat()
    return {
        "status": "ok",
        "path": str(db_path),
        "size_bytes": stat.st_size,
        "size_mb": round(stat.st_size / (1024 * 1024), 2),
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "sha256": sha256_file(db_path),
    }
