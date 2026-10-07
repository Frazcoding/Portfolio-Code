"""Free-form shape optimisation: cost vs carbon per kg for high-wire fruit veg in Perthshire, grid-backed wind.

Each candidate (design.py shape x glazing x size up to 30 ha) is evaluated end to end:
  light/areas (design.analyse) -> greenhouse_fast year (humidity control, cover temperature from U, ASABE 0.75 ACH,
  design -3.1 C at the crop night setpoint) -> grid-backed wind (energy_grid) -> capex and embodied carbon
  (costing, sizing) + heat pump -> yield = CBS NL glass yield x (light / Dutch reference light)^0.8 (Marcelis et al.
  2006) x usable floor -> GBP/kg and kg CO2e/kg on the comparison-page basis (compare.json).
Usage: python optimise.py [n_samples] [crop ...]   -> results/optimise/<crop>.json
"""
import json
import math
import sys
import time
import types
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
sys.path.insert(0, str(HERE.parent))           # repo copy of simcore first (cloud has no ../simcore)
sys.path.insert(0, str(HERE))
sys.modules.setdefault("searoute", types.ModuleType("searoute"))
import config  # noqa: E402
import costing  # noqa: E402
import crops  # noqa: E402
import design as D  # noqa: E402
import energy_grid  # noqa: E402
import greenhouse  # noqa: E402
import greenhouse_fast  # noqa: E402
import run_perthshire as rp  # noqa: E402
from simcore import weather  # noqa: E402

OUT = HERE / "results" / "optimise"
LAT, LON = 56.42, -3.20
HP_GBP_KW = (850 + 140) * 1.18     # CALCULATIONS_WHITE_PAPER 6.1 (unsourced; register) per kW design heat loss
LIGHT_ELASTICITY = 0.8
GLAZINGS = ("dbl_ar_lowe", "dbl_ar", "single_2ar", "etfe3")
_CACHE = {}


def _state():
    if not _CACHE:
        weather.SITES.setdefault("perth_carse", (LAT, LON, 0, "Carse of Gowrie"))
        weather.SITES.setdefault("westland", (52.00, 4.20, 1, "Westland"))
        wx = weather.load("perth_carse")
        ref = D.Design(length=100, n_spans=12, span_w=8.0, gutter_h=6.0,
                       profile=[(0, 0), (0.25, 0.81), (0.5, 0), (0.75, 0.81), (1, 0)], glazing="single_plain")
        L_ref = float(D.analyse(ref, weather.load("westland"), 52.0, 4.2)["I_floor"].sum())
        resid, _ = costing.calibration(wx, LAT, LON)
        pu, price, ci = energy_grid.inputs()
        cmp = json.loads((HERE / "results" / "compare.json").read_text())
        _CACHE.update(wx=wx, L_ref=L_ref, resid=resid, pu=pu, price=price, ci=ci, uk=cmp["uk"], D=cmp["defaults"],
                      R=costing.rates())
    return _CACHE


def profile(form, k, pitch, apex, rise_ratio, span_w):
    """Cross-section points (x/span, z m above gutter)."""
    if form == "arch":
        xs = np.linspace(0, 1, 9)
        z = rise_ratio * span_w * (1 - (2 * xs - 1) ** 2) ** 0.75
        return [(float(x), float(v)) for x, v in zip(xs, z)]
    pts = [(0.0, 0.0)]
    wr = 1.0 / k
    for i in range(k):
        a = 0.5 if form == "pitched" else apex
        rise = math.tan(math.radians(pitch)) * a * wr * span_w
        pts += [(i * wr + a * wr, rise), ((i + 1) * wr, 0.0)]
    return pts


def sample(rng):
    form = str(rng.choice(["pitched", "sawtooth", "arch"]))
    span_w = float(np.exp(rng.uniform(np.log(6.4), np.log(32.0))))
    area = float(np.exp(rng.uniform(np.log(1e4), np.log(30e4))))
    aspect = float(np.exp(rng.uniform(np.log(0.5), np.log(4.0))))
    width = math.sqrt(area / aspect)
    n_spans = max(1, round(width / span_w))
    p = dict(form=form, k=int(rng.integers(1, 4)) if form != "arch" else 1, pitch=float(rng.uniform(12, 35)),
             apex=float(rng.uniform(0.6, 0.92)), rise_ratio=float(rng.uniform(0.12, 0.35)), span_w=span_w)
    return dict(p, n_spans=n_spans, length=area / (n_spans * span_w), gutter_h=float(rng.uniform(4.0, 7.5)),
                bearing=float(rng.choice([0.0, 90.0])), opaque_north=bool(rng.integers(0, 2)),
                glazing=str(rng.choice(GLAZINGS)))


def build(x):
    pr = profile(x["form"], x["k"], x["pitch"], x["apex"], x["rise_ratio"], x["span_w"])
    return D.Design(length=x["length"], n_spans=x["n_spans"], span_w=x["span_w"], profile=pr, gutter_h=x["gutter_h"],
                    ridge_bearing=x["bearing"], glazing=x["glazing"], opaque_north=x["opaque_north"])


