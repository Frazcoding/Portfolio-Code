"""Capital cost and embodied carbon of a design.py shape, from quantities x data/rates.csv.

Cost is anchored to a sourced total: the reference design (Venlo, 8 m trellis with two 4 m roofs, single 2xAR glass,
1 ha) is set to SAC/SRUC (2026) Table 11 'commercial glasshouse' GBP 2M/ha. Everything the bottom-up list does not
price (installation labour, climate computer, irrigation, vents, crop wires, design fees ...) is the calibration
residual, applied per m2 of floor to every design. Design-to-design differences therefore come from the itemised
quantities only. Items whose rate is a placeholder ('needs quote') are reported, with how much of the total they make up,
so a result that hangs on a placeholder is visible.

Embodied carbon is bottom-up only (no calibration): quantities x factors, annualised over each item's life.
Items without a sourced factor are listed as missing rather than set to zero silently.
"""
import csv
import math
from pathlib import Path

import design as D
import sizing

HERE = Path(__file__).resolve().parent
SAC_COMMERCIAL_GBP_M2 = 200.0       # SAC/SRUC (2026) Table 11: commercial glasshouse GBP 2M/ha
GLAZING_RATE = {"single_2ar": "glass_single_m2", "dbl_ar_lowe": "glass_dbl_lowe_m2", "dbl_ar": "glass_dbl_ar_m2",
                "pc_twin": "pc_twin_m2", "etfe3": "etfe3_m2"}
# aluminium in the glazing system, kg per m of bar / cushion extrusion (placeholders until supplier data)
AL_KG_PER_M = {"single_2ar": 1.2, "dbl_ar_lowe": 1.6, "dbl_ar": 1.6, "pc_twin": 1.0, "etfe3": 3.0}
GLASS_PANES = {"single_2ar": 1, "dbl_ar_lowe": 2, "dbl_ar": 2}
BEARING_KPA = 100.0                 # allowable ground bearing for pads (site investigation needed)


def rates():
    out = {}
    with open(HERE / "data" / "rates.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            num = {k: (float(r[k]) if r[k] not in ("", None) else None)
                   for k in ("cost_low", "cost_central", "cost_high", "co2_low", "co2_central", "co2_high", "life_yr")}
            out[r["key"]] = {**r, **num}
    return out


def bill(d, a=None, edge_insulation=False, pipe_m_per_m2=2.25):
    """Quantities by rate key for design d (a: design.analyse result, for areas)."""
    if a is None:
        a = dict(a_roof_glazed=0.0, a_wall_glazed=0.0, a_opaque=0.0)
    st = sizing.size(d)
    glazed = a["a_roof_glazed"] + a["a_wall_glazed"]
    n_cols = st["n_columns"]
    pad_area = max(0.36, st["column_N_kN"] / 1.4 / BEARING_KPA)
    perim = 2 * (d.length + d.width)
    concrete = n_cols * pad_area * 0.8 + perim * 0.45 * 0.6 + d.floor * d.path_frac * 0.15
    q = {"steel": st["steel_kg"] / 1e3,
         "aluminium": glazed / D.GLAZING[d.glazing]["pane_w"] * AL_KG_PER_M[d.glazing],
         GLAZING_RATE[d.glazing]: glazed,
         "concrete": concrete,
         "pir_panel_m2": a["a_opaque"],
         "heating_pipe_m": pipe_m_per_m2 * d.floor,
         "energy_screen_m2": d.floor}
    if edge_insulation:
        q["xps_m2"] = perim * 1.0
    return q, st


def evaluate(d, a, edge_insulation=False, R=None, case="central", pipe_m_per_m2=2.25):
    """Cost (GBP), embodied carbon (kg CO2e total and per year) and their provenance for design d."""
    R = R or rates()
    q, st = bill(d, a, edge_insulation, pipe_m_per_m2)
    cost_items, co2_items, missing_co2, placeholder_gbp = {}, {}, [], 0.0
    for k, qty in q.items():
        r = R[k]
        c = r[f"cost_{case}"] if r[f"cost_{case}"] is not None else r["cost_central"]
        cost_items[k] = qty * c
        if "placeholder" in r["cost_tier"]:
            placeholder_gbp += qty * c
        f = r[f"co2_{case}"] if r[f"co2_{case}"] is not None else r["co2_central"]
        if f is None:
            if qty > 0:
                missing_co2.append(k)
            continue
        co2_items[k] = qty * f
        if k == GLAZING_RATE[d.glazing] and k.startswith("glass"):
            pass
    co2_year = sum(v / (R[k]["life_yr"] or 30.0) for k, v in co2_items.items())
    return dict(quantities=q, sizing=st, cost_items=cost_items, itemised_gbp=sum(cost_items.values()),
                placeholder_gbp=placeholder_gbp, co2_items=co2_items, co2_total_kg=sum(co2_items.values()),
                co2_kg_m2_yr=co2_year / d.floor, missing_co2=missing_co2)


