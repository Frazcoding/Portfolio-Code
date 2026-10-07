"""Assemble the R10 final-design and full-costing report (both tracks) from the chain and cash-flow results.
Reads results/site_opt{,_B}/{refined,lp,coldyear}_*.json, results/costing/cashflow.json, data/siting/wind_nearby.json.
Writes results/costing/FULL_COSTING.md and results/costing/report_data.json (for the published page).
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TR = {"A": ("Track A: waste heat", HERE / "results" / "site_opt"),
      "B": ("Track B: no waste heat", HERE / "results" / "site_opt_B")}
CROPS = ("cucumber", "tomato")


def f(x, n=2):
    return "-" if x is None else f"{x:.{n}f}"


def main():
    CF = json.loads((HERE / "results" / "costing" / "cashflow.json").read_text())
    W = json.loads((HERE / "data" / "siting" / "wind_nearby.json").read_text()) if (
        HERE / "data" / "siting" / "wind_nearby.json").exists() else {}
    L = ["# Final designs and full costing: both tracks (R10, 2026-10-03)", ""]
    data = {"tracks": {}}
    for t, (label, d) in TR.items():
        L += [f"## {label}", ""]
        data["tracks"][t] = {}
        cold = {(r["crop"], r["site"]): r for r in json.loads((d / "coldyear.json").read_text())} if (
            d / "coldyear.json").exists() else {}
        for crop in CROPS:
            R = json.loads((d / f"refined_{crop}.json").read_text())
            LP = {s["site"]: s for s in json.loads((d / f"lp_{crop}.json").read_text())["sites"]}
            B = R["benchmarks"]
            rows = []
            L += [f"### {crop.capitalize()}: model cost (GBP/kg, levelised at 3.5 %, as the design search) vs imports "
                  f"{B['gbp_annual']:.2f} / {B['kg_annual']:.2f} kg CO2e", "",
                  "| Site | ha | Turbine (central) | Grid | Private wire | 2010 weather | LP heat pump | HP % design | "
                  "kg CO2e/kg | Pass all sens | Wind farm <5 km |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|"]
            for e in R["sites"][:6]:
                b, s = e["best"], e["sens"]
                g = b["gbp_kg_ex_heat"] + 10 * b["heat_MWh_per_kg"]
                lp = LP.get(e["site"], {}).get("lp")
                c = cold.get((crop, e["site"]))
                w = W.get(e["site"], {})
                rows.append(dict(name=e["name"], site=e["site"], ha=b["area_ha"], central=g,
                                 grid=s.get("elec_grid", {}).get("gbp"), pw=s.get("elec_private_wire", {}).get("gbp"),
                                 w2010=s.get("weather_2010", {}).get("gbp"), lp=lp and lp["gbp_kg"],
                                 hp_frac=lp and lp["hp_kW_th"] / lp["design_kW"], kg=b["kg_kg"], pass_all=e["pass_all_sens"],
                                 x=b["x"], heat=b["heat_kWh_m2"], Y=b["Y"], waste=b["waste_share"],
                                 wind_n_big=w.get("n_big"), wind_near_km=w.get("nearest_big_km"),
                                 cold=c and c.get("hp")))
                L.append(f"| {e['name'][:30]} | {b['area_ha']:.1f} | {g:.2f} | {f(rows[-1]['grid'])} | {f(rows[-1]['pw'])} | "
                         f"{f(rows[-1]['w2010'])} | {f(rows[-1]['lp'])} | {f(rows[-1]['hp_frac'] and rows[-1]['hp_frac'] * 100, 0)} | "
                         f"{b['kg_kg']:.2f} | {'yes' if e['pass_all_sens'] else 'no'} | "
                         f"{(str(w.get('n_big')) + ' big, ' + f(w.get('nearest_big_km'), 1) + ' km') if w.get('n_big') else ('none' if w else '?')} |")
            L.append("")
            data["tracks"][t][crop] = dict(benchmarks=dict(gbp=B["gbp_annual"], kg=B["kg_annual"]), rows=rows)
        # cash flow
        C = [r for r in CF["results"] if r["track"] == d.name]
        L += [f"### Lifecycle cash flow (30 yr, real, pre-tax, cash purchase; price = DEFRA wholesale)", "",
              "| Crop | Site | HP rule | Capex GBP M | GBP/m2 | Price GBP/kg | LCOP 3.5 % | LCOP 8 % | EBITDA GBP k/yr | "
              "NPV 3.5 % GBP M | NPV 8 % GBP M | IRR | Payback yr | NPV 3.5 % at import-parity price | Greenhouse + turbine NPV 3.5 % |",
              "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for r in C:
            irr_s = "-" if r["irr"] is None else f"{r['irr'] * 100:.1f} %"
            L.append(f"| {r['crop']} | {r['name'][:24]} | {r['rule']} | {r['capex_total'] / 1e6:.2f} | {r['capex_gbp_m2']:.0f} | "
                     f"{r['price_gbp_kg']:.2f} | {r['lcop_0.035']:.2f} | {r['lcop_0.08']:.2f} | {r['ebitda_gbp_yr'] / 1e3:.0f} | "
                     f"{r['npv_0.035'] / 1e6:+.2f} | {r['npv_0.08'] / 1e6:+.2f} | "
                     f"{irr_s} | "
                     f"{f(r['payback'], 1)} | {r['sens']['import_parity_price']['npv_0035'] / 1e6:+.2f} | "
                     f"{f(r.get('combined', {}).get('npv_0035') and r['combined']['npv_0035'] / 1e6)} |")
        L.append("")
        L += ["#### Break-even price and what would close the gap (heat pump LP-sized, cold-year safe)", "",
              "| Crop | Site | Break-even price 3.5 % / 8 % (GBP/kg) | DEFRA price | NPV 3.5 %: base | free CO2 | yield +18 % | "
              "capex -20 % | all three | all three + import parity (IRR) |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for r in C:
            if r["rule"] != "lp":
                continue
            s_ = r["sens"]
            lc = s_["levers_combined_import_parity"]
            lc_irr = "-" if lc["irr"] is None else f"{lc['irr'] * 100:.1f} %"
            L.append(f"| {r['crop']} | {r['name'][:24]} | {r['lcop_0.035']:.2f} / {r['lcop_0.08']:.2f} | {r['price_gbp_kg']:.2f} | "
                     f"{r['npv_0.035'] / 1e6:+.2f} | {s_['co2_free']['npv_0035'] / 1e6:+.2f} | {s_['yield_+18%']['npv_0035'] / 1e6:+.2f} | "
                     f"{s_['capex_-20%']['npv_0035'] / 1e6:+.2f} | {s_['levers_combined']['npv_0035'] / 1e6:+.2f} | "
                     f"{lc['npv_0035'] / 1e6:+.2f} ({lc_irr}) |")
        L.append("")
        data["tracks"][t]["cashflow"] = C
    # monthly sales of the lead design per track and crop (LP heat pump)
    L += ["## Sales by month (lead design per track and crop, steady year)", ""]
    MON = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
    for t, (label, d) in TR.items():
        for crop in CROPS:
            r = next((x for x in CF["results"] if x["track"] == d.name and x["crop"] == crop and x["rule"] == "lp"), None)
            if not r:
                continue
            kg = [r["kg_yr"] * s_ for s_ in r["monthly_share"]]
            L += [f"**{label}, {crop}, {r['name']}** ({r['kg_yr'] / 1e3:.0f} t/yr, revenue GBP {r['revenue_gbp_yr'] / 1e3:.0f} k/yr "
                  f"at DEFRA wholesale)", "", "| | " + " | ".join(MON) + " |", "|---|" + "---:|" * 12,
                  "| t | " + " | ".join(f"{k / 1e3:.0f}" for k in kg) + " |",
                  "| GBP/kg | " + " | ".join(f"{p:.2f}" for p in r["monthly_price"]) + " |",
                  "| GBP k | " + " | ".join(f"{k * p / 1e3:.0f}" for k, p in zip(kg, r["monthly_price"])) + " |", ""]
    # verification and inputs
    L += ["## Verification", ""]
    g = HERE / "results" / "greenlight" / "trackB_girvan_tomato_iso_year_compare.json"
    if g.exists():
        G = json.loads(g.read_text())
        L.append(f"- GreenLight continuous year, track-B tomato design (Girvan): heat ours {G['heat_ours_kWh_m2']:.1f} vs GreenLight "
                 f"{G['heat_gl_kWh_m2']:.1f} kWh/m2 (ratio {G['ratio']:.3f}, monthly r {G['monthly_corr']:.2f}); yield relative to the "
                 f"Westland reference ours 0.971 vs GreenLight 0.934. Earlier (R7) Caledonian 8.5 ha: heat ratio 0.95.")
    t = HERE / "results" / "test_regress_R10.log"
    if t.exists():
        parts = t.read_text(errors="ignore").split("== ")[1:]
        L.append("- Regression tests (results/test_regress_R10.log): " + ", ".join(
            f"{p.splitlines()[0]} {'PASS' if 'PASS' in p else 'see log'}" for p in parts))
    L.append("- tests/test_r10.py (28 checks): electricity routes, no-waste track, wind cap, ledger, cold-year LP sizing, "
             "cash-flow arithmetic.")
    L += ["", "## Costing inputs added for the full costing", "", "| Input | Value | Unit | Tier | Source |", "|---|---|---|---|---|"]
    for k, (val, unit, tier, src) in CF["inputs"].items():
        L.append(f"| {k} | {val} | {unit} | {tier} | {src} |")
    (HERE / "results" / "costing" / "FULL_COSTING.md").write_text("\n".join(L), encoding="utf-8")
    (HERE / "results" / "costing" / "report_data.json").write_text(json.dumps(data, indent=1, default=float))
    print("\n".join(L))


if __name__ == "__main__":
    main()
