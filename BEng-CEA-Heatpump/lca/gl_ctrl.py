"""R6: controlled-weather comparison of our greenhouse model and GreenLight on the Caledonian tomato design.

Both models get the same constant synthetic weather for 12 days (no seasons, no diurnal cycle), so each physical block
can be compared alone: night envelope loss (screen open / closed), summer ventilation + solar, spring and dull days.
GreenLight starts from the mature crop state of the annual runs (a fresh GreenLight crop has LAI 0.1-0.3 and
transpires almost nothing, which made the first version of this comparison invalid for day cases) and uses the ISO-soil variant (hSoOut from gl_variant.h_soil_out) and soil layers seeded at 15 C.
Usage: <greenlight python> gl_ctrl.py launch   |   python gl_ctrl.py compare
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
OUT = HERE / "results" / "greenlight"
BASE = "caledonian_tomato"
GL_PY = Path.home() / ".venvs" / "greenlight" / "Scripts" / "python.exe"
DAYS = 12
# name: (T_out C, global radiation W/m2, RH %, wind m/s)
CASES = {"night_cold": (5.0, 0.0, 80.0, 3.5), "night_mild": (16.0, 0.0, 80.0, 3.5), "night_cold_calm": (5.0, 0.0, 80.0, 0.5),
         "day_summer": (20.0, 600.0, 70.0, 3.5), "day_spring": (8.0, 300.0, 80.0, 3.5), "day_dull": (6.0, 80.0, 85.0, 3.5),
         "day_hot": (28.0, 700.0, 60.0, 3.5)}
SKY_DROP = 12.0
T_SOIL = 10.0


def satvp(t):
    return 610.78 * np.exp(17.2694 * t / (t + 238.3))


def launch():
    from gl_variant import SOIL_DEFS, h_soil_out
    prep = json.loads((OUT / f"{BASE}_prep.json").read_text())
    base = json.loads((OUT / f"{BASE}_mods.json").read_text())
    hso = h_soil_out(0.0572)
    from gl_chunks import DEFS
    st = json.loads((OUT / f"{BASE}_day66_state.json").read_text())
    n = DAYS * 24
    procs = []
    for name, (to, g, rh, wd) in CASES.items():
        t = np.arange(n) * 3600.0
        day = float(g > 20)
        W = pd.DataFrame({"Time": t, "tOut": to, "vpOut": rh / 100 * satvp(to), "co2Out": 420.0 / 0.554, "wind": wd,
                          "tSky": to - SKY_DROP, "tSoOut": T_SOIL, "iGlob": g, "dayRadSum": g * 86400e-6, "isDay": day,
                          "isDaySmooth": day, "hElevation": 10.0})
        units = ["s", "°C", "Pa", "mg m**-3", "m s**-1", "°C", "°C", "W m**-2", "MJ m**-2", "-", "-", "m above sea level"]
        wpath = OUT / f"ctrl_{name}_weather.csv"
        with open(wpath, "w", encoding="utf-8", newline="") as f:
            f.write(",".join(W.columns) + "\n")
            f.write(",".join(["Time since start of data"] + ["synthetic"] * 11) + "\n")
            f.write(",".join(units) + "\n")
            W.to_csv(f, header=False, index=False)
        mp = json.loads(json.dumps(base[1]))
        key = next(iter(mp))
        mp[key]["hSoOut"] = {"definition": str(hso), "unit": "", "type": "const", "description": "iso soil"}
        states = {k: {"type": "state", "definition": SOIL_DEFS[k], "init": "15.0", "unit": "", "description": "seed"}
                  for k in SOIL_DEFS}
        for k, v in st.items():           # mature crop (LAI ~2.6), as the annual chunk runs; a young crop has LAI 0.1-0.3
            states[k] = {"type": "state", "definition": DEFS[k], "init": str(v), "unit": "", "description": "mature crop"}
        mods = [str(wpath.resolve()), mp, {"ctrl states": states},
                {"options": {"t_start": "0", "t_end": str(DAYS * 86400), "max_step": "300"}}]
        case = f"ctrl_{name}"
        (OUT / f"{case}_mods.json").write_text(json.dumps(mods, indent=1))
        log = open(OUT / f"{case}_run.log", "w")
        procs.append(subprocess.Popen([str(GL_PY), str(HERE / "gl_run.py"), case], stdout=log, stderr=subprocess.STDOUT))
        print("launched", case, flush=True)
    for p in procs:
        p.wait()
    print("ctrl done", flush=True)


def ours(name, **env_kw):
    """Our model on the same constant weather. env_kw overrides Envelope fields."""
    import copy

    import gl_validate
    import greenhouse_fast
    site, s, d, a, cfg, S = gl_validate._case()
    to, g, rh, wd = CASES[name]
    wx = S["wx"].iloc[:8760].copy()
    wx["T_amb"], wx["ghi"], wx["RH"], wx["wind10"] = to, g, rh, wd
    wx["T_sky"], wx["T_soil_2m"], wx["cloud"] = to - SKY_DROP, T_SOIL, 50.0
    pv = rh / 100 * 610.94 * np.exp(17.625 * to / (to + 243.04))
    wx["w_amb"] = 0.62198 * pv / (101325.0 - pv)       # the sim reads the outdoor humidity ratio, not RH
    for c in ("dni", "dhi", "diffuse", "direct"):
        if c in wx:
            wx[c] = 0.0
    c = copy.deepcopy(cfg)
    c.location.site = "ctrl_" + name
    for k, v in env_kw.items():
        setattr(c.envelope, k, v)
    key = ("wx", c.location.site, c.location.lat, c.location.lon)
    greenhouse_fast._MEMO[key] = (wx, (c.location.lat, c.location.lon))
    tau = float(a["I_floor"].sum() / S["wx"]["ghi"].iloc[:8760].sum())
    H, *_ = greenhouse_fast.simulate_fast(c, i_floor=np.full(8760, g * tau), waste_kw=None)
    sl = slice((DAYS - 4) * 24, DAYS * 24)
    A = d.floor
    return dict(q=float(H["Q_pipe"][sl].mean() / A * 1e3), T=float(H["T_air_in"][sl].mean()), RH=float(H["RH_in"][sl].mean()),
                ach=float(H["ach"][sl].mean()), Tfl=float(H["T_floor"][sl].mean()), vent=float(H["vent"][sl].mean()),
                LE=float(H["LE"][sl].mean() / A * 1e3), Qcov=float(H["Q_cover"][sl].mean() / A * 1e3),
                Qvent=float(H["Q_vent"][sl].mean() / A * 1e3), Qfl=float(H["Q_floor"][sl].mean() / A * 1e3))


def gl(name):
    d = pd.read_csv(OUT / f"ctrl_{name}_out.csv", skiprows=[1, 2], low_memory=False).apply(pd.to_numeric, errors="coerce")
    d = d[d["Time"] >= (DAYS - 4) * 86400]
    h_gh = json.loads((OUT / f"{BASE}_prep.json").read_text())["h_gh"]
    m = lambda c: float(d[c].mean())
    return dict(q=m("hBoilPipe"), T=m("tAir"), RH=m("rhIn"), Tfl=m("tFlr"), Tcan=m("tCan"), uThScr=m("uThScr"), uRoof=m("uRoof"),
                ach=(m("fLeakage") + m("fVentRoof") + m("fVentSide") + m("fThScr")) * 3600 / h_gh,
                hCanAir=m("hCanAir"), hPipeAir=m("hPipeAir"), hAirTop=m("hAirTop"), hAirOut=m("hAirOut"),
                hCovInCovE=m("hCovInCovE"), hFlrSo1=m("hFlrSo1"))


def compare():
    for name in CASES:
        try:
            g, o = gl(name), ours(name)
        except Exception as e:  # noqa: BLE001
            print(name, "failed:", e)
            continue
        print(f"\n== {name} {CASES[name]}")
        print("  GL  ", {k: round(v, 2) for k, v in g.items()})
        print("  ours", {k: round(v, 2) for k, v in o.items()})


if __name__ == "__main__":
    launch() if (sys.argv[1:] or ["compare"])[0] == "launch" else compare()
