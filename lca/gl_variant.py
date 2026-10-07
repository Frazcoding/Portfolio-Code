"""R6: GreenLight variant runs that remove confounders from the R5 heat comparison (same chunking as gl_chunks.py).

R5 found GreenLight uses 2x our heat. Two things in the R5 GreenLight runs are not the greenhouse's controls:
  1. GreenLight's soil is 1.24 m of layers plus a 1.28 m external layer to the 2 m soil temperature, i.e. a 1-D
     conduction path (U ~ 0.37 W/m2K) that drains ~49 kWh/m2/yr from the floor; our floor uses the ISO 13370
     long-run slab value (U = 0.057 W/m2K for this 8.5 ha slab). Under a large greenhouse the deep ground warms over
     years, so the long-run value is the right one for a 25-year asset.
  2. Quarters 2-4 start with GreenLight's default 10 C soil, which the floor then has to warm.
Variants (case name suffix):
  iso    deep soil resistance set to the ISO 13370 U of our design (hSoOut), soil layers seeded with the R5 run's
         own soil temperatures at the chunk start (mature soil)
Usage: <greenlight venv python> gl_variant.py launch iso   |   python gl_variant.py compare iso
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "greenlight"
BASE = "caledonian_tomato"
GL_PY = Path.home() / ".venvs" / "greenlight" / "Scripts" / "python.exe"
CHUNKS = [(0, 91), (91, 182), (182, 273), (273, 365)]
SPIN = 6
LAMBDA_SO = 0.85
SOIL_DEFS = {"tSo1": "1 / capSo1 * (hFlrSo1 - hSo1So2)", "tSo2": "1 / capSo2 * (hSo1So2 - hSo2So3)",
             "tSo3": "1 / capSo3 * (hSo2So3 - hSo3So4)", "tSo4": "1 / capSo4 * (hSo3So4 - hSo4So5)",
             "tSo5": "1 / capSo5 * (hSo4So5 - hSo5SoOut)"}
HSO5 = 0.64


def soil_at(day):
    """Soil layer temperatures of the R5 chunk run at a day of the year (the chunk that covers it); the year start
    takes the end of December."""
    day = 364.0 if day <= 0 else day
    for a, b in CHUNKS:
        if a <= day < b or (day >= 364 and a == 273):
            d = pd.read_csv(OUT / f"{BASE}_chunk{a}_out.csv", skiprows=[1, 2], low_memory=False).apply(pd.to_numeric,
                                                                                                       errors="coerce")
            row = d.iloc[(d["Time"] - day * 86400).abs().idxmin()]
            return {k: float(row[k]) for k in SOIL_DEFS}


def h_soil_out(u_iso):
    """External soil layer thickness (m) that makes the whole soil column conduct u_iso (W/m2K) in steady state:
    R = (0.02/1.7) + (sum of layers 1-4 + hSo5/2)/lam + (hSo5 + hSoOut)/(2 lam)."""
    layers = 0.04 + 0.08 + 0.16 + 0.32
    r_target = 1 / u_iso
    r_fixed = 0.02 / 1.7 + (layers + 0.5 * HSO5) / LAMBDA_SO
    return 2 * LAMBDA_SO * (r_target - r_fixed) - HSO5


def launch(variant):
    assert variant == "iso"
    prep = json.loads((OUT / f"{BASE}_prep.json").read_text())
    u_iso = float(prep.get("u_floor_iso", 0.0572))
    hso = h_soil_out(u_iso)
    print(f"ISO U {u_iso:.4f} W/m2K -> hSoOut {hso:.1f} m", flush=True)
    base = json.loads((OUT / f"{BASE}_mods.json").read_text())
    st = json.loads((OUT / f"{BASE}_day66_state.json").read_text())
    sys.path.insert(0, str(HERE))
    from gl_chunks import DEFS
    procs = []
    for a, b in CHUNKS:
        t0 = max(a - SPIN, 0)
        mods_p = json.loads(json.dumps(base[1]))
        key = next(iter(mods_p))
        mods_p[key]["hSoOut"] = {"definition": str(hso), "unit": "", "type": "const", "description": "R6 iso variant"}
        states = {}
        for k, v in soil_at(t0).items():
            states[k] = {"type": "state", "definition": SOIL_DEFS[k], "init": str(v), "unit": "", "description": "mature soil"}
        if a > 0:
            for k, v in st.items():
                states[k] = {"type": "state", "definition": DEFS[k], "init": str(v), "unit": "", "description": "chunk init"}
            states["time_state"] = {"type": "state", "definition": DEFS["time_state"], "init": str(t0), "unit": "day",
                                    "description": "chunk init"}
        mods = [base[0], mods_p, {"chunk initial states": states},
                {"options": {"t_start": str(t0 * 86400), "t_end": str(b * 86400), "max_step": "300"}}]
        case = f"{BASE}_{variant}_chunk{a}"
        (OUT / f"{case}_mods.json").write_text(json.dumps(mods, indent=1))
        log = open(OUT / f"{case}_run.log", "w")
        procs.append(subprocess.Popen([str(GL_PY), str(HERE / "gl_run.py"), case], stdout=log, stderr=subprocess.STDOUT,
                                      env={**__import__("os").environ, "PYTHONUNBUFFERED": "1"}))
        print(f"launched {case}: days {t0}-{b}", flush=True)
    for p in procs:
        p.wait()
    print("chunks done", flush=True)


def load(variant):
    cols = ("hBoilPipe", "tAir", "tFlr", "rhIn", "hFlrSo1", "tSo1", "iGlob")
    G = {c: np.full(8760, np.nan) for c in cols}
    for a, b in CHUNKS:
        name = f"{BASE}_chunk{a}_out.csv" if variant == "base" else f"{BASE}_{variant}_chunk{a}_out.csv"
        d = pd.read_csv(OUT / name, skiprows=[1, 2], low_memory=False).apply(pd.to_numeric, errors="coerce")
        h = (d["Time"] // 3600).astype(int).to_numpy()
        keep = (h >= a * 24) & (h < min(b * 24, 8760))
        for c in cols:
            G[c][h[keep]] = d[c].to_numpy()[keep]
    return G


def compare(variant):
    sys.path.insert(0, str(HERE))
    import gl_validate
    q_us, H, s, dd = gl_validate.ours()
    month = np.minimum(np.arange(8760) // 730, 11)
    print(f"ours {q_us.sum():.1f} kWh/m2")
    for v in ("base", variant):
        G = load(v)
        q = G["hBoilPipe"] / 1e3
        m = np.array([np.nansum(q[month == i]) for i in range(12)])
        print(f"GreenLight {v}: {np.nansum(q):.1f} kWh/m2 (ours/GL {q_us.sum() / np.nansum(q):.2f}, "
              f"missing {int(np.isnan(q).sum())} h), floor-to-soil {np.nansum(G['hFlrSo1']) / 1e3:.1f} kWh/m2/yr, "
              f"mean tFlr {np.nanmean(G['tFlr']):.1f}")
        print("   monthly", np.round(m, 1).tolist())
    print("   ours   ", np.round(np.bincount(month, q_us, minlength=12), 1).tolist())


if __name__ == "__main__":
    cmd, var = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "iso")
    launch(var) if cmd == "launch" else compare(var)
