from __future__ import annotations

import json
import math
import shutil
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

from winglabs.paths import BASE_DIR, CSPROJ_3D_PATH, DEFAULT_OUTPUT_DIR, GENERATOR_3D_DIR

__all__ = [
    "BASE_DIR",
    "GENERATOR_3D_DIR",
    "CSPROJ_3D_PATH",
    "DEFAULT_OUTPUT_DIR",
    "Wing3DParams",
    "write_3d_config",
    "run_3d_generator",
    "build_wing_preview_mesh",
]


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
    gerado pelo Módulo 1 e dos parâmetros 3D da asa, transmitindo logs em tempo real.
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

    timed_out = False

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        def _kill_on_timeout():
            nonlocal timed_out
            timed_out = True
            try:
                proc.kill()
            except Exception:
                pass

        timer = threading.Timer(timeout_s, _kill_on_timeout)
        timer.start()
        try:
            if proc.stdout is not None:
                for line in proc.stdout:
                    stripped = line.strip()
                    if stripped:
                        _log(f"[3D] {stripped}")
            proc.wait()
        finally:
            timer.cancel()

        if timed_out:
            return False, output_stl_path, "Tempo limite excedido ao executar o Módulo 2."

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
    Constrói a malha 3D (X, Y, Z) da asa em tempo real de forma 100% vetorizada
    usando broadcasting NumPy para visualização imediata na UI.
    Retorna arrays 2D (n_sections+1, n_pts) prontos para plot_surface.
    """
    idx = np.linspace(0, len(x_airfoil) - 1, min(n_profile_pts, len(x_airfoil)), dtype=int)
    x_p = x_airfoil[idx][None, :]
    y_p = y_airfoil[idx][None, :]

    n_sec = max(4, int(n_sections))
    span = max(10.0, float(params.span_mm))
    c_root = max(10.0, float(params.root_chord_mm))
    c_tip = max(10.0, float(params.tip_chord_mm))
    twist_rad = math.radians(float(params.tip_twist_deg))
    sweep_tan = math.tan(math.radians(float(params.wing_sweep_deg)))
    dihedral_tan = math.tan(math.radians(float(params.wing_dihedral_deg)))

    t = np.linspace(0.0, 1.0, n_sec + 1)[:, None]
    z_pos = t * span
    chord = c_root + (c_tip - c_root) * t
    theta = twist_rad * t
    sweep_x = sweep_tan * z_pos
    dihedral_y = dihedral_tan * z_pos

    lx = x_p * chord
    ly = y_p * chord

    cos_t = np.cos(theta)
    sin_t = np.sin(theta)

    X_grid = (c_root / 2.0) + sweep_x + (lx * cos_t - ly * sin_t)
    Y_grid = dihedral_y + (lx * sin_t + ly * cos_t)
    Z_grid = np.broadcast_to(z_pos, X_grid.shape).copy()

    return X_grid, Y_grid, Z_grid
