from __future__ import annotations

import numpy as np


def generator(code: str, n_points: int) -> tuple[np.ndarray, np.ndarray]:
    """Gera coordenadas (x, y) de um perfil NACA 4 dígitos."""
    M = int(code[0]) / 100.0
    P = int(code[1]) / 10.0
    T = int(code[2:4]) / 100.0

    beta = np.linspace(0, np.pi, n_points)
    x = (1 - np.cos(beta)) / 2

    yt = (T / 0.2) * (
        0.2969 * np.sqrt(x)
        - 0.1260 * x
        - 0.3516 * x**2
        + 0.2843 * x**3
        - 0.1036 * x**4
    )

    if M == 0.0 or P == 0.0:
        yc = np.zeros_like(x)
        dyc_dx = np.zeros_like(x)
    else:
        yc = np.where(
            x < P,
            (M / P**2) * (2 * P * x - x**2),
            (M / (1 - P) ** 2) * (1 - 2 * P + 2 * P * x - x**2),
        )
        dyc_dx = np.where(
            x < P,
            (2 * M / P**2) * (P - x),
            (2 * M / (1 - P) ** 2) * (P - x),
        )

    theta = np.arctan(dyc_dx)

    xU = x - yt * np.sin(theta)
    yU = yc + yt * np.cos(theta)
    xL = x + yt * np.sin(theta)
    yL = yc - yt * np.cos(theta)

    x_full = np.concatenate([xU[::-1], xL[1:]])
    y_full = np.concatenate([yU[::-1], yL[1:]])

    return x_full, y_full