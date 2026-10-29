"""Multi-crop UK glasshouse energy: 1 ha Venlo at Chelmsford, ground-source R717 heat pump sized to each crop's
night setpoint, unlit. Yield is not simulated here (crops.py literature values), except avocado (crop.py).

Variants <system>_<cover>: "baseline" (thesis control), "ctrl" (low-temperature control + variable-speed pump) and
"opt" (config.optimised: also grow pipes, larger HX, seasonal borehole store with semi-closed cooling), all ground
source, and "ctrlair" (controls + pump on the air-source R717 unit, no boreholes); covers "pc" (twin-wall
polycarbonate) and "glass".
`python run_crops.py [variant ...]` runs only those variants and merges them into the existing results.
Writes results/crops_sim.json and the hourly electricity profile of every case to results/profiles/<case>.npy
(kW per m2) for the wind/battery sizing in energy_systems.py.
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import climate  # noqa: E402
import config  # noqa: E402
import crop  # noqa: E402
import crops  # noqa: E402
import greenhouse  # noqa: E402
from config import CO2, Cooling, HeatSupply, with_  # noqa: E402

VARIANTS = ("baseline_pc", "baseline_glass", "ctrl_pc", "ctrl_glass", "opt_pc", "opt_glass", "ctrlair_pc", "ctrlair_glass")


def base_cfg(key, source="ground"):
    if key == "avocado":   # semi-closed cooling needs the ground field; off for air source
        return with_(config.commercial(1.0, source, climate=climate.crop_led()), co2=CO2(enrich=True),
                     cooling=Cooling(enabled=source != "air"))
    clim = crops.CLIMATES[key]
    night = max(p.heat_night for p in clim.periods)
    return with_(config.commercial(1.0, source, climate=clim),
                 heat=HeatSupply("hp", source, design_indoor_C=max(18.0, night)))


def variant(cfg, v):
    system, cov = v.split("_")
    if system == "opt":
        out = config.optimised(cfg)
    elif system in ("ctrl", "ctrlair"):   # low-temperature control + variable-speed pump (no new hardware but the VSD)
        out = config.optimised(cfg, seasonal_store=False, pipe_m_per_m2=cfg.hydronics.pipe_m_per_m2, hx_scale=1.0)
    else:
        out = cfg
    return config.cover(out, cov)


def cases(variants=VARIANTS):
    return {f"{k}|{v}": variant(base_cfg(k, "air" if v.startswith("ctrlair") else "ground"), v)
            for k in [*crops.CROPS, "avocado"] for v in variants}


def run(item):
    key, cfg = item
    H, acc, wx, gr, meta, _ = greenhouse.simulate(cfg)
    s = greenhouse.summary(H, gr, meta)
    s["case"] = key
    if key.startswith("avocado"):
        c = crop.from_greenhouse(H, meta, cfg).annual
        s.update({f"crop_{k}": v for k, v in c.items()})
    prof = HERE / "results" / "profiles"
    prof.mkdir(exist_ok=True)
    np.save(prof / f"{key.replace('|', '__')}.npy", (H["W_total"] / meta["area_m2"]).astype(np.float32))
    return s


if __name__ == "__main__":
    todo = cases(tuple(sys.argv[1:]) or VARIANTS)
    for heat in {(c.heat.cycle, c.heat.hx_scale, c.heat.source) for c in todo.values()}:   # build maps once, not per worker
        greenhouse.build_map(HeatSupply("hp", heat[2], cycle=heat[0], hx_scale=heat[1]))
    with ProcessPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(run, todo.items()))
    out = HERE / "results" / "crops_sim.json"
    old = {r["case"]: r for r in json.loads(out.read_text())} if out.exists() and sys.argv[1:] else {}
    old.update({r["case"]: r for r in res})
    out.write_text(json.dumps(list(old.values()), indent=1, default=float))
    print(f"{'case':<24}{'heat':>7}{'elec':>7}{'comp':>7}{'aux':>6}{'SCOP':>6}{'unmet':>6}{'h>30':>6}{'yield':>7}")
    for r in res:
        y = r.get("crop_yield_t_ha", float("nan"))
        print(f"{r['case']:<24}{r['heat_kWh_m2']:>7.0f}{r['electricity_kWh_m2']:>7.1f}{r['comp_kWh_m2']:>7.1f}"
              f"{r['aux_kWh_m2']:>6.1f}{r['scop_unit']:>6.2f}{r['hours_unmet']:>6}{r['hours_above_30']:>6}{y:>7.2f}")
