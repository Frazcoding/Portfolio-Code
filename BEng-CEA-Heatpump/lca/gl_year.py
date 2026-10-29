"""R6/R8: one continuous GreenLight year (Caledonian tomato, ISO-equivalent soil, mature soil seed, planted 1 Jan by GreenLight's
own young crop) for the tomato YIELD comparison with crop_gh.py. Run once, with the GreenLight venv:
    <greenlight python> gl_year.py          (then <greenlight python> gl_run.py caledonian_tomato_iso_year; ~40 min)
Usage here: python gl_year.py prep | compare
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "greenlight"
import os
BASE = os.environ.get("GLV_CASE", "caledonian_tomato")      # R10: base case prepared by gl_validate.py prep
CASE = f"{BASE}_iso_year"


def prep():
    sys.path.insert(0, str(HERE))
    from gl_variant import SOIL_DEFS, h_soil_out, soil_at
    base = json.loads((OUT / f"{BASE}_mods.json").read_text())
    mp = json.loads(json.dumps(base[1]))
    key = next(iter(mp))
    mp[key]["hSoOut"] = {"definition": str(h_soil_out(0.0572)), "unit": "", "type": "const", "description": "iso soil"}
    states = {k: {"type": "state", "definition": SOIL_DEFS[k], "init": str(v), "unit": "", "description": "mature soil"}
              for k, v in soil_at(0).items()}
    mods = [base[0], mp, {"soil states": states}, {"options": {"t_start": "0", "t_end": str(365 * 86400), "max_step": "300"}}]
    (OUT / f"{CASE}_mods.json").write_text(json.dumps(mods, indent=1))
    print("written", CASE)


def compare():
    d = pd.read_csv(OUT / f"{CASE}_out.csv", skiprows=[1, 2], low_memory=False).apply(pd.to_numeric, errors="coerce")
    har = d["mcFruitHar"].to_numpy() * 3600 * 1e-6 / 0.06          # kg fresh / m2 per hour at 6 % dry matter (Katzin 2021)
    t = d["Time"].to_numpy()
    print("GreenLight continuous year: days", t[-1] / 86400, "restarts file:", (OUT / f"{CASE}_restarts.json").read_text()[:200])
    print("fresh yield kg/m2 (cumulative harvest):", round(float(np.nansum(har * np.gradient(t) / 3600)), 1))
    m = np.minimum((t // 86400 // 30.4).astype(int), 11)
    print("monthly yield:", [round(float(np.nansum((har * np.gradient(t) / 3600)[m == i])), 1) for i in range(12)])
    print("annual heat kWh/m2:", round(float(np.nansum(d["hBoilPipe"].to_numpy() * np.gradient(t) / 3600 / 1e3)), 1))


if __name__ == "__main__":
    prep() if (sys.argv[1:] or ["prep"])[0] == "prep" else compare()
