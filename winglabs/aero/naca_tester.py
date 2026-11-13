from __future__ import annotations

from winglabs.aero import xfoil_engine
from winglabs.core import environment as env
from winglabs.core import naca as ng


def run(args: tuple) -> tuple[str, dict | None]:
    code, cond, cfg, idx, total = args

    x, y = ng.generator(code, n_points=255)
    result = xfoil_engine.analyzeWithXfoil(x, y, cond, nome=f"NACA{code}", cfg=cfg)

    status = "✓" if result else "✗"
    print(f"  [{idx:>3}/{total}] NACA {code} {status}     ", end="\r")

    if result is None:
        return code, None

    # Filtro 2: validação física com limites dinâmicos por Reynolds
    if not _valida_resultado(result, cfg, cond):
        return code, None

    return code, result


def _valida_resultado(
    result: dict,
    cfg: dict,
    cond: env.FlightConditions | None = None,
) -> bool:
    re = cond.reynolds if cond is not None else 1_000_000.0
    min_cd = cfg.get("cd_min")
    if min_cd is None or min_cd <= 0:
        min_cd = env.min_Cd(re)

    max_efficiency = cfg.get("eff_max")
    if max_efficiency is None or max_efficiency <= 0:
        max_efficiency = env.max_efficiency(re)

    if result["cd"] < min_cd:
        return False
    if result["efficiency"] > max_efficiency:
        return False

    return True
