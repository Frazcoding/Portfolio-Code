"""The port reproduces the Ember Google Sheet (tab Site Selection 3.3 / 3.4, state of 2026-10-28) for S1, S2 and S3."""
import pytest

# sheet values: (S1 Temple Works, S2 Filton, S3 Avonmouth)
SHEET = {
    "energy_rotation_kWh": (428.6, 444.2, 449.0),
    "soc_plug_in": (0.310, 0.285, 0.277),
    "charge_min": (42 + 51 / 60, 44 + 25 / 60, 44 + 54 / 60),
    "cycle_min": (7 * 60 + 29 + 51 / 60, 7 * 60 + 55 + 25 / 60, 8 * 60 + 3 + 54 / 60),
    "fleet": (8, 8, 9),
    "fleet_total": (8, 8, 9),
    "active_chargers": (1, 1, 1),
    "total_chargers": (2, 2, 2),
    "peak_kVA": (1328.936627, 1328.936627, 1328.936627),
    "substation_kVA": (2000, 2000, 2000),
    "driving_min": (6 * 60 + 32, 6 * 60 + 56, 7 * 60 + 4),
    "shift_min": (7 * 60 + 57, 8 * 60 + 21, 8 * 60 + 29),
    "shifts_per_driver_week": (5, 4, 4),
    "drivers": (34, 42, 42),
    "peak_drivers": (8, 9, 9),
    "area_req_m2": (6034, 6115, 6325),
    "total_gbp_yr": (2819401, 2873320, 2832664),
    "gbp_per_trip": (322, 328, 323),
    "rank": (1, 3, 2),
}
COSTS = {
    "land_lease": (233700, 239134, 137758.4),
    "site_works": (73753, 74739, 77306),
    "chargers": (44708.85, 44708.85, 44708.85),
    "grid_connection": (76745.64, 29486.21, 32796.41),
    "fleet": (192000, 192000, 216000),
    "driver_wages": (1253556, 1316628, 1337652),
    "electricity": (944937, 976624, 986442),
}
# Sheet values above are as displayed (whole pounds / m2 where the sheet rounds the display).
ROUNDED = {"area_req_m2", "total_gbp_yr", "gbp_per_trip"}


@pytest.fixture(scope="module")
def rows(baseline):
    by_id = {r["site_id"]: r for r in baseline.sites}
    return [by_id["S1"], by_id["S2"], by_id["S3"]]


@pytest.mark.parametrize("key", list(SHEET))
def test_site_results_match_sheet(rows, key):
    for r, expected in zip(rows, SHEET[key]):
        tol = 0.5 if key in ROUNDED else 1e-3 if key == "soc_plug_in" else 0.05
        assert r[key] == pytest.approx(expected, abs=tol), (r["site_id"], key)


@pytest.mark.parametrize("item", list(COSTS))
def test_cost_items_match_sheet(rows, item):
    for r, expected in zip(rows, COSTS[item]):
        assert r["costs_gbp_yr"][item] == pytest.approx(expected, abs=0.5), (r["site_id"], item)


def test_all_feasible_and_s1_recommended(baseline, rows):
    assert all(r["feasible"] and r["battery_ok"] and r["eu_ok"] and r["area_ok"] for r in rows)
    assert baseline.selected["site_id"] == "S1" and baseline.selected["rank"] == 1


def test_route_level_values(baseline):
    p = baseline.params
    assert p.trips_per_day == pytest.approx(24.0)
    assert p.trips_per_week == pytest.approx(168.0)
    assert p.charger_VA / 1000 == pytest.approx(644.4683136)
