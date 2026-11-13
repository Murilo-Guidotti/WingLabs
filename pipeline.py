from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import math
import shutil
import subprocess
from typing import Callable

import numpy as np


BASE_DIR = Path(__file__).resolve().parent
GENERATOR_3D_DIR = BASE_DIR / "3D Generator"
CSPROJ_3D_PATH = GENERATOR_3D_DIR / "winglabs.csproj"
DEFAULT_OUTPUT_DIR = BASE_DIR / "output"


@dataclass
class Wing3DParams:
    span_mm: float = 5000.0
    root_chord_mm: float = 1200.0
    tip_chord_mm: float = 700.0
    tip_twist_deg: float = -3.0
    wing_sweep_deg: float = 15.0
    wing_dihedral_deg: float = 2.0
    tip_chanfer_deg: float = 0.0
    target_section_size_mm: float = 250.0
    voxel_size_mm: float = 2.5


def write_3d_config(
    dat_path: Path,
    output_stl_path: Path,
    params: Wing3DParams,
    config_path: Path,
) -> Path:
    """Salva o JSON de configuração lido pelo Módulo 2 (C# / PicoGK)."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    output_stl_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "dat_file_path": str(dat_path.resolve()),
        "output_stl_path": str(output_stl_path.resolve()),
        "span_mm": float(params.span_mm),
        "root_chord_mm": float(params.root_chord_mm),
        "tip_chord_mm": float(params.tip_chord_mm),
        "tip_twist_deg": float(params.tip_twist_deg),
        "wing_sweep_deg": float(params.wing_sweep_deg),
        "wing_dihedral_deg": float(params.wing_dihedral_deg),
        "tip_chanfer_deg": float(params.tip_chanfer_deg),
        "target_section_size_mm": float(params.target_section_size_mm),
        "voxel_size_mm": float(params.voxel_size_mm),
    }
    config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return config_path


def _find_3d_executable() -> Path | None:
    """Procura executável já compilado do Módulo 2 para execução mais rápida."""
    bin_dir = GENERATOR_3D_DIR / "bin"
    if not bin_dir.exists():
        return None
    for name in ("winglabs.exe", "winglabs"):
        matches = list(bin_dir.rglob(name))
        if matches:
            return matches[0]
    return None


def run_3d_generator(
    dat_path: Path,
    output_stl_path: Path,
    params: Wing3DParams,
    log_callback: Callable[[str], None] | None = None,
    timeout_s: int = 180,
) -> tuple[bool, Path, str]:
    """
    Executa o Módulo 2 (C# / PicoGK) de forma autônoma a partir do .dat
    gerado pelo Módulo 1 e dos parâmetros 3D da asa.
    """
    def _log(msg: str):
        if log_callback:
            log_callback(msg)

    dat_path = Path(dat_path).resolve()
    output_stl_path = Path(output_stl_path).resolve()
    if not dat_path.exists():
        return False, output_stl_path, f"Arquivo .dat não encontrado: {dat_path}"

    config_path = output_stl_path.parent / "wing3d_config.json"
    write_3d_config(dat_path, output_stl_path, params, config_path)
    _log(f"[Pipeline] Config 3D salva em: {config_path.name}")

    exe_path = _find_3d_executable()
    dotnet_bin = shutil.which("dotnet")

    if dotnet_bin and CSPROJ_3D_PATH.exists():
        cmd = [
            dotnet_bin,
            "run",
            "--project",
            str(CSPROJ_3D_PATH),
            "--",
            "--config",
            str(config_path),
        ]
        cwd = str(GENERATOR_3D_DIR)
        _log("[Pipeline] Iniciando Módulo 2 via dotnet run...")
    elif exe_path is not None:
        cmd = [str(exe_path), "--config", str(config_path)]
        cwd = str(exe_path.parent)
        _log(f"[Pipeline] Iniciando Módulo 2 via {exe_path.name}...")
    else:
        return (
            False,
            output_stl_path,
            "SDK .NET (dotnet) ou executável do Módulo 2 não encontrado. "
            f"Configuração salva em {config_path}.",
        )

    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout_s,
        )
        if proc.stdout:
            for line in proc.stdout.splitlines():
                if line.strip():
                    _log(f"[3D] {line}")

        if proc.returncode != 0:
            return (
                False,
                output_stl_path,
                f"Módulo 2 retornou código {proc.returncode}.",
            )

        if not output_stl_path.exists():
            return (
                False,
                output_stl_path,
                "Módulo 2 finalizou sem gerar o arquivo STL esperado.",
            )

        _log(f"[Pipeline] STL gerado com sucesso: {output_stl_path.name}")
        return True, output_stl_path, f"STL gerado em: {output_stl_path}"

    except subprocess.TimeoutExpired:
        return False, output_stl_path, "Tempo limite excedido ao executar o Módulo 2."
    except Exception as exc:
        return False, output_stl_path, f"Erro ao executar o Módulo 2: {exc}"


def build_wing_preview_mesh(
    x_airfoil: np.ndarray,
    y_airfoil: np.ndarray,
    params: Wing3DParams,
    n_sections: int = 16,
    n_profile_pts: int = 80,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Constrói a malha 3D (X, Y, Z) da asa em tempo real usando a mesma
    geometria de lofting de planeWings.cs para visualização imediata na UI.
    Retorna arrays 2D (n_sections+1, n_pts) prontos para plot_surface.
    """
    idx = np.linspace(0, len(x_airfoil) - 1, min(n_profile_pts, len(x_airfoil)), dtype=int)
    x_p = x_airfoil[idx]
    y_p = y_airfoil[idx]

    n_sec = max(4, int(n_sections))
    span = max(10.0, float(params.span_mm))
    c_root = max(10.0, float(params.root_chord_mm))
    c_tip = max(10.0, float(params.tip_chord_mm))
    twist_rad = math.radians(float(params.tip_twist_deg))
    sweep_tan = math.tan(math.radians(float(params.wing_sweep_deg)))
    dihedral_tan = math.tan(math.radians(float(params.wing_dihedral_deg)))

    X_grid = np.zeros((n_sec + 1, len(x_p)))
    Y_grid = np.zeros((n_sec + 1, len(x_p)))
    Z_grid = np.zeros((n_sec + 1, len(x_p)))

    for i in range(n_sec + 1):
        t = i / n_sec
        z_pos = t * span
        chord = c_root + (c_tip - c_root) * t
        theta = twist_rad * t
        sweep_x = sweep_tan * z_pos
        dihedral_y = dihedral_tan * z_pos

        # Coordenadas locais escaladas pela corda da seção
        lx = x_p * chord
        ly = y_p * chord

        # Rotação de torção (washout) no plano XY + translação
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)
        wx = (c_root / 2.0) + sweep_x + (lx * cos_t - ly * sin_t)
        wy = dihedral_y + (lx * sin_t + ly * cos_t)

        X_grid[i, :] = wx
        Y_grid[i, :] = wy
        Z_grid[i, :] = z_pos

    return X_grid, Y_grid, Z_grid
