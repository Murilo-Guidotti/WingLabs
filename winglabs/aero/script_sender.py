from __future__ import annotations


def build_script(
    dat_path: str,
    polar_path: str,
    re: float,
    mach: float,
    alpha_start: float,
    alpha_end: float,
    alpha_step: float,
    n_panels: int,
    n_iter: int,
) -> str:
    """Gera o script de comandos do XFOIL diretamente em memória (sem I/O de disco)."""
    cmds = [
        "PLOP",
        "G F",
        "",
        f"LOAD {dat_path}",
        "",
        "PPAR",
        f"N {n_panels}",
        "",
        "",
        "OPER",
        "VISC 1",
        f"Re {re}",
        f"MACH {mach}",
        f"ITER {n_iter}",
        "PACC",
        polar_path,
        "",
        f"ASEQ {alpha_start} {alpha_end} {alpha_step}",
        "PACC",
        "",
        "QUIT",
    ]
    return "\n".join(cmds) + "\n"


def sendScript(
    dat_path: str,
    polar_path: str,
    re: float,
    mach: float,
    alpha_start: float,
    alpha_end: float,
    alpha_step: float,
    script_path: str,
    n_panels: int,
    n_ITER: int,
) -> None:
    content = build_script(
        dat_path, polar_path, re, mach, alpha_start, alpha_end, alpha_step, n_panels, n_ITER
    )
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(content)
