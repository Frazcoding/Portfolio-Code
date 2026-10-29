"""Step 3c: in-ground beds, venting at 24 C, CO2 on: LED intensity x semi-closed cooling. Follows the break-even
screen (§3.10), which found LED electricity the largest avoidable term. Writes results/step3c_summary.json."""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import climate  # noqa: E402
import config  # noqa: E402
from config import CO2, Cooling, Lighting, with_  # noqa: E402
from run_step3 import run  # noqa: E402


def cases():
    out = {}
    for ppfd in (0.0, 75.0, 150.0):
        base = with_(config.commercial(1.0, "ground", climate=climate.crop_led()),
                     co2=CO2(enrich=True), lighting=Lighting(ppfd=ppfd))
        out[f"beds LED{ppfd:.0f}"] = base
        out[f"beds LED{ppfd:.0f} + semi-closed"] = with_(base, cooling=Cooling(enabled=True))
    return out


if __name__ == "__main__":
    with ProcessPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(run, cases().items()))
    (HERE / "results" / "step3c_summary.json").write_text(json.dumps(res, indent=1, default=float))
    cols = [("crop_yield_t_ha", "t/ha", 2), ("crop_co2_dosed_kg_m2", "CO2 kg/m2", 1), ("heat_kWh_m2", "heat/m2", 0),
            ("cool_kWh_m2", "cool/m2", 0), ("electricity_kWh_m2", "elec/m2", 0), ("hours_above_30", "h>30", 0),
            ("kWh_elec_per_kg", "elec/kg", 0)]
    print(f"{'case':<30}" + "".join(f"{c[1]:>10}" for c in cols))
    for r in res:
        print(f"{r['case']:<30}" + "".join(f"{r[k]:>10.{d}f}" for k, _, d in cols))
