import NacaGenerator as ng
import main


def run(args: tuple) -> tuple[str, dict | None]:
    code, cond, cfg, idx, total = args

    x, y   = ng.generator(code, n_points=255)
    result = main.analyzeWithXfoil(x, y, cond, nome=f"NACA{code}", cfg=cfg)

    status = "✓" if result else "✗"
    print(f"  [{idx:>3}/{total}] NACA {code} {status}     ", end="\r")

    if result is None:
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
    
    return True