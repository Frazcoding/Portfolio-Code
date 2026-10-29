"""Ember Bristol-London coach charging hub: operations, cost and site model.

Two parts:

* :class:`HubModel` is a line-by-line port of the Ember Google Sheet (tabs "Inputs & Variables" and "Site Selection",
  2026-10-27). For every candidate hub site it sizes the fleet, chargers, grid connection, drivers and hub area, checks
  battery / EU driving-hours / area feasibility and annualises the costs. Each method names the sheet cells it
  reproduces; ``tests/test_sheet_parity.py`` pins the sheet values.
* :class:`DaySimulation` is new: a time-stepped operating day (1 min steps) of the timetable with the sized fleet and
  chargers. Coaches are dispatched to departures, run the route, queue for a charger and recharge, so the sheet's steady
  state assumptions (charge time, slack, peak load) can be seen and checked minute by minute. It drives the playhead.

This is an operations / cost model, not physics, so it composes nothing from simcore except unit conversion. The cost
annuity and substation size table are project-level relations (sheet formulas), not candidates for simcore.

Internally everything is SI (s, m, J, W, VA, £); the output frame is converted to min / km / kWh / kW / kVA at the edge.
One deliberate deviation from the sheet: annual totals use ``365 x days_per_week / 7`` operating days (the sheet uses 365
whatever the days per week); at the baseline 7 days per week the two are identical.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, ClassVar

import numpy as np
import pandas as pd
from simcore.core import Units

from .config import Config
from .design import HubDesign

MIN_S = 60.0
H_S = 3600.0
DAY_S = 86400.0


# ---------------------------------------------------------------------------------------------------------------------
# parameters (SI)
# ---------------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Params:
    """Model parameters in SI (s, m, J, W, VA, £), built from the user-facing :class:`~.config.Config`."""

    # route + timetable
    distance_m: float
    drive_s: float
    headway_s: float
    service_s: float
    days_per_week: float
    turnaround_s: float
    intermediate_break_s: float
    first_departure_s: float
    # coach
    battery_J: float
    consumption_J_per_m: float
    bus_length_m: float
    bus_width_m: float
    length_clearance_m: float
    width_clearance_m: float
    turning_circle_m: float
    maintenance_spare: int
    # charging hub
    charge_power_W: float
    charger_utilisation: float
    backup_chargers: int
    efficiency: float
    aux_VA: float
    power_factor: float
    min_soc_plug_in: float
    gross_to_net: float
    # drivers
    max_continuous_drive_s: float
    mandatory_break_s: float
    daily_drive_limit_s: float
    driver_week_s: float
    driver_days_per_week: float
    checks_s: float
    pre_checks_s: float
    post_checks_s: float
    break_dest_s: float
    spare_cover: float
    # costs
    electricity_gbp_per_J: float
    driver_gbp_per_s: float
    coach_cost_gbp: float
    coach_life_yr: float
    charger_capex_gbp: float
    charger_life_yr: float
    grid_fixed_gbp: float
    grid_cable_gbp_per_m: float
    grid_reinforcement_gbp_per_VA: float
    civils_gbp_per_m2: float
    infrastructure_life_yr: float
    discount_rate: float
    # simulation
    horizon_s: float
    dt_s: float

    # sheet 2.3 fixed hub assets: (label, length m, width m, quantity) - quantities that scale are set in HubModel.area
    SUBSTATION_M2: ClassVar[float] = 3.8 * 2.8
    CHARGER_M2: ClassVar[float] = 1.0 * 1.5
    OFFICE_M2: ClassVar[float] = round(12.19 * 2.44, 2)
    REST_M2: ClassVar[float] = 2 * round(12.19 * 2.44, 2)
    CAR_SPACE_M2: ClassVar[float] = 4.8 * 2.4
    CAR_SPACES_PER_PEAK_DRIVER: ClassVar[int] = 2   # shift changeover (IV!H39; 16 bays on EMB-HUB-003)
    WASH_M2: ClassVar[float] = 20.0 * 6.0
    TURNING_FACTOR: ClassVar[float] = 1.85      # swept area = 1.85 x turning-circle disc (sheet I34)

    @classmethod
    def from_config(cls, c: Config) -> "Params":
        r, t, b, h, d, k, s = c.route, c.timetable, c.bus, c.hub, c.drivers, c.cost, c.sim
        return cls(
            distance_m=r.distance_km * 1000.0, drive_s=r.drive_time_min * MIN_S,
            headway_s=t.headway_min * MIN_S, service_s=t.service_hours * H_S, days_per_week=t.days_per_week,
            turnaround_s=t.turnaround_london_min * MIN_S, intermediate_break_s=t.intermediate_break_min * MIN_S,
            first_departure_s=t.first_departure_h * H_S,
            battery_J=Units.kWh_to_J(b.battery_kWh), consumption_J_per_m=Units.kWh_to_J(b.consumption_kWh_per_km) / 1000.0,
            bus_length_m=b.length_m, bus_width_m=b.width_m, length_clearance_m=b.length_clearance_m,
            width_clearance_m=b.width_clearance_m, turning_circle_m=b.turning_circle_m,
            maintenance_spare=int(round(b.maintenance_spare)),
            charge_power_W=Units.kW_to_W(h.charge_power_kW), charger_utilisation=h.charger_utilisation,
            backup_chargers=int(round(h.backup_chargers)), efficiency=h.efficiency, aux_VA=h.aux_load_kVA * 1000.0,
            power_factor=h.power_factor, min_soc_plug_in=h.min_soc_plug_in, gross_to_net=h.gross_to_net,
            max_continuous_drive_s=d.max_continuous_drive_min * MIN_S, mandatory_break_s=d.mandatory_break_min * MIN_S,
            daily_drive_limit_s=d.daily_drive_limit_min * MIN_S, driver_week_s=d.hours_per_week * H_S,
            driver_days_per_week=d.days_per_week, checks_s=(d.pre_shift_checks_min + d.post_shift_checks_min) * MIN_S,
            pre_checks_s=d.pre_shift_checks_min * MIN_S, post_checks_s=d.post_shift_checks_min * MIN_S,
            break_dest_s=d.break_london_min * MIN_S, spare_cover=d.spare_cover,
            electricity_gbp_per_J=k.electricity_gbp_per_kWh / Units.kWh_to_J(1.0), driver_gbp_per_s=k.driver_gbp_per_h / H_S,
            coach_cost_gbp=k.coach_cost_gbp, coach_life_yr=k.coach_life_yr, charger_capex_gbp=k.charger_capex_gbp,
            charger_life_yr=k.charger_life_yr, grid_fixed_gbp=k.grid_fixed_gbp, grid_cable_gbp_per_m=k.grid_cable_gbp_per_m,
            grid_reinforcement_gbp_per_VA=k.grid_reinforcement_gbp_per_kVA / 1000.0, civils_gbp_per_m2=k.civils_gbp_per_m2,
            infrastructure_life_yr=k.infrastructure_life_yr, discount_rate=k.discount_rate,
            horizon_s=s.horizon_h * H_S, dt_s=s.dt_min * MIN_S,
        )

    # ------------------------------------------------------------------ derived (route level)
    @property
    def trips_per_day(self) -> float:
        """Return journeys per day (sheet I15 = (C8/24)/C7)."""
        return self.service_s / self.headway_s

    @property
    def trips_per_week(self) -> float:
        """Sheet I16 = I15 x C9."""
        return self.trips_per_day * self.days_per_week

    @property
    def operating_days_per_year(self) -> float:
        return 365.0 * self.days_per_week / 7.0

    @property
    def trips_per_year(self) -> float:
        return self.trips_per_day * self.operating_days_per_year

    @property
    def return_energy_J(self) -> float:
        """Route energy for one return trip, coach station to coach station (sheet C17 = 2 x C5 x I5)."""
        return 2.0 * self.distance_m * self.consumption_J_per_m

    @property
    def charger_VA(self) -> float:
        """Grid apparent power of one charger at full output (sheet C25 = O3 / (O6 x O8))."""
        return self.charge_power_W / (self.efficiency * self.power_factor)


# ---------------------------------------------------------------------------------------------------------------------
# project-level relations (sheet formulas)
# ---------------------------------------------------------------------------------------------------------------------
class Annuity:
    """Equivalent annual cost of a capital sum (spreadsheet ``PMT(rate, n, -pv)``)."""

    @staticmethod
    def payment(rate: float, years: float, pv: float) -> float:
        r"""$$ A = PV \frac{r}{1 - (1 + r)^{-n}} \quad (A = PV/n \text{ at } r = 0) $$"""
        if years <= 0:
            return 0.0
        if rate == 0:
            return pv / years
        return pv * rate / (1.0 - (1.0 + rate) ** -years)


class SubstationSizes:
    """Standard distribution transformer ratings (sheet Lookups!B2:B13, BS EN 60076), kVA."""

    SIZES_kVA: ClassVar[tuple[float, ...]] = (315, 500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3150, 4000)

    @classmethod
    def select_VA(cls, required_VA: float) -> float | None:
        """Smallest standard rating >= required (sheet XLOOKUP match mode 1); None above the largest ("> 4000")."""
        for s in cls.SIZES_kVA:
            if s * 1000.0 >= required_VA - 1e-6:
                return s * 1000.0
        return None


# ---------------------------------------------------------------------------------------------------------------------
# sites
# ---------------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class SiteCase:
    """One candidate hub site (sheet Site Selection 3.2), SI."""

    id: str
    name: str
    lon: float
    lat: float
    deadrun_m: float
    deadrun_s: float
    area_m2: float
    lease_gbp_m2_yr: float
    grid_distance_m: float
    spare_grid_VA: float
    meta: dict = field(default_factory=dict, compare=False)

    @classmethod
    def from_config(cls, c: Config) -> "SiteCase":
        s = c.site
        return cls(id=s.id, name=s.name, lon=s.lon, lat=s.lat, deadrun_m=s.deadrun_km * 1000.0, deadrun_s=s.deadrun_min * MIN_S,
                   area_m2=s.area_m2, lease_gbp_m2_yr=s.lease_gbp_per_m2_yr, grid_distance_m=s.grid_distance_m,
                   spare_grid_VA=s.spare_grid_kVA * 1000.0)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "SiteCase":
        """From the web / data-file shape (km, min, kVA)."""
        known = {"id", "name", "lon", "lat", "deadrun_km", "deadrun_min", "area_m2", "lease_gbp_per_m2_yr",
                 "grid_distance_m", "spare_grid_kVA"}
        return cls(id=str(d["id"]), name=str(d["name"]), lon=float(d["lon"]), lat=float(d["lat"]),
                   deadrun_m=float(d["deadrun_km"]) * 1000.0, deadrun_s=float(d["deadrun_min"]) * MIN_S,
                   area_m2=float(d["area_m2"]), lease_gbp_m2_yr=float(d["lease_gbp_per_m2_yr"]),
                   grid_distance_m=float(d["grid_distance_m"]), spare_grid_VA=float(d["spare_grid_kVA"]) * 1000.0,
                   meta={k: v for k, v in d.items() if k not in known})

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "lon": self.lon, "lat": self.lat, "deadrun_km": self.deadrun_m / 1000.0,
                "deadrun_min": self.deadrun_s / MIN_S, "area_m2": self.area_m2, "lease_gbp_per_m2_yr": self.lease_gbp_m2_yr,
                "grid_distance_m": self.grid_distance_m, "spare_grid_kVA": self.spare_grid_VA / 1000.0, **self.meta}


@dataclass
class SiteResult:
    """Sheet Site Selection 3.3 + 3.4 for one site (SI; see :meth:`to_dict` for display units)."""

    site: SiteCase
    energy_rotation_J: float
    soc_plug_in: float
    battery_ok: bool
    charge_s: float
    cycle_s: float
    fleet: int
    fleet_total: int
    active_chargers: int
    total_chargers: int
    peak_VA: float
    substation_VA: float | None
    driving_s: float
    shift_s: float
    eu_ok: bool
    shifts_per_driver_week: int
    drivers: int
    peak_drivers: int
    area_req_m2: float
    area_ok: bool
    feasible: bool
    costs_gbp_yr: dict[str, float]
    total_gbp_yr: float
    gbp_per_trip: float
    slack_s: float
    rank: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            **{f"site_{k}": v for k, v in self.site.to_dict().items() if k in ("id", "name", "lon", "lat")},
            "site": self.site.to_dict(),
            "energy_rotation_kWh": Units.J_to_kWh(self.energy_rotation_J), "soc_plug_in": self.soc_plug_in,
            "battery_ok": self.battery_ok, "charge_min": self.charge_s / MIN_S, "cycle_min": self.cycle_s / MIN_S,
            "slack_min": self.slack_s / MIN_S, "fleet": self.fleet, "fleet_total": self.fleet_total,
            "active_chargers": self.active_chargers, "total_chargers": self.total_chargers, "peak_kVA": self.peak_VA / 1000.0,
            "substation_kVA": None if self.substation_VA is None else self.substation_VA / 1000.0,
            "driving_min": self.driving_s / MIN_S, "shift_min": self.shift_s / MIN_S, "eu_ok": self.eu_ok,
            "shifts_per_driver_week": self.shifts_per_driver_week, "drivers": self.drivers, "peak_drivers": self.peak_drivers,
            "area_req_m2": self.area_req_m2, "area_ok": self.area_ok, "feasible": self.feasible,
            "costs_gbp_yr": dict(self.costs_gbp_yr), "total_gbp_yr": self.total_gbp_yr, "gbp_per_trip": self.gbp_per_trip,
            "rank": self.rank,
        }


# ---------------------------------------------------------------------------------------------------------------------
# sheet model
# ---------------------------------------------------------------------------------------------------------------------
class HubModel:
    """Port of the Ember sheet: sizing, feasibility and annual cost of a hub site for the route and timetable in ``p``.

    Cell references are to tab "Site Selection" unless prefixed ``IV!`` ("Inputs & Variables").
    """

    COST_ITEMS: ClassVar[tuple[str, ...]] = ("land_lease", "site_works", "chargers", "grid_connection", "fleet",
                                             "driver_wages", "electricity")

    def __init__(self, p: Params):
        self.p = p

    # ------------------------------------------------------------------ energy and charging
    def energy_rotation_J(self, s: SiteCase) -> float:
        """Energy per rotation incl. both dead runs (I13 = IV!C17 + 2 x I4 x IV!I5)."""
        return self.p.return_energy_J + 2.0 * s.deadrun_m * self.p.consumption_J_per_m

    def charge_s(self, s: SiteCase) -> float:
        """Time to put the rotation energy back at full charger output (I16 = I13 / IV!O3)."""
        return self.energy_rotation_J(s) / self.p.charge_power_W

    def cycle_s(self, s: SiteCase) -> float:
        """Coach return cycle (I17 = 2 x drive + turnaround + intermediate break + 2 x dead run + charge)."""
        p = self.p
        return 2 * p.drive_s + p.turnaround_s + p.intermediate_break_s + 2 * s.deadrun_s + self.charge_s(s)

    # ------------------------------------------------------------------ drivers
    def driving_s(self, s: SiteCase) -> float:
        """Driving per shift incl. dead runs (I24 = 2 x IV!C6 + 2 x I12)."""
        return 2 * self.p.drive_s + 2 * s.deadrun_s

    def shift_s(self, s: SiteCase) -> float:
        """Shift length (I25 = I24 + checks IV!C20 + destination break IV!I22)."""
        return self.driving_s(s) + self.p.checks_s + self.p.break_dest_s

    def eu_ok(self, s: SiteCase) -> bool:
        """I26: one leg incl. dead run <= max continuous driving, driving <= daily limit, break >= mandatory break."""
        p = self.p
        return (p.drive_s + s.deadrun_s <= p.max_continuous_drive_s + 1e-6 and self.driving_s(s) <= p.daily_drive_limit_s + 1e-6
                and p.break_dest_s >= p.mandatory_break_s - 1e-6)

    # ------------------------------------------------------------------ area
    def area_m2(self, fleet_total: int, total_chargers: int, peak_drivers: int) -> float:
        """Gross hub area (I30): net footprint of sheet 2.3 (bays x fleet, chargers, 2 car spaces per peak driver), x gross-to-net."""
        p = self.p
        bay = (p.bus_length_m + p.length_clearance_m) * (p.bus_width_m + p.width_clearance_m)
        turning = math.pi * (p.turning_circle_m / 2) ** 2 * Params.TURNING_FACTOR
        net = (fleet_total * bay + turning + Params.SUBSTATION_M2 + total_chargers * Params.CHARGER_M2 + Params.OFFICE_M2
               + Params.REST_M2 + Params.CAR_SPACES_PER_PEAK_DRIVER * peak_drivers * Params.CAR_SPACE_M2 + Params.WASH_M2)
        return net * p.gross_to_net

    # ------------------------------------------------------------------ evaluation
    def evaluate(self, s: SiteCase) -> SiteResult:
        p = self.p
        e_rot = self.energy_rotation_J(s)
        soc = 1.0 - e_rot / p.battery_J                                         # I14
        battery_ok = soc >= p.min_soc_plug_in - 1e-9                            # I15
        charge = self.charge_s(s)
        cycle = self.cycle_s(s)
        fleet = math.ceil(cycle / p.headway_s - 1e-9)                           # I18
        fleet_total = fleet + p.maintenance_spare                               # I19
        active = math.ceil((charge / p.headway_s) / p.charger_utilisation - 1e-9)  # I20
        total_ch = active + p.backup_chargers                                   # I21
        peak = total_ch * p.charger_VA + p.aux_VA                               # I22 (the standby charger is counted)
        substation = SubstationSizes.select_VA(peak / p.charger_utilisation)    # I23
        driving, shift = self.driving_s(s), self.shift_s(s)
        eu = self.eu_ok(s)
        shifts = int(min(p.driver_days_per_week, math.floor(p.driver_week_s / shift + 1e-9)))  # I27
        drivers = math.ceil(p.trips_per_week / max(shifts, 1) * (1 + p.spare_cover) - 1e-9) if shifts > 0 else 10**6  # I28
        peak_drivers = math.ceil(shift / p.headway_s - 1e-9)                    # I29
        area = self.area_m2(fleet_total, total_ch, peak_drivers)                # I30
        area_ok = area <= s.area_m2                                             # I31
        feasible = battery_ok and eu and area_ok and substation is not None and shifts > 0   # I32

        r, inf_life = p.discount_rate, p.infrastructure_life_yr
        reinforcement_VA = max(0.0, (substation if substation is not None else peak / p.charger_utilisation) - s.spare_grid_VA)
        costs = {
            "land_lease": s.area_m2 * s.lease_gbp_m2_yr,                                                    # I35
            "site_works": Annuity.payment(r, inf_life, area * p.civils_gbp_per_m2),                         # I36
            "chargers": Annuity.payment(r, p.charger_life_yr, total_ch * p.charger_capex_gbp),              # I37
            "grid_connection": Annuity.payment(r, inf_life, p.grid_fixed_gbp + s.grid_distance_m * p.grid_cable_gbp_per_m
                                               + reinforcement_VA * p.grid_reinforcement_gbp_per_VA),       # I38
            "fleet": fleet_total * p.coach_cost_gbp / p.coach_life_yr,                                      # I39 (straight line)
            "driver_wages": p.trips_per_year * shift * p.driver_gbp_per_s * (1 + p.spare_cover),           # I40
            "electricity": (p.trips_per_year * e_rot / p.efficiency
                            + p.aux_VA * p.power_factor * 8760 * H_S) * p.electricity_gbp_per_J,            # I41
        }
        total = sum(costs.values())                                                                         # I42
        return SiteResult(
            site=s, energy_rotation_J=e_rot, soc_plug_in=soc, battery_ok=battery_ok, charge_s=charge, cycle_s=cycle,
            fleet=fleet, fleet_total=fleet_total, active_chargers=active, total_chargers=total_ch, peak_VA=peak,
            substation_VA=substation, driving_s=driving, shift_s=shift, eu_ok=eu, shifts_per_driver_week=shifts,
            drivers=drivers, peak_drivers=peak_drivers, area_req_m2=area, area_ok=area_ok, feasible=feasible,
            costs_gbp_yr=costs, total_gbp_yr=total, gbp_per_trip=total / p.trips_per_year,                  # I43
            slack_s=fleet * p.headway_s - cycle,
        )

    def compare(self, sites: list[SiteCase]) -> list[SiteResult]:
        """Evaluate every site and rank the feasible ones by total annual cost (I44); infeasible sites get rank None."""
        res = [self.evaluate(s) for s in sites]
        feas = sorted((r for r in res if r.feasible), key=lambda r: r.total_gbp_yr)
        for i, r in enumerate(feas, 1):
            r.rank = i
        return res


# ---------------------------------------------------------------------------------------------------------------------
# operating-day simulation
# ---------------------------------------------------------------------------------------------------------------------
class Mode:
    """Coach states in the day simulation (also the integer codes in the output frame)."""

    PARKED, DEADRUN_OUT, OUTBOUND, TURNAROUND, INBOUND, DEADRUN_IN, QUEUED, CHARGING = range(8)
    LABELS: ClassVar[tuple[str, ...]] = ("Parked", "Dead run out", "Outbound", "Turnaround", "Inbound", "Dead run in",
                                         "Queued", "Charging")
    MOVING: ClassVar[frozenset[int]] = frozenset({1, 2, 4, 5})
    AT_HUB: ClassVar[frozenset[int]] = frozenset({0, 6, 7})


@dataclass
class Coach:
    """Mutable state of one coach during the day simulation (SI)."""

    idx: int
    soc_J: float
    mode: int = Mode.PARKED
    t_start: float = 0.0
    duration: float = 0.0
    charger: int = -1
    queued_at: float = 0.0
    trip: int = -1


@dataclass
class TripRecord:
    """One departure: scheduled and actual times (s from the simulation start) and the coach that ran it."""

    sched_dep: float
    coach: int = -1
    hub_leave: float = math.nan
    dep: float = math.nan
    arr_hub: float = math.nan
    plug_in: float = math.nan
    soc_plug_in: float = math.nan

    @property
    def delay_s(self) -> float:
        return self.dep - self.sched_dep


class DaySimulation:
    r"""Time-stepped operation of the hub with the sized fleet and chargers.

    Departures leave the origin coach station every headway during the service window, starting at ``first_departure``.
    At ``departure - dead run`` the coach at the hub with the most charge leaves, provided it holds the rotation energy plus
    the minimum plug-in SOC reserve; otherwise the departure waits (and runs late) until one does. A coach unplugs when
    dispatched. Legs: dead run, outbound (drive + half the intermediate break), turnaround, inbound, dead run. Back at
    the hub a coach joins a first-come-first-served queue for the active chargers (the standby charger is not used) and
    charges at constant power to full:

    $$ \frac{dE}{dt} = P_\mathrm{charger}, \qquad S_\mathrm{grid} = \frac{n_\mathrm{charging} P_\mathrm{charger}}{\eta\,\mathrm{PF}} + S_\mathrm{aux} $$

    Energy on each leg falls linearly with distance. The run starts with every coach full at the hub and simulates one
    warm-up day before the reported ``horizon``.
    """

    WARMUP_S: ClassVar[float] = DAY_S

    def __init__(self, p: Params, site: SiteResult):
        self.p = p
        self.r = site
        self.s = site.site

    def departures(self, t_end: float) -> list[float]:
        p = self.p
        out = []
        day = 0
        while day * DAY_S < t_end:
            k = 0
            while k * p.headway_s < p.service_s - 1e-6:
                t = day * DAY_S + p.first_departure_s + k * p.headway_s
                if t >= p.first_departure_s and t < t_end:
                    out.append(t)
                k += 1
            day += 1
        return sorted(out)

    def run(self) -> tuple[pd.DataFrame, list[TripRecord], dict[str, float]]:
        p, s = self.p, self.s
        dt = p.dt_s
        t_end = self.WARMUP_S + p.horizon_s
        n_all = int(round(t_end / dt))
        n_coach = self.r.fleet_total
        n_chg = self.r.active_chargers
        coaches = [Coach(i, p.battery_J) for i in range(n_coach)]
        chargers: list[int] = [-1] * n_chg
        trips = [TripRecord(t) for t in self.departures(t_end)]
        e_dead = s.deadrun_m * p.consumption_J_per_m
        e_leg = p.distance_m * p.consumption_J_per_m
        leg_s = {Mode.DEADRUN_OUT: s.deadrun_s, Mode.OUTBOUND: p.drive_s + p.intermediate_break_s / 2,
                 Mode.TURNAROUND: p.turnaround_s, Mode.INBOUND: p.drive_s + p.intermediate_break_s / 2,
                 Mode.DEADRUN_IN: s.deadrun_s}
        leg_e = {Mode.DEADRUN_OUT: e_dead, Mode.OUTBOUND: e_leg, Mode.TURNAROUND: 0.0, Mode.INBOUND: e_leg,
                 Mode.DEADRUN_IN: e_dead}
        need_J = self.r.energy_rotation_J + p.min_soc_plug_in * p.battery_J

        mode = np.zeros((n_all, n_coach), dtype=np.int8)
        prog = np.zeros((n_all, n_coach))
        soc = np.zeros((n_all, n_coach))
        chg_of = np.full((n_all, n_coach), -1, dtype=np.int8)
        pending = 0                          # index of the next trip not yet dispatched

        for i in range(n_all):
            t = i * dt
            # 1. dispatch every departure whose hub-leave time has come
            while pending < len(trips) and t >= trips[pending].sched_dep - s.deadrun_s - 1e-6:
                cands = [c for c in coaches if c.mode in Mode.AT_HUB and c.soc_J >= need_J - 1e-6]
                if not cands:
                    break                    # no coach ready: the departure waits and runs late
                c = max(cands, key=lambda c: (c.soc_J, -c.idx))
                if c.charger >= 0:
                    chargers[c.charger] = -1
                    c.charger = -1
                tr = trips[pending]
                tr.coach, tr.hub_leave = c.idx, t
                c.mode, c.t_start, c.duration, c.trip = Mode.DEADRUN_OUT, t, leg_s[Mode.DEADRUN_OUT], pending
                pending += 1
            # 2. advance coaches on the road
            for c in coaches:
                if c.mode in leg_s:
                    frac_prev = min(1.0, (t - dt - c.t_start) / c.duration) if c.duration > 0 else 1.0
                    frac = min(1.0, (t - c.t_start) / c.duration) if c.duration > 0 else 1.0
                    c.soc_J -= leg_e[c.mode] * max(0.0, frac - max(0.0, frac_prev))
                    if frac >= 1.0 - 1e-9:
                        tr = trips[c.trip]
                        nxt = c.mode + 1
                        t_done = c.t_start + c.duration
                        if c.mode == Mode.DEADRUN_OUT:
                            tr.dep = t_done
                        if nxt == Mode.QUEUED:
                            tr.arr_hub = t_done
                            c.mode, c.queued_at = Mode.QUEUED, t_done
                        else:
                            c.mode, c.t_start, c.duration = nxt, t_done, leg_s[nxt]
            # 3. chargers: finish full coaches, then serve the queue first come first served
            for c in coaches:
                if c.mode == Mode.CHARGING:
                    c.soc_J = min(p.battery_J, c.soc_J + p.charge_power_W * dt)
                    if c.soc_J >= p.battery_J - 1e-6:
                        chargers[c.charger] = -1
                        c.charger, c.mode = -1, Mode.PARKED
            queue = sorted((c for c in coaches if c.mode == Mode.QUEUED), key=lambda c: (c.queued_at, c.idx))
            for c in queue:
                free = [j for j, o in enumerate(chargers) if o < 0]
                if not free:
                    break
                chargers[free[0]] = c.idx
                c.charger, c.mode = free[0], Mode.CHARGING
                tr = trips[c.trip]
                tr.plug_in, tr.soc_plug_in = t, c.soc_J / p.battery_J
            # 4. record
            for c in coaches:
                mode[i, c.idx] = c.mode
                soc[i, c.idx] = c.soc_J / p.battery_J
                chg_of[i, c.idx] = c.charger
                if c.mode in leg_s and c.duration > 0:
                    prog[i, c.idx] = min(1.0, (t - c.t_start) / c.duration)

        k0 = int(round(self.WARMUP_S / dt))
        mode, prog, soc, chg_of = mode[k0:], prog[k0:], soc[k0:], chg_of[k0:]
        n = len(mode)
        t_h = np.arange(n) * dt / H_S
        n_charging = (mode == Mode.CHARGING).sum(axis=1)
        charge_kW = n_charging * Units.W_to_kW(p.charge_power_W)
        grid_kVA = (n_charging * p.charger_VA + p.aux_VA) / 1000.0
        # drivers on duty: sign-on before hub leave, sign-off after return to the hub
        abs_t = self.WARMUP_S + np.arange(n) * dt
        on_duty = np.zeros(n)
        for tr in trips:
            if math.isnan(tr.hub_leave):
                continue
            t_off = (tr.arr_hub if not math.isnan(tr.arr_hub) else math.inf) + p.post_checks_s
            on_duty += (abs_t >= tr.hub_leave - p.pre_checks_s) & (abs_t < t_off)
        delay_now = np.zeros(n)
        for tr in trips:
            if tr.sched_dep >= self.WARMUP_S and not math.isnan(tr.dep):
                delay_now[(abs_t >= tr.dep) & (abs_t < tr.dep + p.headway_s)] = max(0.0, tr.delay_s / MIN_S)

        cols: dict[str, Any] = {
            "t_h": t_h,
            "on_road": np.isin(mode, list(Mode.MOVING) + [Mode.TURNAROUND]).sum(axis=1),
            "at_hub": np.isin(mode, list(Mode.AT_HUB)).sum(axis=1),
            "charging": n_charging,
            "queued": (mode == Mode.QUEUED).sum(axis=1),
            "charge_kW": charge_kW,
            "grid_kVA": grid_kVA,
            "soc_mean_pct": 100 * soc.mean(axis=1),
            "soc_min_pct": 100 * soc.min(axis=1),
            "drivers_on_duty": on_duty,
            "delay_min": delay_now,
        }
        for j in range(n_coach):
            cols[f"c{j + 1}_mode"] = mode[:, j]
            cols[f"c{j + 1}_prog"] = prog[:, j]
            cols[f"c{j + 1}_soc"] = 100 * soc[:, j]
            cols[f"c{j + 1}_chg"] = chg_of[:, j]
        frame = pd.DataFrame(cols, index=pd.date_range("2026-01-05", periods=n, freq=pd.Timedelta(seconds=dt), name="time"))

        shown = [tr for tr in trips if self.WARMUP_S <= tr.sched_dep < t_end]
        ran = [tr for tr in shown if not math.isnan(tr.dep)]
        delays = np.array([max(0.0, tr.delay_s) for tr in ran]) / MIN_S
        plugged = [tr for tr in trips if self.WARMUP_S <= tr.plug_in < t_end]
        waits = np.array([tr.plug_in - tr.arr_hub for tr in plugged]) / MIN_S if plugged else np.zeros(1)
        socs = np.array([tr.soc_plug_in for tr in plugged]) if plugged else np.ones(1)
        days = p.horizon_s / DAY_S
        kpis = {
            "sim_departures": float(len(shown)),
            "sim_missed": float(len(shown) - len(ran)),
            "sim_on_time_pct": 100.0 * float((delays <= 1.0).sum()) / max(len(shown), 1),
            "sim_max_delay_min": float(delays.max()) if len(delays) else p.horizon_s / MIN_S,
            "sim_mean_queue_min": float(waits.mean()),
            "sim_max_queue_min": float(waits.max()),
            "sim_min_soc_plug_in_pct": 100.0 * float(socs.min()),
            "sim_peak_kVA": float(grid_kVA.max()),
            "sim_mean_kVA": float(grid_kVA.mean()),
            "sim_grid_kWh_per_day": float(Units.J_to_kWh((charge_kW * 1000.0 / p.efficiency + p.aux_VA * p.power_factor).sum() * dt) / days),
            "sim_charger_util_pct": 100.0 * float(n_charging.mean()) / max(n_chg, 1),
            "sim_peak_drivers": float(on_duty.max()),
        }
        return frame, trips, kpis


# ---------------------------------------------------------------------------------------------------------------------
# output
# ---------------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Variable:
    """One output column exposed to plots and the web front end."""

    key: str
    column: str
    label: str
    unit: str


@dataclass(frozen=True)
class KpiInfo:
    key: str
    label: str
    unit: str
    dec: int = 2


@dataclass
class SimOutput:
    """Operating-day frame (one row per time step), KPIs, site comparison and layout of one run."""

    frame: pd.DataFrame
    kpis: dict[str, float]
    sites: list[dict]
    selected: dict
    trips: list[dict]
    layout: dict
    params: Params = field(repr=False)

    VARIABLES: ClassVar[tuple[Variable, ...]] = (
        Variable("on_road", "on_road", "Coaches on the road", "–"),
        Variable("at_hub", "at_hub", "Coaches at the hub", "–"),
        Variable("charging", "charging", "Coaches charging", "–"),
        Variable("queued", "queued", "Coaches queuing", "–"),
        Variable("charge_kW", "charge_kW", "Charging power", "kW"),
        Variable("grid_kVA", "grid_kVA", "Site grid load", "kVA"),
        Variable("soc_mean", "soc_mean_pct", "Mean fleet SOC", "%"),
        Variable("soc_min", "soc_min_pct", "Lowest coach SOC", "%"),
        Variable("drivers", "drivers_on_duty", "Drivers on duty", "–"),
        Variable("delay", "delay_min", "Departure delay", "min"),
    )

    KPI_INFO: ClassVar[tuple[KpiInfo, ...]] = (
        KpiInfo("fleet", "Coaches in service", "–", 0),
        KpiInfo("fleet_total", "Fleet incl. spare", "–", 0),
        KpiInfo("total_chargers", "Chargers incl. backup", "–", 0),
        KpiInfo("active_chargers", "Active chargers", "–", 0),
        KpiInfo("peak_kVA", "Peak load (sheet)", "kVA", 0),
        KpiInfo("substation_kVA", "Substation size", "kVA", 0),
        KpiInfo("drivers", "Drivers required", "–", 0),
        KpiInfo("peak_drivers", "Peak drivers on shift", "–", 0),
        KpiInfo("shift_min", "Shift length", "min", 0),
        KpiInfo("cycle_min", "Coach return cycle", "min", 0),
        KpiInfo("charge_min", "Charge time", "min", 1),
        KpiInfo("slack_min", "Timetable slack", "min", 1),
        KpiInfo("soc_plug_in_pct", "SOC at plug-in", "%", 1),
        KpiInfo("energy_rotation_kWh", "Energy per rotation", "kWh", 1),
        KpiInfo("area_req_m2", "Hub area required", "m²", 0),
        KpiInfo("site_area_m2", "Site area", "m²", 0),
        KpiInfo("total_gbp_yr", "Annual cost", "£/yr", 0),
        KpiInfo("gbp_per_trip", "Cost per trip", "£/trip", 0),
        KpiInfo("trips_per_day", "Return trips per day", "–", 1),
        KpiInfo("feasible", "Feasible (1 = yes)", "–", 0),
        KpiInfo("battery_ok", "Battery check (1 = OK)", "–", 0),
        KpiInfo("eu_ok", "EU driving hours (1 = OK)", "–", 0),
        KpiInfo("area_ok", "Area check (1 = OK)", "–", 0),
        KpiInfo("rank", "Site rank (0 = excluded)", "–", 0),
        KpiInfo("sim_on_time_pct", "On-time departures (sim)", "%", 1),
        KpiInfo("sim_max_delay_min", "Worst delay (sim)", "min", 0),
        KpiInfo("sim_mean_queue_min", "Mean charger queue (sim)", "min", 1),
        KpiInfo("sim_max_queue_min", "Longest charger queue (sim)", "min", 0),
        KpiInfo("sim_min_soc_plug_in_pct", "Lowest SOC at plug-in (sim)", "%", 1),
        KpiInfo("sim_peak_kVA", "Peak grid load (sim)", "kVA", 0),
        KpiInfo("sim_mean_kVA", "Mean grid load (sim)", "kVA", 0),
        KpiInfo("sim_grid_kWh_per_day", "Grid energy per day (sim)", "kWh/d", 0),
        KpiInfo("sim_charger_util_pct", "Charger utilisation (sim)", "%", 1),
        KpiInfo("sim_peak_drivers", "Peak drivers on duty (sim)", "–", 0),
        KpiInfo("sim_departures", "Departures simulated", "–", 0),
        KpiInfo("sim_missed", "Departures not run (sim)", "–", 0),
        KpiInfo("design_lanes", "Drive-through lanes in the design", "–", 0),
        KpiInfo("layout_fits", "Fleet fits the hub design (1 = yes)", "–", 0),
    ) + tuple(KpiInfo(f"cost_{k}", f"Cost: {k.replace('_', ' ')}", "£/yr", 0) for k in HubModel.COST_ITEMS)

    @property
    def n_coaches(self) -> int:
        return int(self.selected["fleet_total"])

    def variables(self) -> list[Variable]:
        """Aggregate variables plus four per coach (mode, leg progress, SOC, charger index)."""
        out = list(self.VARIABLES)
        for j in range(1, self.n_coaches + 1):
            out += [Variable(f"c{j}_mode", f"c{j}_mode", f"Coach {j} state", "code"),
                    Variable(f"c{j}_prog", f"c{j}_prog", f"Coach {j} leg progress", "–"),
                    Variable(f"c{j}_soc", f"c{j}_soc", f"Coach {j} SOC", "%"),
                    Variable(f"c{j}_chg", f"c{j}_chg", f"Coach {j} charger", "index")]
        return out


# ---------------------------------------------------------------------------------------------------------------------
# simulation
# ---------------------------------------------------------------------------------------------------------------------
class Simulation:
    """Sheet model for the selected site and the alternatives, then the operating-day simulation of the selected site."""

    def __init__(self, params: Params, site: SiteCase, alternatives: list[SiteCase] | None = None,
                 design: HubDesign | None = None):
        self.p = params
        self.site = site
        self.alternatives = [a for a in (alternatives or []) if a.id != site.id]
        self.design = design

    @classmethod
    def from_config(cls, cfg: Config, alternatives: list[SiteCase] | None = None,
                    design: HubDesign | None = None) -> "Simulation":
        return cls(Params.from_config(cfg), SiteCase.from_config(cfg), alternatives, design)

    def run(self) -> SimOutput:
        model = HubModel(self.p)
        results = model.compare([self.site] + self.alternatives)
        sel = results[0]
        frame, trips, sim_kpis = DaySimulation(self.p, sel).run()
        d = sel.to_dict()
        kpis: dict[str, float] = {
            "fleet": d["fleet"], "fleet_total": d["fleet_total"], "total_chargers": d["total_chargers"],
            "active_chargers": d["active_chargers"], "peak_kVA": d["peak_kVA"],
            "substation_kVA": d["substation_kVA"] if d["substation_kVA"] is not None else 0.0,   # 0 = above 4,000 kVA
            "drivers": d["drivers"], "peak_drivers": d["peak_drivers"], "shift_min": d["shift_min"],
            "cycle_min": d["cycle_min"], "charge_min": d["charge_min"], "slack_min": d["slack_min"],
            "soc_plug_in_pct": 100 * d["soc_plug_in"], "energy_rotation_kWh": d["energy_rotation_kWh"],
            "area_req_m2": d["area_req_m2"], "site_area_m2": self.site.area_m2, "total_gbp_yr": d["total_gbp_yr"],
            "gbp_per_trip": d["gbp_per_trip"], "trips_per_day": self.p.trips_per_day, "feasible": float(d["feasible"]),
            "battery_ok": float(d["battery_ok"]), "eu_ok": float(d["eu_ok"]), "area_ok": float(d["area_ok"]),
            "rank": float(d["rank"] or 0),
            **sim_kpis,
            **{f"cost_{k}": v for k, v in d["costs_gbp_yr"].items()},
        }
        trip_rows = [{k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in asdict(t).items()}
                     | {"delay_s": t.delay_s if not math.isnan(t.dep) else None}
                     for t in trips if t.sched_dep >= DaySimulation.WARMUP_S]
        layout = self.design.layout(sel.fleet_total, self.site.id, sel.area_ok) if self.design else {}
        kpis["design_lanes"] = float(layout.get("lanes", 0))
        kpis["layout_fits"] = float(layout.get("fits", sel.area_ok))
        return SimOutput(frame=frame, kpis=kpis, sites=[r.to_dict() for r in results], selected=d, trips=trip_rows,
                         layout=layout, params=self.p)
