from __future__ import annotations

import sys
from pathlib import Path


def resolve_base_dir() -> Path:
    """Retorna o diretório raiz do projeto (ou _MEIPASS quando empacotado)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent.parent


def resolve_output_dir() -> Path:
    """Retorna o diretório padrão de saída (output/)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "output"
    return resolve_base_dir() / "output"


BASE_DIR = resolve_base_dir()
XFOIL_PATH = BASE_DIR / "xfoil.exe"
GENERATOR_3D_DIR = BASE_DIR / "3D Generator"
CSPROJ_3D_PATH = GENERATOR_3D_DIR / "winglabs.csproj"
DEFAULT_OUTPUT_DIR = resolve_output_dir()
