"""BP32: lit winter crop on the GBP 10 M lead design (2.9 ha, single 2xAR glass, pipe 4.5 m/m2, third-party turbine at
GBP 90/MWh private wire), cucumber, Stranraer. Same machinery as the year-round study (bplan_yearround.Point): LED capex
from rates.csv led_kw (RVO cap GBP 900/kW high, GBP 515 central), crop-model monthly harvest share, winter prices from the
DEFRA series with the UK import CIF where DEFRA has < 3 observations (BP2).

    python bplan_lit_winter.py            -> results/bplan/lit_winter.json (resumable)
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent))
sys.path.insert(0, str(HERE.parent))           # repo copy of simcore first (cloud has no ../simcore)
import bplan_yearround as Y  # noqa: E402

OUT = Y.OUT / "lit_winter.json"


class LitWinter:
    LEAD = dict(site="site_028", ha=2.9, glazing="single_2ar", cap=500.0, product="cucumber", follow=None, pipe=4.5,
                co2="bought", bulk=False, wind="ppa", turbines=1, inter_frac=0.4, hours=18.0, dli=25.0)
    LEVELS = (0.0, 100.0, 150.0, 220.0)               # PPFD umol/m2/s from the LED rows; 0 = the unlit lead

    def designs(self):
        return [{**self.LEAD, "ppfd": p, "inter_frac": 0.0 if p == 0 else self.LEAD["inter_frac"]} for p in self.LEVELS]

    def run(self):
        done = json.loads(OUT.read_text()) if OUT.exists() else []
        seen = {json.dumps(r["design"], sort_keys=True) for r in done}
        for d in self.designs():
            if json.dumps(d, sort_keys=True) in seen:
                continue
            r = Y._point("cucumber", d)
            done.append(r)
            OUT.write_text(json.dumps(done, indent=1, default=float))
            if "error" in r:
                print(d["ppfd"], "ERROR", r["error"], flush=True)
            else:
                print(f"ppfd {d['ppfd']:>4.0f} Y {r['Y']:.1f} capex {r['capex'] / 1e6:.2f} M winter share {r['winter_share']:.2f} "
                      f"month-min {r['month_min_ratio']:.2f} cover {r['price_cover']:.2f} lcop8 {r['lcop8']:.2f} "
                      f"payback lender {r['payback_lender']} premium {r['payback_premium']} CO2e {r['carbon']:.2f}", flush=True)
        return done


if __name__ == "__main__":
    LitWinter().run()
