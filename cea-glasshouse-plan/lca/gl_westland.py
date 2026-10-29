"""R8: GreenLight tomato on the Westland (NL) reference house, for the RELATIVE yield check.

GreenLight is not calibrated to CBS (Caledonian tomato: 62 kg/m2 vs CBS 48 for NL), so its absolute yield is not comparable with our
CBS-anchored model; the Scotland / Westland ratio is. Same set-up as gl_year.py (ISO soil, mature soil seed, planted 1 Jan).
Usage: python gl_westland.py prep ; <greenlight python> gl_run.py westland_tomato ; python gl_westland.py compare
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
OUT = HERE / "results" / "greenlight"
CASE = "westland_tomato"


def prep():
    import crop_gh
    import gl_validate
    from gl_variant import SOIL_DEFS, h_soil_out, soil_at
    ref, a, wx = crop_gh.reference_house()
    H, meta, cfg, doy = crop_gh.climate_run(ref, a, wx, "westland", 52.0, 4.2, "tomato")
    pitch = float(np.degrees(np.arctan(0.81 / (0.25 * 8.0))))
    gl_validate.prep(365.0, ctx=(ref, a, cfg, wx, pitch), case=CASE)
    mods = json.loads((OUT / f"{CASE}_mods.json").read_text())
    mp = mods[1]
    key = next(iter(mp))
    u_b = cfg.u_floor_below()
    mp[key]["hSoOut"] = {"definition": str(h_soil_out(u_b)), "unit": "", "type": "const", "description": "iso soil"}
    states = {k: {"type": "state", "definition": SOIL_DEFS[k], "init": str(v), "unit": "", "description": "mature soil"}
              for k, v in soil_at(0).items()}
    mods = [mods[0], mp, {"soil states": states}, {"options": {"t_start": "0", "t_end": str(365 * 86400), "max_step": "300"}}]
    (OUT / f"{CASE}_mods.json").write_text(json.dumps(mods, indent=1))
    print("prepared", CASE, "floor", ref.floor, "U_b", round(u_b, 4), "pitch", round(pitch, 1))


def gl_yield(case):
    d = pd.read_csv(OUT / f"{case}_out.csv", skiprows=[1, 2], low_memory=False).apply(pd.to_numeric, errors="coerce")
    t = d["Time"].to_numpy()
    har = d["mcFruitHar"].to_numpy() * 3600e-6 / 0.06
    return float(np.nansum(har * np.gradient(t) / 3600)), float(np.nansum(d["hBoilPipe"].to_numpy() * np.gradient(t) / 3600 / 1e3)), d


def compare():
    import config
    import crop_gh
    import gl_validate
    import greenhouse_fast
    yw, hw, _ = gl_yield(CASE)
    yc, hc, _ = gl_yield("caledonian_tomato_iso_year")
    site, s, d, a, cfg, S = gl_validate._case()
    H, acc, wx, gr, meta, _ = greenhouse_fast.simulate_fast(cfg, i_floor=a["I_floor"], waste_kw=None)
    doy = S["wx"]["time"].dt.dayofyear.to_numpy()[:8760]
    cal = crop_gh.load_cal()["tomato"]
    y_c, _ = crop_gh.run(H, meta, cfg.__class__(**{**cfg.__dict__, "co2": config.CO2(enrich=True)}), "tomato", doy, cal["partition"])
    print(f"GreenLight: Westland {yw:.1f} kg/m2, Caledonian {yc:.1f} -> Caledonian/Westland {yc / yw:.2f}  (heat {hw:.0f} / {hc:.0f} kWh/m2)")
    print(f"Ours (CBS-anchored): Westland {cal['ref_yield_kg_m2']:.1f}, Caledonian {y_c:.1f} -> ratio {y_c / cal['ref_yield_kg_m2']:.2f}")
    print(f"GreenLight Westland / CBS = {yw / cal['ref_yield_kg_m2']:.2f} (GreenLight is uncalibrated)")


if __name__ == "__main__":
    prep() if (sys.argv[1:] or ["prep"])[0] == "prep" else compare()
