from __future__ import annotations


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
):
    cmds = [
        "PLOP",                                         # PLOP -> to set up the plotting environment in XFOIL.
        "G F",                                          # G F  -> to not show the graphics when running the simulation.
        "",                                             # Exit    the PLOP menu.
        f"LOAD {dat_path}",                             # LOAD -> to load the airfoil .dat file into XFOIL.
        "",                                             # Exit    the LOAD menu.
        "PPAR",                                         # PPAR -> to set up the paneling of the airfoil in XFOIL.
        f"N {n_panels}",                                # N    -> to set the size of the mesh.
        "",                                             # Exit    the Mesh menu.
        "",                                             # Exit    the PPAR menu.
        "OPER",                                         # OPER -> to set up the operating conditions for the simulation in XFOIL.
        "VISC 1",                                       # VISC -> to turn on viscosity in XFOIL.
        f"Re {re:.0f}",                                 # Re   -> Reynolds number.
        f"MACH {mach:.4f}",                             # MACH -> Mach number.
        f"ITER {n_ITER}",                               # ITER -> max iterations.
        "PACC",                                         # PACC -> polar accumulation.
        polar_path,                                     # Path -> polar output file.
        "",                                             # Exit    the PACC Path menu.
        f"ASEQ {alpha_start} {alpha_end} {alpha_step}", # ASEQ -> angle of attack sequence.
        "PACC",                                         # PACC -> stop polar accumulation.
        "",                                             # Exit    the OPER menu.
        "QUIT",                                         # QUIT -> exit XFOIL.
    ]
    with open(script_path, "w", encoding="utf-8") as f:
        f.write("\n".join(cmds) + "\n")
