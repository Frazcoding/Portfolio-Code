"""Step 3: yield, energy and CO2 for setpoint, lighting, CO2 and planting options. Writes results/step3_summary.json."""
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import climate  # noqa: E402
import config  # noqa: E402
import crop  # noqa: E402
import greenhouse  # noqa: E402
from config import CO2, Crop, Lighting, with_  # noqa: E402


def cases():
    base = config.commercial(1.0, "ground", climate=climate.crop_led())
    co2 = CO2(enrich=True)
    led = Lighting(ppfd=150.0)
    return {
        "1ha thesis 18C": with_(base, climate=climate.thesis()),
        "1ha crop-led": base,
        "1ha crop-led +CO2": with_(base, co2=co2),
        "1ha crop-led +CO2 +LED150": with_(base, co2=co2, lighting=led),
        "1ha crop-led +CO2 +LED150 container": with_(base, co2=co2, lighting=led, crop=Crop(planting="container")),
        "rooftop 2000m2 London +CO2 +LED150": with_(config.rooftop(50, 40, "london", 8.0, "air", climate=climate.crop_led()),
                                                    co2=co2, lighting=led),
    }


def run(item):
    name, cfg = item
    t = time.time()
    H, acc, wx, gr, meta, _ = greenhouse.simulate(cfg)
    s = greenhouse.summary(H, gr, meta)
    c = crop.from_greenhouse(H, meta, cfg).annual
    s.update({f"crop_{k}": v for k, v in c.items()})
    s["kWh_heat_per_kg"] = s["heat_kWh_m2"] / max(c["yield_kg_m2"], 1e-9)
    s["kWh_elec_per_kg"] = s["electricity_kWh_m2"] / max(c["yield_kg_m2"], 1e-9)
    s["case"], s["seconds"] = name, round(time.time() - t)
    return s


if __name__ == "__main__":
    with ProcessPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(run, cases().items()))
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "step3_summary.json").write_text(json.dumps(res, indent=1, default=float))
    cols = [("crop_yield_t_ha", "t/ha", 1), ("crop_flowering_factor", "flower", 2), ("crop_mean_ppm_day", "ppm day", 0),
            ("crop_co2_dosed_kg_m2", "CO2 kg/m2", 1), ("heat_kWh_m2", "heat/m2", 0), ("electricity_kWh_m2", "elec/m2", 0),
            ("led_kWh_m2", "LED/m2", 0), ("kWh_heat_per_kg", "heat/kg", 1), ("kWh_elec_per_kg", "elec/kg", 1),
            ("hours_above_30", "h>30", 0), ("crop_hours_chill", "h chill", 0)]
    print(f"{'case':<38}" + "".join(f"{c[1]:>10}" for c in cols))
    for r in res:
        print(f"{r['case']:<38}" + "".join(f"{r[k]:>10.{d}f}" for k, _, d in cols))
