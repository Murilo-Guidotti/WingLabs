from __future__ import annotations

import math
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

from winglabs.aero import naca_tester
from winglabs.core import environment as env


def _build_coarse_cfg(cfg_fine: dict) -> dict:
    """
    Constrói a configuração do Estágio 1 (triagem rápida Coarse-to-Fine):
    reduz o número de painéis (~100–120), dobra o passo de alpha e reduz iterações
    para descartar ~85% dos candidatos rapidamente antes do refinamento fino.
    """
    n_panels_fine = int(cfg_fine.get("n_panels", 240))
    n_iter_fine = int(cfg_fine.get("n_ITER", 100))
    alpha_start = float(cfg_fine.get("alpha_start", -2.0))
    alpha_end = float(cfg_fine.get("alpha_end", 12.0))
    alpha_step_fine = max(0.1, float(cfg_fine.get("alpha_step", 0.5)))
    cl_tol_fine = float(cfg_fine.get("cl_tolerance", 0.15))

    coarse_panels = min(n_panels_fine, max(100, min(120, n_panels_fine // 2)))
    coarse_iter = min(n_iter_fine, max(40, int(round(n_iter_fine * 0.6))))
    alpha_span = max(0.0, alpha_end - alpha_start)
    coarse_step = min(2.0, alpha_step_fine * 2.0) if alpha_span >= alpha_step_fine * 4.0 else alpha_step_fine
    # Tolerância levemente ampliada na triagem para não descartar perfis cujo ótimo caia entre passos maiores de alpha
    coarse_tol = max(cl_tol_fine, cl_tol_fine * 1.35)

    return {
        **cfg_fine,
        "n_panels": coarse_panels,
        "n_ITER": coarse_iter,
        "alpha_step": coarse_step,
        "cl_tolerance": coarse_tol,
        "n_points": 129,
    }


def _executar_lote(
    codigos: list[str],
    cond: env.FlightConditions,
    cfg_stage: dict,
    n_threads: int,
    done_offset: int,
    total_steps: int,
    progress_callback: Callable[[int, int, str, dict | None], None] | None,
    cancel_event: threading.Event | None,
) -> tuple[list[tuple[str, dict]], int, bool]:
    """Executa um lote de perfis NACA em paralelo no ThreadPoolExecutor."""
    tarefas = [
        (code, cond, cfg_stage, done_offset + idx + 1, total_steps)
        for idx, code in enumerate(codigos)
    ]
    resultados: list[tuple[str, dict]] = []
    done = done_offset
    cancelado = False

    with ThreadPoolExecutor(max_workers=n_threads) as executor:
        futures = {executor.submit(naca_tester.run, t): t for t in tarefas}
        for future in as_completed(futures):
            if cancel_event is not None and cancel_event.is_set():
                cancelado = True
                for f in futures:
                    f.cancel()
                break
            code, result = future.result()
            done += 1
            if result is not None:
                resultados.append((code, result))
            if progress_callback is not None:
                progress_callback(done, total_steps, code, result)

    return resultados, done, cancelado


def run(
    cond: env.FlightConditions,
    cfg: dict,
    progress_callback: Callable[[int, int, str, dict | None], None] | None = None,
    cancel_event: threading.Event | None = None,
) -> tuple[str, dict | None, list[tuple[str, dict]]]:
    n_threads = max(1, int(cfg.get("n_threads", 1)))
    cl_tolerance = cfg.get("cl_tolerance", 0.01)
    camber_max = cfg.get("camber_max", 6)
    espessuras = cfg.get("espessuras", [8, 10, 12, 15, 18])
    n_ITER = int(cfg.get("n_ITER", 100))
    search_mode = cfg.get("search_mode", "target_cl")

    # Limites dinâmicos calculados e garantidos no dicionário de execução
    min_cd = cfg.get("cd_min") or env.min_Cd(cond.reynolds)
    max_efficiency = cfg.get("eff_max") or env.max_efficiency(cond.reynolds)
    cfg_fine = {
        **cfg,
        "n_ITER": n_ITER,
        "cd_min": min_cd,
        "eff_max": max_efficiency,
        "n_points": 255,
    }

    codigos: list[str] = []
    for M in range(0, camber_max + 1):
        for P in range(2, 8):
            for T in espessuras:
                codigos.append(f"{M}{P}{T:02d}")

    total_perfis = len(codigos)
    if total_perfis == 0:
        return "2412", None, []

    use_two_stage = bool(cfg.get("two_stage", True)) and total_perfis > 8
    top_k_quota = min(total_perfis, max(6, math.ceil(total_perfis * 0.15))) if use_two_stage else 0
    total_steps = (total_perfis + top_k_quota) if use_two_stage else total_perfis

    print(f"\n  Testando {total_perfis} perfis com {n_threads} threads paralelas...")
    if use_two_stage:
        print(f"  Estratégia    : Busca em 2 estágios (Coarse-to-Fine, Top {top_k_quota} refinados)")
    if search_mode == "payload":
        print(f"  Modo          : Carga / Peso ({cfg_fine.get('payload_kg', 0):.2f} kg)")
        print(f"  CL mínimo req.: {cfg_fine.get('required_cl', cond.target_cl):.4f}")
    else:
        print(f"  Modo          : CL Alvo ({cond.target_cl:.3f} ±{cl_tolerance})")
    print(f"  CD mínimo     : {min_cd:.4f}")
    print(f"  CL/CD máximo  : {max_efficiency:.1f}")
    print(f"  Iterações     : {n_ITER:.0f}\n")

    if not use_two_stage:
        candidatos, _, _ = _executar_lote(
            codigos, cond, cfg_fine, n_threads, 0, total_steps, progress_callback, cancel_event
        )
    else:
        # Estágio 1: Triagem rápida (Coarse) em todos os perfis
        cfg_coarse = _build_coarse_cfg(cfg_fine)
        candidatos_coarse, done_s1, cancelado = _executar_lote(
            codigos, cond, cfg_coarse, n_threads, 0, total_steps, progress_callback, cancel_event
        )
        if cancelado or not candidatos_coarse:
            return "2412", None, []

        candidatos_coarse.sort(key=lambda c: c[1]["efficiency"], reverse=True)
        finalistas_codes = [code for code, _ in candidatos_coarse[:top_k_quota]]

        # Estágio 2: Refinamento de alta resolução (Fine) apenas no Top 10-15%
        candidatos_fine, _, cancelado = _executar_lote(
            finalistas_codes,
            cond,
            cfg_fine,
            n_threads,
            done_s1,
            done_s1 + len(finalistas_codes),
            progress_callback,
            cancel_event,
        )
        if cancelado:
            return "2412", None, []

        # Se o refinamento fino convergir, usa os resultados finos; complementa com triagem se < 4 candidatos
        fine_codes = {code for code, _ in candidatos_fine}
        candidatos = list(candidatos_fine)
        if len(candidatos) < 4:
            for code_c, res_c in candidatos_coarse:
                if code_c not in fine_codes:
                    if search_mode == "payload" or abs(res_c["cl"] - cond.target_cl) <= float(cl_tolerance):
                        candidatos.append((code_c, res_c))
                        if len(candidatos) >= 4:
                            break

    if not candidatos:
        return "2412", None, []

    candidatos.sort(key=lambda c: c[1]["efficiency"], reverse=True)
    best_code, best_result = candidatos[0]
    top4 = candidatos[:4]

    return best_code, best_result, top4