def evaluate(x, crop):
    S = _state()
    d = build(x)
    a = D.analyse(d, S["wx"], LAT, LON)
    if a["usable_frac"] <= 0.2:
        return None
    base = rp.cases()[f"{crop}|ctrlair_pc"]
    night = max(p.heat_night for p in crops.CLIMATES[crop].periods)
    base = replace(base, envelope=replace(base.envelope, infiltration_ach=0.75, cover_t_from_u=True),
                   heat=replace(base.heat, design_outdoor_C=-3.1, design_indoor_C=night),
                   hum=config.HumidityControl(enabled=True))
    cfg = D.to_config(d, a, base)
    H, acc, wx, gr, meta, _ = greenhouse_fast.simulate_fast(cfg, i_floor=a["I_floor"])
    sm = greenhouse.summary(H, gr, meta)
    en = energy_grid.supply(H["W_total"][:8760], S["pu"], S["price"], S["ci"])
    cap = costing.capex(d, a, S["resid"], R=S["R"])
    Dd, u = S["D"], S["uk"][crop]
    ann = lambda n: Dd["rate"] / (1 - (1 + Dd["rate"]) ** -n)  # noqa: E731
    hp_gbp = meta["design_heat_loss_kw"] * HP_GBP_KW
    A = d.floor
    Y = u["yield_glass"][0] * (a["I_floor"].sum() / S["L_ref"]) ** LIGHT_ELASTICITY * a["usable_frac"]   # kg/m2 floor
    gbp_m2 = (cap["capex_gbp"] * ann(Dd["structure_life"]) + hp_gbp * ann(Dd["hp_life"])
              + (cap["capex_gbp"] + hp_gbp) * Dd["om_frac"] + en["cost_gbp"]) / A \
        + u["labour_h"] * Dd["labour_rate"] * a["usable_frac"] + u["co2_dose"] * Dd["co2_price"] * a["usable_frac"]
    kg_m2 = en["carbon_kg"] / A + cap["co2_kg_m2_yr"] + u["consumables"] * a["usable_frac"]
    return dict(x=x, crop=crop, area_ha=A / 1e4, Y=Y, gbp_kg=gbp_m2 / Y + u["pack_gbp"],
                kg_kg=kg_m2 / Y + u["per_kg_fixed"], light_rel=float(a["I_floor"].sum() / S["L_ref"]),
                usable=a["usable_frac"], shade=a["shade"], heat_kWh_m2=sm["heat_kWh_m2"],
                elec_kWh_m2=sm["electricity_kWh_m2"], unmet_h=sm["hours_unmet"], capex_gbp_m2=cap["capex_gbp_m2"],
                hp_gbp_m2=hp_gbp / A, placeholder_share=cap["placeholder_share"],
                embodied_kg_m2_yr=cap["co2_kg_m2_yr"], steel_kg_m2=cap["sizing"]["steel_kg_m2"],
                wind_kW=en["wind_kW"], elec_price=en["price"], elec_ci=en["ci"], missing_co2=cap["missing_co2"])


def _job(args):
    x, crop = args
    try:
        return evaluate(x, crop)
    except Exception as e:  # keep the sweep going; report
        return {"x": x, "crop": crop, "error": repr(e)}


def pareto(rows):
    rows = sorted(rows, key=lambda r: (r["gbp_kg"], r["kg_kg"]))
    front, best = [], math.inf
    for r in rows:
        if r["kg_kg"] < best:
            front.append(r)
            best = r["kg_kg"]
    return front


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    crop_list = sys.argv[2:] or ["tomato", "cucumber"]
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(1)
    xs = [sample(rng) for _ in range(n)]
    for crop in crop_list:
        t = time.time()
        with ProcessPoolExecutor(max_workers=7) as ex:
            res = list(ex.map(_job, [(x, crop) for x in xs], chunksize=4))
        ok = [r for r in res if r and "error" not in r]
        bad = [r for r in res if r and "error" in r]
        front = pareto(ok)
        (OUT / f"{crop}.json").write_text(json.dumps({"rows": ok, "errors": bad, "front": front}, indent=1,
                                                     default=float))
        print(f"{crop}: {len(ok)} designs, {len(bad)} errors, {time.time() - t:.0f} s; Pareto front {len(front)}")
        for r in front[:12]:
            x = r["x"]
            print(f"  {r['gbp_kg']:.2f} GBP/kg {r['kg_kg']:.3f} kg/kg | {x['form']:<8} k{x['k']} span {x['span_w']:4.1f} "
                  f"pitch {x['pitch']:4.1f} gutter {x['gutter_h']:.1f} bearing {x['bearing']:.0f} "
                  f"N-opaque {x['opaque_north']!s:<5} {x['glazing']:<11} {r['area_ha']:5.1f} ha | "
                  f"light {r['light_rel']:.2f} usable {r['usable']:.2f} Y {r['Y']:.1f} heat {r['heat_kWh_m2']:.0f} "
                  f"capex {r['capex_gbp_m2']:.0f}")
