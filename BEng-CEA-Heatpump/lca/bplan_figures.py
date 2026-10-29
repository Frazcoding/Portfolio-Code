"""Business plan figures (2026-10-05). Reads results/costing/cashflow.json (cashflow.py) and results/bplan/perf_{A,B}.json
(bplan_perf.py); writes PNGs to ../figures/business_plan/.

Lead case (user, 2026-10-05): track B (no waste heat), cucumber, Stranraer location; track A shown as an option; both
heat-pump rules; 8 % commercial headline, 3.5 % Green Book second. Visual standard: ../CLAUDE.md section 6.

    python bplan_figures.py
"""
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


class Style:
    SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
    SURFACE, INK, GRID = "#fcfcfb", "#000000", "#e4e3df"
    GOOD, BAD = "#2a78d6", "#e34948"
    MONTHS = "J F M A M J J A S O N D".split()
    TRACK_NAME = {"A": "Track A: waste heat", "B": "Track B: own heat pump + wind"}
    SITE_NAMES = {"The Creamery": "Stranraer", "Cameronbridge": "Cameronbridge", "Girvan": "Girvan",
                  "Sapphire": "Leslie", "HATTON": "Tay/Hatton", "NIGG": "Aberdeen", "Caledonian": "Irvine",
                  "North British": "Edinburgh"}

    @classmethod
    def apply(cls):
        plt.rcParams.update({
            "figure.facecolor": cls.SURFACE, "axes.facecolor": cls.SURFACE, "savefig.facecolor": cls.SURFACE,
            "font.size": 9, "font.family": "DejaVu Sans", "text.color": cls.INK, "axes.labelcolor": cls.INK,
            "axes.edgecolor": cls.INK, "xtick.color": cls.INK, "ytick.color": cls.INK, "axes.grid": True,
            "grid.color": cls.GRID, "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False,
            "axes.titlesize": 10, "axes.titleweight": "bold", "axes.titlelocation": "left", "legend.frameon": False,
            "axes.axisbelow": True, "legend.labelcolor": cls.INK})

    @classmethod
    def site(cls, name):
        return next((v for k, v in cls.SITE_NAMES.items() if k in name), name[:20])

    @staticmethod
    def legend_below(fig, handles, ncol=3, y=-0.02):
        fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, y), ncol=ncol, fontsize=8)

    @staticmethod
    def box(color, label):
        return plt.Rectangle((0, 0), 1, 1, color=color, label=label)

    @staticmethod
    def line(color, label, lw=2, ls="-", marker=None):
        return plt.Line2D([], [], color=color, lw=lw, ls=ls, marker=marker, label=label)


@dataclass
class Results:
    cashflow: list
    perf: list = field(default_factory=list)
    TRACK_DIR = {"site_opt": "A", "site_opt_B": "B"}

    @classmethod
    def load(cls, res=HERE / "results"):
        cf = json.loads((res / "costing" / "cashflow.json").read_text())["results"]
        for r in cf:
            r["T"] = cls.TRACK_DIR[r["track"]]
        perf = [p for t in ("A", "B") if (res / "bplan" / f"perf_{t}.json").exists()
                for p in json.loads((res / "bplan" / f"perf_{t}.json").read_text())]
        return cls(cf, perf)

    def pick(self, track, crop, rule="lp", rank=0):
        rows = [r for r in self.cashflow if r["T"] == track and r["crop"] == crop and r["rule"] == rule]
        return rows[rank] if len(rows) > rank else None

    def twin(self, r, rule):
        return next(x for x in self.cashflow if x["T"] == r["T"] and x["crop"] == r["crop"] and x["site"] == r["site"]
                    and x["rule"] == rule)


