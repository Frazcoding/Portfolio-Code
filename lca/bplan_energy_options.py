"""Energy options on the 8 ha lit cucumber house (user 2026-10-07: run the Loch Ryan heat pump and The Creamery's waste
heat, eliminate grid top-ups, and make all electricity as cheap as possible; lights keep their fixed schedule).

Variants (physics through bplan_viable.py, each the full chain): air-source lead; sea-water heat pump (Loch Ryan); host
waste heat (The Creamery, 4.6 GWh/yr at 80 C); zero grid import with 4 / 6 / 8 PPA turbines and a firm backup engine
(natural-gas CHP, biomethane CHP or HVO generator, finalist_lp.BACKUP) plus optional PV, battery and heat store sized by the
LP. Each goes through bplan_plan.Design: full staffing, lender-sized debt, Monte Carlo.

Pick rule for the energy supply: the cheapest zero-grid variant (minimum price for a 12 % equity return) whose carbon stays
at or below CARBON_MAX kg CO2e/kg (PLACEHOLDER 0.50, against ~0.81 for imports, so the low-carbon claim holds) and whose PPA
still pays the turbine developer 8 % (HighlandDev.margin >= 0, within rounding): more turbines export more at GBP 60/MWh,
so their developer needs a dearer PPA, and gas CHP displaces wind until the PPA no longer pays.

    python bplan_energy_options.py   -> results/bplan/energy_options.json, ENERGY_OPTIONS.md
"""
import json

import bplan_plan as P
import finance as F

OUT = F.OUT
CARBON_MAX = 0.50


class Variant:
    @staticmethod
    def label(d):
        if d.get("grid") == "none":
            b = {"gas_chp": "gas CHP", "biomethane_chp": "biomethane CHP", "hvo": "HVO generator"}[d["plant"]["backup"]]
            w = " + Creamery heat" if d.get("waste") else ""
            return f"Zero grid: {d['turbines']} turbines at GBP {d.get('ppa', 0.090) * 1e3:.0f}/MWh + {b}{w}"
        if d.get("hp_source") == "sea":
            return "Sea-water heat pump (Loch Ryan)"
        if d.get("waste"):
            return "Creamery waste heat + air heat pump"
        return "Lead: air-source heat pump, grid top-up"

    @staticmethod
    def is_base(d):
        return not (d.get("grid") or d.get("hp_source") or d.get("waste"))


class Study:
    def __init__(self, ha=8.0):
        rows = json.loads((OUT / "viable_lit.json").read_text())
        self.rows = [r for r in rows if r["crop"] == "cucumber" and r["design"]["ha"] == ha]

    def run(self):
        out = []
        for r in self.rows:
            d = P.Design(r)
            fin = d.finance()
            e, s = r["entry"], r["summary"]
            c = e["costs"]
            out.append(dict(label=Variant.label(r["design"]), design=r["design"], capex=sum(d.project.capex0.values()),
                            energy_gbp_yr=sum(c.get(k, 0.0) for k in F.ELEC_KEYS) + c.get("engine_pv_om", 0.0),
                            grid_gbp_yr=c.get("electricity_grid", 0.0), wind_gbp_yr=c.get("electricity_wind_from_turbine", 0.0),
                            fuel_gbp_yr=c.get("backup_fuel", 0.0), kg=e["kg_yr"], Y=s["Y"], carbon=s["carbon"],
                            hp_kW_th=s["hp_kW_th"], store_MWh=s["store_kWh"] / 1e3, import_peak_kW=s["import_peak_kW"],
                            engine_capex=e["capex"].get("backup_engine", 0.0), pv_capex=e["capex"].get("solar_pv", 0.0),
                            battery_capex=e["capex"].get("battery", 0.0), lcop8=s["lcop8"], min_price=fin["min_price"],
                            equity_irr=fin["central"]["equity_irr"], p50=fin["monte_carlo"]["equity_irr"]["P50"],
                            p_dscr_1=fin["monte_carlo"]["p_dscr_below_1.0"], equity=fin["equity_need"],
                            debt=fin["central"]["debt"], viable=fin["viable"], developer_gbp_mwh=s["developer"]))
            print(out[-1]["label"], round(out[-1]["min_price"], 3), round(out[-1]["carbon"], 2), flush=True)
        zero = [o for o in out if o["design"].get("grid") == "none" and o["carbon"] <= CARBON_MAX and o["developer_gbp_mwh"] >= -0.5]
        pick = min(zero, key=lambda o: o["min_price"]) if zero else None
        return dict(options=sorted(out, key=lambda o: o["min_price"]), pick=pick and pick["label"], carbon_max=CARBON_MAX)

    @staticmethod
    def markdown(res):
        pct = F.Report.pct
        L = ["# Energy options, 8 ha lit cucumber", "", f"Pick (cheapest zero-grid with carbon <= {res['carbon_max']}): {res['pick']}", "",
             "| Option | Capex GBP M | Energy GBP k/yr | of which fuel | Carbon kg/kg | Min price GBP/kg | Equity IRR | P50 | "
             "Equity GBP M | Developer margin GBP/MWh | Viable |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
        for o in res["options"]:
            L.append(f"| {o['label']} | {o['capex'] / 1e6:.2f} | {o['energy_gbp_yr'] / 1e3:,.0f} | {o['fuel_gbp_yr'] / 1e3:,.0f} | "
                     f"{o['carbon']:.2f} | {o['min_price']:.3f} | {pct(o['equity_irr'])} | {pct(o['p50'])} | "
                     f"{o['equity'] / 1e6:.2f} | {o['developer_gbp_mwh']:+.1f} | {'yes' if o['viable'] else 'no'} |")
        return "\n".join(L) + "\n"


if __name__ == "__main__":
    res = Study().run()
    (OUT / "energy_options.json").write_text(json.dumps(res, indent=1, default=float))
    md = Study.markdown(res)
    (OUT / "ENERGY_OPTIONS.md").write_text(md)
    print(md)
