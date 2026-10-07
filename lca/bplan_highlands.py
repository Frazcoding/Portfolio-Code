"""Highlands screen (user, 2026-10-05): the GBP 10 M lead design (bplan_10m.LeadCase: 2.9 ha single glass, R717 heat pump +
store sized by the LP, 0.5 MVA import cap, third-party 2.5 MW turbine on a private wire, CO2 1,000 ppm) moved to mainland
Highland locations already in data/siting/shortlist.json (track B: used as locations only, no waste heat), against
Stranraer. Each site gets its own weather, light, wind, heat-pump/store sizing and haul to the Central Belt RDCs.

Regional price: supermarkets price nationally, so a Highland grower's only price lever is the retailer's avoided cost
of trucking produce north from its Central Belt RDCs. The upper bound is the study's own haul cost between the site and
the RDCs (siting.logistics); the captured share is a labelled PLACEHOLDER (50 %). Local demand is capped at the
Highlands and Islands population x UK consumption per head (DEFRA 2025: (51.0 + 202.6) kt / 69.3 M = 3.66 kg/person;
HIE area ~0.47 M people, NRS mid-2023, to cite) = ~1.7 kt/yr; the rest is sold at the evidence or contract price.

    python bplan_highlands.py        # writes results/bplan/highlands.json
"""
import json

import bplan_5ha as B5
import bplan_10m as M
import cashflow
import finalist_lp
import site_opt

SITES = ("site_028", "site_034", "site_011", "site_037")    # Stranraer, Inverness, Invergordon, Moray coast (Roseisle)
KG_PER_HEAD, HI_PEOPLE = (51.0 + 202.6) / 69.3, 0.47e6
UPLIFT_SHARE = (0.5, "placeholder", "share of the retailer's avoided Central Belt -> Highland haul passed to the grower")
PRICES = {"evidence (DEFRA farm-gate 2023-25)": 1.01, "premium contract": M.CapexCapStudy.P}


class HighlandScreen:
    def __init__(self):
        self.st = M.CapexCapStudy()
        self.sites = {s["site_key"]: s for s in json.loads((B5.HERE / "data" / "siting" / "shortlist.json").read_text())}
        self.L = M.LeadCase()

    def case(self, key):
        st, L, site = self.st, self.L, self.sites[key]
        x = st.layout(L.HA, L.GLAZING)
        o = {"elec": st.ELEC, "pipe_m2": L.PIPE, "hx_scale": 1.0}
        ev_o = {**o, "hp_boiler": 0.5, "co2": st.CO2}
        row = site_opt.evaluate(site, x, B5.CROP, ev_o)
        yc = st.yield_cap(site_opt.evaluate(site, x, B5.CROP, {**o, "hp_boiler": 0.5}))
        lp = finalist_lp.run(site, x, B5.CROP, row, st.study.price, "lp", store_kwh0=B5.CopLevers.STORE0 * L.HA / B5.HA,
                             o=o, boiler=False, elec=st.ELEC, import_cap_kw=L.CAP * 0.95, store=True)
        A = row["ledger"]["area_m2"]
        row_c = site_opt.evaluate(site, x, B5.CROP, {**ev_o, "yield_mult": yc})
        gbp_c, kg_c = st.search_basis(row_c, lp, A)
        kg = row["Y"] * yc * A
        haul = row["logistics_gbp_kg"]
        local_share = min(1.0, KG_PER_HEAD * HI_PEOPLE / kg) if key != "site_028" else 0.0
        uplift = local_share * haul * UPLIFT_SHARE[0]
        entry = {"site": key, "name": site["name"], "best": {"x": x}}
        out = dict(site=key, name=site["name"], lat=site["lat"], Y=row["Y"] * yc, light_rel=row["light_rel"],
                   heat_kWh_m2=row["heat_kWh_m2"], wind_hub=site["wind_hub_best2km"], hp_kW_th=lp["hp_kW_th"],
                   store_kWh=lp["store_kWh"], design_kW=lp["design_kW"], unmet_2010_h=lp.get("unmet_2010_h"),
                   search_gbp_kg_exfarm=gbp_c - row_c["logistics_gbp_kg"], search_kg_kg=kg_c, haul_gbp_kg=haul,
                   rdc_road_km=site["rdc_road_km_mean"], local_share=local_share, regional_uplift_gbp_kg=uplift,
                   wind_used_MWh=lp["used_wind_MWh"], developer=self.developer(site, lp), scenarios={})
        for name, p in PRICES.items():
            r = cashflow.build(site_opt.OUT, B5.CROP, entry, lp, "lp",
                               {"eval": ev_o, "yield_mult": yc, "commission": 0.0, "labour_mult": M.LABOUR_MULT,
                                "haul_mult": 0.0, "price_flat": p + uplift})
            out["scenarios"][name] = dict(price=p + uplift, capex=r["capex_total"], opex_gbp_kg=r["opex_gbp_yr"] / r["kg_yr"],
                                          ebitda=r["revenue_gbp_yr"] - r["opex_gbp_yr"], payback=r["payback"],
                                          npv_008=r["npv_0.08"], irr=r["irr"], lcop_008=r["lcop_0.08"])
        return out

    @staticmethod
    def developer(site, lp):
        """Third-party turbine at this site: revenue per MWh (private-wire sales + export) vs its LCOE at 8 %."""
        import energy_grid
        O, Oo = energy_grid.ELEC_OPTIONS["tp_2p5MW"], energy_grid.ELEC_OPTIONS["own_2p5MW"]
        gen = float((O["kw"] * site_opt.site_state(site)["pu80"][:8760]).sum()) / 1e3
        a8 = 0.08 / (1 - 1.08 ** -20)
        lcoe8 = (Oo["kw"] * Oo["capex"] * a8 + Oo["kw"] * Oo["om_kw_yr"]) / gen
        used = lp["used_wind_MWh"]
        rev = (used * O["ppa"] * 1e3 + (gen - used) * Oo["export"] * 1e3) / gen
        return dict(gen_MWh=gen, used_MWh=used, lcoe_8pct_gbp_mwh=lcoe8, revenue_gbp_mwh=rev, margin_gbp_mwh=rev - lcoe8)

    def run(self):
        rows = []
        for k in SITES:
            c = self.case(k)
            rows.append(c)
            e, p = c["scenarios"]["evidence (DEFRA farm-gate 2023-25)"], c["scenarios"]["premium contract"]
            print(f"{c['name'][:28]:<29} lat {c['lat']:.1f}  Y {c['Y']:.1f}  heat {c['heat_kWh_m2']:.0f}  wind {c['wind_hub']:.1f} m/s  "
                  f"HP {c['hp_kW_th']:.0f} store {c['store_kWh'] / 1e3:.0f}  capex {p['capex'] / 1e6:.2f} M  cost {c['search_gbp_kg_exfarm']:.3f}  "
                  f"CO2e {c['search_kg_kg']:.3f}  opex {p['opex_gbp_kg']:.3f}/kg  uplift {c['regional_uplift_gbp_kg']:.3f}  "
                  f"payback evidence {e['payback'] and round(e['payback'], 1)} / premium {p['payback'] and round(p['payback'], 1)}  "
                  f"dev margin {c['developer']['margin_gbp_mwh']:.1f}", flush=True)
            (B5.OUTDIR / "highlands.json").write_text(json.dumps(rows, indent=1, default=float))
        return rows


if __name__ == "__main__":
    HighlandScreen().run()
