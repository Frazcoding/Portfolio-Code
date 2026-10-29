"""Business plan (2026-10-05): diversification screen. Per-m2 annual margin of candidate products grown at the track-B
lead location (Stranraer), on the same cost basis as cashflow.py, so products can be compared with the cucumber and tomato
lead designs. A SCREEN, not a design result: every input carries a tier (sourced / model / estimate / placeholder) and
the report lists which products rest on placeholders.

Method
  revenue    yield x usable floor x harvest-weighted monthly price. Price by month = DEFRA UK wholesale 2023-26 where
             >= 3 observations, otherwise UK import CIF (Comtrade 2023-25, data/imports_monthly*.csv), as cashflow.py.
  heat       heating degree-hours on the crop's setpoint calendar (crops.CLIMATES), scaled by one coefficient fitted to
             the verified track-B cucumber and tomato simulations at the same site (results/bplan/perf_B.json).
  energy     heat / seasonal COP of the lead design + auxiliary electricity per m2, at the lead design's electricity price.
  capital    structure + heat pump per m2 from the lead design (cashflow.json); heat pump scaled by the crop's design
             temperature lift; cheaper structure options from SAC/SRUC (2026) Table 11; annuity over 30 yr at 8 % / 3.5 %.

    python bplan_diversify.py
"""
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import crops  # noqa: E402

OUT = HERE / "results" / "bplan"


@dataclass(frozen=True)
class Product:
    key: str
    name: str
    climate: str                     # crops.CLIMATES key for the heating calendar
    yield_kg_m2: tuple               # central, low, high (growing floor)
    yield_tier: str
    yield_src: str
    harvest: tuple                   # calendar months with harvest (equal weights unless the lead design's profile is used)
    price: tuple                     # (DEFRA item, variety, CIF crop or None)
    labour_h_m2: float
    labour_tier: str
    inputs_gbp_m2: float             # plants, substrate, fertiliser, protection
    pack_gbp_kg: float
    co2_kg_m2: float
    unit_kg: float = 1.0             # DEFRA price unit in kg (lettuce per head)


ALL = tuple(range(1, 13))
PRODUCTS = [
    Product("cucumber", "Cucumber (lead)", "cucumber", (54.6, 46.4, 64.4), "model", "crop_gh at Stranraer, R10", ALL,
            ("cucumbers", "cucumbers", "cucumber"), 0.8, "estimate", 6.25, 0.10, 40.0),
    Product("tomato_round", "Tomato, round loose", "tomato", (41.7, 35.4, 49.2), "model", "crop_gh at Stranraer, R10", ALL,
            ("tomatoes", "round", "tomato"), 0.9, "estimate", 7.15, 0.15, 40.0),
    Product("tomato_vine", "Tomato, on the vine", "tomato", (37.5, 33.4, 41.7), "placeholder",
            "0.8-1.0 x round (truss harvest loses no fruit; varieties lower-yielding): KWIN-AGV to source", ALL,
            ("tomatoes", "vine", "tomato"), 0.95, "estimate", 7.15, 0.15, 40.0),
    Product("tomato_cherry", "Tomato, cherry", "tomato", (25.0, 20.0, 30.0), "placeholder",
            "unlit cherry ~0.5-0.7 x round (KWIN-AGV to source)", ALL, ("tomatoes", "cherry", "tomato"), 1.5, "estimate",
            7.15, 0.30, 40.0),
    Product("pepper", "Sweet pepper (red)", "pepper", (23.0, 21.0, 26.4), "sourced+scaled",
            "CBS NL 26.4 kg/m2 x Stranraer light (~0.87)", tuple(range(3, 12)), ("capsicum", "red", "pepper"), 0.75,
            "estimate", 6.0, 0.15, 30.0),
    Product("strawberry", "Strawberry, two forced crops", "strawberry", (11.1, 8.0, 11.8), "sourced (NL glass+tunnel)",
            "CBS NL 'onder glas en tunnels'", (4, 5, 6, 9, 10, 11), ("strawberries", "strawberries", "strawberry"), 1.4,
            "estimate", 6.0, 0.50, 10.0),
    Product("raspberry", "Raspberry, long cane + primocane", "raspberry", (3.0, 2.0, 4.0), "estimate",
            crops.YIELD_NOTES["raspberry"], (4, 5, 6, 9, 10, 11), ("raspberries", "raspberries", "raspberry"), 1.0,
            "estimate", 5.0, 0.60, 0.0),
    Product("blueberry", "Blueberry, forced", "blueberry", (2.5, 2.0, 3.0), "estimate", crops.YIELD_NOTES["blueberry"],
            (5, 6), ("blueberries", "blueberries", "blueberry"), 0.6, "estimate", 3.0, 0.50, 0.0),
    Product("lettuce", "Lettuce, butterhead (head 0.2 kg)", "lettuce", (20.0, 12.0, 41.0), "estimate",
            crops.YIELD_NOTES["lettuce"], ALL, ("lettuce", "butterhead_indoor", "lettuce"), 0.35, "estimate", 4.0, 0.10,
            10.0, unit_kg=0.2),
    Product("babyleaf", "Baby-leaf salad / rocket", "lettuce", (6.0, 4.0, 10.0), "placeholder",
            "12-15 cuts/yr x 0.4-0.6 kg/m2 (to source)", ALL, ("mixed_babyleaf_salad", "pillow_pack", None), 0.8,
            "estimate", 4.0, 0.60, 0.0),
    Product("avocado", "Avocado, dwarf trees", "grape", (1.0, 0.8, 1.15), "model (earlier study)",
            "SCOPE 3.12: 0.8-1.15 kg/m2", (1, 2, 3, 4, 5), (None, None, "avocado"), 0.15, "estimate", 1.0, 0.25, 0.0),
]


