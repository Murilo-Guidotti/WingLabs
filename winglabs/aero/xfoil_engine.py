# ============================================================
# WingLabs — Motor de Análise XFOIL 2D e Exportadores
# ============================================================

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

try:
    import svgwrite
    _HAS_SVGWRITE = True
except ImportError:
    _HAS_SVGWRITE = False

from winglabs.aero import script_sender as sender
from winglabs.core import environment as env
from winglabs.core import naca as nc
from winglabs.paths import XFOIL_PATH


def nacaGenerator(code: str, n_points: int) -> tuple[np.ndarray, np.ndarray]:
    return nc.generator(code, n_points)


def _escreve_dat(x: np.ndarray, y: np.ndarray, nome: str, caminho: str):
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(f"{nome}\n")
        for xi, yi in zip(x, y):
            f.write(f"{xi:.6f}  {yi:.6f}\n")


def send_script(
    dat_path: str,
    polar_path: str,
    re: float,
    mach: float,
    alpha_start: float,
    alpha_end: float,
    alpha_step: float,
    script_path: str,
    n_panels: int,
    n_iter: int,
):
    sender.sendScript(
        dat_path, polar_path, re, mach, alpha_start,
        alpha_end, alpha_step, script_path, n_panels, n_iter
    )


def _parseia_polar(polar_path: str) -> list[dict] | None:
    if not os.path.exists(polar_path):
        return None

    resultados = []
    lendo = False

    with open(polar_path, "r", encoding="utf-8", errors="ignore") as f:
        for linha in f:
            if "alpha" in linha and "CL" in linha:
                lendo = True
                continue
            if lendo:
                partes = linha.split()
                if len(partes) < 5:
                    continue
                try:
                    resultados.append({
                        "alpha": float(partes[0]),
                        "cl":    float(partes[1]),
                        "cd":    float(partes[2]),
                        "cm":    float(partes[3]),
                    })
                except ValueError:
                    continue

    return resultados if resultados else None


def select_best_polar_point(
    resultados: list[dict],
    cond: env.FlightConditions,
    cfg: dict | None = None,
) -> dict | None:
    """
    Seleciona o melhor ponto da polar conforme o modo de busca:
      - 'target_cl': |CL - target_cl| <= cl_tolerance, maximizando CL/CD.
      - 'payload':   CL >= required_cl (qualquer CL capaz de sustentar a carga),
                     maximizando CL/CD.
    """
    if cfg is None:
        cfg = {}

    search_mode = cfg.get("search_mode", "target_cl")
    if search_mode == "payload":
        req_cl = float(cfg.get("required_cl", cond.target_cl))
        validos = [r for r in resultados if r["cd"] > 0 and r["cl"] >= req_cl]
    else:
        tol = float(cfg.get("cl_tolerance", 0.01))
        validos = [
            r for r in resultados
            if r["cd"] > 0 and abs(r["cl"] - cond.target_cl) <= tol
        ]

    if not validos:
        return None

    melhor = max(validos, key=lambda r: r["cl"] / r["cd"])
    out = {
        "alpha_opt":  melhor["alpha"],
        "cl":         melhor["cl"],
        "cd":         melhor["cd"],
        "cm":         melhor["cm"],
        "efficiency": melhor["cl"] / melhor["cd"],
    }

    wing_area = cfg.get("wing_area_m2")
    if wing_area is not None and wing_area > 0:
        lift_n = 0.5 * cond.rho * (cond.velocity ** 2) * float(wing_area) * melhor["cl"]
        out["lift_n"] = lift_n
        out["lift_kg"] = lift_n / env.GRAVITY
    if search_mode == "payload":
        out["required_cl"] = float(cfg.get("required_cl", cond.target_cl))

    return out


def analyzeWithXfoil(
    x: np.ndarray,
    y: np.ndarray,
    cond: env.FlightConditions,
    nome: str = "perfil",
    cfg: dict | None = None,
) -> dict | None:
    if cfg is None:
        cfg = {}

    alpha_start = cfg.get("alpha_start", 0.0)
    alpha_end   = cfg.get("alpha_end",   0.0)
    alpha_step  = cfg.get("alpha_step",  0.5)
    n_panels    = cfg.get("n_panels",    240)
    n_ITER      = cfg.get("n_ITER", cfg.get("n_iterations", 100))

    with tempfile.TemporaryDirectory() as tmpdir:
        dat_path    = os.path.join(tmpdir, "perfil.dat")
        script_path = os.path.join(tmpdir, "script.in")
        polar_path  = os.path.join(tmpdir, "polar.txt")

        _escreve_dat(x, y, nome, dat_path)
        send_script(
            dat_path, polar_path, cond.reynolds, cond.mach,
            alpha_start, alpha_end, alpha_step, script_path, n_panels, n_ITER
        )

        script_content = Path(script_path).read_text(encoding="utf-8")
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0

        try:
            subprocess.run(
                [str(XFOIL_PATH)],
                input=script_content,
                text=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=45,
                cwd=tmpdir,
                creationflags=creation_flags,
            )
        except subprocess.TimeoutExpired:
            return None
        except FileNotFoundError:
            raise FileNotFoundError(
                f"xfoil.exe não encontrado em: {XFOIL_PATH}\n"
                "Coloque o xfoil.exe na pasta raiz do projeto."
            )

        resultados = _parseia_polar(polar_path)
        if not resultados:
            return None

        return select_best_polar_point(resultados, cond, cfg)


