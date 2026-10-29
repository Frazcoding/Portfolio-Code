"""Speed-up for gl_validate.py: run the rest of the year as parallel GreenLight chunks on the idle cores.

Each chunk starts SPIN days before the part it reports, with the calendar state (time_state) set to its start day
and the crop states (cLeaf, cStem, cFruit, cBuf, tCanSum, tCan24) taken from a mature crop (day 66 of the first,
continuous run, which failed there). Greenhouse thermal states settle within the spin-up. Heat from the chunks is a
provisional full-year answer; the continuous run (gl_run.py) remains the reference and the only valid yield.
Each run uses gl_run.py's auto-restart.
Usage: python gl_chunks.py launch | merge
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "greenlight"
CASE = "caledonian_tomato"
GL_PY = Path.home() / ".venvs" / "greenlight" / "Scripts" / "python.exe"
CHUNKS = [(0, 91), (91, 182), (182, 273), (273, 365)]
SPIN = 6
CROP_STATES = ("cLeaf", "cStem", "cFruit", "cBuf", "tCanSum", "tCan24")
DEFS = {"cBuf": "mcAirBuf - mcBufFruit - mcBufLeaf - mcBufStem - mcBufAir",
        "cFruit": "mcBufFruit - mcFruitAir - mcFruitHar", "cLeaf": "mcBufLeaf - mcLeafAir - mcLeafHar",
        "cStem": "mcBufStem - mcStemAir", "tCanSum": "1 / 86400 * tCan", "tCan24": "(1 / 86400) * (tCan - tCan24)",
        "time_state": "1/86400"}     # copied from the katzin_2021 / vanthoor_2011 definitions


def crop_state(day=66.0):
    src = OUT / f"{CASE}_day66_state.json"
    if src.exists():
        return json.loads(src.read_text())
    d = pd.read_csv(OUT / f"{CASE}_out.csv", skiprows=[1, 2], low_memory=False).apply(pd.to_numeric, errors="coerce")
    row = d.iloc[(d["Time"] - day * 86400).abs().idxmin()]
    st = {k: float(row[k]) for k in CROP_STATES}
    src.write_text(json.dumps(st, indent=1))
    return st


def launch():
    base = json.loads((OUT / f"{CASE}_mods.json").read_text())
    st = crop_state()
    procs = []
    for a, b in CHUNKS:
        if a == 0:                                     # first quarter: GreenLight's own young crop from 1 Jan
            mods = [base[0], base[1], {"options": {"t_start": "0", "t_end": str(b * 86400), "max_step": "300"}}]
        else:
            t0 = (a - SPIN) * 86400
            states = {k: {"type": "state", "definition": DEFS[k], "init": str(v), "unit": "",
                          "description": "chunk init"} for k, v in st.items()}
            states["time_state"] = {"type": "state", "definition": DEFS["time_state"], "init": str(a - SPIN),
                                    "unit": "day", "description": "chunk init"}
            mods = [base[0], base[1], {"chunk initial states": states},
                    {"options": {"t_start": str(t0), "t_end": str(b * 86400), "max_step": "300"}}]
        case = f"{CASE}_chunk{a}"
        (OUT / f"{case}_mods.json").write_text(json.dumps(mods, indent=1))
        log = open(OUT / f"{case}_run.log", "w")
        procs.append(subprocess.Popen([str(GL_PY), str(HERE / "gl_run.py"), case], stdout=log, stderr=subprocess.STDOUT,
                                      env={**__import__("os").environ, "PYTHONUNBUFFERED": "1"}))
        print(f"launched {case}: days {max(a - SPIN, 0)}-{b} (reports {a}-{b})", flush=True)
    for p in procs:
        p.wait()
    print("chunks done", flush=True)


def merge():
    """Heat per hour (kW/m2) for the whole year from the four quarter chunks."""
    q = np.full(8760, np.nan)
    for a, b in CHUNKS:
        d = pd.read_csv(OUT / f"{CASE}_chunk{a}_out.csv", skiprows=[1, 2], low_memory=False).apply(pd.to_numeric,
                                                                                                   errors="coerce")
        h = (d["Time"] // 3600).astype(int).to_numpy()
        keep = (h >= a * 24) & (h < min(b * 24, 8760))
        q[h[keep]] = d["hBoilPipe"].to_numpy()[keep] / 1e3
    sys.path.insert(0, str(HERE))
    import gl_validate
    q_us, H, s, dd = gl_validate.ours()
    month = np.minimum(np.arange(8760) // 730, 11)
    m_gl = np.array([np.nansum(q[month == i]) for i in range(12)])
    m_us = np.bincount(month, q_us, minlength=12)
    missing = int(np.isnan(q).sum())
    res = dict(heat_gl_kWh_m2=float(np.nansum(q)), heat_ours_kWh_m2=float(q_us.sum()), missing_hours=missing,
               monthly_gl=m_gl.tolist(), monthly_ours=m_us.tolist(),
               ratio=float(q_us.sum() / np.nansum(q)), monthly_corr=float(np.corrcoef(m_gl, m_us)[0, 1]))
    res["pass_heat"] = bool(abs(res["ratio"] - 1) <= 0.15)
    (OUT / f"{CASE}_chunks_compare.json").write_text(json.dumps(res, indent=1))
    print(f"PROVISIONAL (chunks): heat GreenLight {res['heat_gl_kWh_m2']:.1f} vs ours {res['heat_ours_kWh_m2']:.1f} "
          f"kWh/m2, ours/GL {res['ratio']:.2f}, pass +-15 %: {res['pass_heat']}, monthly r {res['monthly_corr']:.2f}, "
          f"missing hours {missing}")
    for i in range(12):
        print(f"  month {i + 1:>2}: GL {m_gl[i]:5.1f}  ours {m_us[i]:5.1f}")


if __name__ == "__main__":
    launch() if (sys.argv[1:] or ["launch"])[0] == "launch" else merge()
