"""Step 2 check runs: setpoint strategy, scale and rooftop effects on heat and electricity demand.

Writes results/step2_summary.json and prints a table. Cases run in parallel processes.
"""
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import climate  # noqa: E402
import config  # noqa: E402
import greenhouse  # noqa: E402


def cases():
    th = config.with_(config.thesis("air"), legacy_aux_vent=False)
    return {
        "400m2 air thesis-climate": config.with_(th, name="400m2 air thesis-climate"),
        "400m2 air crop-led": config.with_(th, name="400m2 air crop-led", climate=climate.crop_led()),
        "400m2 air crop-led ISO floor": config.with_(th, name="400m2 air crop-led ISO floor", climate=climate.crop_led(),
                                                     location=config.Location("chelmsford")),
        "1ha ground crop-led": config.commercial(1.0, "ground", climate=climate.crop_led()),
        "4ha ground crop-led": config.commercial(4.0, "ground", climate=climate.crop_led()),
        "rooftop 50x40 London air crop-led": config.rooftop(50, 40, "london", 8.0, "air", climate=climate.crop_led()),
    }


def run(item):
    name, cfg = item
    t = time.time()
    H, acc, wx, gr, meta, _ = greenhouse.simulate(cfg)
    out = greenhouse.summary(H, gr, meta)
    out["case"], out["seconds"] = name, round(time.time() - t)
    return out


if __name__ == "__main__":
    with ProcessPoolExecutor(max_workers=5) as ex:
        res = list(ex.map(run, cases().items()))
    dst = HERE / "results"
    dst.mkdir(exist_ok=True)
    (dst / "step2_summary.json").write_text(json.dumps(res, indent=1, default=float))
    cols = [("area_m2", "m2", 0), ("u_floor", "U floor", 2), ("hp_scale", "HP x", 2), ("heat_kWh_m2", "heat kWh/m2", 0), ("electricity_kWh_m2", "elec kWh/m2", 0),
            ("scop_system", "SCOP sys", 2), ("peak_heat_kW", "peak kW", 0), ("mean_T_in", "T mean", 1),
            ("hours_unmet", "h unmet", 0), ("below_kWh_m2", "below kWh/m2", 0), ("hours_above_30", "h >30C", 0), ("seconds", "s", 0)]
    print(f"{'case':<36}" + "".join(f"{c[1]:>12}" for c in cols))
    for r in res:
        print(f"{r['case']:<36}" + "".join(f"{r[k]:>12.{d}f}" for k, _, d in cols))
