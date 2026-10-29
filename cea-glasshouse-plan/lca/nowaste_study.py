"""R10: two tracks side by side (user, 2026-10-03): A = waste heat (Gate B designs), B = no waste heat.

Designs: the top three refined finalists per crop (results/site_opt/refined_<crop>.json, optimised WITH waste heat; a
track-B sweep comes later). Track B uses the control package of the first lever pass without the night setpoint drop
(user dropped it: crop_gh has no development-rate effect): humidity set 90 % RH + heat-recovery dehumidification.

  fast  every design x track x electricity route (energy_grid.ELEC_OPTIONS) at the Green Book 3.5 % and a commercial
        8 % real discount rate; heat pump at full standby (central rule). ~1 min.
  lp    finalist_lp on track B with the same controls: 'standby' vs 'lp' (LP sizes the heat pump and the hot-water
        store), to put a number on the half-size heat pump. 12 LPs, 6 workers, ~5-10 min on the 32 GB desktop.

Writes results/nowaste/study_fast.json, results/nowaste/study_lp.json; `python nowaste_study.py report` prints both.
"""
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import breakeven  # noqa: E402
import energy_grid  # noqa: E402
import site_opt  # noqa: E402

OUT = HERE / "results" / "nowaste"
CROPS = ("cucumber", "tomato")
TOP = 3
CTRL = {"hum_rh": 90.0, "hrd": True}
TRACKS = {"A_waste": {}, "B_nowaste": dict(CTRL, no_waste=True)}
RATES = (0.035, 0.08)
IMPORT = {"cucumber": (1.574, 0.81), "tomato": (1.77, 1.30)}       # GBP/kg, kg CO2e/kg delivered to the Scottish RDCs
HEAT_GBP_MWH = 10.0


def finalists():
    SL = {s["site_key"]: s for s in json.loads((HERE / "data" / "siting" / "shortlist.json").read_text())}
    for crop in CROPS:
        for e in json.loads((site_opt.OUT / f"refined_{crop}.json").read_text())["sites"][:TOP]:
            yield crop, SL[e["site"]], e["best"]


def set_rate(r):
    breakeven.RATE = r                                   # wind / battery annuities (offgrid.annuity)
    site_opt.optimise._state()["D"]["rate"] = r          # structure, heat pump, pipe annuities


def fast():
    rows = []
    for crop, site, b in finalists():
        for track, o in TRACKS.items():
            for elec in energy_grid.ELEC_OPTIONS:
                for rate in RATES:
                    set_rate(rate)
                    r = site_opt.evaluate(site, b["x"], crop, dict(o, elec=elec))
                    gbp = r["gbp_kg_ex_heat"] + HEAT_GBP_MWH * r["heat_MWh_per_kg"]
                    rows.append(dict(crop=crop, site=site["site_key"], name=site["name"], track=track, elec=elec,
                                     rate=rate, gbp_kg=gbp, kg_kg=r["kg_kg"], heat_kWh_m2=r["heat_kWh_m2"],
                                     elec_kWh_m2=r["elec_kWh_m2"], elec_price=r["elec_price"], elec_ci=r["elec_ci"],
                                     self_share=r["self_share"], wind_kW=r["wind_kW"], batt_kWh=r["batt_kWh"],
                                     area_ha=r["area_ha"], Y=r["Y"], unmet_h=r["unmet_h"], turbine=r["turbine"]))
    set_rate(0.035)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "study_fast.json").write_text(json.dumps(rows, indent=1, default=float))
    return rows


def _lp_job(args):
    import finalist_lp
    crop, site, b, rule = args
    o = TRACKS["B_nowaste"]
    row = site_opt.evaluate(site, b["x"], crop, o)            # track-B sweep row: the LP result is a delta on this
    _, price, finalist_lp.CI = energy_grid.inputs()
    r = finalist_lp.run(site, b["x"], crop, row, price, rule, None, o)
    return crop, site["site_key"], site["name"], rule, r


def lp(workers=6):
    jobs = [(c, s, b, rule) for c, s, b in finalists() for rule in ("standby", "lp")]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        out = list(ex.map(_lp_job, jobs))
    res = [dict(r, crop=c, site=k, name=n) for c, k, n, rule, r in out]
    (OUT / "study_lp.json").write_text(json.dumps(res, indent=1, default=float))
    return res


def report():
    F = json.loads((OUT / "study_fast.json").read_text())
    print("FAST: GBP/kg (kg CO2e/kg) by electricity route; heat pump at full standby. Imports: cucumber 1.57 (0.81), "
          "tomato 1.77 (1.30)")
    elecs = list(energy_grid.ELEC_OPTIONS)
    for rate in RATES:
        print(f"\n-- discount {rate:.1%}")
        print(f"{'crop':9}{'site':22}{'track':10}" + "".join(f"{e:>15}" for e in elecs))
        keys = sorted({(r["crop"], r["name"], r["track"]) for r in F}, key=lambda k: (k[0], k[2], k[1]))
        for c, n, t in keys:
            cell = {r["elec"]: r for r in F if (r["crop"], r["name"], r["track"], r["rate"]) == (c, n, t, rate)}
            print(f"{c:9}{n[:21]:22}{t:10}" + "".join(
                f"{cell[e]['gbp_kg']:>8.2f} ({cell[e]['kg_kg']:.2f})" for e in elecs))
    print("\nOwned 2.5 MW turbine as its own business (3.5 %; value of power = greenhouse's avoided grid price + export "
          "at the PPA price):")
    for r in F:
        if r["elec"] == "own_2p5MW" and r["rate"] == 0.035 and r["track"] == "B_nowaste":
            t = r["turbine"]
            print(f"  {r['crop']:9}{r['name'][:21]:22} CF {t['cf']:.0%}  LCOE {t['lcoe_gbp_mwh']:.0f}/MWh  used "
                  f"{t['used_MWh']:.0f} MWh  export {t['export_MWh']:.0f} MWh  payback {t['payback_yr_at_avoided']:.1f} yr  "
                  f"NPV {t['npv_at_avoided_gbp'] / 1e6:+.2f} M  (export-only NPV {t['export_only_npv_gbp'] / 1e6:+.2f} M)")
    p = OUT / "study_lp.json"
    if p.exists():
        L = json.loads(p.read_text())
        print("\nLP, track B (3.5 %): full standby vs LP-sized heat pump + hot-water store")
        for r in L:
            print(f"  {r['crop']:9}{r['name'][:21]:22}{r['rule']:8} GBP/kg {r['gbp_kg']:.3f} (sweep {r['sweep_gbp_kg']:.3f})  "
                  f"kg {r['kg_kg']:.2f}  HP {r['hp_kW_th'] / 1e3:.2f} MWth of design {r['design_kW'] / 1e3:.2f}  store "
                  f"{r['store_kWh'] / 1e3:.1f} MWh  wind {r['wind_kW']:.0f} kW  batt {r['batt_kWh']:.0f} kWh")


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    t = time.time()
    if what in ("fast", "all"):
        fast()
        print(f"fast done {time.time() - t:.0f} s", flush=True)
    if what in ("lp", "all"):
        lp()
        print(f"lp done {time.time() - t:.0f} s", flush=True)
    report()
