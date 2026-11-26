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
    "WingSection",
    "Wing3DParams",
    "generate_wing_sections",
    "write_3d_config",
    "run_3d_generator",
    "build_wing_preview_mesh",
]


@dataclass
class WingSection:
    z_mm: float
    chord_mm: float
    sweep_x_mm: float = 0.0
    dihedral_y_mm: float = 0.0
    twist_deg: float = 0.0
    thickness_scale: float = 1.0

    def to_dict(self) -> dict[str, float]:
        return {
            "z_mm": float(self.z_mm),
            "chord_mm": float(self.chord_mm),
            "sweep_x_mm": float(self.sweep_x_mm),
            "dihedral_y_mm": float(self.dihedral_y_mm),
            "twist_deg": float(self.twist_deg),
            "thickness_scale": float(self.thickness_scale),
        }


@dataclass
class Wing3DParams:
    span_mm: float = 1000.0
    root_chord_mm: float = 500.0
    tip_chord_mm: float = 500.0
    tip_twist_deg: float = 0.0
    wing_sweep_deg: float = 0.0
    wing_dihedral_deg: float = 0.0
    tip_chanfer_deg: float = 0.0
    target_section_size_mm: float = 50.0
    voxel_size_mm: float = 2.0
    shell_thickness_mm: float = 0.0
    export_voxel_mesh: bool = False
    elliptical_transition: bool = True
    rounded_tip_cap: bool = False
    tip_cap_radius_mm: float = 60.0
    custom_sections: list[WingSection] | None = None


def generate_wing_sections(params: Wing3DParams, n_sections: int | None = None) -> list[WingSection]:
    """Gera a lista de seções editáveis da asa a partir dos parâmetros globais."""
    span = max(10.0, float(params.span_mm))
    c_root = max(10.0, float(params.root_chord_mm))
    c_tip = max(5.0, float(params.tip_chord_mm))
    sec_size = max(5.0, float(params.target_section_size_mm))

    if n_sections is None:
        n_sec = max(5, min(100, int(round(span / sec_size))))
    else:
        n_sec = max(2, int(n_sections))

    sweep_tan = math.tan(math.radians(float(params.wing_sweep_deg)))
    dihedral_tan = math.tan(math.radians(float(params.wing_dihedral_deg)))
    twist_total = float(params.tip_twist_deg)

    sections: list[WingSection] = []
    e_ellip = 0.80
    s_root = math.sqrt(1.0 - e_ellip * e_ellip)  # 0.60
    for i in range(n_sec + 1):
        u = i / n_sec
        if params.elliptical_transition:
            t = 0.5 * u + 0.5 * math.sin(0.5 * math.pi * u)
            z_val = t * span
            ellip_factor = (math.sqrt(1.0 - (e_ellip * t) ** 2) - s_root) / (1.0 - s_root)
            chord_val = c_tip + (c_root - c_tip) * ellip_factor
            s_twist = 0.4 * t + 0.6 * (t * t * (3.0 - 2.0 * t))
            twist_val = twist_total * s_twist
            sweep_x_val = sweep_tan * z_val
            dihedral_y_val = dihedral_tan * z_val
        else:
            t = u
            z_val = t * span
            chord_val = c_root + (c_tip - c_root) * t
            twist_val = twist_total * t
            sweep_x_val = sweep_tan * z_val
            dihedral_y_val = dihedral_tan * z_val

        sections.append(
            WingSection(
                z_mm=z_val,
                chord_mm=chord_val,
                sweep_x_mm=sweep_x_val,
                dihedral_y_mm=dihedral_y_val,
                twist_deg=twist_val,
                thickness_scale=1.0,
            )
        )
    return sections


