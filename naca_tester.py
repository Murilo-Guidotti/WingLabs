import naca_generator as ng
import threading as thread
# from main import analyzeWithXfoil
import main


def run(args: tuple) -> tuple[str, dict | None]:
    code, cond, cfg, tolerancia_cl, idx, total = args

    x, y   = ng.generator(code)
    result = main.analyzeWithXfoil(x, y, cond, nome=f"NACA{code}", cfg=cfg)

    with thread.Lock():
        status = "✓" if result else "✗"
        print(f"  [{idx:>3}/{total}] NACA {code} {status}     ", end="\r")

    if result is None:
        return code, None

    # ~~ TODO: permitir o usuário escolher entre tolerância explicita ou não, explicita é para Lift superior e inferior ~~
    # ~~       tolerância não explitica se aplica apenas a Lifts MENORES que a o target_CL ~~

    
        # Caso o CL resultante seja menor que o piso da tolerância ou maior que o teto da tolerância, ele é descartado.
    if result["cl"] < (cond.target_cl - tolerancia_cl) or result["cl"] > (cond.target_cl + tolerancia_cl): # Tolerância explicita
        return code, None

    # Filtro 2: validação física com limites dinâmicos por Reynolds
    if not _valida_resultado(result, cfg):
        return code, None

    return code, result

def _valida_resultado(result: dict, cfg: dict) -> bool:
    
    min_cd  = cfg.get("cd_min")
    max_efficiency = cfg.get("eff_max")

    if result["cd"] < min_cd:
        return False
    if result["efficiency"] > max_efficiency:
        return False
    if result["cl"] <= 0:
        return False

    return True