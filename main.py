# ============================================================
# NACA Wing Profile Generator
# Software 1 de 2 — Gerador de Perfil 2D + Pipeline Autônoma 3D
# TCC — Gerador de Asa NACA (WingLabs)
# ============================================================

from __future__ import annotations

import subprocess
import tempfile
import os
import json
import time
import threading
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

try:
    import svgwrite
    _HAS_SVGWRITE = True
except ImportError:
    _HAS_SVGWRITE = False

import ScriptSender as sender
import NacaGenerator as nc
import optimizer
import Enviroment
import pipeline

# ============================================================
# CONFIGURAÇÃO
# ============================================================

XFOIL_PATH = Path(__file__).parent / "xfoil.exe"
print_lock = threading.Lock()


# ============================================================
# SEÇÃO 1 — GERAÇÃO DO PERFIL NACA 4 DÍGITOS
# ============================================================

def nacaGenerator(code: str, n_points: int) -> tuple[np.ndarray, np.ndarray]:
    return nc.generator(code, n_points)


# ============================================================
# SEÇÃO 2 — ANÁLISE AERODINÂMICA COM XFOIL VIA SUBPROCESS
# ============================================================

def _escreve_dat(x: np.ndarray, y: np.ndarray, nome: str, caminho: str):
    with open(caminho, "w") as f:
        f.write(f"{nome}\n")
        for xi, yi in zip(x, y):
            f.write(f"{xi:.6f}  {yi:.6f}\n")


def send_script(dat_path: str, polar_path: str, re: float,
                mach: float, alpha_start: float, alpha_end: float,
                alpha_step: float, script_path: str, n_panels: int, n_iter: int):
    sender.sendScript(dat_path, polar_path, re, mach, alpha_start,
                      alpha_end, alpha_step, script_path, n_panels, n_iter)


def _parseia_polar(polar_path: str) -> list[dict] | None:
    if not os.path.exists(polar_path):
        return None

    resultados = []
    lendo = False

    with open(polar_path, "r") as f:
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
    cond: Enviroment.FlightConditions,
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
        out["lift_kg"] = lift_n / Enviroment.GRAVITY
    if search_mode == "payload":
        out["required_cl"] = float(cfg.get("required_cl", cond.target_cl))

    return out


def analyzeWithXfoil(x: np.ndarray, y: np.ndarray, cond: Enviroment.FlightConditions,
                     nome: str = "perfil", cfg: dict | None = None) -> dict | None:
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

        try:
            subprocess.run(
                f'"{XFOIL_PATH}" < "{script_path}"',
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=45
            )
        except subprocess.TimeoutExpired:
            return None
        except FileNotFoundError:
            raise FileNotFoundError(
                f"xfoil.exe não encontrado em: {XFOIL_PATH}\n"
                "Coloque o xfoil.exe na mesma pasta do script."
            )

        resultados = _parseia_polar(polar_path)
        if not resultados:
            return None

        return select_best_polar_point(resultados, cond, cfg)


# ============================================================
# SEÇÃO 5 — EXPORTS: SVG, DAT, JSON E PLOT
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

    out_path = output_dir / f"naca_{code}.svg"
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
            f'  <path d="{d_str}" fill="#E8F4FD" stroke="#185FA5" stroke-width="1.5"/>\n'
            f'  <text x="{padding}" y="25" font-size="14px" font-family="sans-serif" fill="#333">NACA {code}</text>\n'
            f'</svg>\n'
        )
        out_path.write_text(svg_xml, encoding="utf-8")

    return out_path


def export_dat(x: np.ndarray, y: np.ndarray, code: str, output_dir: Path) -> Path:
    dat_path = output_dir / f"naca_{code}.dat"
    with open(dat_path, "w") as f:
        f.write(f"NACA {code}\n")
        for xi, yi in zip(x, y):
            f.write(f" {xi:.6f}  {yi:.6f}\n")
    return dat_path


def export_json(code: str, result: dict, cond: Enviroment.FlightConditions,
                dat_path: Path, output_dir: Path, extra_cfg: dict | None = None) -> Path:
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

    json_path = output_dir / f"naca_{code}_result.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return json_path


def export_plot(x: np.ndarray, y: np.ndarray, code: str,
                result: dict, output_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(10, 4))
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
    plt.tight_layout()
    plot_path = output_dir / f"naca_{code}_perfil.png"
    plt.savefig(plot_path, dpi=150)
    plt.close()
    return plot_path


# ============================================================
# SEÇÃO 6 — ENTRADA DE PARÂMETROS PELO USUÁRIO (CLI)
# ============================================================

