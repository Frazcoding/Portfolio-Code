"""R5: GreenLight (Katzin 2021 / Vanthoor 2011, tomato) cross-check of our heat model on the Gate B design.

Case: Caledonian Paper (Irvine), tomato (GreenLight's crop model is tomato only), refined Gate B design
(results/site_opt/refined_tomato.json), 2023 ERA5 weather at the site (the same file our model uses). The waste heat
is irrelevant here: both models are asked for the heat the greenhouse needs (GreenLight: boiler to pipe rail; ours:
heat delivered to the pipes with a heat pump only).

Matched inputs (ours -> GreenLight):
  geometry      floor, glazed cover area, mean height (volume / floor), roof pitch; screen at gutter height
  cover         double AR glass U 2.9 W/m2K (ours, Hemming et al. 2011) -> one lumped 8 mm layer with conductivity
                0.008 / (1/2.9 - 1/6.2) W/mK (6.2 = ASABE EP406.4 single glass; the convection terms stay GreenLight's);
                light: our design's annual floor light / outdoor global = tau_eff; frame shading -> etaGlobAir,
                glass -> tauRfPar = tauRfNir = tau_eff / (1 - shade)
  setpoints     tomato calendar (crops.CLIMATES): heat 19 day / 17 night, crop change 8 C from doy 340; vent at
                heat + 4 (day) / + 3 (night); RH limit 85 %; screen closes at night below 15 C outdoors, never by day (day threshold -15 C: a
                -100 C threshold overflowed GreenLight's smooth controller and blew the model up silently)
  infiltration  0.75 ACH at the site's mean wind (ASABE EP406.4 new glass) -> cLeakage
  heating       pipe rail 2.25 m/m2 of 51 mm; boiler capacity 1.5 x our design heat loss (never limiting)
  lamps         none (lamp clock disabled so day setpoints follow daylight only)
  CO2           GreenLight default 1,000 ppm by day, capacity scaled per m2 (affects yield, not heat)
Solver: max_step 300 s (default 3600 s blew up at the sunset screen closure on day 67; Katzin's runs use
5-minute weather, which keeps steps short).
Not matched (model structure): GreenLight's own ventilation physics (roof vent area 11.7 % of floor as Katzin 2021),
its cover convection, its crop transpiration; that is what the cross-check tests.
Acceptance (user, 2026-10-02): annual heat within +-15 %, same monthly shape, yield within the CBS range.

Usage:
  python gl_validate.py prep [days]      -> results/greenlight/caledonian_tomato_{weather.csv,mods.json}
  <greenlight venv python> gl_run.py     -> results/greenlight/caledonian_tomato_out.csv
  python gl_validate.py compare          -> results/greenlight/caledonian_tomato_compare.json + table
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
OUT = HERE / "results" / "greenlight"
import os
# R10 (2026-10-03): any refined tomato design can be checked: GLV_CASE (case name), GLV_TRACK (A|B: which results dir),
# GLV_SITE (substring of the site name). Defaults reproduce the R5/R7 Caledonian Gate B case. Heat-recovery dehumidification
# is switched off on our side for the comparison (GreenLight has no such unit).
CASE = os.environ.get("GLV_CASE", "caledonian_tomato")
GLV_SITE = os.environ.get("GLV_SITE", "Caledonian")
U_SINGLE = 6.2
DMC_TOMATO = 0.06           # fruit dry-matter content used by Katzin (2021) to convert harvest to fresh weight
CO2_OUT_PPM = 420.0


def _case():
    import site_opt
    SL = {s["site_key"]: s for s in json.loads((HERE / "data" / "siting" / "shortlist.json").read_text())}
    R = json.loads((site_opt.OUT / "refined_tomato.json").read_text())
    s = [x for x in R["sites"] if GLV_SITE in x["name"]][0]
    site = SL[s["site"]]
    d, a, cfg, low, avail, waste_kw = site_opt.site_setup(site, s["best"]["x"], "tomato", {"hrd": False})
    return site, s, d, a, cfg, site_opt.site_state(site)


def satvp(t):
    return 610.78 * np.exp(17.2694 * t / (t + 238.3))


def prep(days=365.0, ctx=None, case=None):
    """ctx = (d, a, cfg, wx, pitch_deg) prepares any design/location (e.g. the Westland reference house); None = Caledonian."""
    import crops
    global CASE
    OUT.mkdir(parents=True, exist_ok=True)
    if ctx is None:
        site, s, d, a, cfg, S = _case()
        wx = S["wx"].iloc[:8760]
        pitch = float(s["best"]["x"]["pitch"])
    else:
        d, a, cfg, wx, pitch = ctx
        wx = wx.iloc[:8760]
        CASE = case
        s = {"best": {"x": {"pitch": pitch}}}
    n = len(wx)
    t = np.arange(n) * 3600.0
    ghi = wx["ghi"].to_numpy()
    day_sum = pd.Series(ghi).groupby(np.arange(n) // 24).transform("sum").to_numpy() * 3600e-6
    is_day = (ghi > 20).astype(float)
    W = pd.DataFrame({"Time": t, "tOut": wx["T_amb"].to_numpy(),
                      "vpOut": wx["RH"].to_numpy() / 100 * satvp(wx["T_amb"].to_numpy()),
                      "co2Out": np.full(n, CO2_OUT_PPM / 0.554), "wind": wx["wind10"].to_numpy(),
                      "tSky": wx["T_sky"].to_numpy(), "tSoOut": wx["T_soil_2m"].to_numpy(), "iGlob": ghi,
                      "dayRadSum": day_sum, "isDay": is_day, "isDaySmooth": is_day, "hElevation": np.full(n, 10.0)})
    units = ["s", "°C", "Pa", "mg m**-3", "m s**-1", "°C", "°C", "W m**-2", "MJ m**-2", "-", "-", "m above sea level"]
    with open(OUT / f"{CASE}_weather.csv", "w", encoding="utf-8", newline="") as f:
        f.write(",".join(W.columns) + "\n")
        f.write(",".join(["Time since start of data"] + ["ERA5 (Open-Meteo) Caledonian Paper 2023"] * 11) + "\n")
        f.write(",".join(units) + "\n")
        W.to_csv(f, header=False, index=False)

    I = a["I_floor"][:n]
    tau_eff = float(I.sum() / ghi.sum())
    shade = float(a["shade"])
    h_gh = a["volume"] / d.floor
    wind_mean = float(wx["wind10"].mean())
    per = crops.CLIMATES["tomato"].periods
    main, change = per[0], per[1]
    c0 = change.start_doy - 1                                   # GreenLight dayOfYear is 0-based from t = 0 (1 Jan)
    r_extra = 1 / cfg.envelope.u_cover - 1 / U_SINGLE
    lam_eq = 0.008 / r_extra if r_extra > 1e-6 else 1.05      # single glass: plain glass conductivity (1.05 W/mK)
    p = {
        "aFlr": d.floor, "aCov": a["a_roof_glazed"] + a["a_wall_glazed"], "hGh": h_gh, "hAir": d.gutter_h - 0.2,
        "psi": pitch,
        "aRoof": 0.117 * d.floor, "hVent": 1.3,
        "cLeakage": cfg.envelope.infiltration_ach * h_gh / 3600.0 / wind_mean,
        "hRf": 0.008, "lambdaRf": lam_eq, "rhoRf": 2600, "cPRf": 840,
        "tauRfPar": tau_eff / (1 - shade), "tauRfNir": tau_eff / (1 - shade), "etaGlobAir": shade,
        "lPipe": cfg.hydronics.pipe_m_per_m2, "pBoil": 1.5 * cfg.design_heat_loss_w(),
        "phiExtCo2": 20.56e4 / 4e4 * d.floor,
        "thetaLampMax": 0, "thetaIntLampMax": 0, "aLamp": 0, "lampTimeOn": 0, "lampTimeOff": 0,
        "dayLampStart": -1, "dayLampStop": -0.5,
        "tSpDay": f"ifElse(dayOfYear >= {c0}, {change.heat_day}, {main.heat_day})",
        "tSpNight": f"ifElse(dayOfYear >= {c0}, {change.heat_night}, {main.heat_night})",
        "heatDeadZone": f"isDayInside * {main.vent_day - main.heat_day} + (1 - isDayInside) * "
                        f"{main.vent_night - main.heat_night}",
        "rhMax": cfg.hum.rh_set, "thScrSpDay": -15,   # never by day here (2023 min -4.5 C); -100 overflowed exp()
        "thScrSpNight": cfg.envelope.screen_below_C,
    }
    mods = {"Gate B Caledonian tomato (gl_validate.py)": {
        k: {"definition": str(v), "unit": "", "type": "const" if not isinstance(v, str) else "aux",
            "description": "set by gl_validate.py"} for k, v in p.items()}}
    mods = [str((OUT / f"{CASE}_weather.csv").resolve()), mods, {"options": {"t_end": str(days * 86400), "max_step": "300"}}]
    (OUT / f"{CASE}_mods.json").write_text(json.dumps(mods, indent=1))
    info = dict(tau_eff=tau_eff, shade=shade, lambda_eq=lam_eq, h_gh=h_gh, wind_mean=wind_mean, params=p,
                floor_m2=d.floor, design_kW=cfg.design_heat_loss_w() / 1e3, days=days)
    (OUT / f"{CASE}_prep.json").write_text(json.dumps(info, indent=1, default=float))
    print(json.dumps({k: v for k, v in info.items() if k != "params"}, indent=1, default=float))


def ours():
    import greenhouse
    import greenhouse_fast
    site, s, d, a, cfg, S = _case()
    H, acc, wx, gr, meta, _ = greenhouse_fast.simulate_fast(cfg, i_floor=a["I_floor"], waste_kw=None)
    q = H["Q_pipe"][:8760] / d.floor                            # kW per m2 floor, hourly
    return q, H, s, d


def compare():
    info = json.loads((OUT / f"{CASE}_prep.json").read_text())
    gl = pd.read_csv(OUT / f"{CASE}_out.csv", skiprows=[1, 2], low_memory=False)
    gl = gl.apply(pd.to_numeric, errors="coerce")
    n = len(gl)
    q_gl = (gl["hBoilPipe"] + gl.get("hBoilGroPipe", 0)).to_numpy() / 1e3          # kW/m2
    q_us, H, s, d = ours()
    q_us = q_us[:n]
    month = np.minimum(np.arange(n) // 730, 11)
    m_gl = np.bincount(month, q_gl, minlength=12)
    m_us = np.bincount(month, q_us, minlength=12)
    har = gl["mcFruitHar"].to_numpy() * 3600 * 1e-6 / DMC_TOMATO                     # kg fresh / m2 per hour
    days = n / 24
    res = dict(days=days, heat_gl_kWh_m2=float(q_gl.sum()), heat_ours_kWh_m2=float(q_us.sum()),
               ratio=float(q_us.sum() / max(q_gl.sum(), 1e-9)), monthly_gl=m_gl.tolist(), monthly_ours=m_us.tolist(),
               monthly_corr=float(np.corrcoef(m_gl[m_gl + m_us > 0], m_us[m_gl + m_us > 0])[0, 1]),
               yield_gl_kg_m2=float(har.sum()), yield_ours_kg_m2=float(s["best"]["Y"]),
               tAir_gl_mean=float(gl["tAir"].mean()), tAir_ours_mean=float(H["T_air_in"][:n].mean()),
               rh_gl_mean=float(gl["rhIn"].mean()) if "rhIn" in gl else None,
               rh_ours_mean=float(H["RH_in"][:n].mean()))
    res["pass_heat"] = bool(abs(res["ratio"] - 1) <= 0.15)
    (OUT / f"{CASE}_compare.json").write_text(json.dumps(res, indent=1))
    print(f"{days:.0f} days: heat GreenLight {res['heat_gl_kWh_m2']:.1f} vs ours {res['heat_ours_kWh_m2']:.1f} kWh/m2 "
          f"(ours/GL {res['ratio']:.2f}, pass +-15 %: {res['pass_heat']}); monthly r {res['monthly_corr']:.2f}")
    print("month  GL   ours")
    for i in range(12):
        if m_gl[i] + m_us[i] > 0:
            print(f"{i + 1:>5} {m_gl[i]:5.1f} {m_us[i]:5.1f}")
    print(f"yield: GreenLight {res['yield_gl_kg_m2']:.1f} kg/m2 (fresh, {DMC_TOMATO:.0%} DM) vs ours "
          f"{res['yield_ours_kg_m2']:.1f}; T_air {res['tAir_gl_mean']:.1f} vs {res['tAir_ours_mean']:.1f} C")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "prep"
    if cmd == "prep":
        prep(float(sys.argv[2]) if len(sys.argv) > 2 else 365.0)
    else:
        compare()
