"""Annual glasshouse crops (tomato, cucumber): climate-driven yield from the hourly greenhouse climate (R8, 2026-10-03).

Uses crop.py's leaf and canopy photosynthesis (Farquhar-von Caemmerer-Berry, Bernacchi et al. temperature responses,
Beer-Lambert canopy, greenhouse CO2 balance with dosing) with annual-crop parameters, the LAI schedule of transp.py, and
a carbon balance: available = net canopy assimilation - maintenance; fruit DM = partition x available / glucose cost.

What is sourced and what is calibrated (every value is in data/input_register.csv):
  sourced     maintenance Rm25 0.015 g CH2O/g DM/d x ~0.7 kg/m2 standing vegetative DM = 0.3 g CH2O/m2/h at 20 C and CH2O -> DM
              conversion 0.7 for tomato (leaf-level tomato model, PLOS ONE 17(11):e0275047); tomato fruit set limited above a
              daily mean of 25-26 C, -40 % at +2.5 K (Mediterranean protected-cultivation study; Peet & Willits): factor
              1 - 0.16/K above 25 C, floor 0.2; cucumber optimum 25-30 C: 1 - 0.10/K above 28 C (PLACEHOLDER);
              leaf kinetics and temperature responses (Bernacchi 2001/2003, Medlyn 2002, as crop.py); canopy light
              extinction; Q10 2 for maintenance; LAI schedule (transp.py); fruit dry-matter content
  calibrated  the fruit partition of net assimilate, set so the model reproduces the CBS (Dutch) glasshouse yield on the
              Westland reference house under its own climate (the same anchor the old scaling used). Absolute leaf Amax and
              the maintenance rate are therefore not separately identified: they set the SHAPE of the response (how
              strongly light, temperature, CO2 and VPD change yield), which is what moves a Scottish site off the anchor
  placeholder leaf Amax and quantum yield, maintenance rate, glucose cost: literature-range values, flagged below
Validation (`python crop_gh.py validate`): light elasticity of yield against the 0.8 of Marcelis et al. (2006); the seasonal
shape; GreenLight's tomato yield on the Caledonian case (only once GreenLight's continuous year has been run).
"""
import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import config  # noqa: E402
import crop as cropmod  # noqa: E402
import transp  # noqa: E402

CAL = HERE / "data" / "crop_gh_calibration.json"
CBS_REF = {"tomato": 48.0, "cucumber": 65.0}           # kg/m2/yr, crops.py (CBS NL), the reference-house anchor

# leaf parameters: PLACEHOLDERS in the literature range (greenhouse tomato leaf Amax ~ 20-30, cucumber ~ 25-35 umol/m2/s
# at 25 C, 400 ppm, saturating light); they set response shape, the absolute scale is calibrated through the partition
PARAMS = {
    "tomato": dict(leaf=cropmod.LeafParams(amax_ref=25.0, phi_app=0.055, vpd_slope=0.15, chill_factor=1.0),
                   carbon=cropmod.CarbonParams(gr_fruit=1 / 0.7, dm_fraction=0.06), maint20=0.30, k_ext=0.7, lai=2.6,
                   heat_stress=(25.0, 0.16, 0.2)),
    "cucumber": dict(leaf=cropmod.LeafParams(amax_ref=30.0, phi_app=0.055, vpd_slope=0.20, chill_factor=1.0),
                     carbon=cropmod.CarbonParams(gr_fruit=1 / 0.7, dm_fraction=0.04), maint20=0.30, k_ext=0.7, lai=3.0,
                     heat_stress=(28.0, 0.10, 0.2)),
}


def run(H, meta, cfg, crop, doy, partition, hours=8760):
    """Annual crop run on greenhouse output H (dict of hourly arrays). Returns (yield kg/m2, crop result)."""
    p = PARAMS[crop]
    lai_h = transp.lai_by_doy(crop, doy)[:hours]
    fi = cfg.lighting.inter_frac
    par = (np.asarray(H["PAR_nat"]) + np.asarray(H["PAR_led"]) * (1.0 - fi))[:hours]
    par_inter = np.asarray(H["PAR_led"])[:hours] * fi if fi > 0 else None
    cal = dict(maint_g_m2_h_20C=p["maint20"], partition=partition)
    crop_cfg = config.Crop(lai=p["lai"], k_ext=p["k_ext"])
    res = cropmod.simulate(np.asarray(H["T_air_mean"])[:hours], np.asarray(H["VPD"])[:hours], par,
                           ach=np.asarray(H["ach"])[:hours], volume=meta["volume_m3"], area=meta["area_m2"],
                           vent_pct=np.asarray(H["vent"])[:hours], co2cfg=cfg.co2, crop=crop_cfg, cal=cal, cp=p["carbon"],
                           lai_h=lai_h, leaf=cropmod.Leaf(p["leaf"]), annual=True, heat_stress=p["heat_stress"],
                           par_inter=par_inter)
    return res.annual["yield_kg_m2"], res


def load_cal():
    return json.loads(CAL.read_text()) if CAL.exists() else {}