def input_float(prompt: str, default: float,
                minval: float | None, maxval: float | None) -> float:
    while True:
        try:
            entrada = input(f"{prompt} [{default}]: ").strip()
            valor = float(entrada) if entrada else default
            if minval is not None and valor < minval:
                print(f"    ! Valor mínimo: {minval}")
                continue
            if maxval is not None and valor > maxval:
                print(f"    ! Valor máximo: {maxval}")
                continue
            return valor
        except ValueError:
            print("    ! Digite um número válido.")


def input_int(prompt: str, default: int,
              minval: int | None, maxval: int | None) -> int:
    while True:
        try:
            entrada = input(f"{prompt} [{default}]: ").strip()
            valor = int(entrada) if entrada else default
            if minval is not None and valor < minval:
                print(f"    ! Valor mínimo: {minval}")
                continue
            if maxval is not None and valor > maxval:
                print(f"    ! Valor máximo: {maxval}")
                continue
            return valor
        except ValueError:
            print("    ! Digite um número inteiro válido.")


def coletar_parametros() -> tuple[Enviroment.FlightConditions, dict, pipeline.Wing3DParams]:
    print("\n" + "=" * 56)
    print("  Parâmetros de Voo")
    print("  (Enter = usar valor padrão)")
    print("=" * 56)

    altitude   = input_float("  Altitude (m)",     1500, 0, 12000)
    a_sound    = Enviroment.speed_of_sound(altitude)
    velocidade = input_float("  Velocidade (m/s)", 60,   1, a_sound)
    corda      = input_float("  Corda raiz (m)",   1.2,  0.1, 10)

    print("\n  Modo de seleção aerodinâmica:")
    print("    1 - CL alvo fixo")
    print("    2 - Peso da carga (kg) -> busca melhor CL >= CL_req")
    modo_op = input_int("  Escolha o modo (1 ou 2)", 2, 1, 2)
    search_mode = "payload" if modo_op == 2 else "target_cl"

    span_mm      = input_float("  Envergadura 3D (mm)",   5000.0, 200.0, 50000.0)
    tip_chord_mm = input_float("  Corda da ponta (mm)",  corda * 600.0, 50.0, 20000.0)
    sweep_deg    = input_float("  Enflechamento (°)",     15.0,  -45.0, 60.0)
    twist_deg    = input_float("  Torção na ponta (°)",   -3.0,  -30.0, 30.0)
    dihedral_deg = input_float("  Diedro (°)",            2.0,   -20.0, 30.0)

    wing_3d = pipeline.Wing3DParams(
        span_mm=span_mm,
        root_chord_mm=corda * 1000.0,
        tip_chord_mm=tip_chord_mm,
        tip_twist_deg=twist_deg,
        wing_sweep_deg=sweep_deg,
        wing_dihedral_deg=dihedral_deg,
    )

    area_m2 = Enviroment.wing_area_m2(wing_3d.span_mm, wing_3d.root_chord_mm, wing_3d.tip_chord_mm)
    payload_kg = None

    if search_mode == "payload":
        payload_kg = input_float("  Peso da carga / massa total (kg)", 120.0, 0.1, 50000.0)
        cond_tmp = Enviroment.FlightConditions(altitude=altitude, velocity=velocidade, target_cl=0.5, chord_size=corda)
        req_cl = Enviroment.required_cl(payload_kg, cond_tmp.rho, velocidade, area_m2)
        target_cl = req_cl
        print(f"\n  Área alar calculada : {area_m2:.3f} m²")
        print(f"  CL mínimo requerido : {req_cl:.4f}")
    else:
        target_cl = input_float("  CL alvo", 0.8, 0.1, 2.5)
        req_cl = target_cl

    cond = Enviroment.FlightConditions(
        altitude   = altitude,
        velocity   = velocidade,
        target_cl  = target_cl,
        chord_size = corda,
    )

    print(f"\n  Densidade do ar     : {cond.rho:.4f} kg/m³")
    print(f"  Viscosidade dinâmica: {cond.mi:.2e} Pa·s")
    print(f"  Reynolds calculado  : {cond.reynolds:,.0f}")
    print(f"  Mach calculado      : {cond.mach:.4f}")
    input("Pressione Enter para confirmar...")

    print("\n" + "=" * 56)
    print("  Configurações da Busca")
    print("=" * 56)

    cl_tolerance = input_float("  Tolerância CL (±)",   0.15, 0.01, 0.5)
    camber_max   = input_int(  "  Camber máximo (0-9)", 6,    0,    9)

    print("\n  Espessuras a testar (separadas por vírgula):")
    while True:
        entrada = input("  Espessuras [8,10,12,15,18]: ").strip()
        if not entrada:
            espessuras = [8, 10, 12, 15, 18]
            break
        try:
            espessuras = [int(e.strip()) for e in entrada.split(",")]
            if all(1 <= e <= 40 for e in espessuras):
                break
            print("    ! Espessuras devem estar entre 1 e 40.")
        except ValueError:
            print("    ! Digite números inteiros separados por vírgula.")

    cd_auto  = Enviroment.min_Cd(cond.reynolds)
    eff_auto = Enviroment.max_efficiency(cond.reynolds)
    cd_entrada  = input(f"  CD mínimo [{cd_auto:.4f}]: ").strip()
    cd_min_user = float(cd_entrada) if cd_entrada else cd_auto
    eff_entrada = input(f"  CL/CD máximo [{eff_auto:.1f}]: ").strip()
    eff_max_user = float(eff_entrada) if eff_entrada else eff_auto

    print("\n" + "=" * 56)
    print("  Parâmetros do XFOIL")
    print("=" * 56)

    alpha_start = input_float("  Alpha início (°)",   -2.0, -20, 10)
    alpha_end   = input_float("  Alpha fim (°)",      12.0, -10, 40)
    alpha_step  = input_float("  Passo do alpha (°)", 0.5,  0.1, 2)
    n_panels    = input_int(  "  Número de painéis",  240,  80,  500)
    n_ITER      = input_int(  "  Iterações",          100,  1,   None)
    n_threads   = input_int(  "  Threads paralelas",  4,    1,   32)

    cfg = {
        "search_mode":  search_mode,
        "payload_kg":   payload_kg,
        "required_cl":  req_cl,
        "wing_area_m2": area_m2,
        "n_ITER":       n_ITER,
        "n_threads":    n_threads,
        "cl_tolerance": cl_tolerance,
        "camber_max":   camber_max,
        "espessuras":   espessuras,
        "cd_min":       cd_min_user,
        "eff_max":      eff_max_user,
        "alpha_start":  alpha_start,
        "alpha_end":    alpha_end,
        "alpha_step":   alpha_step,
        "n_panels":     n_panels,
    }

    return cond, cfg, wing_3d


