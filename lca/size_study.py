"""Gate B: re-run the leading sites' designs at fixed sizes (5 / 10 / 20 / 30 ha), to separate a real size optimum
from the wall-light credit (light through the side walls helps small houses most).

For each finalist site (refined_<crop>.json) and size: start from the refined design, scale its floor to the size
at the same aspect ratio, then local refinement (refine.perturb without the 'area' move, BUDGET steps). Each result
is reported with the full wall light (central) and with no wall light (wall_light = 0: walls still lose heat but
transmit nothing), which bounds the credit. Above the area the site's waste heat supports, the R717 heat pump
supplies the rest (it is sized to the full design load anyway).
Writes results/site_opt/size_<crop>.json.
"""
import json
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import refine  # noqa: E402
import site_opt  # noqa: E402

SIZES_HA = (5.0, 10.0, 20.0, 30.0)
BUDGET = 40
TAG = "_fixedresid" if float(os.environ.get("CEA_RESID_FIXED", 0.0)) else ""     # BP19d: fixed share of the residual
FINALISTS = 3


def at_area(x, ha):
    y = dict(x)
    aspect = y["length"] / (y["n_spans"] * y["span_w"])
    width = math.sqrt(ha * 1e4 / aspect)
    y["n_spans"] = max(1, round(width / y["span_w"]))
    y["length"] = ha * 1e4 / (y["n_spans"] * y["span_w"])
    return y


def _job(args):
    site, x0, crop, ha, seed = args
    rng = np.random.default_rng(seed)
    x = at_area(x0, ha)
    best = site_opt.evaluate(site, x, crop)
    for _ in range(BUDGET):
        y = refine.perturb(best["x"], rng)
        y = at_area(y, ha)                                   # undo any area change from aspect / span moves
        try:
            r = site_opt.evaluate(site, y, crop)
        except Exception:
            r = None
        if r is not None and refine.cost(r) < refine.cost(best):
            best = r
    nowall = site_opt.evaluate(site, best["x"], crop, dict(wall_light=0.0))
    return dict(site=site["site_key"], name=site["name"], crop=crop, ha=ha, gbp=refine.cost(best), kg=best["kg_kg"],
                gbp_nowall=refine.cost(nowall) if nowall else None, kg_nowall=nowall["kg_kg"] if nowall else None,
                waste_share=best["waste_share"], hp_MW=best["hp_kW"] / 1e3, x=best["x"], Y=best["Y"])


def main(crop):
    t = time.time()
    SL = {s["site_key"]: s for s in json.loads((HERE / "data" / "siting" / "shortlist.json").read_text())}
    R = json.loads((site_opt.OUT / f"refined_{crop}.json").read_text())
    sites = R["sites"][:FINALISTS]
    jobs = [(SL[s["site"]], s["best"]["x"], crop, ha, i * 10 + j) for i, s in enumerate(sites)
            for j, ha in enumerate(SIZES_HA)]
    with ProcessPoolExecutor(max_workers=7) as ex:
        res = list(ex.map(_job, jobs))
    ref = {s["site"]: (refine.cost(s["best"]), s["best"]["area_ha"]) for s in sites}
    if TAG:                                                  # BP19d: re-cost the refined design with the same fixed residual
        ref = {s["site"]: (refine.cost(site_opt.evaluate(SL[s["site"]], s["best"]["x"], crop)), s["best"]["area_ha"]) for s in sites}
    (site_opt.OUT / f"size_{crop}{TAG}.json").write_text(json.dumps(
        {"refined": ref, "rows": res, "benchmarks": R["benchmarks"]}, indent=1, default=float))
    print(f"== {crop} ({time.time() - t:.0f} s): GBP/kg at GBP 10/MWh heat [no wall light]; imports "
          f"{R['benchmarks']['gbp_annual']:.2f}")
    for s in sites:
        rows = [r for r in res if r["site"] == s["site"]]
        cells = "  ".join(f"{r['ha']:>4.0f} ha {r['gbp']:.3f} [{r['gbp_nowall']:.3f}] w{r['waste_share'] * 100:.0f}%"
                          for r in rows)
        print(f"{s['name'][:30]:<31} free {ref[s['site']][0]:.3f} at {ref[s['site']][1]:.1f} ha | {cells}")


if __name__ == "__main__":
    for c in sys.argv[1:] or ["cucumber", "tomato"]:
        main(c)