class Prices:
    MIN_OBS = 3

    def __init__(self):
        d = pd.read_csv(HERE / "data" / "defra_wholesale_prices.csv", parse_dates=["date"])
        self.defra = d[d["date"].dt.year.between(2023, 2026)]
        frames = [pd.read_csv(p) for p in (HERE / "data").glob("imports_monthly*.csv")]
        im = pd.concat(frames)
        self.cif = im[im["origin"] == "World"].groupby(["crop", "month"])["gbp_per_kg_cif"].mean()

    def monthly(self, item, variety, cif_crop, unit_kg=1.0):
        m = pd.Series(np.nan, index=range(1, 13))
        n = pd.Series(0, index=range(1, 13))
        if item:
            s = self.defra[(self.defra["item"] == item) & (self.defra["variety"] == variety)]
            g = s.groupby(s["date"].dt.month)["price"]
            m, n = g.mean().reindex(range(1, 13)) / unit_kg, g.count().reindex(range(1, 13)).fillna(0)
        src = pd.Series("DEFRA", index=range(1, 13))
        if cif_crop and cif_crop in self.cif.index.get_level_values(0):
            c = self.cif.loc[cif_crop].reindex(range(1, 13))
            fill = (n < self.MIN_OBS) & c.notna()
            m, src = m.where(~fill, c), src.where(~fill, "CIF")
        src = src.where(m.notna(), "interp")
        return m.interpolate(limit_direction="both").to_numpy(), src.to_numpy()


class HeatModel:
    """Heat = k x heating degree-hours on the crop's setpoint calendar, k fitted to the verified simulations."""
    DAY = (7, 19)

    def __init__(self, t_amb, perf_lead):
        self.t = np.asarray(t_amb)[:8760]
        self.hour = np.arange(8760) % 24
        self.doy = np.arange(8760) // 24 + 1
        x = np.array([self.degree_hours(c) for c in ("cucumber", "tomato")])
        y = np.array([sum(perf_lead[c]["heat_kWh_m2"]) for c in ("cucumber", "tomato")])
        self.k = float(x @ y / (x @ x))
        self.fit = {c: (float(self.k * xi), float(yi)) for c, xi, yi in zip(("cucumber", "tomato"), x, y)}

    def setpoints(self, climate):
        periods = sorted(crops.CLIMATES[climate].periods, key=lambda p: p.start_doy)
        day, night = np.zeros(8760), np.zeros(8760)
        for p in periods:
            sel = self.doy >= p.start_doy
            day[sel], night[sel] = p.heat_day, p.heat_night
        return np.where((self.hour >= self.DAY[0]) & (self.hour < self.DAY[1]), day, night)

    def degree_hours(self, climate):
        return float(np.maximum(self.setpoints(climate) - self.t, 0.0).sum())

    def heat(self, climate):
        return self.k * self.degree_hours(climate)

    def design_lift(self, climate, t_design=-3.1):
        return max(max(p.heat_night for p in crops.CLIMATES[climate].periods) - t_design, 0.0)


