from dataclasses import dataclass, field
from ambiance import Atmosphere

# ============================================================
# GENERATING FLIGHT CONDITIONS AND ATMOSPHERIC PROPERTIES
# ============================================================

@dataclass
class FlightConditions:
    altitude:   float           # meters
    velocity:   float           # m/s
    target_cl:  float
    chord_size: float = 1.0     # meters

    rho:        float = field(init=False)   # alias for density
    mi:         float = field(init=False)   # alias for dynamic viscosity
    reynolds:   float = field(init=False)   # Reynolds number
    mach:       float = field(init=False)   # Mach number

    def __post_init__(self):
        atmosphere      = Atmosphere(self.altitude)
        self.rho        = float(atmosphere.density[0])
        self.mi         = float(atmosphere.dynamic_viscosity[0])
        self.reynolds   = (self.rho * self.velocity * self.chord_size) / self.mi
        self.mach       = self.velocity / float(atmosphere.speed_of_sound[0])

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