class ScenarioFlows:
    """Cash flows of the lead design under the route-to-viability scenarios (calls cashflow.build)."""

    def __init__(self, track="B", crop="cucumber", rule="lp"):
        self.track, self.crop, self.rule = track, crop, rule

    def run(self):
        os.environ["CEA_TRACK"] = self.track
        import importlib
        import cashflow
        import site_opt
        importlib.reload(site_opt)
        refined = json.loads((site_opt.OUT / f"refined_{self.crop}.json").read_text())
        lp = {s["site"]: s for s in json.loads((site_opt.OUT / f"lp_{self.crop}.json").read_text())["sites"]}
        entry = next(e for e in refined["sites"][:cashflow.TOP] if e["site"] in lp)
        parity = refined["benchmarks"]["gbp_annual"]
        levers = dict(co2_mult=0.0, yield_mult=1.18, capex_mult=0.8)
        scenarios = {"Base: DEFRA wholesale price": {}, "Import-parity contract price": dict(price_flat=parity),
                     "Levers: free CO2, yield +18 %, capex -20 %": levers,
                     "Levers + import-parity price": dict(levers, price_flat=parity)}
        out = {k: cashflow.build(site_opt.OUT, self.crop, entry, lp[entry["site"]][self.rule], self.rule, o)
               for k, o in scenarios.items()}
        return out, entry["name"]


