"""greenhouse_fast.simulate_fast() against the reference greenhouse.simulate(), month by month.

Cases: the three thesis configurations (air, ground, river) and a Perthshire commercial case with the newer options
(crop-led climate, 7 m gutter, north wall, edge insulation). Every hourly series in H is compared as monthly sums;
the test fails if any month of any series differs by more than TOL (relative, with an absolute floor), so a change
that only shows in winter or only in summer cannot hide inside an annual total. Run from lca/:
    python tests/test_fast.py
"""
import sys
import time
import types
from dataclasses import replace
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.modules.setdefault("searoute", types.ModuleType("searoute"))
import config  # noqa: E402
import greenhouse  # noqa: E402
import greenhouse_fast  # noqa: E402

# Tolerances per kind of series. The two versions differ only in floating-point rounding (~1e-9); the on/off heat-pump
# controller amplifies that into start events shifting by a 10-min step, so discrete/control series drift while the
# energy does not. Physics flows must agree tightly, heat-pump energy within 0.5 % in every month, control series are
# reported only.
TOL_PHYS = 1e-4
TOL_HP = 5e-3
PHYS = {"Q_pipe", "Q_cover", "Q_vent", "Q_floor", "Q_sol", "LE", "trans_kg", "cond_kg", "T_air_in", "T_air_mean",
        "T_floor", "T_set", "RH_in", "VPD", "W_led", "PAR_nat", "PAR_led", "Q_below"}
HP = {"Q_c", "Q_e", "W_comp", "W_total", "Q_def", "W_aux", "vent", "ach", "T_pipe", "Q_waste"}   # W_aux: pumps follow the on/off control
TOL = {**{k: TOL_PHYS for k in PHYS}, **{k: TOL_HP for k in HP}}


def perth_case():
    import run_perthshire as rp
    cfg = rp.cases()["tomato|ctrlair_pc"]
    return replace(cfg, geometry=replace(cfg.geometry, gutter_height=7.0),
                   envelope=replace(cfg.envelope, u_cover=1.9, tau_solar=0.8356, infiltration_ach=0.75,
                                    u_north_wall=0.25),
                   location=replace(cfg.location, edge_insul_depth_m=1.0, edge_insul_R=2.94, edge_insul_d_m=0.1))


def compare(name, cfg, i_floor=None, **kw):
    t = time.time()
    H0, acc0, *_ = greenhouse.simulate(cfg, i_floor=i_floor, **kw)
    t_ref = time.time() - t
    t = time.time()
    H1, acc1, *_ = greenhouse_fast.simulate_fast(cfg, i_floor=i_floor, **kw)
    t_fast = time.time() - t
    month = np.minimum(np.arange(len(H0["Q_c"])) // 730, 11)
    ok = True
    worst = {"phys": (0.0, ""), "hp": (0.0, ""), "control": (0.0, "")}
    for k in H0:
        a, b = np.bincount(month, H0[k]), np.bincount(month, H1[k])
        grp = "phys" if k in PHYS else "hp" if k in HP else "control"
        # heat-pump energy: error relative to the month, but at least to the average month, so one start shifting
        # in a near-idle summer month (e.g. 16 kWh of 331) does not fail while a real seasonal divergence would
        scale = np.maximum(np.abs(a), max(np.abs(a).mean(), 1e-3) if grp == "hp" else 1e-3)
        rel = np.abs(a - b) / scale
        j = int(rel.argmax())
        if rel[j] > worst[grp][0]:
            worst[grp] = (float(rel[j]), f"{k} m{j + 1}")
        if k in TOL and rel[j] > TOL[k]:
            ok = False
    print(f"{name:<14} ref {t_ref:6.1f}s  fast {t_fast:5.1f}s  worst monthly: "
          + "  ".join(f"{g} {v:.1e} ({w})" for g, (v, w) in worst.items()) + f"  {'OK' if ok else 'FAIL'}", flush=True)
    return ok


if __name__ == "__main__":
    greenhouse_fast.simulate_fast(config.thesis("air"))   # compile once (cached to disk afterwards)
    hum = perth_case()
    hum = replace(hum, envelope=replace(hum.envelope, cover_t_from_u=True), hum=config.HumidityControl(enabled=True))
    hrd = replace(hum, hrd=config.HeatRecoveryDehum(enabled=True))
    cases = {f"thesis_{s}": config.thesis(s) for s in ("air", "ground", "water")} | {
        "perth_new": perth_case(), "perth_humidity": hum, "perth_hum_hrd": hrd}
    results = [compare(k, v) for k, v in cases.items()]
    # a free-form design (sawtooth, east-west, insulated north faces) with its own light series
    import design
    from simcore import weather
    d = design.Design(length=100, n_spans=10, span_w=10.0, profile=[(0, 0), (0.8, 3.5), (1, 0)], ridge_bearing=90,
                      opaque_north=True)
    wx = weather.load("perth_carse")
    a = design.analyse(d, wx, 56.42, -3.20)
    results.append(compare("design_sawtooth", design.to_config(d, a, hum), i_floor=a["I_floor"]))
    # waste heat: direct 80 C source of 300 kW with a 4-week summer stop; and an effluent-like water source
    import numpy as np
    wk = np.full(8760, 300.0)
    wk[24 * 190:24 * 218] = 0.0
    results.append(compare("waste_direct", hum, waste_kw=wk))
    water = replace(config.thesis("water"), name="effluent_source")
    t_eff = 12.3 + 4.0 * np.sin(2 * np.pi * (np.arange(8760) / 8760 - 0.30))
    results.append(compare("waste_effluent", water, t_source=t_eff))
    print("PASS" if all(results) else "FAIL")
