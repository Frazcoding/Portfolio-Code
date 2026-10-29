"""R6/R7 options (layered soil, Vanthoor vent law, LAI-driven transpiration, LAI-driven floor light share) in the fast
sim against the reference sim, month by month, on the Gate B tomato case at Caledonian Paper. Run from lca/:
    python tests/test_r6_options.py
"""
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import gl_validate  # noqa: E402
import greenhouse  # noqa: E402
import greenhouse_fast  # noqa: E402

TOL = 1e-4
KEYS = ["Q_pipe", "Q_cover", "Q_vent", "Q_floor", "Q_sol", "LE", "trans_kg", "cond_kg", "T_air_in", "T_floor", "RH_in", "VPD",
        "Q_below"]

site, s, d, a, cfg, S = gl_validate._case()
e = cfg.envelope
assert e.soil_layers and e.vent_area_frac > 0 and e.transp_hourly is not None and e.floor_frac_hourly is not None
t = time.time()
Hf, *_ = greenhouse_fast.simulate_fast(cfg, i_floor=a["I_floor"], waste_kw=None)
t_fast = time.time() - t
t = time.time()
Hr, *_ = greenhouse.simulate(cfg, i_floor=a["I_floor"], waste_kw=None)
print(f"fast {t_fast:.1f} s, reference {time.time() - t:.0f} s")
month = np.minimum(np.arange(8760) // 730, 11)
bad = 0
for k in KEYS:
    f, r = np.asarray(Hf[k])[:8760], np.asarray(Hr[k])[:8760]
    mf, mr = np.bincount(month, f, minlength=12), np.bincount(month, r, minlength=12)
    err = np.abs(mf - mr) / np.maximum(np.abs(mr), 1e-3 * max(np.abs(mr).max(), 1e-9))
    flag = err.max() > TOL
    bad += flag
    print(f"{k:10s} max monthly relative difference {err.max():.2e} {'FAIL' if flag else 'ok'}")
print("PASS" if not bad else f"FAIL ({bad} series)")
sys.exit(1 if bad else 0)
