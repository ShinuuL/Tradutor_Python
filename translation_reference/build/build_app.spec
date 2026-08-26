# -*- mode: python ; coding: utf-8 -*-
# build_app.spec - PyInstaller spec para o APP GUI (TradutorDGames)
#
# Modo: onedir (diretorio, mais rapido e compativel com Tkinter)
# Entry point: translation_reference/app/text_scanner_app.py
# console: False (janela grafica)

import os
from pathlib import Path

BLOCK_CIPHER = None

# Caminhos relativos a este arquivo .spec
SPECDIR = os.path.dirname(os.path.abspath(SPEC))

# Caminhos absolutos para o projeto
PROJECT_ROOT = Path(SPECDIR).resolve().parents[1]  # TradutorDGames/
APP_DIR = PROJECT_ROOT / "translation_reference" / "app"
SCRIPTS_DIR = PROJECT_ROOT / "translation_reference" / "scripts"
LIB_DIR = SCRIPTS_DIR / "lib"

a = Analysis(
    [str(APP_DIR / "text_scanner_app.py")],
    pathex=[
        str(SCRIPTS_DIR),
        str(LIB_DIR),
    ],
    binaries=[],
    datas=[],
    hiddenimports=[
        # Tkinter (GUI)
        "tkinter",
        "tkinter.ttk",
        "tkinter.filedialog",
        "tkinter.messagebox",
        "tkinter.font",
        # Modulos top-level do lib/
        "appliers",
        "global_tm",
        "name_repair",
        "placeholders",
        "tm_db",
        "tm_store",
        "translation_engine",
        # Adapters
        "adapters",
        "adapters.godot",
        "adapters.kirikiri",
        "adapters.renpy",
        "adapters.rpgmaker_vxace",
        "adapters.scanner_integration",
        "adapters.tyrano",
        "adapters.wolfrpg",
        # Validators
        "validators",
        "validators.base",
        "validators.godot_val",
        "validators.renpy_val",
        "validators.rpgmaker",
        "validators.tyrano_val",
    ],
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
    name="TradutorDGames",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI, sem janela de console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon=None  # placeholder: adicionar caminho para .ico futuramente
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="TradutorDGames",
)
