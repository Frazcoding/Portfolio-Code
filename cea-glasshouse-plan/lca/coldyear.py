"""R10 weather-year check (2026-10-03). The study's weather year 2023 is mild for these sites (heating degree-days 15.5 C:
Cameronbridge 2,313 vs 2,809 in 2010; Girvan 1,909 vs 2,601). Two checks on the refined finalists of the current track:

  cost   the same design evaluated on 2010 (coldest recent year) and 2018 (Beast from the East) weather: GBP/kg, heat
  hp     the LP-sized heat pump + hot-water store chosen on 2023 run against the 2010 hourly heat demand (greedy store:
         charge whenever the heat pump has spare output, so it is the best case for meeting demand): unmet heat, and
         the heat-pump size (fraction of design load) that meets 2010 with that store

Weather for other years is fetched from Open-Meteo (simcore.weather) and stored under an alias site key so the rest of
the model (which reads the 2023 file name) runs unchanged; grid prices and carbon stay 2023. Writes
<site_opt.OUT>/coldyear.json.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
sys.path.insert(0, str(HERE.parent))           # repo copy of simcore first (cloud has no ../simcore)
sys.path.insert(0, str(HERE))
import energy_grid  # noqa: E402
import finalist_lp  # noqa: E402
import site_opt  # noqa: E402
from simcore import CACHE, YEAR, weather  # noqa: E402

YEARS = (2010, 2018)
TOP = 3


def alias(site, year):
    key = f"{site['site_key']}_y{year}"
    path = CACHE / f"weather_{key}_{YEAR}.csv"
    if not path.exists():
        weather.SITES.setdefault(site["site_key"], (site["lat"], site["lon"], 0, site["name"]))
        weather._source_frame(site["site_key"], year).to_csv(path, index=False)
    weather.SITES.setdefault(key, (site["lat"], site["lon"], 0, f"{site['name']} ({year} weather)"))
    return dict(site, site_key=key)


def store_check(q, cop, hp_el, store, boiler_kw=0.0):
    """Greedy hourly dispatch: returns unmet kWh and hours. boiler_kw: constant peak-boiler thermal output (BP19i)."""
    soc, un, hrs = store, 0.0, 0
    cap = hp_el * cop + boiler_kw
    for i in range(q.shape[0]):
        d = q[i] - cap[i]
        if d <= 0:
            soc = min(store, soc - d)
        else:
            take = min(d, soc)
            soc -= take
            if d - take > 1e-6:
                un += d - take
                hrs += 1
    return un, hrs


def min_frac(q, cop, store, design_kw, cop_design):
    lo, hi = 0.2, 1.5
    for _ in range(25):
        m = 0.5 * (lo + hi)
        if store_check(q, cop, m * design_kw / cop_design, store)[0] > 0:
            lo = m
        else:
            hi = m
    return hi


def main(crops=("cucumber", "tomato")):
    SL = {s["site_key"]: s for s in json.loads((HERE / "data" / "siting" / "shortlist.json").read_text())}
    _, price, finalist_lp.CI = energy_grid.inputs()
    out = []
    for crop in crops:
        R = json.loads((site_opt.OUT / f"refined_{crop}.json").read_text())["sites"][:TOP]
        for e in R:
            site, x = SL[e["site"]], e["best"]["x"]
            row = site_opt.evaluate(site, x, crop)
            rec = dict(crop=crop, site=site["site_key"], name=site["name"],
                       base=dict(gbp=row["gbp_kg_ex_heat"] + 10 * row["heat_MWh_per_kg"], heat=row["heat_kWh_m2"],
                                 Y=row["Y"], kg=row["kg_kg"]))
            for y in YEARS:
                r = site_opt.evaluate(alias(site, y), x, crop)
                rec[str(y)] = dict(gbp=r["gbp_kg_ex_heat"] + 10 * r["heat_MWh_per_kg"], heat=r["heat_kWh_m2"],
                                   Y=r["Y"], kg=r["kg_kg"])
            lp = finalist_lp.run(site, x, crop, row, price, "lp")
            P10 = finalist_lp.profiles(alias(site, 2010), x, crop)
            P23 = finalist_lp.profiles(site, x, crop)
            cd = float(np.percentile(P23["cop"], 1))
            q10 = P10["q"] - (P10["waste_kw"] * P10["avail"] if P10["waste_kw"] else 0.0)   # waste heat covers first
            q10 = np.maximum(q10, 0.0)
            un, hrs = store_check(q10, P10["cop"], lp["hp_kW_el"], lp["store_kWh"])
            rec["hp"] = dict(frac_2023=lp["hp_kW_th"] / lp["design_kW"], store_kWh=lp["store_kWh"],
                             unmet_2010_kWh=un, unmet_2010_h=hrs, unmet_2010_share=un / max(q10.sum(), 1.0),
                             frac_needed_2010=min_frac(q10, P10["cop"], lp["store_kWh"], lp["design_kW"], cd))
            out.append(rec)
            h = rec["hp"]
            print(f"{crop:9}{site['name'][:24]:25} GBP/kg 2023 {rec['base']['gbp']:.2f} | 2010 {rec['2010']['gbp']:.2f} | "
                  f"2018 {rec['2018']['gbp']:.2f}   heat {rec['base']['heat']:.0f}/{rec['2010']['heat']:.0f}/"
                  f"{rec['2018']['heat']:.0f}   HP(LP 2023) {h['frac_2023']:.0%} + {h['store_kWh'] / 1e3:.1f} MWh: 2010 unmet "
                  f"{h['unmet_2010_kWh'] / 1e3:.1f} MWh in {h['unmet_2010_h']} h; needs {h['frac_needed_2010']:.0%}",
                  flush=True)
    (site_opt.OUT / "coldyear.json").write_text(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main(sys.argv[1:] or ("cucumber", "tomato"))
