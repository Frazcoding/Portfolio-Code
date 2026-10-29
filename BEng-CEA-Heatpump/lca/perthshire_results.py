"""Perthshire off-grid scenario, step 3: carbon and cost per kg for every crop against imports delivered to a central
Scotland RDC. Same per-kg method as the comparison page (compare.py / crop_compare_template.html), with:

  * electricity: off-grid wind + battery + heat store from offgrid.py (base wind and +15 % "ridge" wind)
  * yield: literature glass yields x PC light factor x (site / Westland annual radiation)^0.8 (light elasticity,
    Marcelis et al. 2006); avocado from its growth model at the site
  * imports: each origin's footprint plus the extra haul to central Scotland (sea origins +460 km from the port,
    road origins +500 km), reefer HGV factor; CIF prices unchanged (UK border)
  * grid-connected reference at the same site: DESNZ-scaled hourly tariff and carbon

Writes results/perthshire/results.json and ../figures/perthshire_offgrid.png.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
sys.path.insert(0, str(HERE.parent))           # repo copy of simcore first (cloud has no ../simcore)
sys.path.insert(0, str(HERE))
import breakeven  # noqa: E402
import compare  # noqa: E402
import imports  # noqa: E402
from simcore import weather  # noqa: E402

OUT = HERE / "results" / "perthshire"
EXTRA_KM = {"sea": 460.0, "road": 500.0, "air": 460.0}


def radiation_factor():
    weather.SITES.setdefault("perth_carse", (56.42, -3.20, 0, "Carse of Gowrie, Perthshire, UK"))
    weather.SITES.setdefault("westland", (52.00, 4.20, 1, "Westland glasshouse district, Netherlands"))
    g = {s: weather.load(s)["ghi"].sum() for s in ("perth_carse", "westland")}
    return g["perth_carse"] / g["westland"]


def scotland_imports(imp, ff, loss):
    """Volume-weighted import carbon with the extra haul to a central Scotland RDC."""
    tot = cov = 0.0
    for o in imp["origins"]:
        extra = EXTRA_KM[o["mode"]] / 1000 * ff["reefer_hgv"] / (1 - loss)
        tot += (o["total"] + extra) * o["share"]
        cov += o["share"]
    return tot / cov


def per_kg(u, v, sim, og, Y, D, heat):
    """Carbon (kg CO2e/kg) and cost (GBP/kg) with their breakdowns, same terms as the comparison page."""
    ann = lambda n: D["rate"] / (1 - (1 + D["rate"]) ** -n)  # noqa: E731
    E = og["elec_used_MWh"] * 1e3 / 1e4 if og else sim["electricity_kWh_m2"]
    bore = v["bore_m_m2"] if heat == "ground" else 0.0
    carbon = {"electricity": E * og["ci"] / Y if og else E * v["elec"]["grid_2025"]["ci"] / Y,
              "structure": D["structure_co2"] / Y, "boreholes": bore * D["borehole_co2_kg_m"] / D["borehole_life"] / Y,
              "consumables": u["consumables"] / Y, "pack_haul": u["per_kg_fixed"]}
    capS = D["structure_capex"] + D["vsd_gbp_m2"]
    capH = v["design_kW_m2"] * (D["hp_skid_gbp_kw"] + (D["air_src_gbp_kw"] if heat == "air" else 0)) * (1 + D["install_frac"])
    capB = bore * D["borehole_gbp_m"] * (1 + D["install_frac"])
    elec_cost = og["capex_ann_gbp"] / 1e4 if og else E * v["elec"]["grid_2025"]["price"]
    cost = {"capital": (capS * ann(D["structure_life"]) + capH * ann(D["hp_life"]) + capB * ann(D["borehole_life"])) / Y,
            "o_and_m": (capS + capH) * D["om_frac"] / Y, "labour": u["labour_h"] * D["labour_rate"] / Y,
            "electricity": elec_cost / Y, "co2": u["co2_dose"] * D["co2_price"] / Y, "packing": u["pack_gbp"]}
    return carbon, cost


def main():
    data = json.loads((HERE / "results" / "compare.json").read_text())
    D = data["defaults"]
    sim = {r["case"]: r for r in json.loads((OUT / "sim.json").read_text())}
    og = json.loads((OUT / "offgrid.json").read_text())
    ff, st, *_ = imports.load()
    rf = radiation_factor()
    light = rf ** compare.LIGHT_ELASTICITY
    rows = []
    for k in data["order"]:
        u, imp = data["uk"][k], data["imports"][k]
        imp_c = scotland_imports(imp, ff, st["transport_loss"])
        res = {"crop": k, "name": u["name"], "imports_kg": imp_c, "imports_gbp": imp["cif_2023_25"],
               "imports_gbp_cheapest": imp["cheapest_cif"]}
        for heat, vk in (("air", "ctrlair_pc"), ("ground", "ctrl_pc")):
            s = sim[f"{k}|{vk}"]
            v = dict(data["uk"][k]["variants"][vk], design_kW_m2=s["design_heat_loss_kw"] / s["area_m2"])
            if k == "avocado":
                Y = s["crop_yield_t_ha"] / 10
            else:
                Y = u["yield_glass"][0] * u["pc_factor"] * light
            for wind in ("base", "ridge"):
                c, g = per_kg(u, v, s, og["cases"][f"{k}|{vk}"][wind], Y, D, heat)
                res[f"{heat}_{wind}"] = {"yield": Y, "kg": sum(c.values()), "gbp": sum(g.values()), "carbon": c, "cost": g,
                                         "offgrid": og["cases"][f"{k}|{vk}"][wind]}
        best = min((res[f"{h}_base"] for h in ("air", "ground")), key=lambda r: r["gbp"])
        res["best_base"] = best
        res["best_ridge"] = min((res[f"{h}_ridge"] for h in ("air", "ground")), key=lambda r: r["gbp"])
        rows.append(res)
    out = {"site": "Carse of Gowrie, Perthshire (56.42 N, 3.20 W), 2023", "radiation_vs_westland": rf,
           "yield_light_factor": light, "cf": og["cf"], "rows": rows}
    (OUT / "results.json").write_text(json.dumps(out, indent=1, default=float))

    print(f"radiation vs Westland {rf:.2f} -> yield x{light:.2f}; wind CF base {og['cf']['base']:.3f}, ridge {og['cf']['ridge']:.3f}")
    print(f"{'crop':<11}{'Y kg/m2':>8}{'imp kg':>7}{'imp £':>7} | {'base kg':>8}{'£':>7}{'£/kWh':>7} | {'ridge kg':>8}{'£':>7}  verdict")
    for r in sorted(rows, key=lambda r: r["best_base"]["gbp"] / r["imports_gbp"]):
        b, rr = r["best_base"], r["best_ridge"]
        vc = "carbon ✓" if b["kg"] < r["imports_kg"] else "carbon ✕"
        vg = "cost ✓" if b["gbp"] < r["imports_gbp"] else ("cost ✓ ridge" if rr["gbp"] < r["imports_gbp"] else "cost ✕")
        print(f"{r['name']:<11}{b['yield']:>8.2f}{r['imports_kg']:>7.2f}{r['imports_gbp']:>7.2f} | {b['kg']:>8.2f}{b['gbp']:>7.2f}"
              f"{b['offgrid']['price']:>7.2f} | {rr['kg']:>8.2f}{rr['gbp']:>7.2f}  {vc}, {vg}")
    plot(rows, HERE.parent / "figures" / "perthshire_offgrid.png")


def plot(rows, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ink, ink2, grid, surf, uk, imp = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb", "#2a78d6", "#eb6834"
    rows = sorted(rows, key=lambda r: r["best_base"]["gbp"] / r["imports_gbp"])
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2), facecolor=surf)
    for ax, key, lab, unit in ((axes[0], "kg", "imports_kg", "kg CO₂e per kg"), (axes[1], "gbp", "imports_gbp", "£ per kg")):
        ax.set_facecolor(surf)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        ax.set_xscale("log")
        ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
        ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        ax.grid(color=grid, lw=0.8, axis="x")
        ax.tick_params(colors=ink2)
        for i, r in enumerate(rows):
            a, b, c = r[lab], r["best_base"][key], r["best_ridge"][key]
            col = "#15803d" if b < a else "#8a97a3"
            ax.plot([min(a, b), max(a, b)], [i, i], color=col, lw=2, zorder=1)
            ax.plot([c, b], [i, i], color=uk, lw=1, alpha=.5, zorder=1)
            ax.scatter(a, i, s=46, color=imp, edgecolor=surf, linewidth=2, zorder=3)
            ax.scatter(b, i, s=46, color=uk, edgecolor=surf, linewidth=2, zorder=3)
            ax.scatter(c, i, s=22, color=uk, alpha=.55, zorder=2)
        ax.set_yticks(range(len(rows)))
        ax.set_yticklabels([r["name"] for r in rows] if ax is axes[0] else [""] * len(rows), color=ink)
        ax.invert_yaxis()
        ax.set_xlabel(unit, color=ink2)
    axes[0].set_title("Carbon per kg delivered to central Scotland", color=ink, loc="left", fontsize=11)
    axes[1].set_title("Cost per kg (imports: price at the UK border)", color=ink, loc="left", fontsize=11)
    h = [plt.Line2D([], [], marker="o", ls="", color=uk, markersize=7),
         plt.Line2D([], [], marker="o", ls="", color=uk, alpha=.55, markersize=5),
         plt.Line2D([], [], marker="o", ls="", color=imp, markersize=7),
         plt.Line2D([], [], color="#15803d", lw=2)]
    fig.legend(h, ["Perthshire glasshouse, off-grid wind (ERA5 wind)", "same, +15 % wind (exposed ridge)",
                   "Imports (volume-weighted)", "UK beats imports"], frameon=False, labelcolor=ink2, loc="lower center", ncol=4)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(path, dpi=150, facecolor=surf)


if __name__ == "__main__":
    main()
