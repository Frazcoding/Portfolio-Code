"""Rank sites from results/site_opt/<crop>.json against imports delivered to the Scottish RDCs.

Imports, same delivery point as the UK produce:
  * cost: CIF at the UK border (Comtrade 2023-25) + road haul from the port to the Central Belt RDCs (TAG basis,
    mean of Dover/Felixstowe/Portsmouth, data/siting/import_ports_haul.json)
  * carbon: compare.json origin footprints + extra haul to central Scotland (perthshire_results.scotland_imports)
  * annual = volume-weighted year; seasonal = weighted by the design's own monthly output (monthly light at the
    site, lagged one month for fruit development: to source) using monthly Comtrade prices and origin mix
UK: GBP/kg = site_opt ex-heat cost + waste heat used x heat price (GBP 0/10/20 per MWh).
Writes results/site_opt/ranking_<crop>.json and prints the table.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import imports  # noqa: E402
import perthshire_results as pr  # noqa: E402
import site_opt  # noqa: E402

HEAT_PRICES = (0.0, 10.0, 20.0)
LAG_MONTHS = 1


def import_benchmarks(crop):
    cmp = json.loads((HERE / "results" / "compare.json").read_text())
    imp = cmp["imports"][crop]
    ports = json.loads((HERE / "data" / "siting" / "import_ports_haul.json").read_text())
    haul_gbp = float(np.mean([p["gbp_kg"] for p in ports.values()]))
    ff, st, *_ = imports.load()
    kg_annual = pr.scotland_imports(imp, ff, st["transport_loss"])
    extra = kg_annual - imp["weighted"]                    # Scotland haul uplift on the volume-weighted footprint
    d = pd.read_csv(HERE / "data" / "imports_monthly.csv")
    d = d[(d.crop == crop) & (d.iso3 != "W00")].copy()
    ci = {o.get("iso3"): o["total"] for o in imp["origins"] if o.get("iso3")}
    d["ci"] = d.iso3.map(ci).fillna(imp["weighted"])
    m = d.groupby("month").apply(lambda s: pd.Series({
        "gbp": (s.gbp_per_kg_cif * s.tonnes).sum() / s.tonnes.sum(),
        "kg": (s.ci * s.tonnes).sum() / s.tonnes.sum()}), include_groups=False)
    return dict(gbp_annual=imp["cif_2023_25"] + haul_gbp, kg_annual=kg_annual, haul_gbp=haul_gbp,
                gbp_month=(m.gbp + haul_gbp).to_numpy(), kg_month=(m.kg + extra).to_numpy())


def rank(crop):
    R = json.loads((site_opt.OUT / f"{crop}.json").read_text())["rows"]
    B = import_benchmarks(crop)
    out = []
    for r in R:
        share = np.roll(np.asarray(r["monthly_share"]), LAG_MONTHS)
        r["imp_gbp_seasonal"] = float(share @ B["gbp_month"])
        r["imp_kg_seasonal"] = float(share @ B["kg_month"])
        for hp in HEAT_PRICES:
            r[f"gbp_kg_h{hp:g}"] = r["gbp_kg_ex_heat"] + r["heat_MWh_per_kg"] * hp
    for hp in HEAT_PRICES:
        k = f"gbp_kg_h{hp:g}"
        best = {}
        for r in R:
            if r["site"] not in best or r[k] < best[r["site"]][k]:
                best[r["site"]] = r
        out.append((hp, sorted(best.values(), key=lambda r: r[k])))
    return B, out


def main(crop):
    B, out = rank(crop)
    print(f"== {crop}: imports delivered to Scottish RDCs: annual GBP {B['gbp_annual']:.2f}/kg (incl. GBP "
          f"{B['haul_gbp']:.2f} haul), {B['kg_annual']:.2f} kg CO2e/kg")
    res = {"benchmarks": {k: (v.tolist() if hasattr(v, "tolist") else v) for k, v in B.items()}, "by_heat_price": {}}
    for hp, rows in out:
        k = f"gbp_kg_h{hp:g}"
        res["by_heat_price"][hp] = rows
        print(f"-- heat GBP {hp:g}/MWh: best design per site (top 15)")
        print(f"{'site':<34}{'kind':<14}{'ha':>5}{'GBP/kg':>8}{'vs imp ann':>11}{'vs seas':>9}{'kgCO2/kg':>9}"
              f"{'imp kg seas':>12}{'waste%':>7}{'wind MW':>8}{'km':>5}")
        for r in rows[:15]:
            print(f"{r['name'][:33]:<34}{r['kind']:<14}{r['area_ha']:5.1f}{r[k]:8.2f}{r[k] - B['gbp_annual']:+11.2f}"
                  f"{r[k] - r['imp_gbp_seasonal']:+9.2f}{r['kg_kg']:9.3f}{r['imp_kg_seasonal']:12.3f}"
                  f"{r['waste_share'] * 100:7.0f}{r['wind_kW'] / 1e3:8.1f}{r['road_km']:5.0f}")
    (site_opt.OUT / f"ranking_{crop}.json").write_text(json.dumps(res, default=float))


if __name__ == "__main__":
    for c in sys.argv[1:] or ["cucumber", "tomato"]:
        main(c)
