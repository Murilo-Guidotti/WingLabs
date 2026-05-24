# ============================================================
# NACA Wing Profile Generator
# Software 1 de 2 — Gerador de Perfil 2D
# TCC — Gerador de Asa NACA
# ============================================================

import subprocess
import tempfile
import os
import json
import time
import threading
import numpy as np
import svgwrite
import matplotlib.pyplot as plt
from ambiance import Atmosphere
from pathlib import Path
import ScriptSender as sender
import NacaGenerator as nc
import Optimizer
import Enviroment

# ============================================================
# CONFIGURAÇÃO
# ============================================================

XFOIL_PATH = Path(__file__).parent / "xfoil.exe"
print_lock  = threading.Lock()

# ============================================================
# SEÇÃO 1 — GERAÇÃO DO PERFIL NACA 4 DÍGITOS
# ============================================================

def nacaGenerator(code: str, n_points: int = 500) -> tuple[np.ndarray, np.ndarray]: 
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


def analyzeWithXfoil(x: np.ndarray, y: np.ndarray, cond: Enviroment.FlightConditions,
                       nome: str = "perfil", cfg: dict | None = None) -> dict | None:
    
    if cfg is None:
        cfg = {}

    alpha_start = cfg.get("alpha_start", 0.0)
    alpha_end   = cfg.get("alpha_end",   0.0)
    alpha_step  = cfg.get("alpha_step",   0.5)
    n_panels    = cfg.get("n_panels",    240)
    n_ITER      = cfg.get("n_ITER",      100)

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

        validos = [r for r in resultados if r["cd"] > 0 and r["cl"] > 0]
        if not validos:
            return None

        melhor = max(validos, key=lambda r: r["cl"] / r["cd"])
        return {
            "alpha_opt":  melhor["alpha"],
            "cl":         melhor["cl"],
            "cd":         melhor["cd"],
            "cm":         melhor["cm"],
            "efficiency": melhor["cl"] / melhor["cd"]
        }


# def optimize_naca(cond: Enviroment.FlightConditions, cfg: dict) -> tuple[str, dict | None, list]:
    
#     n_threads     = cfg.get("n_threads", 1)
#     cl_tolerance = cfg.get("cl_tolerance", 0.01)
#     camber_max    = cfg.get("camber_max", 6)
#     espessuras    = cfg.get("espessuras", [8, 10, 12, 15, 18])
#     n_ITER       = cfg.get("n_ITER", 100)

#     # Limites dinâmicos calculados para exibição
#     min_cd  = cfg.get("cd_min")  or Enviroment.min_Cd(cond.reynolds)
#     max_efficiency = cfg.get("eff_max") or Enviroment.max_efficiency(cond.reynolds)

#     codigos = []
#     for M in range(0, camber_max + 1):
#         for P in range(2, 8):
#             for T in espessuras:
#                 codigos.append(f"{M}{P}{T:02d}")

#     total = len(codigos)
#     print(f"\n  Testando {total} perfis com {n_threads} threads paralelas...\n")
#     print(f"  Tolerância CL : ±{cl_tolerance}")
#     print(f"  CD mínimo     : {min_cd:.4f}")
#     print(f"  CL/CD máximo  : {max_efficiency:.1f}")
#     print(f"  Interações    : {n_ITER:.1f}\n")

#     tarefas = [
#         (code, cond, cfg, cl_tolerance, idx + 1, total)
#         for idx, code in enumerate(codigos)
#     ]

#     candidatos: list[tuple[str, dict]] = []


#     with ThreadPoolExecutor(max_workers=n_threads) as executor:
#         futures = {executor.submit(naca_tester.run, t): t for t in tarefas}
#         for future in as_completed(futures):
#             code, result = future.result()
#             if result is not None:
#                 candidatos.append((code, result))

    if not candidatos:
        return "2412", None, []

    print()

    candidatos.sort(key=lambda c: c[1]["efficiency"], reverse=True)
    best_code, best_result = candidatos[0]
    top5 = candidatos[:5]

    return best_code, best_result, top5


# ============================================================
# SEÇÃO 5 — EXPORTS: SVG, DAT, JSON E PLOT
# ============================================================

def export_svg(x: np.ndarray, y: np.ndarray, code: str, output_dir: Path) -> Path:
    W, H    = 800, 300
    padding = 40

    x_svg = x * (W - 2*padding) + padding
    y_svg = -y * (W - 2*padding) + H / 2

    dwg = svgwrite.Drawing(
        filename=str(output_dir / f"naca_{code}.svg"),
        size=(f"{W}px", f"{H}px"),
        viewBox=f"0 0 {W} {H}"
    )
    dwg.add(dwg.rect(insert=(0, 0), size=(W, H), fill="white"))

    path_d = [f"M {x_svg[0]:.3f} {y_svg[0]:.3f}"]
    for i in range(1, len(x_svg)):
        cp1x = x_svg[i-1] + (x_svg[i] - x_svg[i-1]) / 3
        cp1y = y_svg[i-1] + (y_svg[i] - y_svg[i-1]) / 3
        cp2x = x_svg[i-1] + 2 * (x_svg[i] - x_svg[i-1]) / 3
        cp2y = y_svg[i-1] + 2 * (y_svg[i] - y_svg[i-1]) / 3
        path_d.append(
            f"C {cp1x:.2f} {cp1y:.2f} {cp2x:.2f} {cp2y:.2f} "
            f"{x_svg[i]:.2f} {y_svg[i]:.2f}"
        )
    path_d.append("Z")

    dwg.add(dwg.path(
        d=" ".join(path_d),
        fill="#E8F4FD", stroke="#185FA5", stroke_width=1.5
    ))
    dwg.add(dwg.text(
        f"NACA {code}", insert=(padding, 25),
        font_size="14px", font_family="sans-serif", fill="#333"
    ))
    dwg.save()
    return Path(dwg.filename)


