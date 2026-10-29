"""Step 4: local refinement around each leading site's best design, then sensitivities -> Gate A shortlist.

1. Take the top sites per crop at the central heat price (GBP 10/MWh) from site_rank.
2. Local search: from the site's best design, perturb one or two variables at a time (span, pitch, gutter, size,
   aspect, ridge bearing, roof form/ridges, insulated north faces, glazing), keep improvements; fixed budget.
3. Sensitivities on the refined design: wall light x0.5; placeholder rates at low/high; utility-scale wind
   (GBP 1,400/kW, Arup 2024 for DESNZ); capex -20 % (economies of scale what-if, unsourced); no 2026 network
   increase; connection pipe x0 / x3; heat price 0/10/20; electric HGV haulage carbon; heat-source outages
   (planned only / none); no battery; battery capex x0.5; wholesale share of the electricity price 0.5; wind sized with export revenue (the old rule, shown
   for comparison and excluded from the pass test).
4. Gate A: a site/design passes if it beats imports delivered to the Scottish RDCs on cost (annual and seasonal)
   and carbon in the central case, and the ranking holds under the sensitivities.
Writes results/site_opt/refined_<crop>.json.
"""
import copy
import json
import math
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import costing  # noqa: E402
import energy_grid  # noqa: E402
import site_opt  # noqa: E402
import site_rank  # noqa: E402

HEAT_CENTRAL = 10.0
TOP = 6
BUDGET = 70
# shown but not part of the pass test: the no-export turbine is the "do not build it this way" case (fall back to small
# own-use turbines or grid, both of which are in the test)
NOT_IN_PASS = ("elec_2p5MW_no_export",)


def placeholder_rates(level):
    """Rates with every placeholder item at the low or high end of its stated range."""
    R = copy.deepcopy(costing.rates())
    ranges = {"aluminium": (4, 9), "glass_single_m2": (15, 40), "glass_dbl_lowe_m2": (50, 120),
              "glass_dbl_ar_m2": (45, 100), "pc_twin_m2": (12, 30), "xps_m2": (15, 35),
              "heating_pipe_m": (5, 12), "energy_screen_m2": (4, 9)}
    for k, (lo, hi) in ranges.items():
        R[k]["cost_central"] = lo if level == "low" else hi
    return R


def cost(r, hp=HEAT_CENTRAL):
    return r["gbp_kg_ex_heat"] + r["heat_MWh_per_kg"] * hp


def perturb(x, rng):
    y = dict(x)
    for _ in range(int(rng.integers(1, 3))):
        k = rng.choice(["span", "pitch", "gutter", "area", "aspect", "bearing", "form", "north", "glazing"])
        area = y["length"] * y["n_spans"] * y["span_w"]
        aspect = y["length"] / (y["n_spans"] * y["span_w"])
        if k == "span":
            y["span_w"] = float(np.clip(y["span_w"] * math.exp(rng.normal(0, 0.25)), 6.4, 32))
        elif k == "pitch":
            y["pitch"] = float(np.clip(y["pitch"] + rng.normal(0, 3), 10, 30))
            y["rise_ratio"] = float(np.clip(y["rise_ratio"] + rng.normal(0, 0.03), 0.1, 0.35))
        elif k == "gutter":
            y["gutter_h"] = float(np.clip(y["gutter_h"] + rng.normal(0, 0.4), 4.0, 7.0))
        elif k == "area":
            area = float(np.clip(area * math.exp(rng.normal(0, 0.3)), 1e4, 30e4))
        elif k == "aspect":
            aspect = float(np.clip(aspect * math.exp(rng.normal(0, 0.4)), 0.25, 6))
        elif k == "bearing":
            y["bearing"] = 90.0 - y["bearing"]
        elif k == "form":
            y["form"] = str(rng.choice(["pitched", "sawtooth", "arch"]))
            y["k"] = 1 if y["form"] == "arch" else int(rng.integers(1, 4))
        elif k == "north":
            y["opaque_north"] = not y["opaque_north"]
        else:
            y["glazing"] = "dbl_ar" if y["glazing"] == "dbl_ar_lowe" else "dbl_ar_lowe"
        width = math.sqrt(area / aspect)
        y["n_spans"] = max(1, round(width / y["span_w"]))
        y["length"] = area / (y["n_spans"] * y["span_w"])
    return y


