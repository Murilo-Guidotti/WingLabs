import numpy as np

def generator(code: str, n_points: int) -> tuple[np.ndarray, np.ndarray]:

    M = int(code[0])    / 100      # first digit
    P = int(code[1])    / 10       # second digit
    T = int(code[2:4])  / 100      # third and fourth digits

    beta = np.linspace(0, np.pi, n_points)
    x    = (1 - np.cos(beta)) / 2

    yt = (T / 0.2) * (          # generate thickness distribution or a symmetric airfoil if M and P are zero
          0.2969 * np.sqrt(x)
        - 0.1260 * x            
        - 0.3516 * x**2
        + 0.2843 * x**3         
        - 0.1036 * x**4         
    )                           # the entire formula -> Yt = (T/0.2) [0.2969*√ⅹ - 0.1260*ⅹ - 0.3516*ⅹ² + 0.2843*ⅹ³ - 0.1015*ⅹ⁴]
                                # ▧ if zero-thickness trailing edge is required, one of the coefficients should be modified such that they sum to zero.  ▧
                                # ▧ Modifying the last coefficient (i.e. to −0.1036) results in the smallest change to the overall shape of the airfoil. ▧

    yc = np.where(
        x < P,                                     
        (M / P**2) * (2*P*x - x**2),                    # if 0 ≤ ⅹ ≤ P      complete formula -> Yc = (M/P²) [2Px - x²]
        (M / (1-P)**2) * (1 - 2*P + 2*P*x - x**2)       # if P ≤ ⅹ ≤ 1      complete formula -> Yc = (M/(1-P)²) [(1 - 2P) + 2Px - x²]
    )

    dyc_dx = np.where(
        x < P,
        (2*M / P**2) * (P - x),                         # if 0 ≤ ⅹ ≤ P      complete formula -> dYc/dx = (2M/P²) [P - x]
        (2*M / (1-P)**2) * (P - x)                      # if P ≤ ⅹ ≤ 1      complete formula -> dYc/dx = (2M/(1-P)²) [P - x]
    )

    theta = np.arctan(dyc_dx)

    xU = x  - yt * np.sin(theta)    # ⅹu = ⅹ - yt * sin(θ)
    yU = yc + yt * np.cos(theta)    # yU = yc + yt * cos(θ)
    xL = x  + yt * np.sin(theta)    # ⅹl = ⅹ + yt * sin(θ)
    yL = yc - yt * np.cos(theta)    # yL = yc - yt * cos(θ)

    x_full = np.concatenate([xU[::-1], xL[1:]])
    y_full = np.concatenate([yU[::-1], yL[1:]])

    return x_full, y_full