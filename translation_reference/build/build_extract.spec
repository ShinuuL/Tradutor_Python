# -*- mode: python ; coding: utf-8 -*-
# build_extract.spec - PyInstaller spec para o worker de varredura.

import os
from pathlib import Path

BLOCK_CIPHER = None

SPECDIR = os.path.dirname(os.path.abspath(SPEC))
PROJECT_ROOT = Path(SPECDIR).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "translation_reference" / "scripts"

a = Analysis(
    [str(SCRIPTS_DIR / "extract_non_english_text.py")],
    pathex=[str(SCRIPTS_DIR)],
    binaries=[],
    datas=[],
    hiddenimports=["argparse", "csv", "json", "os", "pathlib", "re"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=BLOCK_CIPHER,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=BLOCK_CIPHER)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="extract_non_english_text",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="extract_non_english_text",
)
