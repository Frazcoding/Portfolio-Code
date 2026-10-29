"""Annual (8760 h) dynamic greenhouse + two-stage R717 heat pump simulation (Chelmsford, 2023).

Extends the BEng thesis model (static heat-load + cycle) to a dynamic, controlled system:
  greenhouse  20 x 20 m Venlo, 5 m gutter, twin-wall cover U 3.0 W/m2K (thesis values), air+crop,
              floor and pipe-rail thermal nodes; humidity balance with transpiration (radiation + VPD)
              and cover condensation; night energy screen; roof-vent cooling/dehumidification;
              continuous 18 C heating setpoint (thesis), 24/22 C day/night venting setpoint
  hydronics   900 m of 51 mm pipe rail (k = 0.7 W/m/K^1.25), 1.5 m3 buffer, mixing valve on PI control
  heat pump   two-stage R717, open reciprocating LP/HP, open intercooler (CoolProp map)
  sources     air (finned coil, frost and reverse-cycle defrost), ground (16-borehole field with
              drawdown and recovery) or river (water temperature lagging air temperature)
Plus the thesis' own calibrated results (first 8760 h of 2018) as a replay scenario.
10-minute control steps; hourly outputs.
"""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT.parent))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from simcore import grid, solar, two_stage, weather  # noqa: E402
from simcore.hx import CP_A, CP_W, H_FG, psat_w, w_sat  # noqa: E402
from simcore.output import Results  # noqa: E402
from simcore.perfmap import PerfMap  # noqa: E402
from simcore.storage import StratifiedTank  # noqa: E402
from simcore.thermo import Fluid  # noqa: E402
from params import AIR, GROUND, WATER  # noqa: E402

DT, SUB = 600.0, 6
A_FLOOR, VOL = 400.0, 2350.0
A_WALL, A_ROOF = 400.0, 431.0
U_COVER = 3.0
SPEEDS = np.array([25, 32, 40, 48, 55, 60], float)
AX_AIR = {"T_air": [-15, -10, -7, -4, -2, 0, 2, 4, 7, 10, 14, 18, 25], "RH": [50, 75, 95],
          "T_w_in": [20, 25, 30, 35, 40, 45, 50, 55, 60, 65], "f": list(SPEEDS), "ua": [0.5, 0.75, 1.0]}
AX_LIQ = {"T_src_in": [-4, -2, 0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20], "T_w_in": [20, 25, 30, 35, 40, 45, 50, 55, 60, 65],
          "f": list(SPEEDS)}
SP_NAMES = {"1": "Evaporator outlet", "2": "LP suction", "3": "LP discharge", "4": "HP suction (intercooler vapour)",
            "5": "HP discharge", "6": "Condenser outlet", "7": "HP valve outlet", "8": "Intercooler vapour",
            "9": "Intercooler liquid", "10": "Evaporator inlet"}
SCENARIOS = {
    "air": dict(name="Chelmsford 2023 · dynamic greenhouse · R717 air-source", badge="Air source", params=AIR, axes=AX_AIR),
    "ground": dict(name="Chelmsford 2023 · dynamic greenhouse · R717 ground-source (16 boreholes)", badge="Ground source",
                   params=GROUND, axes=AX_LIQ),
    "water": dict(name="Chelmsford 2023 · dynamic greenhouse · R717 river-source", badge="River source", params=WATER, axes=AX_LIQ),
    "thesis": dict(name="Thesis calibrated model · 2018 (static load, three sources)", badge="Thesis 2018"),
}


