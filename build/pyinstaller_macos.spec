# -*- mode: python ; coding: utf-8 -*-
"""
pyinstaller_macos.spec — Configuration PyInstaller pour Inventaire AV (macOS).

Usage :
    cd inventaire-app
    pyinstaller build/pyinstaller_macos.spec
"""
import os
import sys
from pathlib import Path

block_cipher = None

ROOT = Path(SPECPATH).parent
APP_DIR = ROOT / "app"

# Données à inclure dans le bundle
datas = [
    (str(APP_DIR / "ui" / "styles_dark.qss"), "app/ui"),
    (str(APP_DIR / "ui" / "icons"), "app/ui/icons"),
    (str(APP_DIR / "config"), "app/config"),
    (str(APP_DIR / "data"), "app/data"),
]

# Fichiers cachés (imports dynamiques)
hidden_imports = [
    "PySide6.QtSvg",
    "PySide6.QtSvgWidgets",
    "reportlab",
    "reportlab.lib",
    "reportlab.platypus",
    "reportlab.graphics",
    "openpyxl",
]

a = Analysis(
    [str(APP_DIR / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter", "unittest", "test", "xmlrpc",
        "pydoc", "doctest", "lib2to3",
    ],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="InventaireAV",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,              # UPX non recommandé sur macOS
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,    # macOS : support glisser-déposer
    target_arch=None,       # Compile pour l'architecture courante
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="InventaireAV",
)

app = BUNDLE(
    coll,
    name="Inventaire AV.app",
    icon=None,              # Sera remplacé par l'icône .icns si disponible
    bundle_identifier="com.inventaireav.app",
    info_plist={
        "CFBundleDisplayName": "Inventaire AV",
        "CFBundleShortVersionString": "2.0.0",
        "CFBundleVersion": "2.0.0",
        "CFBundleName": "Inventaire AV",
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": False,  # Supporte le dark mode macOS
        "CFBundleDocumentTypes": [],
        "LSMinimumSystemVersion": "10.15.0",
        "NSHumanReadableCopyright": "© 2024–2026 Inventaire AV",
    },
)