def reference(wx, lat, lon):
    """SAC 'commercial' anchor: Venlo 8 m trellis, two 4 m roofs at 22 deg, single 2xAR glass, 100 x 100 m."""
    return D.Design(length=100.0, n_spans=12, span_w=8.0, gutter_h=6.0,
                    profile=[(0, 0), (0.25, 0.81), (0.5, 0), (0.75, 0.81), (1, 0)], glazing="single_2ar")


def calibration(wx, lat, lon, R=None):
    """GBP/m2 floor not covered by the itemised list, from the SAC anchor."""
    d = reference(wx, lat, lon)
    a = D.analyse(d, wx, lat, lon)
    e = evaluate(d, a, R=R)
    return SAC_COMMERCIAL_GBP_M2 - e["itemised_gbp"] / d.floor, e


REFERENCE_FLOOR_M2 = 1e4            # the SAC anchor house (reference()) is 100 x 100 m

# Scale anchor for 4-8 ha houses (BP27, 2026-10-05). WUR/LEI Rapport 2016-068 'Local-for-local productie kastomaten'
# (edepot.wur.nl/387511) Bijlage 3 Table B3.1: standard Dutch high-tech tomato house 4-8 ha (7 m posts, diffuse glass,
# energy + gable screen, boiler + heating, CO2 dosing, hanging gutters, basin, irrigation, computer, electrics, internal
# transport, service area/office; excl. CHP and lighting) EUR 110-120/m2, prices 2012-2014; England '+ / ++'
# (+0-10 % / >+10 %). Indexed with Eurostat sts_copi_a NL residential construction (2021 = 100): producer (output)
# prices 2012-14 mean 78.1 -> 2025 127.7 (x1.635, central and high); input costs 83.9 -> 122.8 (x1.464, low).
# EUR_GBP 0.8567 (site_opt). England uplift 1.10 central (the + / ++ boundary), 1.05 low, 1.20 high.
# It includes a boiler that our design does not have (its heat plant is costed separately), so it is conservative.
WUR_EUR_M2 = {"low": 110.0, "central": 115.0, "high": 120.0}
WUR_INDEX = {"low": 122.8 / 83.9, "central": 127.7 / 78.1, "high": 127.7 / 78.1}
WUR_ENGLAND = {"low": 1.05, "central": 1.10, "high": 1.20}
WUR_HA = (4.0, 8.0)


def wur_gbp_m2(case="central"):
    return WUR_EUR_M2[case] * WUR_INDEX[case] * 0.8567 * WUR_ENGLAND[case]


def resid_wur(resid_sac, case="central"):
    """Residual (GBP/m2) that makes the reference house's itemised list + residual equal the WUR 4-8 ha anchor instead
    of the SAC 1 ha anchor (itemised reference = SAC - resid_sac)."""
    return wur_gbp_m2(case) - (SAC_COMMERCIAL_GBP_M2 - resid_sac)


def capex(d, a, resid_gbp_m2, fixed_share=0.0, **kw):
    """fixed_share (BP19d, bplan_residual.ResidualItems.fixed_share): part of the residual that is a per-site cost, set at
    the reference house and not growing with area. 0 = today's linear residual."""
    e = evaluate(d, a, **kw)
    e["resid_gbp"] = resid_gbp_m2 * ((1 - fixed_share) * d.floor + fixed_share * REFERENCE_FLOOR_M2)
    e["capex_gbp"] = e["itemised_gbp"] + e["resid_gbp"]
    e["capex_gbp_m2"] = e["capex_gbp"] / d.floor
    e["placeholder_share"] = e["placeholder_gbp"] / e["capex_gbp"]
    return e
