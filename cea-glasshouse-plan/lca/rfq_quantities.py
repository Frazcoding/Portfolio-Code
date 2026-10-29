"""Quantities for the RFQ (item 8): bill of the placeholder-rated items for the Gate B design at each finalist site.

Reads results/site_opt/refined_<crop>.json (and lp_<crop>.json when present for heat store / heat pump / battery
sizes), prints a markdown table per site and writes results/site_opt/rfq_<crop>.json. RFQ_SPEC.md quotes these.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import costing  # noqa: E402
import design as D  # noqa: E402
import optimise  # noqa: E402
import site_opt  # noqa: E402


def quantities(site, x, crop):
    S = site_opt.site_state(site)
    d = optimise.build(x)
    a = D.analyse(d, S["wx"], site["lat"], site["lon"])
    R = costing.rates()
    q, st = costing.bill(d, a)
    rows = []
    for k, qty in q.items():
        r = R[k]
        rows.append(dict(key=k, unit=r["unit"], qty=qty, rate=r["cost_central"], gbp=qty * r["cost_central"],
                         tier=r["cost_tier"], placeholder="placeholder" in r["cost_tier"]))
    geo = dict(floor_m2=d.floor, length_m=d.length, width_m=d.width, n_spans=d.n_spans, span_w=d.span_w,
               gutter_h=d.gutter_h, ridge_bearing=d.ridge_bearing, glazing=d.glazing, roof_glazed_m2=a["a_roof_glazed"],
               wall_glazed_m2=a["a_wall_glazed"], steel_t=st["steel_kg"] / 1e3, n_columns=st["n_columns"],
               pitch=x["pitch"], form=x["form"])
    return geo, rows


def main(crop):
    SL = {s["site_key"]: s for s in json.loads((HERE / "data" / "siting" / "shortlist.json").read_text())}
    R = json.loads((site_opt.OUT / f"refined_{crop}.json").read_text())
    lp_path = site_opt.OUT / f"lp_{crop}.json"
    lp = {s["site"]: s for s in json.loads(lp_path.read_text())["sites"]} if lp_path.exists() else {}
    out = []
    for s in R["sites"][:3]:
        geo, rows = quantities(SL[s["site"]], s["best"]["x"], crop)
        b = s["best"]
        plant = dict(hp_kW_design=b["hp_kW"], wind_kW=b["wind_kW"], batt_kWh=b["batt_kWh"])
        if s["site"] in lp:
            st = lp[s["site"]]["standby"]
            plant.update(lp_store_kWh=st["store_kWh"], lp_hp_kW_th=st["hp_kW_th"], lp_wind_kW=st["wind_kW"],
                         lp_batt_kWh=st["batt_kWh"])
        out.append(dict(site=s["site"], name=s["name"], geometry=geo, items=rows, plant=plant))
        print(f"\n### {s['name']} — {geo['floor_m2'] / 1e4:.1f} ha, {geo['n_spans']} spans x {geo['span_w']:.1f} m, "
              f"{geo['length_m']:.0f} m long, gutter {geo['gutter_h']:.1f} m, pitch {geo['pitch']:.0f} deg, {geo['glazing']}")
        print("| Item | Unit | Quantity | Model rate (GBP) | Model cost (GBP k) | Status |\n|---|---|---:|---:|---:|---|")
        for r in rows:
            print(f"| {r['key']} | {r['unit']} | {r['qty']:,.0f} | {r['rate']:,.0f} | {r['gbp'] / 1e3:,.0f} | "
                  f"{'PLACEHOLDER' if r['placeholder'] else r['tier']} |")
        print("Plant:", {k: round(v) for k, v in plant.items()})
    (site_opt.OUT / f"rfq_{crop}.json").write_text(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    for c in sys.argv[1:] or ["cucumber"]:
        main(c)
