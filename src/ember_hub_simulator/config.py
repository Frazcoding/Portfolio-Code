"""Configuration: TOML -> validated dataclasses.

All user-facing parameters live in ``config/baseline.toml`` in explicitly unit-suffixed keys. Validation ranges and the
metadata used by the web front end (label, unit, editable?, group) are declared once, in :attr:`Config.SPECS`. Text
fields (route and site names, site id) are free strings and are not range-checked.
"""
from __future__ import annotations

import dataclasses
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar


class ConfigError(ValueError):
    """The configuration is malformed or a value is outside its allowed range."""


@dataclass(frozen=True)
class RouteConfig:
    origin_name: str = "Bristol Coach Station, BS1 3EW"
    dest_name: str = "London Victoria Coach Station, SW1W 9TP"
    origin_lon: float = -2.593702
    origin_lat: float = 51.458905
    dest_lon: float = -0.14807
    dest_lat: float = 51.4926
    distance_km: float = 191.5
    drive_time_min: float = 187.0


@dataclass(frozen=True)
class TimetableConfig:
    headway_min: float = 60.0
    service_hours: float = 24.0
    days_per_week: float = 7.0
    turnaround_london_min: float = 15.0
    intermediate_break_min: float = 0.0
    first_departure_h: float = 0.0


@dataclass(frozen=True)
class BusConfig:
    battery_kWh: float = 621.0
    consumption_kWh_per_km: float = 1.1
    length_m: float = 13.9
    width_m: float = 2.55
    length_clearance_m: float = 1.1
    width_clearance_m: float = 1.45
    turning_circle_m: float = 24.0
    maintenance_spare: float = 0.0


@dataclass(frozen=True)
class HubConfig:
    charge_power_kW: float = 600.0
    charger_utilisation: float = 0.75
    backup_chargers: float = 1.0
    efficiency: float = 0.95
    aux_load_kVA: float = 40.0
    power_factor: float = 0.98
    min_soc_plug_in: float = 0.10
    gross_to_net: float = 3.5


@dataclass(frozen=True)
class DriversConfig:
    max_continuous_drive_min: float = 270.0
    mandatory_break_min: float = 45.0
    daily_drive_limit_min: float = 540.0
    hours_per_week: float = 40.0
    days_per_week: float = 5.0
    pre_shift_checks_min: float = 20.0
    post_shift_checks_min: float = 20.0
    break_london_min: float = 45.0
    spare_cover: float = 0.0


@dataclass(frozen=True)
class CostConfig:
    electricity_gbp_per_kWh: float = 0.22
    driver_gbp_per_h: float = 18.0
    coach_cost_gbp: float = 360000.0
    coach_life_yr: float = 15.0
    charger_capex_gbp: float = 150000.0
    charger_life_yr: float = 10.0
    grid_fixed_gbp: float = 75000.0
    grid_cable_gbp_per_m: float = 500.0
    grid_reinforcement_gbp_per_kVA: float = 150.0
    civils_gbp_per_m2: float = 120.0
    infrastructure_life_yr: float = 20.0
    discount_rate: float = 0.08


@dataclass(frozen=True)
class SiteConfig:
    id: str = "S1"
    name: str = "S1 Temple Works, Mead St BS3 4RP"
    lon: float = -2.582811
    lat: float = 51.445682
    deadrun_km: float = 3.3
    deadrun_min: float = 9.0
    area_m2: float = 9348.0
    lease_gbp_per_m2_yr: float = 25.0
    grid_distance_m: float = 1057.0
    spare_grid_kVA: float = 1000.0


@dataclass(frozen=True)
class SimConfig:
    horizon_h: float = 48.0
    dt_min: float = 1.0


@dataclass(frozen=True)
class ParamSpec:
    """Validation range and front-end metadata of one dotted config key."""

    key: str
    label: str
    unit: str
    lo: float
    hi: float
    step: float = 0.1
    editable: bool = False
    group: str = ""


