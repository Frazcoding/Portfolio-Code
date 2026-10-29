"""Run GreenLight for gl_validate.py (use the GreenLight venv: ~/.venvs/greenlight/Scripts/python gl_run.py [case]).

Model: katzin_2021 main_katzin_2021.json (Vanthoor 2011 greenhouse + tomato, Katzin 2021 extension), with the
weather and parameter modifications written by `python gl_validate.py prep` (or gl_chunks.py).

Auto-restart: on this design scipy's BDF solver sometimes fails at abrupt control switches (screen, heating and vents
switching together at dusk): "Required step size is less than spacing between numbers". The failure depends on the
starting state (the same day runs when started a day earlier), so no solver setting cures it reliably. When a segment
fails, the run restarts from the full model state RESTART_BACK hours before the failure (every state's value taken
from the solution) and continues. A silent blow-up (air temperature outside -50..80 C; GreenLight clips
overflows and replaces NaNs, so the solver does not always fail) is treated the same way; the restart points are logged in <case>_restarts.json.
"""
import json
import os
import sys
import time
from pathlib import Path

import pandas as pd

import greenlight

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "greenlight"
RESTART_BACK = 2 * 3600
MAX_RESTARTS = 40
case = sys.argv[1] if len(sys.argv) > 1 else "caledonian_tomato"
model = os.path.join(os.path.dirname(greenlight.__file__), "models", "katzin_2021", "definition", "main_katzin_2021.json")
mods = json.loads((OUT / f"{case}_mods.json").read_text())
opts = dict(mods[-1]["options"])
t_end = float(opts["t_end"])
t_start = float(opts.get("t_start", 0))
t = time.time()
segs, restarts, extra = [], [], {}
while True:
    m = mods[:-1] + ([{"restart states": extra}] if extra else []) + [{"options": {**opts, "t_start": str(t_start)}}]
    mdl = greenlight.GreenLight(base_path=str(OUT), input_prompt=[model, m], output_path=f"{case}_seg.csv")
    mdl.load()
    mdl.solve()
    mdl.save()
    sol = mdl.full_sol.apply(pd.to_numeric, errors="coerce")
    bad = sol[(sol["tAir"] < -50) | (sol["tAir"] > 80) | sol["tAir"].isna()]   # silent blow-up (GreenLight clips
    if len(bad):                                                                 # overflows and zeroes NaNs)
        sol = sol[sol["Time"] < float(bad["Time"].iloc[0])]
    t_last = float(bad["Time"].iloc[0]) if len(bad) else (float(sol["Time"].iloc[-1]) if len(sol) else t_start)
    if t_last >= t_end - 3600 or len(restarts) >= MAX_RESTARTS:
        segs.append(sol)
        break
    t_back = max(t_start + 3600, t_last - RESTART_BACK)
    keep = sol[sol["Time"] <= t_back]
    if keep.empty:                                    # failed within the first hours: step back from the start
        raise RuntimeError(f"segment from t={t_start} failed at {t_last} before any usable output")
    segs.append(keep)
    row = keep.iloc[-1]
    extra = {k: {"type": "state", "definition": str(mdl.states[k]), "init": repr(float(row[k])), "unit": "",
                 "description": "restart"} for k in mdl.states if k in row.index}
    restarts.append(dict(failed_at_day=t_last / 86400, restart_day=float(row["Time"]) / 86400))
    print(f"restart {len(restarts)}: failed at day {t_last / 86400:.2f}, restarting from {row['Time'] / 86400:.2f}",
          flush=True)
    t_start = float(row["Time"])
full = pd.concat(segs, ignore_index=True).drop_duplicates("Time", keep="last").sort_values("Time")
hdr = pd.read_csv(OUT / f"{case}_seg.csv", nrows=2, header=0)
pd.concat([hdr, full.astype(object)], ignore_index=True).to_csv(OUT / f"{case}_out.csv", index=False,
                                                                 encoding="utf-8-sig")
(OUT / f"{case}_restarts.json").write_text(json.dumps(restarts, indent=1))
print(f"GreenLight {case}: {time.time() - t:.0f} s, {len(restarts)} restarts, simulated to day "
      f"{full['Time'].iloc[-1] / 86400:.1f}", flush=True)
