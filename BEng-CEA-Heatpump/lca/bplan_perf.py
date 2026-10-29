"""Business plan (2026-10-05): monthly energy and climate performance of the lead designs, for the plan's figures and
verification. Re-runs the fast hourly simulation on the refined design of the top TOP sites per crop for one track, with
the same setup as site_opt.evaluate (no model change).

    CEA_TRACK=B python bplan_perf.py      # writes results/bplan/perf_B.json   (track A: CEA_TRACK=A)
"""
import json
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import greenhouse_fast  # noqa: E402
import site_opt  # noqa: E402


class Monthly:
    INDEX = np.minimum(np.arange(8760) // 730, 11)

    @classmethod
    def sum(cls, x):
        return np.bincount(cls.INDEX, np.asarray(x)[:8760], minlength=12)

    @classmethod
    def stat(cls, x, how):
        x = np.asarray(x)[:8760]
        return np.array([getattr(x[cls.INDEX == k], how)() for k in range(12)])

    @classmethod
    def weighted(cls, x, w):
        x, w = np.asarray(x)[:8760], np.asarray(w)[:8760]
        return cls.sum(x * w) / np.maximum(cls.sum(w), 1e-9)


class DesignPerformance:
    def __init__(self, site, x, crop):
        self.site, self.x, self.crop = site, x, crop

    def run(self):
        d, a, cfg, low, avail, waste_kw = site_opt.site_setup(self.site, self.x, self.crop, site_opt.TRACK_OPTS)
        S = site_opt.site_state(self.site)
        H, _, wx, _, meta, _ = greenhouse_fast.simulate_fast(cfg, i_floor=a["I_floor"], waste_kw=waste_kw,
                                                             t_source=S["t_src"] if low else None)
        area = d.floor
        qc, wc = Monthly.sum(H["Q_c"]), Monthly.sum(H["W_comp"])
        t_sup, t_src = Monthly.weighted(H["T_sup"], H["Q_c"]), Monthly.weighted(H["T_src"], H["Q_c"])
        cop = np.where(wc > 0, qc / np.maximum(wc, 1e-9), np.nan)
        # Carnot heating COP = T_sup / (T_sup - T_src), absolute temperatures
        carnot = (t_sup + 273.15) / np.maximum(t_sup - t_src, 1.0)
        ev = site_opt.evaluate(self.site, self.x, self.crop)
        return dict(
            area_m2=area, design_heat_kW=meta["design_heat_loss_kw"],
            heat_kWh_m2=(Monthly.sum(H["Q_pipe"]) / area).tolist(), hp_heat_kWh_m2=(qc / area).tolist(),
            waste_heat_kWh_m2=(Monthly.sum(H["Q_waste"]) / area).tolist(), comp_kWh_m2=(wc / area).tolist(),
            aux_kWh_m2=(Monthly.sum(H["W_aux"]) / area).tolist(), elec_kWh_m2=(Monthly.sum(H["W_total"]) / area).tolist(),
            cop_unit=cop.tolist(), t_sup_C=t_sup.tolist(), t_src_C=t_src.tolist(), carnot_cop=carnot.tolist(),
            carnot_eff=(cop / carnot).tolist(),
            T_in_mean=Monthly.stat(H["T_air_in"], "mean").tolist(), T_in_max=Monthly.stat(H["T_air_in"], "max").tolist(),
            T_in_min=Monthly.stat(H["T_air_in"], "min").tolist(),
            T_out_mean=Monthly.stat(wx["T_amb"].to_numpy(), "mean").tolist(),
            peak_heat_kW=float(np.max(H["Q_pipe"])), hours_gt30=int((H["T_air_in"][:8760] > 30).sum()),
            unmet_h=int((H["unmet"][:8760] > 0).sum()),
            scop_unit=float(H["Q_c"].sum() / max(H["W_comp"].sum(), 1e-9)),
            annual=dict(yield_kg_m2=ev["Y"], kg_co2e_per_kg=ev["kg_kg"], heat_kWh_m2=ev["heat_kWh_m2"],
                        elec_kWh_m2=ev["elec_kWh_m2"], hp_kW=ev["hp_kW"], monthly_share=ev["monthly_share"],
                        wind_kW=ev["wind_kW"], elec_price=ev["elec_price"], elec_ci=ev["elec_ci"],
                        light_rel=ev["light_rel"], usable=ev["usable"], co2_dose_kg_m2=ev["co2_dose_kg_m2"]))


class TrackPerformance:
    TOP = 3
    OUT = HERE / "results" / "bplan"

    def __init__(self, track):
        self.track = track

    def run(self):
        sites = {s["site_key"]: s for s in json.loads((HERE / "data" / "siting" / "shortlist.json").read_text())}
        res = []
        for crop in ("cucumber", "tomato"):
            refined = json.loads((site_opt.OUT / f"refined_{crop}.json").read_text())
            for e in refined["sites"][:self.TOP]:
                r = DesignPerformance(sites[e["site"]], e["best"]["x"], crop).run()
                r.update(track=self.track, crop=crop, site=e["site"], name=e["name"])
                res.append(r)
                print(f"[{self.track}] {crop:9}{e['name'][:28]:29} heat {sum(r['heat_kWh_m2']):5.0f} kWh/m2  "
                      f"SCOP {r['scop_unit']:.2f}  elec {sum(r['elec_kWh_m2']):5.0f}  yield {r['annual']['yield_kg_m2']:.1f}  "
                      f"CO2e {r['annual']['kg_co2e_per_kg']:.2f}  unmet {r['unmet_h']} h", flush=True)
        self.OUT.mkdir(parents=True, exist_ok=True)
        (self.OUT / f"perf_{self.track}.json").write_text(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    TrackPerformance(os.environ.get("CEA_TRACK", "A")).run()
