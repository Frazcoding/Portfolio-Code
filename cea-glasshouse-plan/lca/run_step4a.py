"""Step 4a: system optimisation, one change at a time (tomato setpoints, 1 ha, Chelmsford, ground source, unlit).
Writes results/step4a_summary.json. See SCOPE §3.13."""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import config  # noqa: E402
import crops  # noqa: E402
from config import HeatSupply  # noqa: E402
from run_crops import run  # noqa: E402

PRICE_MEAN = 0.165 + 0.0080  # GBP/kWh, DESNZ non-domestic mean incl. CCL (breakeven.P["elec_price"])


def cases(crop="tomato"):
    clim = crops.CLIMATES[crop]
    base = replace(config.commercial(1.0, "ground", climate=clim), heat=HeatSupply("hp", "ground"))
    hy = base.hydronics
    low_t = replace(base, hydronics=replace(hy, buf_min_C=25.0, hp_margin_K=3.0, sup_base_C=24.0, sup_curve_K_per_K=0.5))
    pump = replace(low_t, hydronics=replace(low_t.hydronics, aux_pump_w_m2=1.0, pump_vsd=True))
    store = replace(pump, heat=replace(pump.heat, field_ua_w_K=14000.0, field_leak_w_K=2250.0, field_cap_J_K=7.0e10),
                    cooling=replace(pump.cooling, enabled=True))
    pipes = replace(store, hydronics=replace(store.hydronics, pipe_m_per_m2=4.5))
    hx = replace(pipes, heat=replace(pipes.heat, hx_scale=2.0))
    opt = config.optimised(base)
    return {
        "1 baseline (thesis control)": base,
        "2 + low-temperature supply": low_t,
        "3 + variable-speed pump": pump,
        "4 + seasonal store, semi-closed": store,
        "5 + grow pipes (2x emitter)": pipes,
        "6 + 2x evaporator/condenser = optimised": hx,
        "7 optimised + price-led buffer": config.optimised(base, shift=True),
        "8 optimised, single-stage NH3": config.optimised(base, cycle="single_stage"),
        "9 optimised, glass cover": config.cover(opt, "glass"),
        "10 baseline, glass cover": config.cover(base, "glass"),
    }


if __name__ == "__main__":
    crop = sys.argv[1] if len(sys.argv) > 1 else "tomato"
    with ProcessPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(run, cases(crop).items()))
    for r in res:
        r["price_eff"] = PRICE_MEAN * r["price_shape_factor"]
    (HERE / "results" / f"step4a_{crop}.json").write_text(json.dumps(res, indent=1, default=float))
    cols = [("heat_kWh_m2", "heat", 0), ("comp_kWh_m2", "comp", 1), ("aux_kWh_m2", "aux", 1),
            ("cool_elec_kWh_m2", "cool", 1), ("electricity_kWh_m2", "elec", 1), ("scop_unit", "SCOP", 2),
            ("tsup_mean_heating", "Tsup", 1), ("tsrc_mean_on", "Tsrc", 1), ("min_T_ground", "Tg min", 1),
            ("max_T_ground", "Tg max", 1), ("hours_unmet", "unmet", 0), ("hours_above_30", "h>30", 0),
            ("price_eff", "£/kWh", 3)]
    print(f"{'case':<36}" + "".join(f"{c[1]:>8}" for c in cols))
    for r in res:
        print(f"{r['case']:<36}" + "".join(f"{r[k]:>8.{d}f}" for k, _, d in cols))
