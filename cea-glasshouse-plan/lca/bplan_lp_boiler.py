"""BP19a: peak-boiler cases WITH a heat store. The LP (finalist_lp.solve, boiler=True) sizes heat pump, electric peak
boiler and hot-water store together on the track-B lead design (Stranraer, cucumber) for the workbook scenarios S1-S4.
Rule 'standby': heat pump + boiler output at the design hour >= design heat load (the user's full-load standby rule, the
boiler being the cheap part of it). Rule 'lp': no standby constraint (sensitivity; 2010 winter not checked).
Writes results/bplan/boiler_store.json and folds the standby results into results/bplan/xlsx_inputs.json (S1-S4)."""
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

os.environ["CEA_TRACK"] = "B"
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent))
sys.path.insert(0, str(HERE.parent))           # repo copy of simcore first (cloud has no ../simcore)
import energy_grid  # noqa: E402
import finalist_lp  # noqa: E402
import site_opt  # noqa: E402

OUTDIR = HERE / "results" / "bplan"
CROP = "cucumber"


class BoilerStoreStudy:
    def __init__(self):
        self.inputs = json.loads((OUTDIR / "xlsx_inputs.json").read_text())
        SL = {s["site_key"]: s for s in json.loads((HERE / "data" / "siting" / "shortlist.json").read_text())}
        refined = json.loads((site_opt.OUT / f"refined_{CROP}.json").read_text())["sites"]
        entry = next(e for e in refined if e["name"] == self.inputs["site"])
        self.site = SL[entry["site"]]
        _, self.price, finalist_lp.CI = energy_grid.inputs()

    def run_case(self, sc, rule):
        x = {**self.inputs["x"], "glazing": sc["glazing"]}
        o = {"elec": sc["elec"]}
        row = site_opt.evaluate(self.site, x, CROP, {**o, "hp_boiler": sc["hp_boiler"]})
        r = finalist_lp.run(self.site, x, CROP, row, self.price, rule, o=o, boiler=True, elec=sc["elec"])
        return r

    def run(self, workers=7):
        jobs = [(sc, rule) for sc in self.inputs["scen"][1:] for rule in ("standby", "lp")]
        with ProcessPoolExecutor(max_workers=workers) as ex:               # one core and ~1.3 GB per LP
            res = list(ex.map(_case, jobs))
        out = {}
        for (sc, rule), r in zip(jobs, res):
            out.setdefault(sc["key"], {})[rule] = r
        for sc in self.inputs["scen"][1:]:
            for rule, r in out[sc["key"]].items():
                print(f"{sc['key']} {rule:<8} GBP/kg {r['gbp_kg']:.3f} HP {r['hp_kW_th']:.0f} kWth boiler {r['boiler_kW_th']:.0f} kWth "
                      f"store {r['store_kWh']:.0f} kWh (design {r['design_kW']:.0f}) boiler {r['boiler_MWh']:.0f} MWh "
                      f"import {r['import_MWh']:.0f} MWh peak {r['import_peak_kW']:.0f} kW", flush=True)
        (OUTDIR / "boiler_store.json").write_text(json.dumps(out, indent=1, default=float))
        self.fold(out)
        return out

    def fold(self, out):
        """Replace the no-store S1-S4 plant sizes in xlsx_inputs.json by the LP standby results (heat pump + boiler + store)."""
        for sc in self.inputs["scen"][1:]:
            r, alt = out[sc["key"]]["standby"], out[sc["key"]]["lp"]
            wind = r["used_wind_MWh"]
            sc.update(hp_kW=r["hp_kW_th"], boiler_kW=r["boiler_kW_th"], store_kWh=r["store_kWh"], boiler_MWh=r["boiler_MWh"],
                      elec_MWh=r["import_MWh"] + wind, self_share=wind / (r["import_MWh"] + wind), net_gbp_yr=r["net_gbp"],
                      gbp_kg_lp_store=r["gbp_kg"], gbp_kg_lp_rule=alt["gbp_kg"], hp_kW_lp_rule=alt["hp_kW_th"],
                      boiler_kW_lp_rule=alt["boiler_kW_th"], store_kWh_lp_rule=alt["store_kWh"],
                      label=sc["label"].replace("heat pump 69 % + electric peak boiler", "LP-sized heat pump + peak boiler + store").replace("heat pump 69 % + peak boiler", "LP-sized heat pump + peak boiler + store"))
        (OUTDIR / "xlsx_inputs.json").write_text(json.dumps(self.inputs, indent=1, default=float))


_STUDY = None


def _case(job):
    global _STUDY
    _STUDY = _STUDY or BoilerStoreStudy()
    return _STUDY.run_case(*job)


if __name__ == "__main__":
    BoilerStoreStudy().run()