def refine_site(args):
    site, x0, crop, seed = args
    rng = np.random.default_rng(seed)
    best = site_opt.evaluate(site, x0, crop)
    trace = [cost(best)]
    for _ in range(BUDGET):
        y = perturb(best["x"], rng)
        try:
            r = site_opt.evaluate(site, y, crop)
        except Exception:
            r = None
        if r is not None and cost(r) < cost(best):
            best = r
        trace.append(cost(best))
    sens = {}
    variants = {"wall_light_x0.5": dict(wall_light=0.5), "placeholders_low": dict(rates=placeholder_rates("low")),
                "placeholders_high": dict(rates=placeholder_rates("high")),
                # R10 electricity routes (central = site_opt.CENTRAL_ELEC, owned 2.5 MW turbine): grid baseline, private
                # wire, small own-use turbines (the Gate B rule), 2.5 MW with a GBP 1 M connection, 2.5 MW with no export
                "elec_grid": dict(elec="grid"), "elec_private_wire": dict(elec="private_wire"),
                "elec_own_small": dict(elec="own_small"), "elec_2p5MW_conn_high": dict(elec="own_2p5MW_conn_high"),
                "elec_2p5MW_no_export": dict(elec="own_2p5MW_no_export"), "winter_waste_x0.8": dict(winter_waste=True),
                "capex_minus20": dict(capex_mult=0.8), "no_network_increase": dict(network=False),
                "pipe_x0": dict(pipe_mult=0.0), "pipe_x3": dict(pipe_mult=3.0),
                "no_unplanned_outage": dict(outage="planned"), "no_outage": dict(outage="none"),
                "no_battery": dict(battery=False),
                "wholesale_share_0.5": dict(price=energy_grid.inputs(0.5)[1]),
                # R8: GreenLight's Caledonian/Westland tomato yield ratio is 0.89 vs ours 0.76 (light elasticity ~0.47 vs ~1.1;
                # literature 0.8-1), so Scottish yield x 0.89/0.76 = 1.18 is the GreenLight-response case; x0.85 the pessimistic one
                "yield_greenlight_x1.18": dict(yield_mult=1.18), "yield_minus15": dict(yield_mult=0.85),
                # transpiration law x0.8 / x1.2 (cucumber constants tested only at LAI 1-1.9; design LAI 3.0)
                "transp_x0.8": dict(transp_mult=0.8), "transp_x1.2": dict(transp_mult=1.2)}
    import coldyear
    variants["weather_2010"] = dict(_site=coldyear.alias(site, 2010))   # coldest recent year (2023 is mild), R10
    for k, o in variants.items():
        o = dict(o)
        r = site_opt.evaluate(o.pop("_site", site), best["x"], crop, o)
        sens[k] = None if r is None else dict(gbp=cost(r), kg=r["kg_kg"])
    for hp in (0.0, 20.0):
        sens[f"heat_{hp:g}"] = dict(gbp=cost(best, hp), kg=best["kg_kg"])
    sens["ehgv"] = dict(gbp=cost(best), kg=best["kg_kg_ehgv"])
    return dict(site=site["site_key"], name=site["name"], kind=site["kind"], crop=crop, best=best, trace=trace,
                sens=sens)


def main(crop):
    t = time.time()
    SL = {s["site_key"]: s for s in json.loads((HERE / "data" / "siting" / "shortlist.json").read_text())}
    B, out = site_rank.rank(crop)
    rows = dict(out)[HEAT_CENTRAL][:TOP]
    jobs = [(SL[r["site"]], r["x"], crop, i) for i, r in enumerate(rows)]
    with ProcessPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(refine_site, jobs))
    for r in res:
        share = np.roll(np.asarray(r["best"]["monthly_share"]), site_rank.LAG_MONTHS)
        r["imp_gbp_seasonal"] = float(share @ B["gbp_month"])
        r["imp_kg_seasonal"] = float(share @ B["kg_month"])
        g = cost(r["best"])
        r["pass_central"] = bool(g < B["gbp_annual"] and g < r["imp_gbp_seasonal"]
                                 and r["best"]["kg_kg"] < min(B["kg_annual"], r["imp_kg_seasonal"]))
        r["pass_all_sens"] = bool(all(v is not None and v["gbp"] < min(B["gbp_annual"], r["imp_gbp_seasonal"])
                                      and v["kg"] < min(B["kg_annual"], r["imp_kg_seasonal"])
                                      for k, v in r["sens"].items() if k not in NOT_IN_PASS))
    res.sort(key=lambda r: cost(r["best"]))
    (site_opt.OUT / f"refined_{crop}.json").write_text(
        json.dumps({"benchmarks": {k: (v.tolist() if hasattr(v, "tolist") else v) for k, v in B.items()},
                    "sites": res}, default=float))
    print(f"== {crop} ({time.time() - t:.0f} s): imports at Scottish RDCs GBP {B['gbp_annual']:.2f}/kg, "
          f"{B['kg_annual']:.2f} kg CO2e/kg")
    for r in res:
        b, x = r["best"], r["best"]["x"]
        s = r["sens"]
        rng_g = [v["gbp"] for k, v in s.items() if v and k not in NOT_IN_PASS]
        print(f"{r['name'][:30]:<31} {cost(b):.2f} (sweep {r['trace'][0]:.2f})  range {min(rng_g):.2f}-{max(rng_g):.2f}  "
              f"seas.imp {r['imp_gbp_seasonal']:.2f}  {b['kg_kg']:.3f} kg (imp {min(B['kg_annual'], r['imp_kg_seasonal']):.2f})"
              f"  pass {r['pass_central']}/{r['pass_all_sens']} | {x['form']} k{x['k']} span {x['span_w']:.1f} "
              f"pitch {x['pitch']:.0f} gutter {x['gutter_h']:.1f} brg {x['bearing']:.0f} N-ins {x['opaque_north']} "
              f"{x['glazing']} {b['area_ha']:.1f} ha  wind {b['wind_kW'] / 1e3:.1f} MW batt {b['batt_kWh'] / 1e3:.1f} MWh "
              f"export {b['export_MWh']:.0f} MWh HP {b['hp_kW'] / 1e3:.1f} MW waste {b['waste_share'] * 100:.0f}%")
        print("      routes GBP/kg (kg): " + "  ".join(f"{k[5:]} {s[k]['gbp']:.2f} ({s[k]['kg']:.2f})" for k in s
                                                     if k.startswith("elec_") and s[k]))


if __name__ == "__main__":
    for c in sys.argv[1:] or ["cucumber", "tomato"]:
        main(c)
