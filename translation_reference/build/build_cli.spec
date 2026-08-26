# -*- mode: python ; coding: utf-8 -*-
# build_cli.spec - PyInstaller spec para o CLI worker (translate_game_text)
#
# Modo: onedir (diretorio)
# Entry point: translation_reference/scripts/translate_game_text.py
# console: True (linha de comando)
#
# O translate_game_text.py adiciona lib/ ao sys.path via __file__.
# Para o PyInstaller encontrar os imports de lib/, incluimos todos os
# modulos como hiddenimports E copiamos a pasta lib/ como dados.

import os
from pathlib import Path

BLOCK_CIPHER = None

# Caminhos relativos a este arquivo .spec
SPECDIR = os.path.dirname(os.path.abspath(SPEC))

# Caminhos absolutos para o projeto
PROJECT_ROOT = Path(SPECDIR).resolve().parents[1]  # TradutorDGames/
SCRIPTS_DIR = PROJECT_ROOT / "translation_reference" / "scripts"
LIB_DIR = SCRIPTS_DIR / "lib"

a = Analysis(
    [str(SCRIPTS_DIR / "translate_game_text.py")],
    pathex=[
        str(SCRIPTS_DIR),
        str(LIB_DIR),
    ],
    binaries=[],
    datas=[
        # Copia a pasta lib/ inteira para ao lado do .exe
        # Assim o __file__-based sys.path do translate_game_text funciona
        (str(LIB_DIR), "lib"),
    ],
    hiddenimports=[
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
    name="translate_game_text",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # CLI, janela de console
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
    name="translate_game_text",
)
