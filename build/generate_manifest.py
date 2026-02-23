#!/usr/bin/env python3
"""
generate_manifest.py — Génère le manifeste d'intégrité SHA-256 pour l'application.

Usage :
    cd inventaire-app
    python build/generate_manifest.py
"""
import sys
from pathlib import Path

# Ajouter le dossier racine au path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.integrity import generate_manifest, verify_manifest


def main():
    print()
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║   Intégrité — Génération du manifeste       ║")
    print("  ╚══════════════════════════════════════════════╝")
    print()

    if "--verify" in sys.argv:
        print("  Mode : vérification")
        ok, errors = verify_manifest(ROOT)
        if ok:
            print("  ✅ Intégrité OK — tous les fichiers sont conformes.")
        else:
            print(f"  ❌ {len(errors)} problème(s) détecté(s) :")
            for e in errors:
                print(f"      • {e}")
        sys.exit(0 if ok else 1)

    print("  Mode : génération")
    path = generate_manifest(ROOT)
    print(f"  ✅ Manifeste généré : {path}")

    # Vérification immédiate
    ok, errors = verify_manifest(ROOT, path)
    if ok:
        print("  ✅ Vérification post-génération OK")
    else:
        print(f"  ⚠ Vérification : {len(errors)} problème(s)")

    print()


if __name__ == "__main__":
    main()
