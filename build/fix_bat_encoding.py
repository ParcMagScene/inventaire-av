#!/usr/bin/env python3
"""
Convertit tous les .bat du projet en CRLF + cp1252 pour compatibilité Windows.
Remplace aussi les caractères Unicode problématiques.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Trouver tous les .bat
bat_files = list(ROOT.rglob("*.bat"))
# Inclure aussi ceux dans USB_Package
bat_files += list((ROOT / "USB_Package").rglob("*.bat")) if (ROOT / "USB_Package").exists() else []

# Remplacements de caractères UTF-8 → ASCII
REPLACEMENTS = {
    "╔": "=",
    "╗": "=",
    "╚": "=",
    "╝": "=",
    "═": "=",
    "║": "|",
    "╠": "=",
    "╣": "=",
    "→": "-",
    "—": "-",
    "─": "-",
    "é": "e",
    "è": "e",
    "ê": "e",
    "ë": "e",
    "à": "a",
    "â": "a",
    "ô": "o",
    "ù": "u",
    "û": "u",
    "ü": "u",
    "ç": "c",
    "î": "i",
    "ï": "i",
    "É": "E",
    "È": "E",
    "Ê": "E",
    "À": "A",
    "Ç": "C",
    "©": "(c)",
}


def fix_bat(path: Path):
    """Corrige un fichier .bat pour Windows."""
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = path.read_text(encoding="cp1252")

    # Remplacer chcp 65001 par chcp 1252
    content = content.replace("chcp 65001", "chcp 1252")

    # Remplacer les caractères Unicode
    for old, new in REPLACEMENTS.items():
        content = old.replace(old, new) if old in content else content
        content = content.replace(old, new)

    # Normaliser les fins de ligne en CRLF
    content = content.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")

    # Écrire en cp1252 avec CRLF
    with open(path, "wb") as f:
        f.write(content.encode("cp1252", errors="replace"))

    print(f"  [OK] {path.relative_to(ROOT)}")


def main():
    print(f"\nCorrection des fichiers .bat ({len(bat_files)} fichiers)...\n")
    for bat in sorted(set(bat_files)):
        if bat.exists():
            fix_bat(bat)
    print("\nTerminé.\n")


if __name__ == "__main__":
    main()
