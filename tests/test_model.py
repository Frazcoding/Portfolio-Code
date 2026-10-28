import math

import numpy as np
import pytest

from ember_hub_simulator import Config, ConfigError, HubDesign, ProjectPaths, Simulation, SiteCase
from ember_hub_simulator.model import Annuity, Mode, SubstationSizes


def run(cfg: Config):
    return Simulation.from_config(cfg, design=HubDesign.load(ProjectPaths.discover().data)).run()


def test_baseline_day_runs_to_timetable(baseline):
    k = baseline.kpis
    assert k["sim_departures"] == 48                      # 24 per day, 48 h shown
    assert k["sim_missed"] == 0 and k["sim_on_time_pct"] == 100.0
    assert k["sim_max_queue_min"] == 0.0                  # one charger, 42.6 min charge every 60 min: never a queue
    assert k["sim_min_soc_plug_in_pct"] == pytest.approx(100 * baseline.selected["soc_plug_in"], abs=0.5)
    assert k["sim_peak_kVA"] == pytest.approx(644.47 + 40, abs=0.1)   # standby charger not used in the simulation


def test_energy_balance_of_the_day(baseline):
    """Grid energy per day = trips x rotation energy / efficiency + auxiliary load (steady state, whole days)."""
    p, k = baseline.params, baseline.kpis
    expected_kWh = p.trips_per_day * baseline.selected["energy_rotation_kWh"] / p.efficiency + p.aux_VA * p.power_factor * 24 / 1000
    assert k["sim_grid_kWh_per_day"] == pytest.approx(expected_kWh, rel=0.01)


def test_fleet_states_are_consistent(baseline):
    f, n = baseline.frame, baseline.n_coaches
    modes = np.stack([f[f"c{j}_mode"].to_numpy() for j in range(1, n + 1)], axis=1)
    assert ((modes >= 0) & (modes <= Mode.CHARGING)).all()
    assert (f["on_road"] + f["at_hub"] == n).all()
    assert (f["charging"] <= baseline.selected["active_chargers"]).all()
    soc = np.stack([f[f"c{j}_soc"].to_numpy() for j in range(1, n + 1)], axis=1)
    assert soc.min() >= 100 * baseline.params.min_soc_plug_in - 1e-6 and soc.max() <= 100 + 1e-9


def test_half_headway_nearly_doubles_fleet_and_chargers(base_config):
    out = run(base_config.with_overrides({"timetable.headway_min": 30.0}))
    assert out.selected["fleet"] == 15 and out.selected["active_chargers"] == 2   # 7:30 cycle / 30 min
    # 15 x 30 min leaves 9 s of slack on a 449.85 min cycle: the minute-step simulation shows small delays
    assert out.selected["slack_min"] < 0.2
    assert 90.0 <= out.kpis["sim_on_time_pct"] < 100.0 and out.kpis["sim_max_delay_min"] <= 5.0


def test_slow_charger_needs_more_chargers_and_queues_in_the_sim(base_config):
    # 300 kW: 86 min charge every 60 min -> sheet sizes 2 active chargers at 75 % utilisation
    out = run(base_config.with_overrides({"hub.charge_power_kW": 300.0}))
    assert out.selected["active_chargers"] == 2
    assert out.selected["fleet"] == 9
    assert out.kpis["sim_on_time_pct"] == 100.0


def test_one_charger_at_full_utilisation(base_config):
    # 420 kW: 61 min charge per 60 min headway needs a second charger even at a 100 % cap
    out = run(base_config.with_overrides({"hub.charge_power_kW": 420.0, "hub.charger_utilisation": 1.0}))
    assert out.selected["active_chargers"] == 2
    # 440 kW: 58.4 min per hour on one charger; regular hourly arrivals never queue, the charger is ~97 % busy
    out = run(base_config.with_overrides({"hub.charge_power_kW": 440.0, "hub.charger_utilisation": 1.0}))
    assert out.selected["active_chargers"] == 1
    assert out.kpis["sim_charger_util_pct"] > 95 and out.kpis["sim_on_time_pct"] == 100.0


def test_long_route_fails_battery_and_eu_checks(base_config):
    out = run(base_config.with_overrides({"route.distance_km": 400.0, "route.drive_time_min": 330.0}))
    s = out.selected
    assert not s["battery_ok"] and not s["eu_ok"] and not s["feasible"] and s["rank"] is None


def test_small_site_fails_area_check(base_config):
    out = run(base_config.with_overrides({"site.area_m2": 3000.0}))
    assert not out.selected["area_ok"] and not out.selected["feasible"]


def test_spare_cover_and_maintenance_spare(base_config):
    out = run(base_config.with_overrides({"drivers.spare_cover": 0.15, "bus.maintenance_spare": 1.0}))
    assert out.selected["drivers"] == math.ceil(168 / 5 * 1.15)
    assert out.selected["fleet_total"] == 9
    assert out.n_coaches == 9 and "c9_soc" in out.frame


def test_annuity_and_substation_table():
    assert Annuity.payment(0.08, 20, 1000) == pytest.approx(101.852, abs=1e-3)
    assert Annuity.payment(0.0, 10, 1000) == 100.0
    assert SubstationSizes.select_VA(1771.9e3) == 2000e3
    assert SubstationSizes.select_VA(4000e3) == 4000e3
    assert SubstationSizes.select_VA(4001e3) is None


def test_site_round_trip(base_config):
    s = SiteCase.from_config(base_config)
    assert SiteCase.from_dict(s.to_dict()) == s


def test_deterministic(base_config):
    a = run(base_config).kpis
    b = run(base_config).kpis
    assert a == b


def test_config_validation(base_config):
    with pytest.raises(ConfigError):
        base_config.with_overrides({"hub.efficiency": 1.5})
    with pytest.raises(ConfigError):
        base_config.with_overrides({"nonsense": 1})
    with pytest.raises(ConfigError):
        Config.from_dict({"hub": {"power": 100}})
    with pytest.raises(ConfigError):
        base_config.with_overrides({"timetable.headway_min": 720.0, "timetable.service_hours": 1.0})
    assert base_config.with_overrides({"site.name": "X"}).site.name == "X"
