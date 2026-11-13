from __future__ import annotations

from dataclasses import dataclass, field
import math

try:
    from ambiance import Atmosphere as _AmbianceAtmosphere
    _HAS_AMBIANCE = True
except ImportError:
    _HAS_AMBIANCE = False

GRAVITY = 9.80665


def _isa_properties(altitude_m: float) -> tuple[float, float, float]:
    """Calcula (rho, mu, speed_of_sound) pela atmosfera padrão ISA."""
    if _HAS_AMBIANCE:
        atm = _AmbianceAtmosphere(altitude_m)
        return (
            float(atm.density[0]),
            float(atm.dynamic_viscosity[0]),
            float(atm.speed_of_sound[0]),
        )

    # Fallback analítico ISA (troposfera <= 11 km e baixa estratosfera <= 20 km)
    h = max(0.0, min(float(altitude_m), 20000.0))
    T0 = 288.15
    P0 = 101325.0
    R = 287.05287
    gamma = 1.4
    L = -0.0065

    if h <= 11000.0:
        T = T0 + L * h
        P = P0 * (T / T0) ** (-GRAVITY / (R * L))
    else:
        T11 = T0 + L * 11000.0
        P11 = P0 * (T11 / T0) ** (-GRAVITY / (R * L))
        T = T11
        P = P11 * math.exp(-GRAVITY * (h - 11000.0) / (R * T11))

    rho = P / (R * T)
    # Lei de Sutherland para viscosidade dinâmica do ar
    mu = 1.458e-6 * (T ** 1.5) / (T + 110.4)
    a = math.sqrt(gamma * R * T)
    return rho, mu, a


def speed_of_sound(altitude_m: float) -> float:
    _, _, a = _isa_properties(altitude_m)
    return a


def wing_area_m2(span_mm: float, root_chord_mm: float, tip_chord_mm: float | None = None) -> float:
    """Área alar trapezoidal S = b * (c_raiz + c_ponta) / 2 em m²."""
    if tip_chord_mm is None:
        tip_chord_mm = root_chord_mm
    b_m = span_mm / 1000.0
    c_mean_m = (root_chord_mm + tip_chord_mm) / 2000.0
    return max(1e-6, b_m * c_mean_m)


def required_cl(payload_kg: float, rho: float, velocity: float, area_m2: float) -> float:
    """CL mínimo necessário para sustentar a carga (L = W = m * g) no cenário de voo."""
    q = 0.5 * rho * (velocity ** 2)
    if q <= 0 or area_m2 <= 0:
        raise ValueError("Velocidade, densidade e área da asa devem ser positivas.")
    weight_n = payload_kg * GRAVITY
    return weight_n / (q * area_m2)


# ============================================================
# GENERATING FLIGHT CONDITIONS AND ATMOSPHERIC PROPERTIES
# ============================================================

@dataclass
class FlightConditions:
    altitude:   float           # meters
    velocity:   float           # m/s
    target_cl:  float
    chord_size: float = 1.0     # meters

    rho:        float = field(init=False)   # density (kg/m³)
    mi:         float = field(init=False)   # dynamic viscosity (Pa·s)
    reynolds:   float = field(init=False)   # Reynolds number
    mach:       float = field(init=False)   # Mach number

    def __post_init__(self):
        self.rho, self.mi, a = _isa_properties(self.altitude)
        self.reynolds = (self.rho * self.velocity * self.chord_size) / self.mi
        self.mach = self.velocity / a


def min_Cd(reynolds: float) -> float:
    if reynolds < 500_000:
        return 0.005
    elif reynolds < 5_000_000:
        return 0.002
    else:
        return 0.001


def max_efficiency(reynolds: float) -> float:
    if reynolds < 500_000:
        return 60.0
    elif reynolds < 2_000_000:
        return 100.0
    else:
        return 150.0