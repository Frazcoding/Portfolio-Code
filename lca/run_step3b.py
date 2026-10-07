"""Step 3b: summer venting setpoint x semi-closed cooling (heat to the borehole field). Writes results/step3b_summary.json."""
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
    for sv in (24.0, 26.0, 28.0):
        base = with_(config.commercial(1.0, "ground", climate=climate.crop_led(summer_vent=sv)),
                     co2=CO2(enrich=True), lighting=Lighting(ppfd=150.0))
        out[f"vent {sv:.0f}C"] = base
        out[f"vent {sv:.0f}C + semi-closed"] = with_(base, cooling=Cooling(enabled=True))
    return out


if __name__ == "__main__":
    with ProcessPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(run, cases().items()))
    (HERE / "results" / "step3b_summary.json").write_text(json.dumps(res, indent=1, default=float))
    cols = [("crop_yield_t_ha", "t/ha", 2), ("crop_mean_ppm_day", "ppm day", 0), ("crop_co2_dosed_kg_m2", "CO2 kg/m2", 1),
            ("heat_kWh_m2", "heat/m2", 0), ("cool_kWh_m2", "cool/m2", 0), ("electricity_kWh_m2", "elec/m2", 0),
            ("scop_unit", "HP SCOP", 2), ("min_T_ground", "Tg min", 1), ("max_T_ground", "Tg max", 1),
            ("hours_above_30", "h>30", 0), ("hours_rh_above_90", "h RH>90", 0), ("kWh_elec_per_kg", "elec/kg", 0)]
    print(f"{'case':<26}" + "".join(f"{c[1]:>10}" for c in cols))
    for r in res:
        print(f"{r['case']:<26}" + "".join(f"{r[k]:>10.{d}f}" for k, _, d in cols))
