"""Record KPIs + hourly totals from the original sim/annual_sim.py so lca/greenhouse.py can be checked against them."""
import json
import sys
import time
from pathlib import Path

import numpy as np

SIM = Path(__file__).resolve().parents[2] / "sim"
sys.path.insert(0, str(SIM))
import annual_sim  # noqa: E402

out = {}
for key in sys.argv[1:] or ["air", "ground", "water"]:
    t = time.time()
    pm = annual_sim.build_map(key)
    sc, wx, gr, acc, H, bufN = annual_sim.simulate(key, pm)
    out[key] = {"seconds": time.time() - t,
                "sums": {k: float(np.sum(v)) for k, v in H.items()},
                "T_air_in_first": H["T_air_in"][:48].tolist()}
    print(key, f"{out[key]['seconds']:.0f}s", "Q_c MWh", out[key]["sums"]["Q_c"] / 1e3, flush=True)
dst = Path(__file__).with_name("reference_original.json")
old = json.loads(dst.read_text()) if dst.exists() else {}
old.update(out)
dst.write_text(json.dumps(old, indent=1))