@dataclass(frozen=True)
class Config:
    """Complete, validated parameter set for one simulation run."""

    route: RouteConfig = field(default_factory=RouteConfig)
    timetable: TimetableConfig = field(default_factory=TimetableConfig)
    bus: BusConfig = field(default_factory=BusConfig)
    hub: HubConfig = field(default_factory=HubConfig)
    drivers: DriversConfig = field(default_factory=DriversConfig)
    cost: CostConfig = field(default_factory=CostConfig)
    site: SiteConfig = field(default_factory=SiteConfig)
    sim: SimConfig = field(default_factory=SimConfig)

    _SECTIONS: ClassVar[dict[str, type]] = {"route": RouteConfig, "timetable": TimetableConfig, "bus": BusConfig,
                                            "hub": HubConfig, "drivers": DriversConfig, "cost": CostConfig,
                                            "site": SiteConfig, "sim": SimConfig}
    TEXT_KEYS: ClassVar[frozenset[str]] = frozenset({"route.origin_name", "route.dest_name", "site.id", "site.name"})

    # Groups "Route" and "Site" are set from the map / site picker; the others appear in the inputs panel.
    SPECS: ClassVar[tuple[ParamSpec, ...]] = (
        ParamSpec("route.origin_lon", "Origin longitude", "°", -180, 180, 1e-6, True, "Route"),
        ParamSpec("route.origin_lat", "Origin latitude", "°", -90, 90, 1e-6, True, "Route"),
        ParamSpec("route.dest_lon", "Destination longitude", "°", -180, 180, 1e-6, True, "Route"),
        ParamSpec("route.dest_lat", "Destination latitude", "°", -90, 90, 1e-6, True, "Route"),
        ParamSpec("route.distance_km", "Distance (one way)", "km", 5, 1500, 0.1, True, "Route"),
        ParamSpec("route.drive_time_min", "Drive time (one way)", "min", 5, 1200, 1, True, "Route"),
        ParamSpec("timetable.headway_min", "Frequency (headway)", "min", 5, 720, 5, True, "Timetable"),
        ParamSpec("timetable.service_hours", "Service hours per day", "h", 1, 24, 1, True, "Timetable"),
        ParamSpec("timetable.days_per_week", "Days per week", "d", 1, 7, 1, True, "Timetable"),
        ParamSpec("timetable.turnaround_london_min", "Turnaround at destination", "min", 0, 240, 5, True, "Timetable"),
        ParamSpec("timetable.intermediate_break_min", "Intermediate break", "min", 0, 120, 5, True, "Timetable"),
        ParamSpec("timetable.first_departure_h", "First departure", "h", 0, 23.75, 0.25, True, "Timetable"),
        ParamSpec("bus.battery_kWh", "Battery capacity", "kWh", 100, 1500, 1, True, "Coach"),
        ParamSpec("bus.consumption_kWh_per_km", "Energy consumption", "kWh/km", 0.4, 3.0, 0.05, True, "Coach"),
        ParamSpec("bus.length_m", "Coach length", "m", 10, 15, 0.1, True, "Coach"),
        ParamSpec("bus.width_m", "Coach width", "m", 2.0, 2.6, 0.05),
        ParamSpec("bus.length_clearance_m", "Length clearance", "m", 0, 5, 0.05),
        ParamSpec("bus.width_clearance_m", "Width clearance", "m", 0, 5, 0.05),
        ParamSpec("bus.turning_circle_m", "Turning circle", "m", 20, 28, 0.5, True, "Coach"),
        ParamSpec("bus.maintenance_spare", "Maintenance spare coaches", "–", 0, 20, 1, True, "Coach"),
        ParamSpec("hub.charge_power_kW", "Charger power", "kW", 50, 1500, 10, True, "Charging"),
        ParamSpec("hub.charger_utilisation", "Max charger utilisation", "–", 0.1, 1.0, 0.05, True, "Charging"),
        ParamSpec("hub.backup_chargers", "Backup chargers", "–", 0, 10, 1, True, "Charging"),
        ParamSpec("hub.efficiency", "Charger efficiency", "–", 0.5, 1.0, 0.01, True, "Charging"),
        ParamSpec("hub.aux_load_kVA", "Depot auxiliary load", "kVA", 0, 500, 5, True, "Charging"),
        ParamSpec("hub.power_factor", "Power factor", "–", 0.5, 1.0, 0.01, True, "Charging"),
        ParamSpec("hub.min_soc_plug_in", "Min. SOC at plug-in", "–", 0, 0.9, 0.01, True, "Charging"),
        ParamSpec("hub.gross_to_net", "Gross-to-net area factor", "–", 1, 10, 0.1, True, "Charging"),
        ParamSpec("drivers.max_continuous_drive_min", "Max continuous driving", "min", 60, 600, 5, True, "Drivers"),
        ParamSpec("drivers.mandatory_break_min", "Mandatory break", "min", 0, 120, 5, True, "Drivers"),
        ParamSpec("drivers.daily_drive_limit_min", "Daily driving limit", "min", 60, 900, 5, True, "Drivers"),
        ParamSpec("drivers.hours_per_week", "Contract hours per week", "h", 10, 60, 1, True, "Drivers"),
        ParamSpec("drivers.days_per_week", "Shifts per week (max)", "d", 1, 7, 1, True, "Drivers"),
        ParamSpec("drivers.pre_shift_checks_min", "Pre-shift checks", "min", 0, 60, 5, True, "Drivers"),
        ParamSpec("drivers.post_shift_checks_min", "Post-shift checks", "min", 0, 60, 5, True, "Drivers"),
        ParamSpec("drivers.break_london_min", "Driver break at destination", "min", 0, 120, 5, True, "Drivers"),
        ParamSpec("drivers.spare_cover", "Driver spare cover", "–", 0, 0.5, 0.01, True, "Drivers"),
        ParamSpec("cost.electricity_gbp_per_kWh", "Electricity price", "£/kWh", 0, 1, 0.01, True, "Costs"),
        ParamSpec("cost.driver_gbp_per_h", "Driver cost (loaded)", "£/h", 5, 60, 0.5, True, "Costs"),
        ParamSpec("cost.coach_cost_gbp", "Coach cost", "£/coach", 0, 1.5e6, 5000, True, "Costs"),
        ParamSpec("cost.coach_life_yr", "Coach life", "yr", 1, 30, 1, True, "Costs"),
        ParamSpec("cost.charger_capex_gbp", "Charger capex (installed)", "£/charger", 0, 1e6, 5000, True, "Costs"),
        ParamSpec("cost.charger_life_yr", "Charger life", "yr", 1, 30, 1, True, "Costs"),
        ParamSpec("cost.grid_fixed_gbp", "Grid connection fixed cost", "£", 0, 1e6, 5000, True, "Costs"),
        ParamSpec("cost.grid_cable_gbp_per_m", "Grid cable cost", "£/m", 0, 5000, 10, True, "Costs"),
        ParamSpec("cost.grid_reinforcement_gbp_per_kVA", "Grid reinforcement", "£/kVA", 0, 2000, 10, True, "Costs"),
        ParamSpec("cost.civils_gbp_per_m2", "Site works and civils", "£/m²", 0, 1000, 5, True, "Costs"),
        ParamSpec("cost.infrastructure_life_yr", "Infrastructure life", "yr", 1, 60, 1, True, "Costs"),
        ParamSpec("cost.discount_rate", "Discount rate", "–", 0, 0.3, 0.005, True, "Costs"),
        ParamSpec("site.lon", "Site longitude", "°", -180, 180, 1e-6, True, "Site"),
        ParamSpec("site.lat", "Site latitude", "°", -90, 90, 1e-6, True, "Site"),
        ParamSpec("site.deadrun_km", "Dead-run distance", "km", 0, 100, 0.1, True, "Site"),
        ParamSpec("site.deadrun_min", "Dead-run time", "min", 0, 180, 1, True, "Site"),
        ParamSpec("site.area_m2", "Site area", "m²", 500, 500000, 10, True, "Site"),
        ParamSpec("site.lease_gbp_per_m2_yr", "Land lease", "£/m²/yr", 0, 500, 0.5, True, "Site"),
        ParamSpec("site.grid_distance_m", "Distance to 33 kV primary", "m", 0, 20000, 1, True, "Site"),
        ParamSpec("site.spare_grid_kVA", "Spare grid capacity", "kVA", 0, 20000, 50, True, "Site"),
        ParamSpec("sim.horizon_h", "Simulated period", "h", 24, 168, 24, True, "Simulation"),
        ParamSpec("sim.dt_min", "Time step", "min", 0.5, 10, 0.5),
    )

    # ------------------------------------------------------------------ construction
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """Build and validate a Config from a nested dict (as produced by ``tomllib``)."""
        data = dict(data)
        data.pop("inputs", None)   # written by simcore Run into config.toml (input file list), not a parameter
        unknown = set(data) - set(cls._SECTIONS)
        if unknown:
            raise ConfigError(f"unknown top-level keys: {sorted(unknown)}")
        kwargs: dict[str, Any] = {}
        for name, section_cls in cls._SECTIONS.items():
            sect = dict(data.get(name, {}))
            valid = {f.name for f in dataclasses.fields(section_cls)}
            bad = set(sect) - valid
            if bad:
                raise ConfigError(f"[{name}] unknown keys: {sorted(bad)}")
            kwargs[name] = section_cls(**sect)
        cfg = cls(**kwargs)
        cfg.validate()
        return cfg

    @classmethod
    def from_toml(cls, path: str | Path) -> "Config":
        path = Path(path)
        try:
            with open(path, "rb") as fh:
                return cls.from_dict(tomllib.load(fh))
        except FileNotFoundError as e:
            raise ConfigError(f"config file not found: {path}") from e
        except tomllib.TOMLDecodeError as e:
            raise ConfigError(f"{path}: invalid TOML: {e}") from e

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    # ------------------------------------------------------------------ access
    def get(self, key: str) -> Any:
        """Value at a dotted key, e.g. ``cfg.get("hub.charge_power_kW")``."""
        obj: Any = self
        for part in key.split("."):
            obj = getattr(obj, part)
        return obj

    def with_overrides(self, overrides: dict[str, Any]) -> "Config":
        """Copy with dotted-key overrides applied, e.g. ``{"hub.charge_power_kW": 450}``; re-validated."""
        sections: dict[str, dict[str, Any]] = {}
        known = {s.key for s in self.SPECS} | self.TEXT_KEYS
        for key, value in overrides.items():
            if key not in known:
                raise ConfigError(f"unknown parameter '{key}'")
            if key in self.TEXT_KEYS:
                value = str(value)
            sec, name = key.split(".", 1)
            sections.setdefault(sec, {})[name] = value
        top = {sec: dataclasses.replace(getattr(self, sec), **vals) for sec, vals in sections.items()}
        cfg = dataclasses.replace(self, **top)
        cfg.validate()
        return cfg

    def validate(self) -> None:
        for spec in self.SPECS:
            value = self.get(spec.key)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ConfigError(f"{spec.key}: expected a number, got {value!r}")
            if not (spec.lo <= value <= spec.hi):
                raise ConfigError(f"{spec.key} = {value:g} {spec.unit} is outside [{spec.lo:g}, {spec.hi:g}]")
        for key in self.TEXT_KEYS:
            if not isinstance(self.get(key), str):
                raise ConfigError(f"{key}: expected text")
        if self.timetable.service_hours * 60 < self.timetable.headway_min:
            raise ConfigError("timetable.service_hours must allow at least one departure (headway is longer)")

    @classmethod
    def editable_specs(cls) -> list[ParamSpec]:
        return [s for s in cls.SPECS if s.editable]


@dataclass(frozen=True)
class ProjectPaths:
    """Project folder layout, resolved from the package location (src/<pkg>/config.py -> project root)."""

    root: Path

    @classmethod
    def discover(cls) -> "ProjectPaths":
        return cls(Path(__file__).resolve().parents[2])

    @property
    def baseline(self) -> Path:
        return self.root / "config" / "baseline.toml"

    @property
    def results(self) -> Path:
        return self.root / "results"

    @property
    def data(self) -> Path:
        return self.root / "data"

    @property
    def cache(self) -> Path:
        return self.root / "data" / "cache"

    @property
    def docs(self) -> Path:
        return self.root / "docs"

    @property
    def figures(self) -> Path:
        return self.root / "docs" / "figures"

    @property
    def app_server(self) -> Path:
        return self.root / "app" / "server.py"