@dataclass(frozen=True)
class Structure:
    name: str
    structure_gbp_m2: float
    tier: str
    source: str


class Screen:
    LABOUR_RATE = 15.0           # GBP/h, NLW + on-costs (estimate, input_register)
    CO2_PRICE = 0.25             # GBP/kg delivered liquid CO2 (breakeven.py, estimate)
    COMMISSION = 0.05
    OM_FRAC = 0.02
    YEARS = 30

    def __init__(self):
        cf = json.loads((HERE / "results" / "costing" / "cashflow.json").read_text())["results"]
        self.lead = next(r for r in cf if r["track"] == "site_opt_B" and r["crop"] == "cucumber" and r["rule"] == "lp")
        perf = json.loads((OUT / "perf_B.json").read_text())
        self.perf = {p["crop"]: p for p in perf if "Creamery" in p["name"]}
        import site_opt
        sites = {s["site_key"]: s for s in json.loads((HERE / "data" / "siting" / "shortlist.json").read_text())}
        self.t_amb = site_opt.site_state(sites[self.lead["site"]])["wx"]["T_amb"].to_numpy()
        self.heat = HeatModel(self.t_amb, self.perf)
        self.prices = Prices()
        area = self.lead["area_ha"] * 1e4
        cap = self.lead["capex"]
        plant = cap["heat_pump"] + cap["hot_water_store"] + cap["battery"]
        self.hp_gbp_m2 = plant * 1.15 / area                              # + development and contingency
        self.struct_gbp_m2 = (self.lead["capex_total"] / area) - self.hp_gbp_m2
        self.usable = self.perf["cucumber"]["annual"]["usable"]
        p = self.perf["cucumber"]
        self.scop = p["scop_unit"]
        self.aux_kWh_m2 = sum(p["elec_kWh_m2"]) - sum(p["comp_kWh_m2"])
        self.elec_price = p["annual"]["elec_price"]
        self.haul_gbp_kg = self.lead["cost_gbp_kg"]["haulage_to_rdc"]
        self.fixed_m2 = (self.lead["costs"]["overheads"] + self.lead["costs"]["land_rent"]) / area
        self.structures = [
            Structure("Lead design (new Venlo-type glass, double AR)", self.struct_gbp_m2, "model + RFQ placeholders",
                      "cashflow.json track B lead"),
            Structure("Basic glasshouse", 100.0 * 1.15 + 15.0, "sourced", "SAC/SRUC 2026 Table 11 GBP 1M/ha (+15 % dev/cont., "
                      "+GBP 15/m2 HV connection share)"),
            Structure("Polycrub (larger)", 170.0 * 1.15, "sourced", "SAC/SRUC 2026 Table 11 GBP 170/m2"),
            Structure("Second-hand glasshouse", 60.0 * 1.15 + 15.0, "sourced", "SAC/SRUC 2026 Table 11 ~GBP 600k/ha"),
        ]

    @classmethod
    def annuity(cls, r):
        return r / (1 - (1 + r) ** -cls.YEARS)

    def evaluate(self, pr, structure, rate=0.08, case=0):
        price_m, src = self.prices.monthly(*pr.price, unit_kg=pr.unit_kg)
        months = np.array(pr.harvest) - 1
        if pr.key == "cucumber" or pr.key.startswith("tomato"):
            w = np.array(self.lead["monthly_share"])                      # lead design's harvest profile
        else:
            w = np.zeros(12)
            w[months] = 1.0
        w = w / w.sum()
        price = float(w @ price_m)
        y = pr.yield_kg_m2[case] * self.usable
        heat = self.heat.heat(pr.climate)
        energy_kWh = heat / self.scop + self.aux_kWh_m2
        lift_ratio = self.heat.design_lift(pr.climate) / self.heat.design_lift("cucumber")
        capex = structure.structure_gbp_m2 + self.hp_gbp_m2 * lift_ratio
        revenue = y * price
        costs = {
            "capital": capex * self.annuity(rate),
            "o_and_m": capex * self.OM_FRAC,
            "energy": energy_kWh * self.elec_price,
            "labour": pr.labour_h_m2 * self.LABOUR_RATE * self.usable,
            "inputs_co2": pr.inputs_gbp_m2 * self.usable + pr.co2_kg_m2 * self.CO2_PRICE * self.usable,
            "pack_haul_comm": y * (pr.pack_gbp_kg + self.haul_gbp_kg) + revenue * self.COMMISSION,
            "overheads_land": self.fixed_m2,
        }
        total = sum(costs.values())
        return dict(product=pr.key, name=pr.name, structure=structure.name, rate=rate, yield_kg_m2=y, price=price,
                    price_cif_months=int(sum(1 for m in months if src[m] == "CIF")), revenue=revenue, costs=costs,
                    total=total, margin=revenue - total, breakeven_price=(total - revenue * self.COMMISSION) /
                    (y * (1 - self.COMMISSION)) if y else None, heat_kWh_m2=heat, capex_m2=capex,
                    yield_tier=pr.yield_tier, yield_src=pr.yield_src, labour_tier=pr.labour_tier)

    def run(self):
        rows = []
        for pr in PRODUCTS:
            for s in self.structures:
                for rate in (0.08, 0.035):
                    for case, lab in ((0, "central"), (1, "low"), (2, "high")):
                        r = self.evaluate(pr, s, rate, case)
                        r["yield_case"] = lab
                        rows.append(r)
        out = dict(rows=rows, heat_fit=self.heat.fit, heat_k=self.heat.k, lead=dict(
            site=self.lead["name"], capex_struct_m2=self.struct_gbp_m2, hp_m2=self.hp_gbp_m2, scop=self.scop,
            elec_price=self.elec_price, usable=self.usable))
        (OUT / "diversify.json").write_text(json.dumps(out, indent=1, default=float))
        self.print_table(rows)
        self.write_markdown(rows)
        return out

    def write_markdown(self, rows):
        structs = list(dict.fromkeys(r["structure"] for r in rows))
        lines = ["| Product | Yield kg/m2 (tier) | Price GBP/kg (CIF months) | Revenue GBP/m2 | "
                 + " | ".join(f"Margin 8 % / 3.5 %: {s}" for s in structs) + " | Break-even GBP/kg, lead structure, 8 % |",
                 "|---|---|---|---:|" + "---:|" * len(structs) + "---:|"]
        for pr in PRODUCTS:
            c = {(r["structure"], r["rate"]): r for r in rows if r["product"] == pr.key and r["yield_case"] == "central"}
            r0 = c[(structs[0], 0.08)]
            if r0["revenue"] != r0["revenue"]:
                continue
            cells = [f"{c[(s, 0.08)]['margin']:+.0f} / {c[(s, 0.035)]['margin']:+.0f}" for s in structs]
            lines.append(f"| {pr.name} | {r0['yield_kg_m2']:.1f} ({pr.yield_tier}) | {r0['price']:.2f} "
                         f"({r0['price_cif_months']}) | {r0['revenue']:.0f} | " + " | ".join(cells)
                         + f" | {r0['breakeven_price']:.2f} |")
        (OUT / "diversify_table.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def print_table(self, rows):
        print(f"heat fit (model vs sim, kWh/m2): {self.heat.fit}")
        print(f"{'product':34}{'structure':42}{'kg/m2':>7}{'£/kg':>7}{'rev':>7}{'cost':>7}{'margin':>8}{'BE £/kg':>8}{'heat':>6}")
        for r in rows:
            if r["rate"] == 0.08 and r["yield_case"] == "central":
                print(f"{r['name'][:33]:34}{r['structure'][:41]:42}{r['yield_kg_m2']:7.1f}{r['price']:7.2f}"
                      f"{r['revenue']:7.0f}{r['total']:7.0f}{r['margin']:8.0f}{r['breakeven_price']:8.2f}"
                      f"{r['heat_kWh_m2']:6.0f}")


class ThermalCampus:
    """Heat recovered from a cooled zone (LED vertical farm or cold store) as the glasshouse heat pump's source.

    All LED electricity ends up as heat in the room (energy balance); the heat pump lifts it from the room's return air
    instead of outdoor air. COP_new = (measured fraction of Carnot) x Carnot(T_sup, T_src_new), month by month, with the
    fraction taken from the lead design's simulation (perf_B.json)."""
    T_SRC_VF = 18.0               # vertical-farm return air / chilled-water loop, C (design choice, typical 18-24 C room)
    LED_W_M2 = 200.0              # LED power per m2 of growing tier, W (placeholder, 150-250; supplier data needed)
    TIER_M2 = (500.0, 1000.0, 3000.0)   # vertical-farm growing-tier area per ha of glasshouse (design choices)
    PHOTOPERIOD_H = 16.0          # lettuce / leafy greens (placeholder, crop-dependent)

    def __init__(self, perf):
        self.p = perf

    def run(self, glass_m2=10000.0):
        heat = np.array(self.p["heat_kWh_m2"]) * glass_m2
        hp_heat = np.array(self.p["hp_heat_kWh_m2"]) * glass_m2
        days = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])
        t_sup = np.array(self.p["t_sup_C"])
        eff = np.nan_to_num(np.array(self.p["carnot_eff"], dtype=float), nan=0.38)
        cop_air = np.array(self.p["cop_unit"], dtype=float)
        cop_vf = eff * (t_sup + 273.15) / np.maximum(t_sup - self.T_SRC_VF, 5.0)
        out = {"heat_MWh": (heat / 1e3).tolist(), "cop_air": cop_air.tolist(), "cop_vf_source": cop_vf.tolist(),
               "glass_m2": glass_m2, "cases": {}}
        per_m2 = self.LED_W_M2 * self.PHOTOPERIOD_H * days / 1e3                         # kWh/m2 tier per month
        # evaporator heat = LED heat; condenser heat = evaporator heat x COP/(COP-1)
        cond_per_m2 = per_m2 * cop_vf / (cop_vf - 1)
        for vf_m2 in self.TIER_M2:
            supplied = np.minimum(cond_per_m2 * vf_m2, heat)
            elec_air = hp_heat / np.where(np.isfinite(cop_air), cop_air, 3.0)
            elec_vf = supplied / cop_vf + np.maximum(heat - supplied, 0) / np.where(np.isfinite(cop_air), cop_air, 3.0)
            surplus = np.maximum(cond_per_m2 * vf_m2 - heat, 0) / cop_vf * (cop_vf - 1)    # LED heat still to reject
            out["cases"][f"{vf_m2:.0f}m2"] = dict(
                vf_tier_m2=vf_m2, heat_from_vf_MWh=(supplied / 1e3).tolist(), led_MWh=(per_m2 * vf_m2 / 1e3).tolist(),
                hp_elec_air_MWh=float(elec_air.sum() / 1e3), hp_elec_vf_MWh=float(elec_vf.sum() / 1e3),
                summer_heat_to_reject_MWh=float(surplus.sum() / 1e3), share_of_heat=float(supplied.sum() / heat.sum()))
        return out


if __name__ == "__main__":
    res = Screen().run()
    perf = {p["crop"]: p for p in json.loads((OUT / "perf_B.json").read_text()) if "Creamery" in p["name"]}
    camp = ThermalCampus(perf["cucumber"]).run()
    (OUT / "thermal_campus.json").write_text(json.dumps(camp, indent=1, default=float))
    for k, c in camp["cases"].items():
        print(f"campus {k}: VF tiers {c['vf_tier_m2']:.0f} m2 per ha glass, covers {c['share_of_heat'] * 100:.0f} % of heat, "
              f"HP electricity {c['hp_elec_air_MWh']:.0f} -> {c['hp_elec_vf_MWh']:.0f} MWh/yr, LED {sum(c['led_MWh']):.0f} MWh/yr, "
              f"summer heat to reject {c['summer_heat_to_reject_MWh']:.0f} MWh")
    print("COP air", np.round(camp["cop_air"], 2), "\nCOP vf ", np.round(camp["cop_vf_source"], 2))