def climate_run(d, a, wx, site_key, lat, lon, crop, source="air"):
    """Greenhouse climate for design d (design.analyse output a) at a location, built like site_opt.site_setup (no waste heat,
    heat pump or outage: the climate does not depend on the heat source). Returns (H, meta, cfg, doy)."""
    import greenhouse_fast
    import run_crops
    import site_opt
    base = run_crops.variant(run_crops.base_cfg(crop, source), "ctrlair_pc")
    base = replace(base, location=replace(base.location, site=site_key, lat=lat, lon=lon))
    night = max(p.heat_night for p in site_opt.crops.CLIMATES[crop].periods)
    base = replace(base, envelope=replace(base.envelope, infiltration_ach=0.75, cover_t_from_u=True,
                                          transp_rad=site_opt.TRANSP[crop][0], transp_vpd=site_opt.TRANSP[crop][1],
                                          vent_area_frac=site_opt.VENT_AREA_FRAC),
                   heat=replace(base.heat, design_outdoor_C=-3.1, design_indoor_C=night),
                   hum=config.HumidityControl(enabled=True),
                   co2=config.CO2(enrich=True))
    cfg = site_opt.D.to_config(d, a, base)
    doy = wx["time"].dt.dayofyear.to_numpy()[:8760]
    tr_r, tr_v = transp.hourly_coeffs(crop, doy)
    cfg = replace(cfg, envelope=replace(cfg.envelope, transp_hourly=(tr_r, tr_v), soil_layers=True,
                                        floor_frac_hourly=transp.floor_light_frac(transp.lai_by_doy(crop, doy))))
    H, acc, wxo, gr, meta, _ = greenhouse_fast.simulate_fast(cfg, i_floor=a["I_floor"], waste_kw=None)
    return H, meta, cfg, doy


def reference_house():
    """The Westland (NL) reference glasshouse of optimise._state(): Venlo, single plain glass, 100 m x 12 spans of 8 m."""
    import design as D
    import optimise
    from simcore import weather
    S = optimise._state()
    ref = D.Design(length=100, n_spans=12, span_w=8.0, gutter_h=6.0,
                   profile=[(0, 0), (0.25, 0.81), (0.5, 0), (0.75, 0.81), (1, 0)], glazing="single_plain")
    wx = weather.load("westland")
    a = D.analyse(ref, wx, 52.0, 4.2)
    return ref, a, wx


def calibrate(crop, verbose=True):
    """Set the fruit partition so the Westland reference house yields the CBS value. Yield is linear in the partition."""
    import time
    ref, a, wx = reference_house()
    t = time.time()
    H, meta, cfg, doy = climate_run(ref, a, wx, "westland", 52.0, 4.2, crop)
    y1, res = run(H, meta, cfg, crop, doy, partition=1.0)
    part = CBS_REF[crop] / y1
    cal = load_cal()
    cal[crop] = dict(partition=part, ref_yield_kg_m2=CBS_REF[crop], unit_partition_yield=y1,
                     net_assim_g_CH2O_m2=res.annual["net_assim_g_CH2O_m2"], maint_g_CH2O_m2=res.annual["maint_g_CH2O_m2"],
                     interception=res.annual["interception"], co2_dosed_kg_m2=res.annual["co2_dosed_kg_m2"],
                     ref_PAR_mol_m2=float(np.sum(H["PAR_nat"][:8760]) * 3600 / 1e6))
    CAL.write_text(json.dumps(cal, indent=1))
    if verbose:
        print(f"{crop}: Westland reference, yield at partition 1 = {y1:.1f} kg/m2 -> partition {part:.3f} "
              f"(net assimilation {res.annual['net_assim_g_CH2O_m2']:.0f}, maintenance {res.annual['maint_g_CH2O_m2']:.0f} g CH2O/m2, "
              f"CO2 dosed {res.annual['co2_dosed_kg_m2']:.1f} kg/m2; {time.time() - t:.0f} s)")
    return cal[crop]


def elasticity(crop, scale=0.10):
    """Yield response to a +-scale change of outdoor light on the Westland reference house (full climate + crop re-run).
    Marcelis et al. (2006): 1 % more light gives ~0.8 % more yield."""
    import design as D
    ref, a0, wx = reference_house()
    part = load_cal()[crop]["partition"]
    out = {}
    for s in (1 - scale, 1.0, 1 + scale):
        w = wx.copy()
        for c in ("ghi", "dni", "dhi"):
            if c in w:
                w[c] = w[c] * s
        a = D.analyse(ref, w, 52.0, 4.2)
        H, meta, cfg, doy = climate_run(ref, a, w, "westland", 52.0, 4.2, crop)
        out[s] = run(H, meta, cfg, crop, doy, partition=part)[0]
    e = (np.log(out[1 + scale]) - np.log(out[1 - scale])) / (np.log(1 + scale) - np.log(1 - scale))
    return out, float(e)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "calibrate"
    for c in (sys.argv[2:] or ["tomato", "cucumber"]):
        if cmd == "calibrate":
            calibrate(c)
        elif cmd == "validate":
            out, e = elasticity(c)
            print(f"{c}: yield at light x0.9/1.0/1.1 = " + " / ".join(f"{v:.1f}" for v in out.values()) +
                  f" kg/m2 -> light elasticity {e:.2f} (Marcelis et al. 2006: 0.8)")