class BusinessPlanFigures:
    OUT = HERE.parent / "figures" / "business_plan"
    IMPORT_CO2 = {"cucumber": 0.81, "tomato": 1.30}
    OPEX_GROUPS = [
        ("Energy", ("electricity_grid", "electricity_wind_from_turbine", "network_charge_increase", "waste_heat_purchase",
                    "heat_pump_om", "store_om")),
        ("Labour", ("labour",)),
        ("Growing inputs + CO2", ("young_plants", "substrate", "fertiliser_protection_other", "co2_purchased")),
        ("Packing, haulage, commission", ("packing", "haulage_to_rdc", "sales_commission")),
        ("O&M, overheads, land", ("structure_om_insurance", "overheads", "land_rent")),
    ]
    CAPEX_GROUPS = [
        ("Glass, steel, aluminium, foundations", ("steel", "aluminium", "glass_dbl_ar_m2", "concrete", "pir_panel_m2")),
        ("Heating pipe + energy screen", ("heating_pipe_m", "energy_screen_m2")),
        ("Installation, climate control, irrigation, vents",
         ("residual (SAC-calibrated: install, climate computer, irrigation, vents ...)",)),
        ("Heat pump + hot-water store + battery", ("heat_pump", "hot_water_store", "battery")),
        ("Connections (waste-heat pipe, HV)", ("waste_heat_pipe", "hv_import_connection")),
        ("Development + contingency", ("development", "contingency")),
    ]
    SENS_LABEL = {"price_-10%": "Price -10 %", "yield_-15%": "Yield -15 %", "capex_+20%": "Capex +20 %",
                  "consumables_x1.5": "Consumables x1.5", "co2_free": "Free CO2 (distillery)",
                  "yield_+18%": "Yield +18 % (GreenLight)", "capex_-20%": "Capex -20 % (quotes)",
                  "import_parity_price": "Import-parity price", "levers_combined": "CO2 + yield + capex levers",
                  "levers_combined_import_parity": "Levers + import parity"}

    def __init__(self, results):
        self.r = results
        Style.apply()
        self.S = Style.SERIES

    def save(self, fig, name):
        self.OUT.mkdir(parents=True, exist_ok=True)
        fig.savefig(self.OUT / f"{name}.png", dpi=200, bbox_inches="tight")
        plt.close(fig)
        print("wrote", self.OUT / f"{name}.png")

    def cost_vs_price(self):
        fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
        for ax, crop in zip(axes, ("cucumber", "tomato")):
            rows = [r for T in ("B", "A") for r in self.r.cashflow if r["T"] == T and r["crop"] == crop and r["rule"] == "lp"]
            y = np.arange(len(rows))[::-1]
            for yi, r in zip(y, rows):
                sb = self.r.twin(r, "standby")
                for off, rate, col in ((0.12, "0.08", self.S[0]), (-0.12, "0.035", self.S[1])):
                    ax.plot([r[f"lcop_{rate}"], sb[f"lcop_{rate}"]], [yi + off] * 2, color=col, lw=2, solid_capstyle="round")
                    ax.plot(r[f"lcop_{rate}"], yi + off, "o", ms=7, color=col, mec=Style.SURFACE, mew=1.5)
            ax.axvline(np.mean([r["price_gbp_kg"] for r in rows]), color=Style.INK, lw=1.5)
            ax.axvline(rows[0]["import_parity_gbp_kg"], color=Style.INK, lw=1.2, ls=(0, (1, 1.5)))
            ax.set_yticks(y, [f"{r['T']} · {Style.site(r['name'])}" for r in rows])
            ax.set_xlabel("Levelised cost [£/kg]")
            ax.set_title(f"{crop.capitalize()}: DEFRA £{rows[0]['price_gbp_kg']:.2f}, import parity "
                         f"£{rows[0]['import_parity_gbp_kg']:.2f} per kg")
            ax.grid(axis="y", visible=False)
        Style.legend_below(fig, [Style.line(self.S[0], "8 % discount rate", marker="o"),
                                 Style.line(self.S[1], "3.5 % discount rate", marker="o"),
                                 Style.line(Style.INK, "DEFRA UK wholesale price", lw=1.5),
                                 Style.line(Style.INK, "Import parity (CIF + haul to RDC)", lw=1.2, ls=(0, (1, 1.5)))], ncol=4)
        fig.suptitle("Cost per kg vs price (dot: LP-sized heat pump + store; line end: full-standby heat pump)",
                     x=0.01, ha="left", fontweight="bold")
        fig.tight_layout()
        self.save(fig, "bp01_cost_vs_price")

    def cost_buildup(self, rate="0.08"):
        cases = [(self.r.pick("B", "cucumber"), "B · cucumber"),
                 (self.r.pick("B", "cucumber", "standby"), "B · cucumber, standby HP"),
                 (self.r.pick("A", "cucumber"), "A · cucumber"), (self.r.pick("B", "tomato"), "B · tomato"),
                 (self.r.pick("A", "tomato"), "A · tomato")]
        fig, ax = plt.subplots(figsize=(10, 3.6))
        y = np.arange(len(cases))[::-1]
        labels = []
        for yi, (r, lab) in zip(y, cases):
            opex = [sum(r["cost_gbp_kg"][k] for k in ks) for _, ks in self.OPEX_GROUPS]
            parts = [r[f"lcop_{rate}"] - sum(opex)] + opex
            left = np.concatenate([[0], np.cumsum(parts)[:-1]])
            for i, (v, l0) in enumerate(zip(parts, left)):
                ax.barh(yi, v - 0.006, left=l0 + 0.003, color=self.S[i], height=0.6)
            ax.plot([r["price_gbp_kg"]] * 2, [yi - 0.38, yi + 0.38], color=Style.INK, lw=2)
            ax.plot([r["import_parity_gbp_kg"]] * 2, [yi - 0.38, yi + 0.38], color=Style.INK, lw=1.2, ls=(0, (1, 1.5)))
            labels.append(f"{lab}, {Style.site(r['name'])}: £{sum(parts):.2f}")
        ax.set_yticks(y, labels)
        ax.set_xlabel(f"Levelised cost at {float(rate) * 100:g} % [£/kg]")
        ax.grid(axis="y", visible=False)
        ax.set_title(f"Cost build-up per kg ({float(rate) * 100:g} % discount rate, LP-sized heat pump unless noted)")
        handles = [Style.box(self.S[0], "Capital recovery (incl. replacements)")]
        handles += [Style.box(self.S[i + 1], g) for i, (g, _) in enumerate(self.OPEX_GROUPS)]
        handles += [Style.line(Style.INK, "DEFRA wholesale price"),
                    Style.line(Style.INK, "Import parity", lw=1.2, ls=(0, (1, 1.5)))]
        Style.legend_below(fig, handles, ncol=4, y=0.0)
        fig.tight_layout()
        self.save(fig, f"bp02_cost_buildup_{rate.replace('0.', '')}")

    def capex(self):
        cases = [(self.r.pick(T, crop, rule), f"{T} · {crop} · {'LP + store' if rule == 'lp' else 'full standby'}")
                 for T, crop in (("B", "cucumber"), ("B", "tomato"), ("A", "cucumber"), ("A", "tomato"))
                 for rule in ("lp", "standby")]
        fig, ax = plt.subplots(figsize=(10, 4.2))
        y = np.arange(len(cases))[::-1]
        labels = []
        for yi, (r, lab) in zip(y, cases):
            area = r["area_ha"] * 1e4
            parts = [sum(r["capex"].get(k, 0.0) for k in ks) / area for _, ks in self.CAPEX_GROUPS]
            left = np.concatenate([[0], np.cumsum(parts)[:-1]])
            for i, (v, l0) in enumerate(zip(parts, left)):
                ax.barh(yi, max(v - 2, 0), left=l0 + 1, color=self.S[i], height=0.62)
            labels.append(f"{lab}: £{sum(parts):.0f}/m², £{r['capex_total'] / 1e6:.1f} M, {r['area_ha']:.1f} ha")
        ax.set_yticks(y, labels)
        ax.set_xlabel("Capital cost [£/m²]")
        ax.grid(axis="y", visible=False)
        ax.set_title("Capital cost per m² of glasshouse (lead site per track and crop; turbine excluded)")
        Style.legend_below(fig, [Style.box(self.S[i], g) for i, (g, _) in enumerate(self.CAPEX_GROUPS)], ncol=3, y=0.0)
        fig.tight_layout()
        self.save(fig, "bp03_capex")

    def cumulative(self, track="B", crop="cucumber"):
        flows, name = ScenarioFlows(track, crop).run()
        fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
        for ax, rate in zip(axes, (0.08, 0.035)):
            disc = (1 + rate) ** -np.arange(31)
            for i, res in enumerate(flows.values()):
                ax.plot(np.arange(31), np.cumsum(np.array(res["cashflow"]) * disc) / 1e6, color=self.S[i], lw=2)
            ax.axhline(0, color=Style.INK, lw=0.8)
            ax.set_xlabel("Year [-]")
            ax.set_title(f"Discounted at {rate * 100:g} %")
        axes[0].set_ylabel("Cumulative discounted cash flow [£ M]")

        def irr(v):
            return f"IRR {v * 100:.1f} %" if v is not None else "IRR n/a"
        Style.legend_below(fig, [Style.line(self.S[i], f"{k}: NPV8 £{res['npv_0.08'] / 1e6:+.1f} M, NPV3.5 "
                                            f"£{res['npv_0.035'] / 1e6:+.1f} M, {irr(res['irr'])}")
                                 for i, (k, res) in enumerate(flows.items())], ncol=1)
        fig.suptitle(f"Route to viability: track {track} {crop}, {Style.site(name)}, LP-sized heat pump",
                     x=0.01, ha="left", fontweight="bold")
        fig.tight_layout()
        self.save(fig, f"bp04_cumulative_{track}_{crop}")

    def sensitivity(self, track="B", crop="cucumber", rate="008"):
        r = self.r.pick(track, crop)
        key = "npv_008" if rate == "008" else "npv_0035"
        base = r["npv_0.08"] if rate == "008" else r["npv_0.035"]
        items = sorted(((self.SENS_LABEL[k], s[key] - base) for k, s in r["sens"].items() if k in self.SENS_LABEL),
                       key=lambda t: abs(t[1]))
        fig, ax = plt.subplots(figsize=(8, 4))
        y = np.arange(len(items))
        ax.barh(y, [d / 1e6 for _, d in items], color=[Style.GOOD if d > 0 else Style.BAD for _, d in items], height=0.6)
        ax.axvline(0, color=Style.INK, lw=1)
        ax.set_yticks(y, [f"{lab} ({d / 1e6:+.1f})" for lab, d in items])
        pct = "8" if rate == "008" else "3.5"
        ax.set_xlabel(f"Change in NPV at {pct} % [£ M]")
        ax.grid(axis="y", visible=False)
        ax.set_title(f"NPV sensitivity: track {track} {crop}, {Style.site(r['name'])} (base £{base / 1e6:+.2f} M at {pct} %)")
        Style.legend_below(fig, [Style.box(Style.GOOD, "Raises NPV"), Style.box(Style.BAD, "Lowers NPV")], ncol=2, y=0.0)
        fig.tight_layout()
        self.save(fig, f"bp05_sensitivity_{track}_{crop}_{rate}")

    def monthly_sales(self):
        im = pd.read_csv(HERE / "data" / "imports_monthly.csv")
        cif = im[im.origin == "World"].groupby(["crop", "month"]).gbp_per_kg_cif.mean()
        fig, axes = plt.subplots(2, 2, figsize=(10, 5.2), sharex=True, gridspec_kw={"height_ratios": [1.2, 1]})
        x = np.arange(12)
        for j, crop in enumerate(("cucumber", "tomato")):
            r = self.r.pick("B", crop)
            axes[0, j].bar(x, np.array(r["monthly_share"]) * r["kg_yr"] / 1e3, color=self.S[0], width=0.72)
            axes[0, j].set_title(f"Track B {crop}, {Style.site(r['name'])}: {r['kg_yr'] / 1e3:.0f} t/yr, {r['area_ha']:.1f} ha")
            axes[0, j].set_ylabel("Harvest [t/month]")
            axes[0, j].grid(axis="x", visible=False)
            axes[1, j].plot(x, r["monthly_price"], color=self.S[1], lw=2, marker="o", ms=4)
            axes[1, j].plot(x, [cif[(crop, m)] for m in range(1, 13)], color=self.S[2], lw=2, marker="o", ms=4)
            axes[1, j].set_ylabel("Price [£/kg]")
            axes[1, j].set_ylim(0, None)
            axes[1, j].set_xticks(x, Style.MONTHS)
            axes[1, j].set_xlabel("Month [-]")
        Style.legend_below(fig, [Style.box(self.S[0], "Harvest"),
                                 Style.line(self.S[1], "UK wholesale (DEFRA 2023-26; import CIF where no UK data)", marker="o"),
                                 Style.line(self.S[2], "Import CIF (Comtrade 2023-25)", marker="o")], ncol=3)
        fig.suptitle("Unlit Scottish glass sells into the summer price trough", x=0.01, ha="left", fontweight="bold")
        fig.tight_layout()
        self.save(fig, "bp06_monthly_sales_price")

    def energy(self):
        cases = sorted([p for p in self.r.perf if p["crop"] == "cucumber" and Style.site(p["name"]) == "Stranraer"],
                       key=lambda p: p["track"], reverse=True)
        fig, axes = plt.subplots(3, len(cases), figsize=(10, 7), sharex=True, squeeze=False)
        x = np.arange(12)
        for j, p in enumerate(cases):
            hp, wh = np.array(p["hp_heat_kWh_m2"]), np.array(p["waste_heat_kWh_m2"])
            axes[0, j].bar(x, hp, color=self.S[0], width=0.72)
            axes[0, j].bar(x, wh, bottom=hp, color=self.S[2], width=0.72)
            axes[0, j].set_title(f"{Style.TRACK_NAME[p['track']]}\nheat {sum(p['heat_kWh_m2']):.0f}, electricity "
                                 f"{sum(p['elec_kWh_m2']):.0f} kWh/m²/yr, SCOP {p['scop_unit']:.2f}")
            axes[0, j].set_ylabel("Heat supplied [kWh/m²]")
            axes[0, j].grid(axis="x", visible=False)
            axes[1, j].plot(x, np.array(p["cop_unit"], dtype=float), color=self.S[1], lw=2, marker="o", ms=4)
            axes[1, j].set_ylim(0, 6)
            axes[1, j].set_ylabel("Heat-pump COP [-]")
            axes[2, j].fill_between(x, p["T_in_min"], p["T_in_max"], color=self.S[3], alpha=0.25, lw=0)
            axes[2, j].plot(x, p["T_in_mean"], color=self.S[3], lw=2)
            axes[2, j].plot(x, p["T_out_mean"], color=self.S[4], lw=2)
            axes[2, j].set_ylabel("Temperature [°C]")
            axes[2, j].set_xticks(x, Style.MONTHS)
            axes[2, j].set_xlabel("Month [-]")
        Style.legend_below(fig, [Style.box(self.S[0], "Heat from heat pump"), Style.box(self.S[2], "Waste heat"),
                                 Style.line(self.S[1], "Monthly COP", marker="o"),
                                 Style.line(self.S[3], "Inside air, mean"), Style.box(self.S[3], "Inside air, min-max"),
                                 Style.line(self.S[4], "Outside air, mean")], ncol=3)
        fig.suptitle("Energy performance: cucumber at the Stranraer location (2023 weather, R717 heat pump)",
                     x=0.01, ha="left", fontweight="bold")
        fig.tight_layout()
        self.save(fig, "bp07_energy_performance")

    def carbon(self):
        fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
        for ax, crop in zip(axes, ("cucumber", "tomato")):
            rows = sorted([p for p in self.r.perf if p["crop"] == crop],
                          key=lambda p: (p["track"] != "B", p["annual"]["kg_co2e_per_kg"]))
            y = np.arange(len(rows))[::-1]
            vals = [p["annual"]["kg_co2e_per_kg"] for p in rows]
            ax.barh(y, vals, color=[self.S[0] if p["track"] == "B" else self.S[2] for p in rows], height=0.6)
            ax.axvline(self.IMPORT_CO2[crop], color=Style.INK, lw=1.5)
            ax.set_yticks(y, [f"{p['track']} · {Style.site(p['name'])} ({v:.2f})" for p, v in zip(rows, vals)])
            ax.set_xlim(0, self.IMPORT_CO2[crop] * 1.15)
            ax.set_xlabel("Carbon delivered to RDC [kg CO₂e/kg]")
            ax.set_title(f"{crop.capitalize()} (imports {self.IMPORT_CO2[crop]:.2f})")
            ax.grid(axis="y", visible=False)
        Style.legend_below(fig, [Style.box(self.S[0], Style.TRACK_NAME["B"]), Style.box(self.S[2], Style.TRACK_NAME["A"]),
                                 Style.line(Style.INK, "Imports to the same RDCs", lw=1.5)], ncol=3)
        fig.suptitle("Carbon per kg: a quarter to a half of imports", x=0.01, ha="left", fontweight="bold")
        fig.tight_layout()
        self.save(fig, "bp08_carbon")

    def diversify_margin(self, rate=0.08):
        d = json.loads((HERE / "results" / "bplan" / "diversify.json").read_text())["rows"]
        rows = [r for r in d if r["rate"] == rate and r["revenue"] == r["revenue"]]
        structs = list(dict.fromkeys(r["structure"] for r in rows))
        prods = list(dict.fromkeys(r["name"] for r in rows))
        fig, ax = plt.subplots(figsize=(10, 5))
        y = np.arange(len(prods))[::-1]
        offs = np.linspace(0.27, -0.27, len(structs))
        for i, s in enumerate(structs):
            for yi, p in zip(y, prods):
                c = {r["yield_case"]: r for r in rows if r["structure"] == s and r["name"] == p}
                if "central" not in c:
                    continue
                ax.plot([c["low"]["margin"], c["high"]["margin"]], [yi + offs[i]] * 2, color=self.S[i], lw=1.5)
                ax.plot(c["central"]["margin"], yi + offs[i], "o", ms=6, color=self.S[i], mec=Style.SURFACE, mew=1.2)
        ax.axvline(0, color=Style.INK, lw=1)
        tiers = {r["name"]: r["yield_tier"] for r in rows}
        ax.set_yticks(y, [f"{p} [{tiers[p]}]" for p in prods])
        ax.set_xlabel(f"Annual margin at {rate * 100:g} % [£/m²] (dot: central yield; line: low-high yield)")
        ax.grid(axis="y", visible=False)
        ax.set_title("Diversification screen: margin per m² by product and structure (Stranraer, DEFRA/CIF prices)")
        Style.legend_below(fig, [Style.line(self.S[i], s, marker="o") for i, s in enumerate(structs)], ncol=2, y=0.0)
        fig.tight_layout()
        self.save(fig, f"bp09_diversify_margin_{int(rate * 1000):03d}")

    def price_windows(self):
        import bplan_diversify as bd
        pr = bd.Prices()
        show = [("strawberries", "strawberries", "strawberry", 1.0, "Strawberry"),
                ("raspberries", "raspberries", "raspberry", 1.0, "Raspberry"),
                ("blueberries", "blueberries", "blueberry", 1.0, "Blueberry"),
                ("tomatoes", "cherry", "tomato", 1.0, "Cherry tomato"),
                ("lettuce", "butterhead_indoor", "lettuce", 0.2, "Butterhead lettuce (0.2 kg head)"),
                ("mixed_babyleaf_salad", "pillow_pack", None, 1.0, "Baby-leaf salad")]
        fig, axes = plt.subplots(2, 3, figsize=(10, 5.4), sharex=True)
        x = np.arange(12)
        for ax, (item, var, cifc, unit, title) in zip(axes.flat, show):
            m, src = pr.monthly(item, var, cifc, unit)
            uk = np.where(src == "DEFRA", m, np.nan)
            imp = np.where(src == "CIF", m, np.nan)
            ax.bar(x, np.nan_to_num(uk), color=self.S[0], width=0.72)
            ax.bar(x, np.nan_to_num(imp), color=self.S[1], width=0.72)
            ax.set_title(title, fontsize=9)
            ax.set_xticks(x, Style.MONTHS)
            ax.grid(axis="x", visible=False)
        for ax in axes[:, 0]:
            ax.set_ylabel("Price [£/kg]")
        for ax in axes[1]:
            ax.set_xlabel("Month [-]")
        Style.legend_below(fig, [Style.box(self.S[0], "UK-grown wholesale (DEFRA 2023-26)"),
                                 Style.box(self.S[1], "No UK supply: import CIF (Comtrade 2023-25)")], ncol=2)
        fig.suptitle("Price windows: where UK supply stops, imports set the price", x=0.01, ha="left", fontweight="bold")
        fig.tight_layout()
        self.save(fig, "bp10_price_windows")

    def thermal_campus(self):
        c = json.loads((HERE / "results" / "bplan" / "thermal_campus.json").read_text())
        x = np.arange(12)
        fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
        axes[0].bar(x, c["heat_MWh"], color=Style.GRID, width=0.75, edgecolor=Style.INK, linewidth=0.6)
        for i, (k, v) in enumerate(c["cases"].items()):
            axes[0].plot(x, v["heat_from_vf_MWh"], color=self.S[i], lw=2, marker="o", ms=4)
        axes[0].set_ylabel("Heat per month [MWh]")
        axes[0].set_title("1 ha cucumber glasshouse: heat met from a vertical farm")
        axes[1].plot(x, c["cop_air"], color=self.S[3], lw=2, marker="o", ms=4)
        axes[1].plot(x, c["cop_vf_source"], color=self.S[4], lw=2, marker="o", ms=4)
        axes[1].set_ylim(0, 8)
        axes[1].set_ylabel("Heat-pump COP [-]")
        axes[1].set_title("COP: outdoor air vs vertical-farm return air (18 °C)")
        for ax in axes:
            ax.set_xticks(x, Style.MONTHS)
            ax.set_xlabel("Month [-]")
        h = [Style.box(Style.GRID, "Glasshouse heat demand")]
        h += [Style.line(self.S[i], f"From {k.replace('m2', ' m²')} of LED tiers: {v['share_of_heat'] * 100:.0f} % of heat, "
                         f"LED {sum(v['led_MWh']):.0f} MWh/yr, HP saves {v['hp_elec_air_MWh'] - v['hp_elec_vf_MWh']:.0f} MWh/yr",
                         marker="o") for i, (k, v) in enumerate(c["cases"].items())]
        h += [Style.line(self.S[3], "COP, outdoor-air source", marker="o"),
              Style.line(self.S[4], "COP, vertical-farm source", marker="o")]
        Style.legend_below(fig, h, ncol=2)
        fig.suptitle("Thermal campus: LED heat as the heat-pump source (200 W/m², 16 h/day; placeholders)", x=0.01,
                     ha="left", fontweight="bold")
        fig.tight_layout()
        self.save(fig, "bp11_thermal_campus")

    def all(self):
        self.cost_vs_price()
        self.cost_buildup("0.08")
        self.cost_buildup("0.035")
        self.capex()
        self.cumulative("B", "cucumber")
        self.sensitivity("B", "cucumber", "008")
        self.sensitivity("B", "cucumber", "0035")
        self.monthly_sales()
        if self.r.perf:
            self.energy()
            self.carbon()
        if (HERE / "results" / "bplan" / "diversify.json").exists():
            self.diversify_margin(0.08)
            self.diversify_margin(0.035)
            self.price_windows()
            self.thermal_campus()


if __name__ == "__main__":
    BusinessPlanFigures(Results.load()).all()