# ============================================================
# SEÇÃO 7 — PROGRAMA PRINCIPAL (PIPELINE AUTÔNOMA)
# ============================================================

def main():
    if not XFOIL_PATH.exists():
        print(f"\n[ERRO] xfoil.exe não encontrado em: {XFOIL_PATH}")
        print("Coloque o xfoil.exe na mesma pasta deste script.")
        return

    cond, cfg, wing_3d = coletar_parametros()

    print("\nIniciando otimização (Módulo 1)...")
    t0 = time.time()

    best_code, result, top4 = optimizer.run(cond, cfg)
    elapsed = time.time() - t0
    print(f"  Tempo total: {elapsed:.1f}s")

    if result is None or not top4:
        print("\n[ERRO] Nenhum perfil passou nos filtros.")
        return

    print(f"\n  Top {len(top4)} candidatos (por CL/CD):")
    print(f"  {'#':<3} {'NACA':<8} {'CL':>7} {'CD':>8} {'CL/CD':>7} {'α':>6}")
    print(f"  {'-'*44}")
    for i, (code, res) in enumerate(top4):
        print(
            f"  {i+1:<3} {code:<8} "
            f"{res['cl']:>7.4f} "
            f"{res['cd']:>8.5f} "
            f"{res['efficiency']:>7.2f} "
            f"{res['alpha_opt']:>5.1f}°"
        )

    idx_escolhido = input_int(f"\n  Escolha qual asa exportar (1 a {len(top4)})", 1, 1, len(top4)) - 1
    chosen_code, chosen_res = top4[idx_escolhido]

    x, y = nc.generator(chosen_code, n_points=255)
    out = Path("output")
    out.mkdir(exist_ok=True)

    svg_path  = export_svg(x, y, chosen_code, out)
    dat_path  = export_dat(x, y, chosen_code, out)
    json_path = export_json(chosen_code, chosen_res, cond, dat_path, out, extra_cfg=cfg)
    plot_path = export_plot(x, y, chosen_code, chosen_res, out)

    print(f"\nArquivos 2D gerados em '{out}/':")
    print(f"  SVG   → {svg_path.name}")
    print(f"  DAT   → {dat_path.name}")
    print(f"  JSON  → {json_path.name}")
    print(f"  Plot  → {plot_path.name}")

    print("\nIniciando pipeline autônoma para o Módulo 2 (3D PicoGK)...")
    stl_path = out / f"wing_naca_{chosen_code}.stl"
    ok, stl_out, msg = pipeline.run_3d_generator(
        dat_path, stl_path, wing_3d, log_callback=print
    )
    if ok:
        print(f"\nPipeline concluída! STL 3D salvo em: {stl_out}")
    else:
        print(f"\n[AVISO Pipeline 3D] {msg}")


if __name__ == "__main__":
    main()
