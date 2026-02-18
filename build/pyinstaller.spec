# -*- mode: python ; coding: utf-8 -*-
"""
pyinstaller.spec — Configuration PyInstaller pour Inventaire AV.

Usage :
    cd inventaire-app
    pyinstaller build/pyinstaller.spec
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
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="InventaireAV",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # Pas de console Windows
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(APP_DIR / "ui" / "icons" / "logo.svg"),
)
