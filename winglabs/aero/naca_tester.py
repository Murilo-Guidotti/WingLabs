from __future__ import annotations

from winglabs.aero import xfoil_engine
from winglabs.core import environment as env
from winglabs.core import naca as ng


def run(args: tuple) -> tuple[str, dict | None]:
    code, cond, cfg, _idx, _total = args

    n_points = int(cfg.get("n_points", 255))
    x, y = ng.generator(code, n_points=n_points)
    result = xfoil_engine.analyzeWithXfoil(x, y, cond, nome=f"NACA{code}", cfg=cfg)

    if result is None:
        return code, None
    if not _valida_resultado(result, cfg, cond):
        return code, None

    return code, result


def _valida_resultado(
    result: dict,
    cfg: dict,
    cond: env.FlightConditions | None = None,
) -> bool:
    re = cond.reynolds if cond is not None else 1_000_000.0
    min_cd = cfg.get("cd_min") or env.min_Cd(re)
    max_efficiency = cfg.get("eff_max") or env.max_efficiency(re)

    return not (result["cd"] < min_cd or result["efficiency"] > max_efficiency)
