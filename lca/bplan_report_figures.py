"""Report figures for the viable design (results/bplan/plan.json, bplan_plan.py). Visual standard: ../CLAUDE.md section 6
(legend below the axes, pure black text, no in-plot annotations, units in brackets). Writes PNG (300 dpi) and SVG to
../figures/report/.

    python bplan_report_figures.py
"""
import json
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bplan_finance_risk as R  # noqa: E402
import bplan_plan as P  # noqa: E402
import finance as F  # noqa: E402
from bplan_figures import Style  # noqa: E402

OUT = HERE.parent / "figures" / "report"
C = Style.SERIES
INK = "#000000"


class Fig:
    def __init__(self, name, w=7.0, h=4.0, nrows=1, ncols=1, **kw):
        self.name = name
        self.fig, self.ax = plt.subplots(nrows, ncols, figsize=(w, h), **kw)

    def legend(self, handles, ncol=3, y=-0.02):
        self.fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, y), ncol=ncol, fontsize=8,
                        labelcolor=INK)

    def save(self):
        OUT.mkdir(parents=True, exist_ok=True)
        self.fig.tight_layout()
        for ext in ("png", "svg"):
            self.fig.savefig(OUT / f"{self.name}.{ext}", dpi=300, bbox_inches="tight")
        plt.close(self.fig)
        return OUT / f"{self.name}.png"


class Data:
    def __init__(self):
        self.plan = json.loads((HERE / "results" / "bplan" / "plan.json").read_text())
        pk = self.plan["pick"]
        self.designs = self.plan["designs"]
        self.pick = next(d for d in self.designs if d["crop"] == pk["crop"] and d["ha"] == pk["ha"]
                         and d["product"] == pk["product"])
        rows = json.loads((HERE / "results" / "bplan" / "viable_lit.json").read_text())
        self.row = next(r for r in rows if r["crop"] == pk["crop"] and r["design"]["ha"] == pk["ha"]
                        and r["design"]["product"] == pk["product"])
        self.design = P.Design(self.row)
        self.scheme = P.LenderSizing(self.design.project).scheme(self.design.price)


