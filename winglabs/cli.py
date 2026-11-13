# ============================================================
# WingLabs — Interface de Linha de Comando (CLI)
# Software 1 de 2 — Gerador de Perfil 2D + Pipeline Autônoma 3D
# ============================================================

from __future__ import annotations

import threading
import time

from winglabs.aero import optimizer
from winglabs.aero.xfoil_engine import (
    XFOIL_PATH,
    export_dat,
    export_json,
    export_plot,
    export_svg,
)
from winglabs.core import environment as env
from winglabs.core import naca as nc
from winglabs.core import pipeline

print_lock = threading.Lock()


def input_float(
    prompt: str,
    default: float,
    minval: float | None,
    maxval: float | None,
) -> float:
    while True:
        try:
            entrada = input(f"{prompt} [{default}]: ").strip().replace(",", ".")
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


def input_int(
    prompt: str,
    default: int,
    minval: int | None,
    maxval: int | None,
) -> int:
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


def coletar_parametros() -> tuple[env.FlightConditions, dict, pipeline.Wing3DParams]:
    print("\n" + "=" * 56)
    print("  Parâmetros de Voo")
    print("  (Enter = usar valor padrão)")
    print("=" * 56)

    altitude   = input_float("  Altitude (m)",     1500, 0, 12000)
    a_sound    = env.speed_of_sound(altitude)
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

    area_m2 = env.wing_area_m2(wing_3d.span_mm, wing_3d.root_chord_mm, wing_3d.tip_chord_mm)
    payload_kg = None
    cond = env.FlightConditions(
        altitude=altitude,
        velocity=velocidade,
        target_cl=0.8,
        chord_size=corda,
    )

    if search_mode == "payload":
        payload_kg = input_float("  Peso da carga / massa total (kg)", 120.0, 0.1, 50000.0)
        req_cl = env.required_cl(payload_kg, cond.rho, velocidade, area_m2)
        target_cl = req_cl
        print(f"\n  Área alar calculada : {area_m2:.3f} m²")
        print(f"  CL mínimo requerido : {req_cl:.4f}")
    else:
        target_cl = input_float("  CL alvo", 0.8, 0.1, 2.5)
        req_cl = target_cl
    cond.target_cl = target_cl

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
            espessuras = [int(e.strip()) for e in entrada.split(",") if e.strip()]
            if espessuras and all(1 <= e <= 40 for e in espessuras):
                break
            print("    ! Espessuras devem estar entre 1 e 40.")
        except ValueError:
            print("    ! Digite números inteiros separados por vírgula.")

    cd_auto  = round(env.min_Cd(cond.reynolds), 4)
    eff_auto = round(env.max_efficiency(cond.reynolds), 1)
    cd_min_user  = input_float("  CD mínimo",    cd_auto,  0.0001, 1.0)
    eff_max_user = input_float("  CL/CD máximo", eff_auto, 1.0,    500.0)

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


def main():
    if not XFOIL_PATH.exists():
        print(f"\n[ERRO] xfoil.exe não encontrado em: {XFOIL_PATH}")
        print("Coloque o xfoil.exe na pasta raiz do projeto.")
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
    out = pipeline.DEFAULT_OUTPUT_DIR
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
