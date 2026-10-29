"""Physical constants and reference properties used across simcore (SI units)."""
from __future__ import annotations

from typing import ClassVar


class Constants:
    """Physical constants and fixed reference properties. All SI."""

    T_ZERO_C: ClassVar[float] = 273.15          # K at 0 °C
    P_ATM: ClassVar[float] = 101325.0           # Pa, standard atmosphere (ISO 2533)
    G: ClassVar[float] = 9.80665                # m/s², standard gravity (CGPM 1901)
    SIGMA: ClassVar[float] = 5.670374419e-8     # W/(m²·K⁴), Stefan–Boltzmann (CODATA 2018)
    R_UNIVERSAL: ClassVar[float] = 8.314462618  # J/(mol·K) (CODATA 2018)

    # Moist air (ASHRAE Handbook — Fundamentals 2009, ch. 1)
    CP_DRY_AIR: ClassVar[float] = 1006.0        # J/(kg·K)
    CP_VAPOUR: ClassVar[float] = 1860.0         # J/(kg·K)
    H_FG_0C: ClassVar[float] = 2501e3           # J/kg, latent heat of vaporisation at 0 °C
    H_SF: ClassVar[float] = 333.5e3             # J/kg, latent heat of fusion of ice at 0 °C
    EPS_WATER_AIR: ClassVar[float] = 0.62198    # –, M_w / M_da

    # Liquid water, representative of 20–60 °C hydronic circuits
    CP_WATER: ClassVar[float] = 4186.0          # J/(kg·K)
    RHO_WATER: ClassVar[float] = 985.0          # kg/m³ (≈ 55 °C)
