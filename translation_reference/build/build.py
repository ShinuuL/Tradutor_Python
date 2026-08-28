# -*- coding: utf-8 -*-
"""Script de build unificado para o TradutorDGames.

Usa apenas stdlib do Python. Chama pyinstaller para gerar executaveis
Windows a partir dos arquivos .spec.

Uso:
    python translation_reference/build/build.py --target app
    python translation_reference/build/build.py --target cli
    python translation_reference/build/build.py --target all
    python translation_reference/build/build.py --help

Pre-requisitos: pyinstaller instalado (pip install pyinstaller).
Este script NAO instala o pyinstaller -- apenas verifica e usa.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


# --- Constantes -----------------------------------------------------------

BUILD_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BUILD_DIR.parents[1]
SPECS = {
    "app": BUILD_DIR / "build_app.spec",
    "extract": BUILD_DIR / "build_extract.spec",
    "cli": BUILD_DIR / "build_cli.spec",
}
TARGETS_VALIDOS = ("app", "cli", "all")


# --- Funcoes auxiliares ---------------------------------------------------

def _log(msg):
    """Log simples para stdout."""
    print(f"[build] {msg}")


def _log_erro(msg):
    """Log de erro para stderr."""
    print(f"[build] ERRO: {msg}", file=sys.stderr)


def _limpar_diretorios():
    """Remove diretorios temporarios de build anterior."""
    for nome in ("build", "dist"):
        alvo = PROJECT_ROOT / nome
        if alvo.exists():
            _log(f"removendo {alvo} ...")
            shutil.rmtree(alvo)


def _verificar_pyinstaller():
    """Verifica se o pyinstaller esta disponivel. Retorna True ou aborta."""
    try:
        import PyInstaller  # noqa: F401
        _log(f"pyinstaller {PyInstaller.__version__} encontrado")
        return True
    except ImportError:
        _log_erro("pyinstaller nao encontrado. Instale com: pip install pyinstaller")
        return False


def _executar_build(target):
    """Executa o pyinstaller para um alvo especifico."""
    spec = SPECS[target]
    if not spec.exists():
        _log_erro(f"arquivo .spec nao encontrado: {spec}")
        return False

    _log(f"construindo {target} ...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        str(spec),
    ]

    _log(f"executando: {' '.join(cmd)}")
    resultado = subprocess.run(cmd, cwd=str(PROJECT_ROOT))

    if resultado.returncode != 0:
        _log_erro(f"pyinstaller falhou para {target} (codigo {resultado.returncode})")
        return False

    _log(f"build de {target} concluido com sucesso")
    return True


# --- Ponto de entrada principal -------------------------------------------

def main(argv=None):
    """Ponto de entrada do script de build."""
    parser = argparse.ArgumentParser(
        description="Script de build do TradutorDGames",
        epilog=(
            "Exemplos:\n"
            "  python translation_reference/build/build.py --target app\n"
            "  python translation_reference/build/build.py --target cli\n"
            "  python translation_reference/build/build.py --target all\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--target",
        choices=TARGETS_VALIDOS,
        required=True,
        help="Alvo a construir: app (GUI + workers), cli (worker de traducao) ou all (GUI + workers)",
    )

    args = parser.parse_args(argv)

    # Verificar pyinstaller
    if not _verificar_pyinstaller():
        sys.exit(1)

    # Definir lista de alvos
    if args.target in {"app", "all"}:
        # A GUI congelada delega para os workers irmaos em dist/.  Sempre
        # construa a distribuicao completa em uma unica limpeza.
        alvos = ["app", "extract", "cli"]
    else:
        alvos = [args.target]

    # Limpar diretorios de build anteriores (uma vez so)
    _limpar_diretorios()

    # Executar builds (nao limpa entre targets quando 'all')
    falhas = []
    for i, target in enumerate(alvos):
        if i > 0:
            # Nao limpar entre targets: manter dist/ do build anterior
            pass
        if not _executar_build(target):
            falhas.append(target)

    # Relatorio final
    print()
    _log("=" * 60)
    if falhas:
        _log_erro(f"falha ao construir: {', '.join(falhas)}")
        sys.exit(1)
    else:
        _log("todos os targets construidos com sucesso")
        _log(f"executaveis disponiveis em: {PROJECT_ROOT / 'dist'}")
        sys.exit(0)


if __name__ == "__main__":
    main()