def write_3d_config(
    dat_path: Path,
    output_stl_path: Path,
    params: Wing3DParams,
    config_path: Path,
) -> Path:
    """Salva o JSON de configuração lido pelo Módulo 2 (C# / PicoGK)."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    output_stl_path.parent.mkdir(parents=True, exist_ok=True)

    payload: dict[str, object] = {
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
        "shell_thickness_mm": max(0.0, float(params.shell_thickness_mm)),
        "export_voxel_mesh": bool(params.export_voxel_mesh),
        "elliptical_transition": bool(params.elliptical_transition),
        "rounded_tip_cap": bool(params.rounded_tip_cap),
        "tip_cap_radius_mm": max(0.0, float(params.tip_cap_radius_mm)),
    }
    if params.custom_sections and len(params.custom_sections) >= 2:
        payload["custom_sections"] = [s.to_dict() for s in params.custom_sections]

    config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return config_path


def _find_3d_executable() -> Path | None:
    """Procura executável já compilado do Módulo 2 (priorizando Release e build mais recente)."""
    bin_dir = GENERATOR_3D_DIR / "bin"
    if not bin_dir.exists():
        return None
    for name in ("winglabs.exe", "winglabs"):
        matches = [p for p in bin_dir.rglob(name) if p.is_file()]
        if matches:
            matches.sort(
                key=lambda p: ("release" in str(p).lower(), p.stat().st_mtime),
                reverse=True,
            )
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

    if exe_path is not None:
        cmd = [str(exe_path), "--config", str(config_path)]
        cwd = str(exe_path.parent)
        _log(f"[Pipeline] Iniciando Módulo 2 via {exe_path.name}...")
    elif dotnet_bin and CSPROJ_3D_PATH.exists():
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
    y_mirror = y_p[:, ::-1]
    y_camber = 0.5 * (y_p + y_mirror)
    y_thick = y_p - y_camber

    n_sec = max(4, int(n_sections))
    c_root = max(10.0, float(params.root_chord_mm))

    # Reutiliza a geração de seções unificada (evitando duplicar a matemática elíptica/linear)
    if params.custom_sections and len(params.custom_sections) >= 2:
        sections_list = sorted(params.custom_sections, key=lambda s: s.z_mm)
    else:
        sections_list = generate_wing_sections(params, n_sections=n_sec)

    z_pos = np.array([s.z_mm for s in sections_list], dtype=float)[:, None]
    chord = np.array([max(2.0, s.chord_mm) for s in sections_list], dtype=float)[:, None]
    sweep_x = np.array([s.sweep_x_mm for s in sections_list], dtype=float)[:, None]
    dihedral_y = np.array([s.dihedral_y_mm for s in sections_list], dtype=float)[:, None]
    theta = np.radians(np.array([s.twist_deg for s in sections_list], dtype=float))[:, None]
    thick_scale = np.array([max(0.05, s.thickness_scale) for s in sections_list], dtype=float)[:, None]

    # Ponta cilíndrica / elíptica 3D (fechamento curvo contínuo tipo meio-cilindro no final da asa)
    if params.rounded_tip_cap and float(params.tip_cap_radius_mm) > 0.5 and len(z_pos) >= 2:
        n_cap = 6
        cap_r = float(params.tip_cap_radius_mm)
        phi = np.linspace(0.5 * np.pi / n_cap, 0.5 * np.pi, n_cap)[:, None]
        sin_p = np.sin(phi)
        cos_p = np.cos(phi)

        dz_step = max(1e-3, float(z_pos[-1, 0] - z_pos[-2, 0]))
        dxdz = float(sweep_x[-1, 0] - sweep_x[-2, 0]) / dz_step
        dydz = float(dihedral_y[-1, 0] - dihedral_y[-2, 0]) / dz_step

        dz_cap = cap_r * sin_p
        z_cap = z_pos[-1:, :] + dz_cap
        chord_cap = np.repeat(chord[-1:, :], n_cap, axis=0)
        sweep_cap = sweep_x[-1:, :] + dxdz * dz_cap
        dihedral_cap = dihedral_y[-1:, :] + dydz * dz_cap
        theta_cap = np.repeat(theta[-1:, :], n_cap, axis=0)
        thick_cap = thick_scale[-1:, :] * np.maximum(0.01, cos_p)

        z_pos = np.vstack([z_pos, z_cap])
        chord = np.vstack([chord, chord_cap])
        sweep_x = np.vstack([sweep_x, sweep_cap])
        dihedral_y = np.vstack([dihedral_y, dihedral_cap])
        theta = np.vstack([theta, theta_cap])
        thick_scale = np.vstack([thick_scale, thick_cap])

    # Rotação de torção aplicada em torno da linha de 25% da corda (centro aerodinâmico c/4)
    pivot_frac = 0.25
    pivot_x = pivot_frac * c_root
    y_scaled = y_camber + y_thick * thick_scale
    lx = (x_p - pivot_frac) * chord
    ly = y_scaled * chord

    cos_t = np.cos(theta)
    sin_t = np.sin(theta)

    X_grid = (c_root / 2.0) + sweep_x + pivot_x + (lx * cos_t - ly * sin_t)
    Y_grid = dihedral_y + (lx * sin_t + ly * cos_t)
    Z_grid = np.broadcast_to(z_pos, X_grid.shape).copy()

    return X_grid, Y_grid, Z_grid
