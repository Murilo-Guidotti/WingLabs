def analyze_with_xfoil(x: np.ndarray, y: np.ndarray, cond: FlightConditions,
                       nome: str = "perfil", cfg: dict | None = None) -> dict | None:
    """
    Roda o XFOIL para um perfil e retorna os coeficientes aerodinâmicos.
    Thread-safe: cada chamada usa seu próprio diretório temporário.
    """
    if cfg is None:
        cfg = {}

    alpha_start = cfg.get("alpha_start", 0.0)
    alpha_end   = cfg.get("alpha_end",   20.0)
    alpha_step  = cfg.get("alpha_step",   0.5)
    n_panels    = cfg.get("n_panels",    240)
    n_ITER      = cfg.get("n_ITER",      100)

    with tempfile.TemporaryDirectory() as tmpdir:
        dat_path    = os.path.join(tmpdir, "perfil.dat")
        script_path = os.path.join(tmpdir, "script.in")
        polar_path  = os.path.join(tmpdir, "polar.txt")

        _escreve_dat(x, y, nome, dat_path)
        send_script(
            dat_path, polar_path, cond.reynolds, cond.mach,
            alpha_start, alpha_end, alpha_step, script_path, n_panels, n_ITER
        )

        try:
            subprocess.run(
                f'"{XFOIL_PATH}" < "{script_path}"',
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=45
            )
        except subprocess.TimeoutExpired:
            return None
        except FileNotFoundError:
            raise FileNotFoundError(
                f"xfoil.exe não encontrado em: {XFOIL_PATH}\n"
                "Coloque o xfoil.exe na mesma pasta do script."
            )

        resultados = _parseia_polar(polar_path)
        if not resultados:
            return None

        validos = [r for r in resultados if r["cd"] > 0 and r["cl"] > 0]
        if not validos:
            return None

        melhor = max(validos, key=lambda r: r["cl"] / r["cd"])
        return {
            "alpha_opt":  melhor["alpha"],
            "cl":         melhor["cl"],
            "cd":         melhor["cd"],
            "cm":         melhor["cm"],
            "efficiency": melhor["cl"] / melhor["cd"]
        }