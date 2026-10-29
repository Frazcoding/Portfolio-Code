"""Checks for BP19: residual itemisation, fixed-share capex, boiler + store LP, second-hand case, permanent store.
Run from lca/: python tests/test_bp19.py"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent))
import bplan_residual  # noqa: E402
import costing  # noqa: E402
import simstore  # noqa: E402

fails = []


def check(name, ok, val=""):
    print(("OK  " if ok else "FAIL"), name, val)
    if not ok:
        fails.append(name)


inp = json.loads((HERE / "results" / "bplan" / "xlsx_inputs.json").read_text())
R = bplan_residual.ResidualItems(inp["resid_gbp_m2"])
check("residual lines sum to the calibrated residual", abs(sum(r["gbp_m2_central"] for r in R.rows) - inp["resid_gbp_m2"]) < 1e-6)
check("fixed share in (0, 0.5)", 0 < R.fixed_share < 0.5, f"{R.fixed_share:.3f}")
check("every residual line has a tier and a life", all(r["tier"] and float(r["life_yr"]) > 0 for r in R.rows))

fx = R.fixed_share
lin = inp["resid_gbp_m2"] * 1e4
mix = lambda floor, f: inp["resid_gbp_m2"] * ((1 - f) * floor + f * costing.REFERENCE_FLOOR_M2)  # noqa: E731
check("fixed share leaves the 1 ha residual unchanged", abs(mix(1e4, fx) - lin) < 1e-6)
check("fixed share lowers the residual per m2 at 10 ha", mix(1e5, fx) / 1e5 < inp["resid_gbp_m2"])

bs = json.loads((HERE / "results" / "bplan" / "boiler_store.json").read_text())
for k, v in bs.items():
    r = v["standby"]
    check(f"{k} standby: heat pump + boiler >= design load", r["hp_kW_th"] + r["boiler_kW_th"] >= r["design_kW"] * 0.999,
          f"{r['hp_kW_th'] + r['boiler_kW_th']:.0f} vs {r['design_kW']:.0f}")
    check(f"{k} standby: LP rule is never dearer than standby", v["lp"]["gbp_kg"] <= r["gbp_kg"] + 1e-6)
    check(f"{k}: store sized (LP, not zero)", r["store_kWh"] > 0)

sh = json.loads((HERE / "results" / "bplan" / "secondhand.json").read_text())["cases"]
check("second-hand cost rises with re-erection cost", sh["low"]["total_gbp_m2"] < sh["central"]["total_gbp_m2"] < sh["high"]["total_gbp_m2"])

a1, a2 = simstore.key("evaluate", {"x": 1, "p": np.arange(3)}), simstore.key("evaluate", {"x": 1, "p": np.arange(3)})
check("store key is stable", a1 == a2)
check("store key changes with an array input", a1 != simstore.key("evaluate", {"x": 1, "p": np.arange(3) + 1}))
check("store key changes with the model code kind", simstore.key("evaluate", 1) != simstore.key("lp", 1))
print("FAIL: " + ", ".join(fails) if fails else "PASS")
sys.exit(1 if fails else 0)