# ============================================================
# EXPORTS: SVG, DAT, JSON E PLOT (API OO THREAD-SAFE)
# ============================================================

def export_svg(x: np.ndarray, y: np.ndarray, code: str, output_dir: Path) -> Path:
    W, H    = 1920, 1080
    padding = 40

    x_svg = x * (W - 2 * padding) + padding
    y_svg = -y * (W - 2 * padding) + H / 2

    path_d = [f"M {x_svg[0]:.3f} {y_svg[0]:.3f}"]
    for i in range(1, len(x_svg)):
        cp1x = x_svg[i - 1] + (x_svg[i] - x_svg[i - 1]) / 3
        cp1y = y_svg[i - 1] + (y_svg[i] - y_svg[i - 1]) / 3
        cp2x = x_svg[i - 1] + 2 * (x_svg[i] - x_svg[i - 1]) / 3
        cp2y = y_svg[i - 1] + 2 * (y_svg[i] - y_svg[i - 1]) / 3
        path_d.append(
            f"C {cp1x:.2f} {cp1y:.2f} {cp2x:.2f} {cp2y:.2f} "
            f"{x_svg[i]:.2f} {y_svg[i]:.2f}"
        )
    path_d.append("Z")
    d_str = " ".join(path_d)

    out_path = output_dir if output_dir.suffix.lower() == ".svg" else output_dir / f"naca_{code}.svg"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if _HAS_SVGWRITE:
        dwg = svgwrite.Drawing(
            filename=str(out_path),
            size=(f"{W}px", f"{H}px"),
            viewBox=f"0 0 {W} {H}"
        )
        dwg.add(dwg.rect(insert=(0, 0), size=(W, H), fill="white"))
        dwg.add(dwg.path(d=d_str, fill="#E8F4FD", stroke="#185FA5", stroke_width=1.5))
        dwg.add(dwg.text(
            f"NACA {code}", insert=(padding, 25),
            font_size="14px", font_family="sans-serif", fill="#333"
        ))
        dwg.save()
    else:
        svg_xml = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}px" height="{H}px" viewBox="0 0 {W} {H}">\n'
            f'  <rect x="0" y="0" width="{W}" height="{H}" fill="white"/>\n'
            f'  <path d="{d_str}" fill="#E8F4FD" stroke="#185FA5" stroke_width="1.5"/>\n'
            f'  <text x="{padding}" y="25" font-size="14px" font-family="sans-serif" fill="#333">NACA {code}</text>\n'
            f'</svg>\n'
        )
        out_path.write_text(svg_xml, encoding="utf-8")

    return out_path


def export_dat(x: np.ndarray, y: np.ndarray, code: str, output_dir: Path) -> Path:
    dat_path = output_dir if output_dir.suffix.lower() == ".dat" else output_dir / f"naca_{code}.dat"
    dat_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dat_path, "w", encoding="utf-8") as f:
        f.write(f"NACA {code}\n")
        for xi, yi in zip(x, y):
            f.write(f" {xi:.6f}  {yi:.6f}\n")
    return dat_path


def export_json(
    code: str,
    result: dict,
    cond: env.FlightConditions,
    dat_path: Path,
    output_dir: Path,
    extra_cfg: dict | None = None,
) -> Path:
    aero = {
        "alpha_opt":  result["alpha_opt"],
        "cl":         result["cl"],
        "cd":         result["cd"],
        "cm":         result["cm"],
        "efficiency": result["efficiency"],
    }
    if "lift_n" in result:
        aero["lift_n"] = result["lift_n"]
        aero["lift_kg"] = result["lift_kg"]
    if "required_cl" in result:
        aero["required_cl"] = result["required_cl"]

    payload = {
        "naca_code": code,
        "dat_file":  dat_path.name,
        "aerodynamics": aero,
        "flight": {
            "altitude":   cond.altitude,
            "velocity":   cond.velocity,
            "reynolds":   cond.reynolds,
            "mach":       cond.mach,
            "rho":        cond.rho,
            "mu":         cond.mi,
            "chord_size": cond.chord_size,
            "target_cl":  cond.target_cl,
        },
    }
    if extra_cfg:
        payload["mission"] = {
            "search_mode":  extra_cfg.get("search_mode", "target_cl"),
            "payload_kg":   extra_cfg.get("payload_kg"),
            "wing_area_m2": extra_cfg.get("wing_area_m2"),
        }

    json_path = output_dir if output_dir.suffix.lower() == ".json" else output_dir / f"naca_{code}_result.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return json_path


def export_plot(
    x: np.ndarray,
    y: np.ndarray,
    code: str,
    result: dict,
    output_dir: Path,
) -> Path:
    """Gera imagem PNG do perfil usando API OO do Matplotlib (thread-safe)."""
    fig = Figure(figsize=(10, 4), dpi=150)
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    ax.plot(x, y, "b-", linewidth=1.5, label=f"NACA {code}")
    ax.fill(x, y, alpha=0.15, color="blue")
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)
    ax.set_xlabel("x/c")
    ax.set_ylabel("y/c")
    ax.set_title(
        f"NACA {code}  |  CL={result['cl']:.3f}  "
        f"CD={result['cd']:.4f}  "
        f"CL/CD={result['efficiency']:.1f}  "
        f"α={result['alpha_opt']:.1f}°"
    )
    ax.legend()
    fig.tight_layout()

    plot_path = output_dir if output_dir.suffix.lower() == ".png" else output_dir / f"naca_{code}_perfil.png"
    plot_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(plot_path, dpi=150)
    return plot_path
