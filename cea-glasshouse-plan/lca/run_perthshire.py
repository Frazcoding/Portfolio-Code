"""Perthshire off-grid scenario, step 1: glasshouse simulations at the Carse of Gowrie (56.42 N, 3.20 W), 2023.

Every crop with the cost-effective system (controls + variable-speed pump, twin-wall PC), on an air-source and a
ground-source R717 heat pump. Saves hourly heat-pump heat output, heat-pump electricity and other electricity per m2
to results/perthshire/<crop>__<variant>.npz for the off-grid sizing (offgrid.py), and the annual summaries to
results/perthshire/sim.json. Site choice: see SCOPE §3.15.
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import crop  # noqa: E402
import crops  # noqa: E402
import greenhouse  # noqa: E402
import run_crops  # noqa: E402
from config import HeatSupply, Location  # noqa: E402

SITE = Location("perth_carse", lat=56.42, lon=-3.20, description="Carse of Gowrie, Perthshire, UK")
OUT = HERE / "results" / "perthshire"
VARIANTS = ("ctrlair_pc", "ctrl_pc")


def cases():
    out = {}
    for k in [*crops.CROPS, "avocado"]:
        for v in VARIANTS:
            src = "air" if v.startswith("ctrlair") else "ground"
            cfg = run_crops.variant(run_crops.base_cfg(k, src), v)
            out[f"{k}|{v}"] = replace(cfg, location=SITE)
    return out


def run(item):
    key, cfg = item
    H, acc, wx, gr, meta, _ = greenhouse.simulate(cfg)
    s = greenhouse.summary(H, gr, meta)
    s["case"] = key
    if key.startswith("avocado"):
        s.update({f"crop_{k}": v for k, v in crop.from_greenhouse(H, meta, cfg).annual.items()})
    A = meta["area_m2"]
    np.savez_compressed(OUT / f"{key.replace('|', '__')}.npz", q_hp=H["Q_c"] / A, w_hp=H["W_comp"] / A,
                        w_other=(H["W_total"] - H["W_comp"]) / A, t_amb=wx["T_amb"].to_numpy()[:8760])
    return s


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    todo = cases()
    for heat in {(c.heat.cycle, c.heat.hx_scale, c.heat.source) for c in todo.values()}:
        greenhouse.build_map(HeatSupply("hp", heat[2], cycle=heat[0], hx_scale=heat[1]))
    with ProcessPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(run, todo.items()))
    (OUT / "sim.json").write_text(json.dumps(res, indent=1, default=float))
    print(f"{'case':<22}{'heat':>6}{'elec':>7}{'hp':>6}{'other':>7}{'SCOP':>6}{'unmet':>6}{'h>30':>6}{'yield':>7}")
    for r in res:
        print(f"{r['case']:<22}{r['heat_kWh_m2']:>6.0f}{r['electricity_kWh_m2']:>7.1f}{r['comp_kWh_m2']:>6.1f}"
              f"{r['electricity_kWh_m2'] - r['comp_kWh_m2']:>7.1f}{r['scop_unit']:>6.2f}{r['hours_unmet']:>6}"
              f"{r['hours_above_30']:>6}{r.get('crop_yield_t_ha', float('nan')):>7.2f}")
