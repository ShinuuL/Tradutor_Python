# -*- coding: utf-8 -*-
"""Testes do script de build (build.py).

Cobertura:
- build.py --help nao levanta excecao e retorna exit code 0;
- build.py --target invalido retorna exit code != 0.

Somente subprocess: nao executa pyinstaller, somente valida o parser.
"""
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILD_DIR = HERE.parent / "build"
BUILD_PY = BUILD_DIR / "build.py"


class TestBuildHelp(unittest.TestCase):
    """build.py --help deve funcionar sem excecao."""

    def test_help_exit_zero(self):
        resultado = subprocess.run(
            [sys.executable, str(BUILD_PY), "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(
            resultado.returncode,
            0,
            f"--help deveria retornar 0, obteve {resultado.returncode}\n"
            f"stdout: {resultado.stdout[:500]}\n"
            f"stderr: {resultado.stderr[:500]}",
        )
        # Deve conter texto de uso do argparse
        self.assertIn("--target", resultado.stdout)


class TestBuildTargetInvalido(unittest.TestCase):
    """build.py com target invalido deve retornar exit code != 0."""

    def test_target_invalido_exit_nao_zero(self):
        resultado = subprocess.run(
            [
                sys.executable,
                str(BUILD_PY),
                "--target",
                "target_que_nao_existe",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertNotEqual(
            resultado.returncode,
            0,
            f"--target invalido deveria retornar != 0, obteve {resultado.returncode}",
        )


if __name__ == "__main__":
    unittest.main()