def build_map(key):
    sc = SCENARIOS[key]
    pt = {k: v[len(v) // 2] for k, v in sc["axes"].items()}
    o, _ = two_stage.solve(sc["params"], pt)
    core = ROOT / "simcore" if (ROOT / "simcore").is_dir() else ROOT.parent / "simcore"
    return PerfMap(f"greenhouse_nh3_{key}", core / "two_stage.py", "solve", sc["params"], sc["axes"], list(o),
                   deps=[core / "hx.py", core / "thermo.py"])


def simulate(key, pmap):
    sc = SCENARIOS[key]
    p = sc["params"]
    air = p["source"] == "air"
    wx = weather.load("chelmsford")
    gr = grid.load()
    n = len(wx)
    lat, lon = weather.SITES["chelmsford"][:2]
    zen, az, doy = solar.position(wx["time"], lat, lon)
    Ta_all, rh_all = wx["T_amb"].to_numpy(), wx["RH"].to_numpy()
    w_out_all = wx["w_amb"].to_numpy()
    ghi = wx["ghi"].to_numpy()
    wind = wx["wind10"].to_numpy()
    sky = wx["T_sky"].to_numpy()
    cloud = wx["cloud"].to_numpy() / 100
    Tsoil2 = wx["T_soil_2m"].to_numpy()
    T7 = pd.Series(Ta_all).rolling(24 * 7, min_periods=1).mean().to_numpy()
    T_river = np.maximum(1.5, 0.85 * T7 + 2.2)
    # state
    T_a, T_f, T_p = 18.0, 15.0, 30.0
    w_a = w_sat(18.0) * 0.8
    T_g = 11.0
    Q_e_prev = 0.0
    buf = StratifiedTank(1.5, 1.8, nodes=10, U_wall=0.35, T_init=45.0)
    integ = 0.0
    on = False
    frost = 0.0
    off_t = 1e9
    K = pmap.out_keys
    acc = {k: np.zeros(n) for k in K}
    names = ["T_air_in", "RH_in", "T_floor", "T_pipe", "T_sup", "Q_pipe", "Q_cover", "Q_vent", "Q_floor", "Q_sol", "LE",
             "trans_kg", "cond_kg", "vent", "screen", "ach", "on_frac", "f_cmd", "Q_c", "W_comp", "W_aux", "W_total",
             "defrosts", "frost", "T_src", "T_ground", "unmet", "starts", "buf_soc", "VPD", "Q_def"]
    H = {k: np.zeros(n) for k in names}
    bufN = np.zeros((n, buf.N))
    m_pipe = 2.0
    L_PIPE, K_PIPE = 900.0, 0.7
    C_air = 1.2 * 1006 * VOL + 400 * 3 * 1500          # air + crop/benching
    C_floor = A_FLOOR * 0.15 * 2.0e6
    C_pipe = 9.0e6
    M_air = 1.2 * VOL
    for i in range(n):
        Ta, rh_o, w_o = Ta_all[i], rh_all[i], w_out_all[i]
        day = ghi[i] > 20
        screen = (not day) and Ta < 15.0
        U_roof = U_COVER * (0.55 if screen else 1.0) + 0.06 * wind[i]
        UA_cov = U_COVER * A_WALL + U_roof * A_ROOF
        T_vent_set = 24.0 if day else 22.0
        I_in = 0.70 * ghi[i]
        for s in range(SUB):
            # ---- climate control
            err = 18.0 - T_a
            integ = float(np.clip(integ + err * DT / 3600 * 6.0, -10, 60))
            T_sup_req = float(np.clip(32.0 + 9.0 * err + integ, 22.0, 72.0)) if (T_a < 19.5 or err > -1.0) else 22.0
            # ---- greenhouse climate: 30 s sub-steps (venting makes the air node time constant ~100 s)
            T_top = buf.T[0]
            heating = T_sup_req > 25
            T_sup = min(T_sup_req, T_top) if heating else T_p
            NC, dtc = 20, DT / 20
            agg = dict(Q_pipe=0.0, Q_cover=0.0, Q_vent=0.0, Q_floor=0.0, Q_sol=0.0, LE=0.0, E=0.0, cond=0.0, Q_in=0.0,
                       vent=0.0, ach=0.0)
            for _c in range(NC):
                pv_a = w_a * 101325 / (0.62198 + w_a)
                rh_in = min(100.0, 100 * pv_a / psat_w(T_a))
                vent = float(np.clip((T_a - T_vent_set) / 4.0, 0, 1))
                vent = max(vent, float(np.clip((rh_in - 85.0) / 10.0, 0, 1)) * 0.12)
                ach = (0.5 + 0.05 * wind[i]) * (0.7 if screen else 1.0) + vent * (6.0 + 3.0 * wind[i])
                m_ex = ach * VOL * 1.2 / 3600
                Q_pipe = K_PIPE * L_PIPE * max(T_p - T_a, 0.0) ** 1.25
                Q_in = m_pipe * CP_W * max(T_sup - T_p, 0.0) * (1 - math.exp(-1.0)) if heating else 0.0
                vpd = max(0.0, psat_w(T_a) - pv_a) / 1000
                LE = (0.30 * I_in * 0.7 + 14.0 * vpd) * A_FLOOR
                E = LE / H_FG
                T_cov = Ta + 0.35 * (T_a - Ta) - (1 - cloud[i]) * 1.5
                cond = max(0.0, 0.0028 * (A_WALL + A_ROOF) * (w_a - w_sat(T_cov)))
                Q_cover = UA_cov * (T_a - Ta) + 0.15 * A_ROOF * (T_a - sky[i]) * (0.4 if screen else 1.0)
                Q_vent = m_ex * CP_A * (T_a - Ta)
                Q_floor = 6.0 * A_FLOOR * (T_f - T_a)
                Q_sol_air = 0.7 * I_in * A_FLOOR
                # implicit treatment of the large linear loss terms keeps the update stable
                G = UA_cov + 0.15 * A_ROOF * (0.4 if screen else 1.0) + m_ex * CP_A + 6.0 * A_FLOOR
                src = Q_pipe + Q_sol_air - LE + 6.0 * A_FLOOR * T_f + 0.5 * cond * H_FG + (UA_cov + m_ex * CP_A) * Ta \
                    + 0.15 * A_ROOF * (0.4 if screen else 1.0) * sky[i]
                T_a = (T_a * C_air / dtc + src) / (C_air / dtc + G)
                T_f = (T_f * C_floor / dtc + 0.3 * I_in * A_FLOOR + 6.0 * A_FLOOR * T_a + 1.2 * A_FLOOR * Tsoil2[i]) \
                    / (C_floor / dtc + 7.2 * A_FLOOR)
                T_p += (Q_in - Q_pipe) * dtc / C_pipe
                w_a = (w_a * M_air / dtc + E - cond + m_ex * w_o) / (M_air / dtc + m_ex)
                w_a = float(np.clip(w_a, 0.0005, w_sat(T_a)))
                for kk, v in (("Q_pipe", Q_pipe), ("Q_cover", Q_cover), ("Q_vent", Q_vent), ("Q_floor", -Q_floor),
                              ("Q_sol", Q_sol_air), ("LE", LE), ("E", E), ("cond", cond), ("Q_in", Q_in), ("vent", vent), ("ach", ach)):
                    agg[kk] += v / NC
            Q_pipe, Q_cover, Q_vent, Q_floor, Q_sol_air, LE = (agg[k] for k in ("Q_pipe", "Q_cover", "Q_vent", "Q_floor", "Q_sol", "LE"))
            E, cond, Q_in_pipe, vent, ach = agg["E"], agg["cond"], agg["Q_in"], agg["vent"], agg["ach"]
            Q_floor = -Q_floor
            T_ret = T_p - 2.0
            m_draw = Q_in_pipe / (CP_W * max(T_top - T_ret, 1.0)) if Q_in_pipe > 0 else 0.0
            # ---- heat pump
            if air:
                T_src = Ta
            elif p is GROUND:
                T_src = T_g - Q_e_prev / 7000.0          # borehole field UA 7 kW/K (16 x 120 m)
            else:
                T_src = T_river[i] - 1.5
            want = buf.T[3] < max(T_sup_req, 35.0) + 1.0 or (on and buf.T[-1] < max(T_sup_req, 35.0) + 4.0)
            if T_sup_req <= 25 and buf.T[3] > 35:
                want = False
            if not on and want and off_t >= DT:
                on = True
                H["starts"][i] += 1
            elif on and not want:
                on = False
                off_t = 0.0
            Q_c = W_c = 0.0
            Q_e = 0.0
            if on:
                T_in = buf.T[-1]
                T_target = max(T_sup_req, 35.0) + 5.0
                Q_target = m_pipe * CP_W * max(T_target - T_in, 1.0) * 0.6
                ua = max(0.5, 1 - 0.5 * min(frost / 24.0, 1.0))
                kw = dict(T_air=Ta, RH=rh_o, ua=ua) if air else dict(T_src_in=T_src)
                qs = np.array([pmap.get(pmap(T_w_in=T_in, f=fs, **kw)[0], "Q_c") * 1e3 for fs in SPEEDS])
                f_cmd = float(np.interp(Q_target, qs, SPEEDS)) if Q_target < qs[-1] else SPEEDS[-1]
                f_cmd = max(SPEEDS[0], f_cmd)
                vec, ok = pmap(T_w_in=T_in, f=f_cmd, **kw)
                Q_c = pmap.get(vec, "Q_c") * 1e3
                W_c = pmap.get(vec, "W_tot") * 1e3
                Q_e = pmap.get(vec, "Q_e") * 1e3
                frac = 1.0
                if air:
                    water = pmap.get(vec, "water")
                    if pmap.get(vec, "Te") + 1.5 < 0 and water > 0:
                        frost += water * DT
                    if frost >= 14.0:
                        E_def = frost * 338e3 + 2.0e6
                        H["defrosts"][i] += 1
                        H["Q_def"][i] += 0.75 * E_def / 3.6e6
                        buf.T -= 0.75 * E_def / (buf.M * CP_W * buf.N)
                        W_c += 0.25 * E_def / DT
                        frac = 1 - min(DT, 180 + E_def / 30e3) / DT
                        frost = 0.0
                for ki, kk in enumerate(K):
                    acc[kk][i] += vec[ki] * frac
                H["on_frac"][i] += frac / SUB
                H["f_cmd"][i] += f_cmd * frac / SUB
                Q_c *= frac
                Q_e *= frac
            else:
                off_t += DT
                if air and Ta > 2:
                    frost = max(0.0, frost - 0.003 * (Ta - 2) * DT)
            if not air and p is GROUND:
                T_g += (9000.0 * (11.0 - T_g) - Q_e) * DT / 4.7e10
            Q_e_prev = Q_e
            buf.step(DT, m_pipe if Q_c > 0 else 0.0, 0.0, m_draw, T_ret, 15.0, Q_c=Q_c if Q_c > 0 else None)
            W_aux = 150.0 + (1200.0 if Q_in_pipe > 0 else 0.0) + (900.0 * vent > 0.02) + (60.0 if screen else 0)
            for kk, v in (("Q_pipe", Q_pipe), ("Q_cover", Q_cover), ("Q_vent", Q_vent), ("Q_floor", -Q_floor), ("Q_sol", Q_sol_air),
                          ("LE", LE), ("Q_c", Q_c), ("W_comp", W_c), ("W_aux", W_aux), ("W_total", W_c + W_aux)):
                H[kk][i] += v / 1e3 / SUB
            H["trans_kg"][i] += E * DT
            H["cond_kg"][i] += cond * DT
            H["vent"][i] += vent * 100 / SUB
            H["ach"][i] += ach / SUB
            H["T_sup"][i] += T_sup / SUB
        H["T_air_in"][i], H["T_floor"][i], H["T_pipe"][i] = T_a, T_f, T_p
        H["RH_in"][i] = min(100.0, 100 * w_a * 101325 / (0.62198 + w_a) / psat_w(T_a))
        H["VPD"][i] = max(0.0, psat_w(T_a) - w_a * 101325 / (0.62198 + w_a)) / 1000
        H["screen"][i] = float(screen) * 100
        H["frost"][i] = frost
        H["T_src"][i] = Ta if air else (T_g - Q_e_prev / 7000.0 if p is GROUND else T_river[i] - 1.5)
        H["T_ground"][i] = T_g if p is GROUND else (T_river[i] if not air else Tsoil2[i])
        H["unmet"][i] = max(0.0, 17.0 - T_a)
        H["buf_soc"][i] = buf.soc(25.0, 70.0) * 100
        bufN[i] = buf.T
        if H["on_frac"][i] > 0:
            for kk in K:
                acc[kk][i] /= H["on_frac"][i] * SUB
            H["f_cmd"][i] /= H["on_frac"][i]
    return sc, wx, gr, acc, H, bufN


def export(key, pmap):
    sc, wx, gr, acc, H, bufN = simulate(key, pmap)
    p = sc["params"]
    air = p["source"] == "air"
    n = len(wx)
    R = Results(key, sc["name"], n)
    on = H["on_frac"] > 0
    of = H["on_frac"]
    F = Fluid("Ammonia")
    Ta = wx["T_amb"].to_numpy()
    for k in acc:
        if k.startswith("sp"):
            sid, fld = k[2:].split("_")
            for i in np.where(~on)[0]:
                st = F.PQ(F.Psat(max(Ta[i], H["T_src"][i]) + 273.15), 1.0)
                acc[k][i] = {"T": st.Tc, "P": st.P / 1e5, "h": st.h / 1e3, "s": st.s / 1e3, "x": np.nan, "m": 0.0, "ex": 0.0}[fld]
        elif k.startswith(("X_", "Ex_")) or k in ("Q_c", "Q_e", "W_lp", "W_hp", "W_fan", "W_tot", "m_lp", "m_hp", "m_vap", "water"):
            acc[k][~on] = 0.0
        else:
            acc[k][~on] = np.nan
    g = "Outdoor & grid"
    R.ch("T_amb", Ta, "°C", "Outdoor air temperature", g, 1)
    R.ch("RH_out", wx.RH, "%", "Outdoor relative humidity", g, 0)
    R.ch("ghi", wx.ghi, "W/m²", "Global horizontal irradiance", g, 0)
    R.ch("wind", wx.wind10, "m/s", "Wind speed", g, 1)
    R.ch("T_sky", wx.T_sky, "°C", "Effective sky temperature", g, 1)
    R.ch("price", gr.price, "p/kWh", "Agile import price", g, 2)
    R.ch("ci", gr.ci, "gCO₂/kWh", "GB grid carbon intensity", g, 0)
    for sid, nm in SP_NAMES.items():
        R.state_point(sid, nm, "R717 circuit", "Ammonia", {f: acc[f"sp{sid}_{f}"] for f in ("T", "P", "h", "s", "x", "m", "ex")})
    src_lbl = "Coil air" if air else ("Borehole brine" if p is GROUND else "River water loop")
    R.state_point("S1", f"{src_lbl} in", "Source", "Air" if air else "Water",
                  {"T": H["T_src"], "P": np.full(n, 1.0 if air else 2.5), "h": np.full(n, np.nan), "m": np.where(on, acc["m_air"] if air else p["m_src"], 0.0)})
    R.state_point("S2", f"{src_lbl} out", "Source", "Air" if air else "Water",
                  {"T": np.where(on, acc["T_air_out"], np.nan), "P": np.full(n, 1.0 if air else 2.3), "h": np.full(n, np.nan),
                   "m": np.where(on, acc["m_air"] if air else p["m_src"], 0.0)})
    R.state_point("W2", "Condenser water out", "Heating water", "Water",
                  {"T": acc["T_w_out"], "P": np.full(n, 2.5), "h": np.nan_to_num(acc["T_w_out"]) * CP_W / 1e3, "m": np.where(on, p["m_w"], 0.0)})
    g = "Refrigerant cycle"
    for k, u, lbl, d in [("Pe", "bar", "Evaporating pressure", 3), ("Pi", "bar", "Intercooler pressure", 3), ("Pc", "bar", "Condensing pressure", 3),
                         ("Te", "°C", "Evaporating temperature", 1), ("Ti", "°C", "Intercooler temperature", 1), ("Tc", "°C", "Condensing temperature", 1),
                         ("lift", "K", "Lift", 1), ("pr_lp", "–", "LP pressure ratio", 2), ("pr_hp", "–", "HP pressure ratio", 2),
                         ("f_hp", "Hz", "HP compressor speed", 1)]:
        R.ch(k, acc[k], u, lbl, g, d)
    R.ch("f_lp", np.where(on, H["f_cmd"], 0.0), "Hz", "LP compressor speed", g, 1)
    R.ch("T_dis_lp", acc["sp3_T"], "°C", "LP discharge temperature", g, 1)
    R.ch("T_dis_hp", acc["sp5_T"], "°C", "HP discharge temperature", g, 1)
    R.ch("m_lp", acc["m_lp"] * 1e3, "g/s", "LP mass flow", g, 1)
    R.ch("m_hp", acc["m_hp"] * 1e3, "g/s", "HP mass flow", g, 1)
    R.ch("Q_c", H["Q_c"], "kW", "Heat pump heat output", "Heat pump", 1)
    R.ch("Q_e", acc["Q_e"] * of, "kW", "Heat extracted from source", "Heat pump", 1)
    R.ch("W_comp", H["W_comp"], "kW", "Compressors + source fans/pumps", "Heat pump", 2)
    R.ch("cop", np.where(H["W_comp"] > 0, H["Q_c"] / np.maximum(H["W_comp"], 1e-9), np.nan), "–", "Unit COP", "Heat pump", 2)
    R.ch("eta_ex", acc["eta_ex"] * 100, "%", "Exergy efficiency", "Heat pump", 1)
    R.ch("on_frac", of * 100, "%", "Run fraction", "Heat pump", 0)
    R.ch("starts", H["starts"], "1/h", "Starts", "Heat pump", 0)
    if air:
        R.ch("frost", H["frost"], "kg", "Coil frost", "Heat pump", 2)
        R.ch("defrosts", H["defrosts"], "1/h", "Defrosts", "Heat pump", 0)
    R.ch("T_src", H["T_src"], "°C", "Source temperature to evaporator", "Source", 1)
    R.ch("src_kind", np.full(n, 0.0 if air else (1.0 if p is GROUND else 2.0)), "–", "Source (0 air, 1 ground, 2 river)", "Source", 0)
    R.ch("T_ground", H["T_ground"], "°C", "Ground / river / soil temperature", "Source", 1)
    for k, lbl in [("X_lp", "LP compressor"), ("X_hp", "HP compressor"), ("X_cond", "Condenser"), ("X_evap", "Evaporator"),
                   ("X_hpeev", "HP valve"), ("X_lpeev", "LP valve"), ("X_flash", "Intercooler"), ("Ex_prod", "Product")]:
        R.ch(k, acc[k] * of, "kW", lbl, "Exergy destruction", 2)
    g = "Greenhouse climate"
    R.ch("T_in", H["T_air_in"], "°C", "Greenhouse air temperature", g, 2)
    R.ch("RH_in", H["RH_in"], "%", "Greenhouse relative humidity", g, 1)
    R.ch("VPD", H["VPD"], "kPa", "Vapour pressure deficit", g, 2)
    R.ch("T_floor", H["T_floor"], "°C", "Floor / soil surface temperature", g, 1)
    R.ch("T_pipe", H["T_pipe"], "°C", "Pipe-rail mean temperature", g, 1)
    R.ch("T_sup", H["T_sup"], "°C", "Pipe-rail supply temperature", g, 1)
    R.ch("vent", H["vent"], "%", "Roof vent opening", g, 0)
    R.ch("screen", H["screen"], "%", "Energy screen closed", g, 0)
    R.ch("ach", H["ach"], "1/h", "Air changes per hour", g, 1)
    R.ch("unmet", H["unmet"], "K", "Deficit below 17 °C", g, 2)
    g = "Greenhouse energy"
    for k, lbl in [("Q_pipe", "Pipe-rail heat to air"), ("Q_cover", "Cover transmission + radiation loss"), ("Q_vent", "Ventilation/infiltration loss"),
                   ("Q_floor", "Floor heat storage (+ = charging)"), ("Q_sol", "Solar gain to air"), ("LE", "Crop transpiration (latent)")]:
        R.ch(k, H[k], "kW", lbl, g, 1)
    R.ch("trans_kg", H["trans_kg"], "kg/h", "Transpiration", g, 1)
    R.ch("cond_kg", H["cond_kg"], "kg/h", "Condensation on cover", g, 1)
    R.ch("buf_soc", H["buf_soc"], "%", "Buffer state of charge", "Buffer", 0)
    for j in range(bufN.shape[1]):
        R.ch(f"buf_T{j + 1}", bufN[:, j], "°C", f"Buffer node {j + 1} (top=1)", "Buffer nodes", 1)
    g = "Electrical & cost"
    R.ch("W_aux", H["W_aux"], "kW", "Pumps, vents, screen motors", g, 2)
    R.ch("W_total", H["W_total"], "kW", "Total electrical demand", g, 2)
    cost = H["W_total"] * gr.price.to_numpy() / 100
    cost_flat = H["W_total"] * 23.0 / 100
    co2 = H["W_total"] * gr.ci.to_numpy() / 1000
    R.ch("cost", cost, "£/h", "Cost (Agile)", g, 3)
    R.ch("cum_cost", np.cumsum(cost), "£", "Cumulative cost (Agile)", g, 0)
    R.ch("co2", co2, "kg/h", "Operational CO₂", g, 2)
    R.start = int(np.argmax(np.where(np.arange(n) < 24 * 50, H["Q_pipe"], -1)))
    k = R.kpi
    Qhp, Wt = H["Q_c"].sum(), H["W_total"].sum()
    k("Seasonal COP (unit)", Qhp / H["W_comp"].sum(), "–", "Performance", 2)
    k("Seasonal system COP (incl. aux)", Qhp / Wt, "–", "Performance", 2)
    k("Heat delivered", Qhp / 1000, "MWh", "Energy", 1)
    k("Pipe-rail heat to greenhouse", H["Q_pipe"].sum() / 1000, "MWh", "Energy", 1)
    k("Solar gain to air", H["Q_sol"].sum() / 1000, "MWh", "Energy", 1)
    k("Ventilation + infiltration loss", H["Q_vent"].sum() / 1000, "MWh", "Energy", 1)
    k("Electricity", Wt / 1000, "MWh", "Energy", 1)
    k("Peak electrical demand", H["W_total"].max(), "kW", "Energy", 1)
    k("Cost at Agile prices", cost.sum(), "£", "Cost & carbon", 0)
    k("Cost at £0.23/kWh (thesis)", cost_flat.sum(), "£", "Cost & carbon", 0)
    k("Operational CO₂", co2.sum() / 1000, "t", "Cost & carbon", 2)
    gas = H["Q_pipe"].sum() / 0.9
    k("Gas boiler CO₂ counterfactual", gas * grid.GAS_CARBON_G_KWH / 1e6, "t", "Cost & carbon", 1)
    k("Mean greenhouse temperature", H["T_air_in"].mean(), "°C", "Climate", 1)
    k("Hours below 17 °C", float((H["unmet"] > 0).sum()), "h", "Climate", 0)
    k("Hours above 28 °C", float((H["T_air_in"] > 28).sum()), "h", "Climate", 0)
    k("Hours RH > 90 %", float((H["RH_in"] > 90).sum()), "h", "Climate", 0)
    k("Crop transpiration", H["trans_kg"].sum() / 1000, "m³", "Climate", 1)
    k("Cover condensation", H["cond_kg"].sum() / 1000, "m³", "Climate", 1)
    k("Energy-screen hours", (H["screen"] > 50).sum(), "h", "Climate", 0)
    k("Run hours", of.sum(), "h", "Operation", 0)
    k("Starts", H["starts"].sum(), "", "Operation", 0)
    k("Max HP discharge temperature", np.nanmax(acc["sp5_T"]), "°C", "Operation", 1)
    k("Min evaporating temperature", np.nanmin(acc["Te"]), "°C", "Operation", 1)
    if air:
        k("Defrost cycles", H["defrosts"].sum(), "", "Operation", 0)
    if p is GROUND:
        k("Minimum ground temperature (drawdown)", H["T_ground"].min(), "°C", "Operation", 2)
    fl = Fluid("Ammonia")
    paths = [["10", "1", "2", "3", "9"], ["6", "7", "9", "10"], ["8", "5", "6"]]
    R.diagrams.append({"type": "ph", "title": "R717 log P–h", "fluid": "Ammonia", "dome": fl.dome(70, 223.0), "paths": paths})
    R.diagrams.append({"type": "ts", "title": "R717 T–s", "fluid": "Ammonia", "dome": fl.dome(70, 223.0), "paths": paths})
    R.diagrams.append({"type": "profile", "title": "Buffer profile", "xLabel": "°C",
                       "series": [{"label": "Buffer", "keys": [f"buf_T{j + 1}" for j in range(10)], "color": "#c2410c"}]})
    R.diagrams.append({"type": "bars", "title": "Greenhouse heat flows now (kW)", "items": [
        {"key": kk, "label": lb} for kk, lb in [("Q_pipe", "Pipes"), ("Q_sol", "Solar"), ("LE", "Transpiration"), ("Q_cover", "Cover"),
                                                ("Q_vent", "Ventilation"), ("Q_floor", "Floor")]]})
    return R, sc


def export_thesis():
    """Replay of the thesis' calibrated outputs (first 8760 h, 2018) for comparison."""
    out = ROOT / "data" / "outputs"
    load = pd.read_csv(out / "calibrated_v2_heat_load.csv").iloc[:8760]
    res = {s: pd.read_csv(out / f"calibrated_v2_results_{s}_source.csv").iloc[:8760] for s in ("air", "ground", "water")}
    n = len(load)
    R = Results("thesis", SCENARIOS["thesis"]["name"], n, t0="2018-01-01T00:00:00Z")
    g = "Boundary (thesis)"
    R.ch("T_amb", load["external_temp_C"], "°C", "External temperature", g, 1)
    R.ch("T_ground", load["ground_temp_C"], "°C", "Ground temperature", g, 1)
    R.ch("T_water", load["water_temp_C"], "°C", "Water temperature", g, 1)
    R.ch("sun", load["sunlight_W"] / 1e3, "kW", "Solar input", g, 2)
    g = "Heat load (thesis)"
    for c, lbl in [("Q_walls_W", "Wall transmission"), ("Q_ground_W", "Ground loss"), ("Q_sun_W", "Solar gain"), ("Q_heat_demand_W", "Heat demand")]:
        R.ch(c.replace("_W", ""), load[c] / 1e3, "kW", lbl, g, 1)
    for s, d in res.items():
        g = f"{s.capitalize()}-source (thesis)"
        R.ch(f"cop_{s}", d["COP"], "–", f"COP {s}", g, 2)
        R.ch(f"W_{s}", d["W_total_kW"], "kW", f"Electric {s}", g, 1)
        R.ch(f"Wlp_{s}", d["W_c1_kW"], "kW", f"LP compressor {s}", g, 1)
        R.ch(f"Whp_{s}", d["W_c2_kW"], "kW", f"HP compressor {s}", g, 1)
        R.ch(f"mlp_{s}", d["m_dot_1_kg_s"] * 1e3, "g/s", f"LP mass flow {s}", g, 1)
        R.kpi(f"Annual COP · {s}", d["Q_c_W"].sum() / 1e3 / d["W_total_kW"].sum(), "–", "Thesis 2018", 2)
        R.kpi(f"Electricity · {s}", d["W_total_kW"].sum() / 1000, "MWh", "Thesis 2018", 1)
    R.kpi("Heat demand", load["Q_heat_demand_W"].sum() / 1e6, "MWh", "Thesis 2018", 1)
    R.kpi("Peak heat demand", load["Q_heat_demand_W"].max() / 1e3, "kW", "Thesis 2018", 1)
    return R


if __name__ == "__main__":
    import time
    for key in (sys.argv[1:] or ["air", "ground", "water"]):
        t = time.time()
        pm = build_map(key)
        R, sc = export(key, pm)
        print(key, "%.0fs" % (time.time() - t), "map %.3f" % pm.coverage())
        for kp in R.kpis:
            print(f"  {kp['label']:<40} {kp['value'] if kp['value'] is not None else float('nan'):.2f} {kp['unit']}")
