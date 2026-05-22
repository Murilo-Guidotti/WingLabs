def sendScript(     dat_path: str, polar_path: str, re: float,
                    mach: float, alpha_start: float, alpha_end: float,
                    alpha_step: float, script_path: str, n_panels: int, n_ITER: int):
    
    cmds = [
        "PLOP",                                         # PLOP -> to set up the plotting environment in XFOIL.
        "G F",                                          # G F  -> to not show the graphics when running the simulation.
        "",                                             # Exit    the PLOP menu.
        f"LOAD {dat_path}",                             # LOAD -> to load the airfoil .dat file into XFOIL.
    #   f"NACA {naca_code}",                            # NACA -> to load a NACA airfoil directly in XFOIL by specifying its 4-digit code.
        "",                                             # Exit    the LOAD menu.
        "PPAR",                                         # PPAR -> to set up the paneling of the airfoil in XFOIL.
        f"N {n_panels}",                                # N    -> to set the size of the mesh. Higher numbers can increase accuracy but also increases signiificant computation time.
        "",                                             # Exit    the Mesh menu.
        "",                                             # Exit    the PPAR menu.
        "OPER",                                         # OPER -> to set up the operating conditions for the simulation in XFOIL.
        f"VISC 1",                                      # VISC -> to turn on viscosity in XFOIL, which is necessary for calculating the polar. (1 true, 0 false)
        f"Re {re:.0f}",                                 # Re   -> to set the Reynolds number for the simulation in XFOIL. The Reynolds number is a dimensionless quantity that describes the flow characteristics around the airfoil.
        f"MACH {mach:.4f}",                             # MACH -> to set the Mach number for the simulation in XFOIL.
        f"ITER {n_ITER}",                               # ITER -> to set the maximum number of iterations for the simulation in XFOIL.
        "PACC",                                         # PACC -> to set up the polar accumulation in XFOIL, which is necessary for saving the polar data to a file.
        polar_path,                                     # Path -> to save the polar data file. This file will contain the results of the simulation, including the lift and drag coefficients at different angles of attack.
        "",                                             # Exit    the PACC Path menu.
        f"ASEQ {alpha_start} {alpha_end} {alpha_step}", # ASEQ -> to set up the angle of attack sequence for the simulation in XFOIL. This command will run the simulation for a range of angles of attack, starting from alpha_start, ending at alpha_end, and incrementing by alpha_step.
        "PACC",                                         # PACC -> to stop the polar accumulation in XFOIL after the simulation is complete.
        "",                                             # Exit    the OPER menu.
        "QUIT"                                          # QUIT -> to exit XFOIL after the simulation is complete.
    ]
    with open(script_path, "w") as f:
        f.write("\n".join(cmds) + "\n") # Write the list of commands to the script file, with each command on a new line. This script can then be executed in XFOIL to run the simulation and save the results to the specified polar file.