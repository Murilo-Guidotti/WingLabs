from __future__ import annotations

import Enviroment as env
import NacaTester
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable


def run(
    cond: env.FlightConditions,
    cfg: dict,
    progress_callback: Callable[[int, int, str, dict | None], None] | None = None,
) -> tuple[str, dict | None, list[tuple[str, dict]]]:
    n_threads = cfg.get("n_threads", 1)
    cl_tolerance = cfg.get("cl_tolerance", 0.01)
    camber_max = cfg.get("camber_max", 6)
    espessuras = cfg.get("espessuras", [8, 10, 12, 15, 18])
    n_ITER = cfg.get("n_ITER", cfg.get("n_iterations", 100))
    search_mode = cfg.get("search_mode", "target_cl")

    # Limites dinâmicos calculados para exibição
    min_cd = cfg.get("cd_min") or env.min_Cd(cond.reynolds)
    max_efficiency = cfg.get("eff_max") or env.max_efficiency(cond.reynolds)

    codigos = []
    for M in range(0, camber_max + 1):
        for P in range(2, 8):
            for T in espessuras:
                codigos.append(f"{M}{P}{T:02d}")

    total = len(codigos)
    print(f"\n  Testando {total} perfis com {n_threads} threads paralelas...\n")
    if search_mode == "payload":
        print(f"  Modo          : Carga / Peso ({cfg.get('payload_kg', 0):.2f} kg)")
        print(f"  CL mínimo req.: {cfg.get('required_cl', cond.target_cl):.4f}")
    else:
        print(f"  Modo          : CL Alvo ({cond.target_cl:.3f} ±{cl_tolerance})")
    print(f"  CD mínimo     : {min_cd:.4f}")
    print(f"  CL/CD máximo  : {max_efficiency:.1f}")
    print(f"  Iterações     : {n_ITER:.0f}\n")

    tarefas = [
        (code, cond, cfg, idx + 1, total)
        for idx, code in enumerate(codigos)
    ]

    candidatos: list[tuple[str, dict]] = []
    done = 0

    with ThreadPoolExecutor(max_workers=n_threads) as executor:
        futures = {executor.submit(NacaTester.run, t): t for t in tarefas}
        for future in as_completed(futures):
            code, result = future.result()
            done += 1
            if result is not None:
                candidatos.append((code, result))
            if progress_callback is not None:
                progress_callback(done, total, code, result)

    if not candidatos:
        return "2412", None, []

    print()

    candidatos.sort(key=lambda c: c[1]["efficiency"], reverse=True)
    best_code, best_result = candidatos[0]
    top4 = candidatos[:4]

    return best_code, best_result, top4