"""BP37c: heat source on the lit lead (lit_open design 2: 2.9 ha, 150 umol, 2 PPA turbines): air vs ground vs Loch Ryan
sea water, then the BP33 financing on each (finance.py, central vendor scheme).

The simulation already models ground (borehole field, config.HeatSupply field_*) and water sources (source temperature
series); site_opt option hp_source selects them (site_opt.source_series, hp_kind). Sea temperature: Millport monthly
means (site_opt.SEA_T_MONTHLY, secondary), ~7.2 C in Feb-Mar.

Source-side works, all PLACEHOLDER (no usable UK cost found 2026-10-07), added to capex with a 40-yr life (no
replacement inside the 30-yr study):
  * sea: intake, screen, outfall, titanium plate exchanger and pumps GBP 300/kW_th of heat pump (range 150-450) plus
    marine licence and survey GBP 50 k; heat pump on the water-source DEA curve.
  * ground: closed-loop boreholes GBP 1,200/kW_th (range 800-1,750: GBP 60-90/m drilled at ~50 W/m extraction).

    python bplan_heat_source.py        -> results/bplan/heat_source.json
Needs the uncached inputs (simcore/cache weather + grid files, lca/results/store): run on the desktop or allow
api.carbonintensity.org.uk, api.octopus.energy and archive-api.open-meteo.com in the cloud environment.
"""
import json

import numpy as np

import bplan_5ha  # noqa: F401  (track B is set at import time, before site_opt)
import bplan_lit_open as L
import finance as F
import site_opt

assert site_opt.TRACK == "B"
OUT = F.OUT / "heat_source.json"


class SourceWorks:
    GBP_KW = {"air": 0.0, "sea": 300.0, "ground": 1200.0}
    FIXED = {"air": 0.0, "sea": 50e3, "ground": 0.0}

    @classmethod
    def capex(cls, source, hp_kw_th):
        return cls.GBP_KW[source] * hp_kw_th + cls.FIXED[source]


class SourceCase(L.LitOpen):
    def __init__(self, source):
        super().__init__()
        self.source = source
        base_opts = self.pt.opts
        self.pt.opts = lambda d: {**base_opts(d), **({} if source == "air" else {"hp_source": source})}


class Study:
    SOURCES = ("air", "sea", "ground")

    @staticmethod
    def lcop(project, s=F.Stress(), rate=0.08):
        r = project.real(s, project.price0)
        cost = r["opex"] + r["rep"]
        cost[F.YEARS] -= r["resid"]
        disc = (1 + rate) ** -np.arange(F.YEARS + 1)
        return (sum(project.capex0.values()) + cost @ disc) / (r["kg"] @ disc)

    def run(self):
        rows = {}
        for src in self.SOURCES:
            lo = SourceCase(src)
            c = lo.case({**lo.BASE, **lo.DESIGNS[2]})
            entry = c["prices"]["undercut 3%"]
            p = F.Project(entry, c["parity_gbp_kg"])
            p.capex0["heat_source_works"] = SourceWorks.capex(src, c["hp_kW_th"])
            f = F.Finance(p, next(sc for sc in F.SCHEMES if sc.name == F.CENTRAL))
            r = f.run(p.parity * 0.9)
            rows[src] = dict(Y=c["Y"], hp_kW_th=c["hp_kW_th"], store_kWh=c["store_kWh"], import_peak_kW=c["import_peak_kW"],
                             carbon=c["carbon"], source_capex=p.capex0["heat_source_works"], capex=sum(p.capex0.values()),
                             elec_gbp_yr=sum(entry["costs"][k] for k in F.ELEC_KEYS), lcop_008=self.lcop(p),
                             min_price=f.min_price(), equity_irr=r["equity_irr"], min_dscr=r["min_dscr"])
            print(src, {k: round(v, 3) if isinstance(v, float) else v for k, v in rows[src].items()}, flush=True)
            OUT.write_text(json.dumps(rows, indent=1, default=float))
        return rows


if __name__ == "__main__":
    Study().run()
