"""Break-even screen: what has to be true for UK greenhouse avocado to beat imports on carbon AND cost.

Per m2 of growing area per year:
    carbon/kg = (E * CI + dosed_CO2 * f_CO2 + S) / Y + k_c
    cost/kg   = (capex annuity + O&M + labour + E * p_e + dosed_CO2 * p_CO2) / Y + k_gbp
with Y yield (kg/m2/yr), E electricity (kWh/m2/yr, heat pump + LED + aux, from the sim), S structure embodied
carbon spread over its life, and k the per-kg packing/ripening/haulage terms. Targets come from imports.py.

This is a screen, not the LCA: S, capex, labour and packing are placeholder estimates (marked below) that steps 5
and 7 (BOM, LCA/LCC) replace. The conclusions are only used where they hold across the stated ranges.
Writes results/breakeven_summary.json and figures/breakeven.png.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import imports  # noqa: E402

RATE = 0.035  # real discount rate, HM Treasury Green Book (SCOPE §2)

# Electricity supply: kg CO2e/kWh incl. upstream, so it matches the WTT-inclusive import transport factors
SUPPLY = {
    "grid_2025": (0.177 + 0.01853 + 0.0459 + 0.00397,
                  "DESNZ (2025) conversion factors: UK electricity generation 0.177 + T&D 0.01853 + WTT gen 0.0459 + WTT T&D 0.00397"),
    "clean_grid": (0.050, "Illustrative decarbonised grid (~50 g/kWh), to be replaced by NESO FES pathway in step 7"),
    "onsite_wind": (0.011, "Onshore wind life-cycle median ~11 g/kWh, IPCC AR5 WGIII Annex III (2014) Table A.III.2"),
}
# Dosed CO2 accounting (user decision §3.8: report both)
CO2_ACCOUNTING = {"emission": 1.0, "by_product": 0.0}

P = {  # value, unit, confidence, source
    "elec_price": (0.165 + 0.0080, "GBP/kWh", "sourced",
                   "DESNZ Quarterly Energy Prices Dec 2025: manufacturing industry average 16.5 p/kWh excl. CCL (Q3 2025) "
                   "+ Climate Change Levy main rate 0.801 p/kWh (Apr 2026)"),
    "co2_price": (0.25, "GBP/kg", "sourced (secondary)", "Bulk liquid CO2 delivered: ChemAnalyst UK USD 345/t (Jun 2026) ~GBP 0.25/kg (secondary); user decision 2026-10-07; Lothian Supply / Clean Carbon quote pending"),
    "structure_capex": (200.0, "GBP/m2", "estimated",
                        "Venlo glasshouse incl. screens, heating pipework, irrigation, foundations, install. Dutch turnkey "
                        "projects quoted ~EUR 240-310/m2 at hectare scale (dutchgreenhouses.com via web summary, unverified); "
                        "range 120-350 tested"),
    "structure_life": (30.0, "yr", "estimated", "Study period, SCOPE §2"),
    "hp_capex": (1200.0, "GBP/kW", "estimated", "Ground-source heat pump + borehole field per kW design heat loss; UK "
                 "non-domestic GSHP indicative 1,000-2,000 GBP/kW; to source in step 5"),
    "hp_life": (20.0, "yr", "estimated", "CIBSE Guide M typical heat pump life"),
    "led_capex": (1.0, "GBP/W", "estimated", "Horticultural LED fixtures incl. install, indicative; to source in step 5"),
    "led_life": (15.0, "yr", "estimated", "Manufacturer L90 ratings ~50,000 h; ~2,500 h/yr used"),
    "om_frac": (0.02, "1/yr", "estimated", "Maintenance + insurance as fraction of capex"),
    "labour_h": (0.15, "h/m2/yr", "estimated", "High-density orchard pruning/harvest; glasshouse tomato is ~0.8-1 h/m2, "
                 "open-field avocado ~0.1"),
    "labour_rate": (15.0, "GBP/h", "estimated", "UK National Living Wage 12.21 GBP/h (Apr 2025) + ~20 % on-costs"),
    "pack_gbp": (0.25, "GBP/kg", "estimated", "Packhouse, carton, cold store; imports carry this inside the CIF price"),
    "structure_co2": (3.0, "kg CO2e/m2/yr", "estimated",
                      "Venlo ~12 kg/m2 galvanised steel x 2.8 + ~3 kg/m2 aluminium x 10 + ~10 kg/m2 glass x 1.44 + "
                      "foundations ~10 = ~90 kg CO2e/m2 over 30 yr (ICE v3 factors, masses estimated). Norwegian Venlo "
                      "tomato LCA attributes ~53 kg CO2e/t to structure. Range 2-5; replaced by BOM in step 5"),
}
# Per-kg carbon at the farm that UK fruit carries like imported fruit
FERT = (0.0272, "Blaauw et al. (2024) fertiliser + pesticide 27.22 kg CO2e/t, used as proxy for UK fertigation")
UK_HAUL_KM = 100.0  # greenhouse -> RDC


def annuity(life):
    return RATE / (1 - (1 + RATE) ** -life)


def per_kg_constants():
    ff, st, *_ = imports.load()
    k_c = st["packhouse"] + st["packaging"] + st["ripening"] + FERT[0] + UK_HAUL_KM / 1000 * ff["reefer_hgv"]
    return k_c, P["pack_gbp"][0]


def fixed_cost_m2(case, structure_capex=None):
    """Annual GBP/m2 independent of energy use: capex annuities + O&M + labour."""
    sc = P["structure_capex"][0] if structure_capex is None else structure_capex
    hp = case["design_heat_loss_kw"] / case["area_m2"] * 1000 * P["hp_capex"][0] / 1000  # GBP/m2
    led_w = case.get("led_kWh_m2", 0) / case["led_hours"] * 1000 if case.get("led_hours") else 0.0
    led = led_w * P["led_capex"][0]
    capex = sc + hp + led
    ann = (sc * annuity(P["structure_life"][0]) + hp * annuity(P["hp_life"][0])
           + led * annuity(P["led_life"][0]))
    return {"capex_m2": capex, "annuity": ann, "om": capex * P["om_frac"][0],
            "labour": P["labour_h"][0] * P["labour_rate"][0], "led_W_m2": led_w}


def evaluate(case, k_c, k_gbp):
    y = case["crop_yield_t_ha"] / 10.0  # kg/m2/yr
    e = case["electricity_kWh_m2"]
    d = case.get("crop_co2_dosed_kg_m2", 0.0)
    s = P["structure_co2"][0]
    carbon = {f"{sup}|{acc}": (e * ci + d * f + s) / y + k_c
              for sup, (ci, _) in SUPPLY.items() for acc, f in CO2_ACCOUNTING.items()}
    fx = fixed_cost_m2(case)
    energy = e * P["elec_price"][0]
    co2 = d * P["co2_price"][0]
    cost = {k: v / y for k, v in (("capex", fx["annuity"]), ("om", fx["om"]), ("labour", fx["labour"]),
                                  ("electricity", energy), ("co2", co2))}
    cost["packing"] = k_gbp
    # Integrated variant: existing structure (S = 0, no structure capex), free waste heat (no heat-pump capex, no
    # compressor electricity), on-site wind, dosed CO2 as by-product. LED capex and fan-coil electricity remain.
    e_int = max(0.0, e - case["heat_kWh_m2"] / case["scop_unit"])
    led_w = fx["led_W_m2"]
    led_capex = led_w * P["led_capex"][0]
    integ_gbp_m2 = (led_capex * (annuity(P["led_life"][0]) + P["om_frac"][0]) + fx["labour"]
                    + e_int * P["elec_price"][0] + co2)
    integrated = {"elec_kWh_m2": e_int, "kg_co2e_per_kg": e_int * SUPPLY["onsite_wind"][0] / y + k_c,
                  "gbp_per_kg": integ_gbp_m2 / y + k_gbp}
    return {"case": case["case"], "yield_kg_m2": y, "elec_kWh_m2": e, "elec_kWh_per_kg": e / y, "co2_dosed_kg_m2": d,
            "capex_gbp_m2": fx["capex_m2"], "carbon_kg_per_kg": carbon, "cost_gbp_per_kg": cost,
            "cost_total": sum(cost.values()), "integrated": integrated}


def requirements(k_c, k_gbp, t_c, t_gbp, case_ref):
    """Closed-form break-even conditions."""
    req = {}
    # Carbon: structure embodied carbon S (kg/m2/yr) alone sets a minimum yield, before any energy
    for s in (0.0, 1.0, 2.0, 3.0):
        req[f"min_yield_carbon_zero_energy|S{s:g}"] = s / (t_c - k_c)
        # max electricity per kg at a given yield, by supply
        for y in (0.75, 1.5, 2.0):
            for sup, (ci, _) in SUPPLY.items():
                req[f"max_kWh_per_kg|S{s:g}|{sup}|Y{y:g}"] = max(0.0, ((t_c - k_c) * y - s) / (y * ci))
    # Cost: minimum yield with zero energy, at reference structure capex and with a free structure (heat pump paid)
    for label, sc in (("ref", None), ("free_structure_hp_paid", 0.0)):
        fx = fixed_cost_m2({**case_ref, "led_kWh_m2": 0, "led_hours": 0}, sc)
        req[f"min_yield_cost_zero_energy|{label}"] = (fx["annuity"] + fx["om"] + fx["labour"]) / (t_gbp - k_gbp)
    # Cost: labour alone
    req["min_yield_cost_labour_only"] = P["labour_h"][0] * P["labour_rate"][0] / (t_gbp - k_gbp)
    # Cost: max total capex per m2 (structure + plant, 30 yr annuity + O&M) at a given yield, zero energy
    for y in (1.0, 2.0, 3.0):
        budget = (t_gbp - k_gbp) * y - P["labour_h"][0] * P["labour_rate"][0]
        req[f"max_capex_gbp_m2|Y{y:g}"] = max(0.0, budget / (annuity(30) + P["om_frac"][0]))
    return req


def best_conceivable(k_c, k_gbp, case_ref):
    """Most favourable combination the study scope allows: structure already exists (rooftop/reused, S = 0, no
    structure capex), heat is free waste heat (no heat-pump capex or electricity), on-site wind, no LEDs, dosed CO2
    as by-product. Electricity = the crop-led no-LED case minus heat-pump compressor share (aux only, ~10 kWh/m2)."""
    e_aux = 10.0
    d = 25.0
    out = {}
    for y in (0.75, 1.5, 2.0):
        carbon = e_aux * SUPPLY["onsite_wind"][0] / y + k_c
        gbp_m2 = P["labour_h"][0] * P["labour_rate"][0] + e_aux * P["elec_price"][0] + d * P["co2_price"][0]
        out[f"Y{y:g}"] = {"kg_co2e_per_kg": carbon, "gbp_per_kg": gbp_m2 / y + k_gbp}
    return out


def plot(rows, cases, k_c, k_gbp, t_c, t_gbp, case_ref, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker  # noqa: F401
    import numpy as np

    ink, ink2, grid, surf = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
    y = np.linspace(0.1, 3.0, 300)
    led_case = next(c for c in cases if c["case"] == "1ha crop-led +CO2 +LED150")
    fx_led, fx_noled = fixed_cost_m2(led_case), fixed_cost_m2({**case_ref, "led_kWh_m2": 0, "led_hours": 0})
    fixed = lambda fx: fx["annuity"] + fx["om"] + fx["labour"]  # noqa: E731
    lab = P["labour_h"][0] * P["labour_rate"][0]
    pe, pc, s = P["elec_price"][0], P["co2_price"][0], P["structure_co2"][0]
    wind, grid25 = SUPPLY["onsite_wind"][0], SUPPLY["grid_2025"][0]
    # (label, colour, kWh/m2, CI, S, fixed GBP/m2, dosed CO2 kg/m2)
    scen = [("New glasshouse + heat pump + LED, grid", "#2a78d6", 147.0, grid25, s, fixed(fx_led), 30.0),
            ("New glasshouse + heat pump, no LED, wind", "#eb6834", 37.0, wind, s, fixed(fx_noled), 25.0),
            ("Existing structure + waste heat, no LED, wind", "#1baf7a", 10.0, wind, 0.0, lab, 25.0)]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.4), facecolor=surf)
    for ax, target, unit in ((axes[0], t_c, "kg CO₂e per kg"), (axes[1], t_gbp, "£ per kg")):
        ax.set_facecolor(surf)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        for sp in ("left", "bottom"):
            ax.spines[sp].set_color(ink2)
        ax.tick_params(colors=ink2)
        ax.grid(color=grid, lw=0.8, which="major")
        ax.set_yscale("log")
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
        ax.set_xlim(0, 3)
        ax.axvspan(1.0, 2.0, color=grid, alpha=0.6, zorder=0)
        ax.axhline(target, color=ink, lw=1.2, ls=(0, (4, 3)))
        ax.set_xlabel("Yield, kg per m² per year  (10 t/ha = 1 kg/m²)", color=ink2)
        ax.set_ylabel(unit, color=ink2)
    axes[0].set_ylim(0.1, 300)
    axes[1].set_ylim(1, 300)
    for label, col, e, ci, sc, fx, d in scen:
        axes[0].plot(y, (e * ci + sc) / y + k_c, color=col, lw=2, label=label)
        axes[1].plot(y, (fx + e * pe + d * pc) / y + k_gbp, color=col, lw=2, label=label)
    axes[0].text(2.97, t_c * 1.12, f"imports {t_c:.2f}", ha="right", fontsize=9, color=ink)
    axes[1].text(2.97, t_gbp * 1.12, f"imports £{t_gbp:.2f} (CIF)", ha="right", fontsize=9, color=ink)
    for ax in axes:
        ax.text(1.5, ax.get_ylim()[1] * 0.75, "open-field orchard\nyields 10–20 t/ha", ha="center", va="top",
                fontsize=8, color=ink2)
    axes[0].set_title("Carbon per kg delivered (dosed CO₂ as by-product)", color=ink, loc="left", fontsize=11)
    axes[1].set_title("Cost per kg (capex, O&M, labour, energy, CO₂, packing)", color=ink, loc="left",
                      fontsize=11)
    for r in rows:
        axes[0].scatter(r["yield_kg_m2"], r["carbon_kg_per_kg"]["grid_2025|by_product"], s=36, color=ink2, zorder=3,
                        edgecolor=surf, linewidth=2)
        axes[1].scatter(r["yield_kg_m2"], r["cost_total"], s=36, color=ink2, zorder=3, edgecolor=surf, linewidth=2)
    handles, labels = axes[0].get_legend_handles_labels()
    handles.append(plt.Line2D([], [], marker="o", ls="", color=ink2, markersize=6))
    labels.append("Simulated cases (step 3), grid 2025")
    fig.legend(handles, labels, frameon=False, labelcolor=ink2, loc="lower center", ncol=2)
    fig.tight_layout(rect=(0, 0.12, 1, 1))
    fig.savefig(path, dpi=150, facecolor=surf)


def main():
    _, imp = imports.run()
    t_c, t_gbp = imp["weighted_kg_co2e_per_kg"], imp["cif_gbp_per_kg_all_origins_2023_25"]
    k_c, k_gbp = per_kg_constants()
    cases = []
    for f in ("step3_summary.json", "step3b_summary.json", "step3c_summary.json"):
        cases += json.loads((HERE / "results" / f).read_text())
    rows = [evaluate(c, k_c, k_gbp) for c in cases if c.get("crop_yield_t_ha", 0) > 0]
    case_ref = next(c for c in cases if c["case"] == "1ha crop-led")
    req = requirements(k_c, k_gbp, t_c, t_gbp, case_ref)
    out = {"targets": {"kg_co2e_per_kg": t_c, "gbp_per_kg": t_gbp}, "per_kg_constants": {"carbon": k_c, "gbp": k_gbp},
           "inputs": {k: {"value": v[0], "unit": v[1], "confidence": v[2], "source": v[3]} for k, v in P.items()},
           "supply": {k: {"kg_co2e_per_kWh": v[0], "source": v[1]} for k, v in SUPPLY.items()},
           "requirements": req, "best_conceivable": best_conceivable(k_c, k_gbp, case_ref), "cases": rows}
    (HERE / "results" / "breakeven_summary.json").write_text(json.dumps(out, indent=1, default=float))
    (HERE.parent / "figures").mkdir(exist_ok=True)
    plot(rows, cases, k_c, k_gbp, t_c, t_gbp, case_ref, HERE.parent / "figures" / "breakeven.png")

    print(f"targets: {t_c:.2f} kg CO2e/kg, GBP {t_gbp:.2f}/kg;  per-kg constants: {k_c:.3f} kg, GBP {k_gbp:.2f}")
    print(f"\n{'case':<34}{'t/ha':>6}{'kWh/kg':>8}{'grid':>7}{'grid+CO2':>9}{'wind':>7}{'£/kg':>8}  cost split")
    for r in rows:
        c = r["carbon_kg_per_kg"]
        split = " ".join(f"{k}:{v:.1f}" for k, v in r["cost_gbp_per_kg"].items())
        print(f"{r['case']:<34}{r['yield_kg_m2']*10:>6.1f}{r['elec_kWh_per_kg']:>8.0f}{c['grid_2025|by_product']:>7.1f}"
              f"{c['grid_2025|emission']:>9.1f}{c['onsite_wind|by_product']:>7.2f}{r['cost_total']:>8.1f}  {split}")
    print()
    for k, v in req.items():
        print(f"{k:<45}{v:>10.2f}")
    print("\nbest conceivable:", json.dumps(out["best_conceivable"], default=lambda x: round(x, 2)))


if __name__ == "__main__":
    main()