def export_dat(x: np.ndarray, y: np.ndarray, code: str, output_dir: Path) -> Path:
    dat_path = output_dir / f"naca_{code}.dat"
    with open(dat_path, "w") as f:
        f.write(f"NACA {code}\n")
        for xi, yi in zip(x, y):
            f.write(f"{xi:.6f}  {yi:.6f}\n")
    return dat_path


def export_json(code: str, result: dict, cond: Enviroment.FlightConditions,
                dat_path: Path, output_dir: Path) -> Path:
    payload = {
        "naca_code": code,
        "dat_file":  dat_path.name,
        "aerodynamics": {
            "alpha_opt":  result["alpha_opt"],
            "cl":         result["cl"],
            "cd":         result["cd"],
            "cm":         result["cm"],
            "efficiency": result["efficiency"]
        },
        "flight": {
            "altitude":   cond.altitude,
            "velocity":  cond.velocity,
            "reynolds":     cond.reynolds,
            "mach":         cond.mach,
            "rho":          cond.rho,
            "mu":           cond.mi,
            "chord_size":      cond.chord_size,
            "target_cl":    cond.target_cl
        }
    }
    json_path = output_dir / f"naca_{code}_result.json"
    with open(json_path, "w") as f:
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
# SEÇÃO 6 — ENTRADA DE PARÂMETROS PELO USUÁRIO
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


def coletar_parametros() -> tuple[Enviroment.FlightConditions, dict]:
    print("\n" + "=" * 56)
    print("  Parâmetros de Voo")
    print("  (Enter = usar valor padrão)")
    print("=" * 56)


    altitude   = input_float("  Altitude (m)",       1500,  0,    12000)
    velocidade = input_float("  Velocidade (m/s)",   60,    0,   Atmosphere(altitude).speed_of_sound[0])
    target_cl  = input_float("  CL alvo",            0.8,   0.1,  2.5)
    corda      = input_float("  Corda (m)",          1.2,   0.1,  10)
   
    cond = Enviroment.FlightConditions(
        altitude   = altitude,
        velocity  = velocidade,
        target_cl    = target_cl,
        chord_size      = corda,
    )


    print(f"\n  Densidade do ar     : {cond.rho:.4f} kg/m³")
    print(f"  Viscosidade dinâmica: {cond.mi:.2e} Pa·s")
    print(f"  Reynolds calculado  : {cond.reynolds:,.0f}")
    print(f"  Mach calculado      : {cond.mach:.4f}")
    input("Pressione Enter para confirmar...")


    print("\n" + "=" * 56)
    print("  Configurações da Busca")
    print("=" * 56)

    cl_tolerance = input_float("  Tolerância CL (±)",      0.15, 0.01, 0.5)
    camber_max    = input_int(  "  Camber máximo (0-9)",    6,    0,   9)

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


    # Mostra os limites automáticos pro usuário saber o que esperar
    cd_auto  = Enviroment.min_Cd(cond.reynolds)
    eff_auto = Enviroment.max_efficiency(cond.reynolds)
    print(f"\n  Limites automáticos para Re={cond.reynolds:,.0f}:")
    print(f"    CD mínimo  → {cd_auto:.3f}")
    print(f"    CL/CD máx  → {eff_auto:.1f}")
    time.sleep(1)
    

    print("\n" + "=" * 56)
    print("  Filtros de Validação Física")
    print("  (Enter = usar limites automáticos por Reynolds)")
    print("=" * 56)

    print("\n" + "=" * 56)
    print("  Referências típicas da literatura:")
    print("  Re < 500k  → perfis de aeromodelo, CD_min ≈ 0.005–0.015")
    print("  Re 500k–5M → aviação geral, CD_min ≈ 0.002–0.006")
    print("  Re > 5M    → aeronaves grandes, CD_min ≈ 0.001–0.003")
    print("=" * 56)

    print(f"  CD mínimo aceito (auto={cd_auto:.4f}):")
    cd_entrada = input(f"  CD mínimo [{cd_auto:.4f}]: ").strip()
    cd_min_user = float(cd_entrada) if cd_entrada else cd_auto
    
    print("\n" + "=" * 56)
    print("  Referências típicas da literatura:")
    print("  ! Maiores números de Reynolds tendem a possuir maiores Coeficientes de Eficiência !")
    print("  Planadores em Re alto chegam a 60-70.")
    print("  Aviação geral em Re 1-5M pode atingir 80-120 em condições ideais.")
    print("=" * 56)

    print(f"  CL/CD máximo aceito (auto={eff_auto:.1f}):")
    eff_entrada = input(f"  CL/CD máximo [{eff_auto:.1f}]: ").strip()
    eff_max_user = float(eff_entrada) if eff_entrada else eff_auto

    print("\n" + "=" * 56)
    print("  Parâmetros do XFOIL")
    print("=" * 56)

    alpha_start = input_float("  Alpha início (°)",   0,   -20,  0)
    alpha_end   = input_float("  Alpha fim (°)",       0,    0,  40)
    alpha_step  = input_float("  Passo do alpha (°)", 0.5,  0.1,  2)
    n_panels    = input_int(  "  Número de painéis", 240,   80,  500)
    n_ITER      = input_int(  "  Interações",        100,    1,  None)
    n_threads   = input_int(  "  Threads paralelas",      1,    1,   32)

    cfg = {
        "n_ITER": n_ITER,
        "n_threads":     n_threads,
        "cl_tolerance": cl_tolerance,
        "camber_max":    camber_max,
        "espessuras":    espessuras,
        "cd_min":        cd_min_user,   # None = usa automático por Reynolds
        "eff_max":       eff_max_user,  # None = usa automático por Reynolds
        "alpha_start":   alpha_start,
        "alpha_end":     alpha_end,
        "alpha_step":    alpha_step,
        "n_panels":      n_panels,
    }

    total = (camber_max + 1) * 4 * len(espessuras)
    print(f"\n  Total de perfis a testar : {total}")
    print(f"  Threads paralelas        : {n_threads}")
    print(f"  Estimativa de tempo      : ~{max(1, total + n_ITER // n_threads * 3)}s")

    confirma = input("\n  Iniciar análise? (Enter = sim / n = não): ").strip().lower()
    if confirma == "n":
        print("  Análise cancelada.")
        exit()

    return cond, cfg


