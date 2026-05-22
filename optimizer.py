import Enviroment as env
import naca_tester
from concurrent.futures import ThreadPoolExecutor, as_completed


def run(cond: env.FlightConditions, cfg: dict) -> tuple[str, dict | None, list]:
    n_threads = cfg.get("n_threads", 1)
    cl_tolerance = cfg.get("cl_tolerance", 0.01)
    camber_max = cfg.get("camber_max", 6)
    espessuras    = cfg.get("espessuras", [8, 10, 12, 15, 18])
    n_ITER       = cfg.get("n_ITER", 100)

    # Limites dinâmicos calculados para exibição
    min_cd  = cfg.get("cd_min")  or env.min_Cd(cond.reynolds)
    max_efficiency = cfg.get("eff_max") or env.max_efficiency(cond.reynolds)

    codigos = []
    for M in range(0, camber_max + 1):
        for P in range(2, 8):
            for T in espessuras:
                codigos.append(f"{M}{P}{T:02d}")

    total = len(codigos)
    print(f"\n  Testando {total} perfis com {n_threads} threads paralelas...\n")
    print(f"  Tolerância CL : ±{cl_tolerance}")
    print(f"  CD mínimo     : {min_cd:.4f}")
    print(f"  CL/CD máximo  : {max_efficiency:.1f}")
    print(f"  Interações    : {n_ITER:.1f}\n")

    tarefas = [
        (code, cond, cfg, cl_tolerance, idx + 1, total)
        for idx, code in enumerate(codigos)
    ]

    candidatos: list[tuple[str, dict]] = []


    with ThreadPoolExecutor(max_workers=n_threads) as executor:
        futures = {executor.submit(naca_tester.run, t): t for t in tarefas}
        for future in as_completed(futures):
            code, result = future.result()
            if result is not None:
                candidatos.append((code, result))

    if not candidatos:
        return "2412", None, []

    print()

    candidatos.sort(key=lambda c: c[1]["efficiency"], reverse=True)
    best_code, best_result = candidatos[0]
    top5 = candidatos[:5]

    return best_code, best_result, top5