class Figures:
    def __init__(self):
        Style.apply()
        self.d = Data()

    def monthly_supply(self):
        p, d = self.d.pick, self.d.design
        share = np.asarray(self.d.row["harvest_share"])
        t = share * p["targets"]["offtake"]["volume_t_yr"]
        par = np.asarray(json.loads((HERE / "results" / "bplan" / "lit_open.json").read_text())[2]["parity_monthly"])
        f = Fig("fig01_monthly_supply", 7, 5.2, 2, 1, sharex=True)
        x = np.arange(12)
        f.ax[0].bar(x, t, color=C[0], width=0.7)
        f.ax[0].set_ylabel("Harvest [t/month]")
        f.ax[1].plot(x, par, color=C[1], lw=2, marker="o", ms=4)
        f.ax[1].plot(x, par * (1 - P.UNDERCUT), color=C[0], lw=2, marker="s", ms=4)
        f.ax[1].set_ylabel("Price [£/kg]")
        f.ax[1].set_xticks(x, Style.MONTHS)
        f.ax[1].set_xlabel("Month")
        f.legend([Style.box(C[0], f"Harvest, {p['ha']:g} ha lit cucumber"), Style.line(C[1], "Import parity (CIF + haul)"),
                  Style.line(C[0], "Contract target (parity -5 %)", marker="s")], ncol=3)
        return f.save()

    def capex(self):
        cap = self.d.design.project.capex0
        groups = {"Structure (steel, aluminium, glass, concrete)": ("steel", "aluminium", "glass_single_m2", "glass_double_m2",
                                                                    "concrete", "pir_panel_m2"),
                  "Heating pipes and screens": ("heating_pipe_m", "energy_screen_m2"),
                  "Other systems (install, climate computer, irrigation, vents)": (F.RESID_KEY,),
                  "Heat pump and store": ("heat_pump", "hot_water_store", "peak_boiler", "battery"),
                  "LED lighting": ("led_lighting",), "Grid connection": ("hv_import_connection",),
                  "Development and contingency": ("development", "contingency")}
        vals = {k: sum(cap.get(i, 0.0) for i in v) / 1e6 for k, v in groups.items()}
        f = Fig("fig02_capex", 7, 3.6)
        names = list(vals)[::-1]
        f.ax.barh(names, [vals[n] for n in names], color=C[0], height=0.6)
        f.ax.set_xlabel("Capital cost [£ M]")
        f.legend([Style.box(C[0], f"Capital cost, total £{sum(vals.values()):.1f} M")], ncol=1, y=-0.05)
        return f.save()

    def unit_cost(self):
        p, d = self.d.pick, self.d.design
        c, kg = d.project.costs, d.project.kg
        groups = {"Electricity": F.ELEC_KEYS, "Crop and harvest labour": ("labour",),
                  "Salaried team, packhouse, on-call": ("staff_salaried_packhouse_oncall",),
                  "Plants, substrate, fertiliser, CO2": ("young_plants", "substrate", "fertiliser_protection_other", "co2_purchased"),
                  "Packing": ("packing",), "Upkeep, insurance, overheads, rent": ("structure_om_insurance", "heat_pump_om",
                                                                                   "store_om", "overheads", "land_rent")}
        vals = {k: sum(c.get(i, 0.0) for i in v) / kg for k, v in groups.items()}
        vals["Capital charge (8 % real, 30 yr)"] = sum(d.project.capex0.values()) * F.cashflow.annuity_at(0.08, 30) / kg
        f = Fig("fig03_unit_cost", 7, 4.2)
        bottom, handles = 0.0, []
        for i, (k, v) in enumerate(vals.items()):
            f.ax.bar([0], [v], bottom=bottom, color=C[i % len(C)], width=0.5, edgecolor="#fcfcfb", linewidth=1.5)
            handles.append(Style.box(C[i % len(C)], f"{k}: £{v:.2f}"))
            bottom += v
        f.ax.axhline(p["price"], color=INK, lw=1.5, ls="--")
        f.ax.axhline(p["parity"], color=INK, lw=1.5, ls=":")
        handles += [Style.line(INK, f"Contract target £{p['price']:.2f}", ls="--"),
                    Style.line(INK, f"Import parity £{p['parity']:.2f}", ls=":")]
        f.ax.set_xticks([0], [f"{p['ha']:g} ha lit cucumber"])
        f.ax.set_xlim(-0.8, 0.8)
        f.ax.set_ylabel("Cost [£/kg]")
        f.legend(handles, ncol=2, y=-0.02)
        return f.save()

    def scale(self):
        cuc = sorted((d for d in self.d.designs if d["crop"] == "cucumber"), key=lambda d: d["ha"])
        ha = [d["ha"] for d in cuc]
        f = Fig("fig04_scale", 7, 4.0)
        f.ax.plot(ha, [d["finance"]["min_price_vendor_dscr_no_staff"] for d in cuc], color=C[2], lw=2, marker="o", ms=6)
        f.ax.plot(ha, [d["finance"]["min_price_vendor_dscr"] for d in cuc], color=C[1], lw=2, marker="o", ms=6)
        f.ax.plot(ha, [d["finance"]["min_price"] for d in cuc], color=C[0], lw=2, marker="s", ms=6)
        f.ax.axhline(cuc[0]["parity"], color=INK, lw=1.5, ls=":")
        f.ax.axhline(cuc[0]["price"], color=INK, lw=1.5, ls="--")
        f.ax.set_xlabel("Glasshouse area [ha]")
        f.ax.set_ylabel("Minimum price [£/kg]")
        f.legend([Style.line(C[2], "Vendor finance, DSCR 1.25, model staffing only", marker="o"),
                  Style.line(C[1], "Vendor finance, DSCR 1.25, full team", marker="o"),
                  Style.line(C[0], "Lender-sized debt, equity 12 %, full team", marker="s"),
                  Style.line(INK, "Import parity", ls=":"), Style.line(INK, "Contract target (parity -5 %)", ls="--")], ncol=2)
        return f.save()

    def cashflow(self):
        r = self.d.pick["finance"]["central"]
        eq = np.asarray(r["equity_cf"]) / 1e6
        yrs = np.arange(len(eq))
        f = Fig("fig05_equity_cashflow", 7, 5.0, 2, 1, sharex=True)
        f.ax[0].bar(yrs, eq, color=np.where(eq >= 0, C[0], C[1]), width=0.7)
        f.ax[0].set_ylabel("Cash to equity [£ M]")
        f.ax[1].plot(yrs, np.cumsum(eq), color=C[0], lw=2)
        f.ax[1].axhline(0, color=INK, lw=0.8)
        f.ax[1].set_ylabel("Cumulative [£ M]")
        f.ax[1].set_xlabel("Year (0 = construction)")
        f.legend([Style.box(C[0], "Cash to equity (nominal, after tax, debt service and reserves)"),
                  Style.box(C[1], "Equity in (construction, replacements)"), Style.line(C[0], "Cumulative cash to equity")],
                 ncol=2)
        return f.save()

    def dscr(self):
        d = self.d.design
        f = Fig("fig06_dscr", 7, 4.0)
        for (lab, s), col in zip((("Central case", F.Stress()), ("Lender case (yield -15 %)", F.Stress(yield_mult=0.85))),
                                 (C[0], C[1])):
            r = F.Finance(d.project, self.d.scheme, s).run(d.price)
            c, sv = np.asarray(r["cfads"]), np.asarray(r["service"])
            yrs = np.nonzero(sv > 0)[0]
            f.ax.plot(yrs, c[yrs] / sv[yrs], color=col, lw=2.5, marker="o", ms=5, label=lab, zorder=3)
        f.ax.axhline(F.DSCR_MIN, color=INK, lw=1.0, ls="--", zorder=2)
        f.ax.axhline(1.0, color=INK, lw=1.0, ls=":")
        f.ax.set_xlabel("Year")
        f.ax.set_ylabel("Debt service cover ratio [-]")
        f.legend([Style.line(C[0], "Central case", marker="o"), Style.line(C[1], "Lender case (yield -15 %)", marker="o"),
                  Style.line(INK, "Covenant 1.25", ls="--"), Style.line(INK, "Break-even 1.0", ls=":")], ncol=4)
        return f.save()

    def monte_carlo(self):
        d = self.d.design
        mc = R.MonteCarlo(d.project, self.d.scheme)
        mc.draws["price_x"] = mc.draws["price_x"] * (1 - P.UNDERCUT) / 0.90
        q = mc.run()
        irr = mc.arrays["equity_irr"] * 100
        f = Fig("fig07_monte_carlo", 7, 4.0)
        f.ax.hist(irr[np.isfinite(irr)], bins=40, color=C[0], edgecolor="#fcfcfb", linewidth=0.8)
        for k, ls in (("P10", ":"), ("P50", "--"), ("P90", "-.")):
            f.ax.axvline(q["equity_irr"][k] * 100, color=INK, lw=1.5, ls=ls)
        f.ax.axvline(F.EQUITY_HURDLE * 100, color=C[1], lw=2)
        f.ax.set_xlabel("Equity IRR, nominal after tax [%]")
        f.ax.set_ylabel("Draws [-]")
        f.legend([Style.box(C[0], "2,000 draws: yield, price, capex, power, CO2, labour")] +
                 [Style.line(INK, f"{k} {q['equity_irr'][k] * 100:.1f} %", ls=ls) for k, ls in
                  (("P10", ":"), ("P50", "--"), ("P90", "-."))] + [Style.line(C[1], "Hurdle 12 %")], ncol=3)
        return f.save(), q

    def crops(self):
        ds = [d for d in self.d.designs if d["ha"] == self.d.pick["ha"]]
        names = [d["product"] if d["crop"] == "mix" else f"{d['crop']} ({d['product']})" if d["crop"] != "cucumber"
                 else "cucumber" for d in ds]
        x = np.arange(len(ds))
        f = Fig("fig08_crops", 8.5, 6.2, 2, 2)
        panels = [("Yield [kg/m2]", [d["physics"]["Y"] for d in ds]),
                  ("Revenue at target [£/m2]", [d["physics"]["Y"] * d["price"] for d in ds]),
                  ("Minimum price / parity [-]", [d["finance"]["min_price"] / d["parity"] for d in ds]),
                  ("Winter share of output [%]", [d["physics"]["winter_share"] * 100 for d in ds])]
        for ax, (lab, v) in zip(f.ax.ravel(), panels):
            ax.bar(x, v, color=[C[i % len(C)] for i in x], width=0.6)
            ax.set_ylabel(lab)
            ax.set_xticks(x, [""] * len(x))
        f.ax[1, 0].axhline(1 - P.UNDERCUT, color=INK, lw=1.5, ls="--")
        f.legend([Style.box(C[i % len(C)], n) for i, n in enumerate(names)] +
                 [Style.line(INK, "Target price / parity", ls="--")], ncol=2)
        return f.save()

    def staffing(self):
        s = self.d.pick["staffing"]
        dep = dict(sorted(s["departments"].items(), key=lambda kv: kv[1]))
        f = Fig("fig09_staffing", 8, 4.0, 1, 2)
        f.ax[0].barh(list(dep), list(dep.values()), color=C[0], height=0.6)
        f.ax[0].set_xlabel("Full-time equivalents [FTE]")
        h = s["hourly"]
        perm = np.full(12, h["permanent_crop_fte"])
        seas = np.asarray(h["seasonal_fte_month"])
        x = np.arange(12)
        f.ax[1].bar(x, perm, color=C[0], width=0.7, edgecolor="#fcfcfb", linewidth=1.0)
        f.ax[1].bar(x, seas, bottom=perm, color=C[1], width=0.7, edgecolor="#fcfcfb", linewidth=1.0)
        f.ax[1].set_xticks(x, Style.MONTHS)
        f.ax[1].set_ylabel("Crop and harvest staff [FTE]")
        f.ax[1].set_xlabel("Month")
        f.legend([Style.box(C[0], f"Permanent (total {s['fte_total']:.0f} FTE incl. salaried and packhouse)"),
                  Style.box(C[1], "Seasonal (summer peak)")], ncol=2)
        return f.save()

    def viability_map(self):
        d = self.d.design
        prices = np.linspace(1.25, 1.60, 15)
        ylds = np.linspace(0.75, 1.05, 13)
        z = np.full((len(ylds), len(prices)), np.nan)
        for j, pr in enumerate(prices):
            sc = P.LenderSizing(d.project).scheme(pr)
            for i, ym in enumerate(ylds):
                v = F.Finance(d.project, sc, F.Stress(yield_mult=ym)).run(pr)["equity_irr"]
                z[i, j] = np.nan if v is None else v * 100
        f = Fig("fig10_viability_map", 7, 4.6)
        im = f.ax.pcolormesh(prices, ylds * d.row["summary"]["Y"], z, cmap="Blues", shading="nearest", vmin=0, vmax=30)
        cb = f.fig.colorbar(im, ax=f.ax)
        cb.set_label("Equity IRR, nominal after tax [%]", color=INK)
        f.ax.contour(prices, ylds * d.row["summary"]["Y"], z, levels=[12.0], colors=[INK], linewidths=1.5)
        f.ax.axvline(d.price, color=C[1], lw=2, ls="--")
        f.ax.set_xlabel("Contract price, today's money [£/kg]")
        f.ax.set_ylabel("Yield achieved [kg/m2]")
        f.ax.grid(False)
        f.legend([Style.line(INK, "Equity IRR = 12 % hurdle"), Style.line(C[1], "Contract target", ls="--")], ncol=2)
        return f.save()

    def growth(self):
        g = json.loads((HERE / "results" / "bplan" / "growth_plan.json").read_text())
        f = Fig("fig11_growth", 7, 4.0)
        names = {"self / yield x1.0": ("From retained cash, model yield", C[0], "-"),
                 "new equity / yield x1.0": ("New equity when lenders allow, model yield", C[1], "-"),
                 "self / yield x0.85": ("From retained cash, yield -15 %", C[0], "--")}
        hs = []
        for k, (lab, col, ls) in names.items():
            a = g[k]["area_by_year"]
            yrs = sorted(int(y) for y in a)
            f.ax.step(yrs, [a[str(y)] for y in yrs], where="post", color=col, lw=2, ls=ls)
            hs.append(Style.line(col, f"{lab} (outside equity £{g[k]['outside_equity'] / 1e6:.1f} M)", ls=ls))
        f.ax.set_xlabel("Year")
        f.ax.set_ylabel("Glasshouse area operating [ha]")
        f.ax.set_ylim(0, 18)
        f.legend(hs, ncol=1)
        return f.save()

    def all(self):
        out = [self.monthly_supply(), self.capex(), self.unit_cost(), self.scale(), self.cashflow(), self.dscr()]
        p, q = self.monte_carlo()
        out += [p, self.crops(), self.staffing(), self.viability_map(), self.growth()]
        return out, q


if __name__ == "__main__":
    paths, q = Figures().all()
    print("\n".join(map(str, paths)))
