"""
Configuration and parameter specifications for the Plantpost modelling suite.
All parameters represent the validated engineering baseline established during
the University of Bologna (UNIBO Incubator) development and Bugnion IP Award.
"""

from dataclasses import dataclass, field
from typing import Tuple, Dict


@dataclass(frozen=True)
class GeometricConfig:
    """Geometric and structural specifications of the Plantpost street pole."""
    height_post_m: float = 4.50
    diameter_canopy_m: float = 2.00
    area_catchment_m2: float = 3.14159  # pi * (D/2)^2
    n_tiers: int = 4
    tier_heights_m: Tuple[float, float, float, float] = (1.0, 2.0, 3.0, 4.0)
    area_tank_m2: float = 0.15  # Footprint of internal base water storage column
    volume_tank_max_l: float = 150.0  # Total water capacity (1.0 m max height)
    tank_height_max_m: float = 1.00  # 150 L / (0.15 m^2 * 1000 L/m^3)
    foliage_area_per_tier_m2: float = 0.25  # Plan area of each planter tier
    foliage_area_total_m2: float = 1.00


@dataclass(frozen=True)
class ElectricalConfig:
    """Electrical, photovoltaic canopy, and LiFePO4 battery storage parameters."""
    # Monocrystalline PV canopy
    pv_efficiency_ref: float = 0.215  # 21.5% cell efficiency at STC
    pv_temp_coeff_per_k: float = -0.0038  # -0.38%/K power derating
    mppt_efficiency: float = 0.98  # Maximum Power Point Tracker efficiency
    bos_dirt_wiring_efficiency: float = 0.95  # Soiling, cabling and mismatch factor
    bos_combined_efficiency: float = 0.98 * 0.95  # 0.931
    # Canopy conical curvature & orientation derating factor (calibrated to UNIBO CAD model 258.1 kWh/yr)
    canopy_geometry_factor: float = 0.2635

    # Loads
    power_light_w: float = 47.1  # High-CRI LED luminaire (as per Excel BOM)
    power_aux_w: float = 1.5  # BMS, microcontroller, and sensor quiescent draw
    twilight_elevation_deg: float = -6.0  # Civil twilight threshold for dusk-to-dawn lighting

    # LiFePO4 Battery Microgrid
    battery_nominal_voltage_v: float = 12.8  # 4S LiFePO4 pack
    battery_nominal_capacity_kwh: float = 1.28  # 100 Ah @ 12.8 V baseline
    battery_max_dod: float = 0.80  # 80% maximum depth of discharge
    battery_soc_min: float = 0.20  # Reserve capacity floor (0.20 SoC)
    battery_soc_max: float = 1.00  # 100% full charge ceiling
    battery_initial_soc: float = 0.85  # Starting SoC on January 1
    battery_roundtrip_efficiency: float = 0.92  # Coulombic round-trip efficiency
    battery_charge_efficiency: float = 0.959166  # sqrt(0.92)
    battery_discharge_efficiency: float = 0.959166  # sqrt(0.92)
    subzero_charge_derate: float = 0.20  # Current derate below 0°C to prevent lithium plating


@dataclass(frozen=True)
class HydraulicConfig:
    """Rainwater harvesting, storage mass balance, and micro-pump hydraulic parameters."""
    runoff_coefficient: float = 0.90  # Sealed composite dish catchment surface
    filter_efficiency: float = 0.95  # First-flush self-cleaning mesh filter
    irrigation_drip_efficiency: float = 0.90  # Pressure-compensating sub-surface drip
    baseline_irrigation_l_day: float = 1.096  # Exact baseline demand from Excel sheet (0.274 L/tier)
    tank_initial_volume_l: float = 75.0  # Initial water level on Jan 1 (50% full)

    # Fluid properties & micro-pump
    fluid_density_kg_m3: float = 1000.0  # Fresh water density
    gravity_m_s2: float = 9.81
    pump_efficiency: float = 0.70  # Centrifugal brushless DC micro-submersible pump
    pipe_internal_diameter_m: float = 0.008  # 8 mm food-grade PE manifold
    pipe_roughness_m: float = 0.0000015  # Commercial smooth plastic pipe
    emitter_operating_head_m: float = 2.00  # Emitter minimum operating pressure head (~0.2 bar)
    nominal_flow_rate_l_min: float = 0.90  # 0.000015 m^3/s delivery rate
    water_viscosity_m2_s: float = 1.004e-6  # Kinematic viscosity of water at 20°C


@dataclass(frozen=True)
class EcosystemConfig:
    """Urban microclimate, particulate air filtration, and carbon offset parameters."""
    latent_heat_vaporization_j_kg: float = 2.45e6  # Latent heat of vaporization at ~20°C
    
    # Grid carbon intensity (g CO2e / kWh)
    grid_carbon_italy_g_kwh: float = 260.0
    grid_carbon_uk_g_kwh: float = 180.0

    # Public lighting displacement baselines
    hps_baseline_power_w: float = 150.0  # High-Pressure Sodium municipal streetlight
    grid_led_baseline_power_w: float = 50.0  # Modern grid-tied LED luminaire

    # Atmospheric Particulate Deposition Parameters
    pm_deposition_velocity_m_s: float = 0.005  # 5 mm/s dry deposition velocity for urban foliage
    
    # Ambient particulate matter concentrations (annual mean, ug/m^3)
    pm_concentrations: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        'bologna': {'pm25': 22.0, 'pm10': 35.0},
        'edinburgh': {'pm25': 7.0, 'pm10': 12.0},
        'london': {'pm25': 11.0, 'pm10': 18.0}
    })


@dataclass(frozen=True)
class CityLocation:
    """Geographic metadata for simulation anchor cities."""
    name: str
    country: str
    latitude: float
    longitude: float
    elevation_m: float
    climate_class: str


CITIES = {
    'bologna': CityLocation(
        name='Bologna',
        country='Italy',
        latitude=44.4949,
        longitude=11.3426,
        elevation_m=54.0,
        climate_class='Cfa (Mediterranean Continental)'
    ),
    'edinburgh': CityLocation(
        name='Edinburgh',
        country='UK',
        latitude=55.9533,
        longitude=-3.1883,
        elevation_m=41.0,
        climate_class='Cfb (Temperate Oceanic / Maritime)'
    ),
    'london': CityLocation(
        name='London',
        country='UK',
        latitude=51.5074,
        longitude=-0.1278,
        elevation_m=25.0,
        climate_class='Cfb (Temperate Oceanic)'
    )
}