# ============================================================
# SEÇÃO 7 — PROGRAMA PRINCIPAL
# ============================================================

def main():

    if not XFOIL_PATH.exists():
        print(f"\n[ERRO] xfoil.exe não encontrado em: {XFOIL_PATH}")
        print("Coloque o xfoil.exe na mesma pasta deste script.")
        return

    cond, cfg = coletar_parametros()

    print("\nIniciando otimização...")
    t0 = time.time()

    best_code, result, top5 = Optimizer.run(cond, cfg)

    elapsed = time.time() - t0
    print(f"  Tempo total: {elapsed:.1f}s")

    if result is None:
        print("\n[ERRO] Nenhum perfil passou nos filtros.")
        print("Sugestões:")
        print("  → Aumente a tolerância CL")
        print("  → Aumente o CL/CD máximo aceito")
        print("  → Diminua o CD mínimo aceito")
        print("  → Ajuste os parâmetros de voo")
        return

    # Top 5
    print(f"\n  Top {len(top5)} candidatos (por CL/CD):")
    print(f"  {'#':<3} {'NACA':<8} {'CL':>7} {'CD':>8} {'CL/CD':>7} {'α':>6}")
    print(f"  {'-'*44}")
    for i, (code, res) in enumerate(top5):
        print(
            f"  {i+1:<3} {code:<8} "
            f"{res['cl']:>7.4f} "
            f"{res['cd']:>8.5f} "
            f"{res['efficiency']:>7.2f} "
            f"{res['alpha_opt']:>5.1f}°"
            "\n"
        )

    print(f"\n{'='*56}")
    print(f"  Melhor perfil encontrado: NACA {best_code}")
    print(f"{'='*56}")
    print(f"  CL           : {result['cl']:.4f}")
    print(f"  CD           : {result['cd']:.5f}")
    print(f"  CL/CD        : {result['efficiency']:.2f}")
    print(f"  Ângulo ideal : {result['alpha_opt']:.1f}°")
    print(f"  CM           : {result['cm']:.4f}")

    print(f"\n  Interpretação:")

    # Exports
    x, y = nc.generator(best_code, n_points = 500)

    out = Path("output")
    out.mkdir(exist_ok=True)

    svg_path  = export_svg(x, y, best_code, out)
    dat_path  = export_dat(x, y, best_code, out)
    json_path = export_json(best_code, result, cond, dat_path, out)
    plot_path = export_plot(x, y, best_code, result, out)

    print(f"\nArquivos gerados em '{out}/':")
    print(f"  SVG   → {svg_path.name}")
    print(f"  DAT   → {dat_path.name}")
    print(f"  JSON  → {json_path.name}")
    print(f"  Plot  → {plot_path.name}")
    print(f"\nPronto! O JSON pode ser lido pelo Software 2 (C#/PicoGK).")


if __name__ == "__main__":
    main()
