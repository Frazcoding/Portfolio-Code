"""Annual (8760 h) simulation of a commercial heat pump retrofit under a 60 kWe grid cap.

Plant: 4 x 40 kW R290 monobloc modules (lead/lag cascade, inverter scrolls, per-module frost and
reverse-cycle defrost), two 100 m3 stratified thermal stores in series (24 nodes), weather-
compensated radiator circuit, 1970s 6,000 m2 office in Edinburgh (ISO 13790 5R1C), real 2023
ERA5 weather, NESO carbon intensity and Agile prices. Control in 10-minute steps.

Scenarios
  tes_smart  : stores charged preferentially in cheap hours, electrical draw held under 60 kWe
  tes_basic  : same plant, thermostatic charging, cap enforced
  direct     : no thermal store (2 m3 buffer), modules follow load, 120 kW electric boiler backup,
               no cap -> shows the grid overloads the store avoids
"""
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_legacy"))  # frozen simcore v0.1.0
sys.path.insert(0, str(HERE))

from simcore import cycles, grid, solar, weather  # noqa: E402
from simcore.building import Zone5R1C  # noqa: E402
from simcore.hx import CP_W  # noqa: E402
from simcore.output import Results  # noqa: E402
from simcore.perfmap import PerfMap  # noqa: E402
from simcore.storage import StratifiedTank  # noqa: E402
from simcore.thermo import Fluid  # noqa: E402
from model.params import MODULE  # noqa: E402

AXES = {"T_air": [-15, -10, -7, -4, -2, 0, 2, 4, 7, 10, 13, 16, 20, 25, 30], "RH": [40, 70, 95],
        "T_w_in": [20, 25, 30, 35, 40, 45, 50, 55, 60, 65], "f": [25, 40, 55, 70, 90, 110], "ua": [0.5, 0.75, 1.0]}
SPEEDS = np.array(AXES["f"], float)
NMOD = 4
DT = 600.0
SUB = 6
GRID_CAP = 60.0          # kWe for the heating plant
A_F = 6000.0
VOL = 18000.0
SP_NAMES = {"1": "Evaporator outlet", "2": "Compressor suction", "3": "Compressor discharge", "4": "Condenser outlet",
            "5": "Evaporator inlet"}
SCENARIOS = {
    "tes_smart": dict(name="Edinburgh 2023 · 200 m³ TES · price-aware charging · 60 kWe cap", badge="TES smart",
                      tes=True, smart=True, cap=True),
    "tes_basic": dict(name="Edinburgh 2023 · 200 m³ TES · thermostatic charging · 60 kWe cap", badge="TES basic",
                      tes=True, smart=False, cap=True),
    "direct": dict(name="Edinburgh 2023 · no TES · direct load following · uncapped", badge="Direct (no TES)",
                   tes=False, smart=False, cap=False),
}


def build_map():
    core = HERE.parent / "_legacy" / "simcore"
    o, _ = cycles.solve(MODULE, dict(T_air=2, RH=80, T_w_in=45, f=60, ua=1.0))
    return PerfMap("retrofit_module_r290", core / "cycles.py", "solve", MODULE, AXES, list(o),
                   deps=[core / "hx.py", core / "thermo.py"])


def radiator(Q_nom, T_flow, T_room, m, n=1.3, dT_nom=50.0):
    if T_flow <= T_room + 0.5:
        return 0.0
    lo, hi = T_room + 1e-3, T_flow
    for _ in range(36):
        Tr = 0.5 * (lo + hi)
        d1, d2 = T_flow - T_room, Tr - T_room
        lm = (d1 - d2) / math.log(d1 / d2) if abs(d1 - d2) > 1e-6 else d1
        if m * CP_W * (T_flow - Tr) > Q_nom * (lm / dT_nom) ** n:
            lo = Tr
        else:
            hi = Tr
    return m * CP_W * (T_flow - Tr)


def simulate(key, pmap):
    sc = SCENARIOS[key]
    wx = weather.load("edinburgh")
    gr = grid.load()
    n = len(wx)
    lat, lon = weather.SITES["edinburgh"][:2]
    zen, az, doy = solar.position(wx["time"], lat, lon)
    phi_sol = np.zeros(n)
    for surf_az, area in ((0, 160), (90, 270), (180, 400), (270, 270)):
        b, d, g, aoi = solar.poa(wx.ghi.to_numpy(), wx.dni.to_numpy(), wx.dhi.to_numpy(), zen, az, doy, 90, surf_az)
        phi_sol += area * 0.55 * 0.7 * 0.7 * (b * solar.iam_ashrae(aoi) + d + g)
    hl = wx["hour_local"].to_numpy()
    work = wx["is_workday"].to_numpy()
    occ = work & (hl >= 7) & (hl < 19)
    gains = np.where(occ, 14.0, 2.5) * A_F                          # people + IT + lighting, W
    zone = Zone5R1C(A_f=A_F, H_tr_w=2000.0, H_tr_op=4300.0, C_m_per_m2=260e3, theta_m=19.0)
    H_inf = 0.34 * 0.3 * VOL
    H_mech = 0.34 * 9000 * (1 - 0.5)                                # 2.5 m3/s AHU, 50 % heat recovery
    H_design = 2000 + 4300 + H_inf + H_mech
    T_fd, T_design = 65.0, -4.0
    Q_design = H_design * (21 - T_design)
    m_heat = Q_design / (CP_W * 15.0)
    lm_d = ((T_fd - 21) - (T_fd - 15 - 21)) / math.log((T_fd - 21) / (T_fd - 36))
    Q_rad_nom = Q_design / (lm_d / 50) ** 1.3
    if sc["tes"]:
        tes = StratifiedTank(200.0, 13.0, nodes=24, U_wall=0.25, T_init=55.0)
        tes.UA[:] *= 1.35                                              # two tanks: extra heads and connecting pipework
    else:
        tes = StratifiedTank(2.0, 2.2, nodes=10, U_wall=0.3, T_init=50.0)
    price = gr["price"].to_numpy()
    day = np.arange(n) // 24
    cheap = np.zeros(n, bool)
    for dd in range(day.max() + 1):
        sl = day == dd
        cheap[sl] = price[sl] <= np.quantile(price[sl], 0.55)
    Ta_all, rh_all = wx["T_amb"].to_numpy(), wx["RH"].to_numpy()
    # heating-season flag for store management: trailing 24 h mean below 13.5 C
    T24 = np.convolve(np.r_[np.full(23, Ta_all[0]), Ta_all], np.ones(24) / 24, mode="valid")
    season = T24 < 13.5
    F = Fluid("Propane")
    K = pmap.out_keys
    acc = {k: np.zeros(n) for k in K}
    names = ["n_on", "f_mod", "Q_hp", "W_hp", "W_fan", "W_pump", "W_aux", "W_backup", "W_total", "Q_need", "Q_emit", "T_room",
             "T_op", "T_set_flow", "T_flow", "unmet", "tes_soc", "tes_loss", "Q_def", "defrosts", "starts", "cap_limited",
             "over_cap", "lead_on", "frost1", "T_ret", "season"]
    H = {k: np.zeros(n) for k in names}
    mod_run = np.zeros((n, NMOD))
    mod_frost = np.zeros(NMOD)
    mod_on = np.zeros(NMOD, bool)
    mod_hours = np.zeros(NMOD)
    tes_nodes = np.zeros((n, tes.N))
    T_room = 20.0
    for i in range(n):
        Ta, rh = Ta_all[i], rh_all[i]
        h = hl[i]
        set_h = 21.0 if (work[i] and 5 <= h < 19) else 16.0
        H_ve = H_inf + (H_mech if occ[i] else 0.0)
        Q_need, _ = zone.demand(Ta, H_ve, gains[i], phi_sol[i], set_h, 99.0)
        Q_need = max(0.0, Q_need)
        T_set = 21 + (T_fd - 21) * max(0.0, (21 - Ta) / (21 - T_design)) ** (1 / 1.3)
        T_set += min(8.0, 3.0 * max(0.0, set_h - T_room))
        T_set = min(T_fd + 5, max(30.0, T_set)) if Q_need > 0 else 30.0
        q_emit_acc = 0.0
        tr_acc = 0.0
        for s in range(SUB):
            T_top = tes.T[0]
            T_flow = min(T_set, T_top)
            Qmax = radiator(Q_rad_nom, T_flow, T_room, m_heat)
            Q_emit = min(Q_need, Qmax)
            T_ret = T_flow - Q_emit / (m_heat * CP_W)
            m_draw = m_heat * min(1.0, (T_flow - T_ret) / max(T_top - T_ret, 0.1)) if Q_emit > 0 else 0.0
            # ---- what heat does the plant want?
            if sc["tes"]:
                # charge to the compensated flow temperature + 8 K (66 C only in cheap hours when price-aware)
                T_ch = 66.0 if (sc["smart"] and cheap[i]) else min(66.0, max(45.0, T_set + 8.0))
                soc = float(np.clip(np.mean(tes.T - 30.0) / (T_ch - 30.0), 0, 1.2))
                T_out_target = T_ch
                if not season[i]:
                    want = Q_need > 0 and T_top < T_set + 1          # summer: no store maintenance
                elif sc["smart"]:
                    want = (cheap[i] and soc < 0.97) or soc < 0.35 or (Q_need > 0 and T_top < T_set + 1)
                else:
                    want = soc < 0.85 or (any(mod_on) and soc < 0.98)
                Q_req = 1e9 if want else 0.0
                T_in = tes.T[-1]
            else:
                want = Q_need > 0 or tes.T[3] < T_set
                T_out_target = T_set + 3
                T_in = tes.T[-1]
                Q_req = max(0.0, Q_emit + (T_set + 2 - tes.T[0]) * tes.M * tes.N * CP_W / 1800) if want else 0.0
            # ---- stage modules and choose speed under the electrical cap
            W_aux = 2.5e3 + (1.2e3 if sc["tes"] else 0.3e3) * (Q_emit > 0)
            W_circ = (1500.0 * (m_draw / m_heat) ** 3 if Q_emit > 0 else 0.0) + (800.0 if sc["tes"] else 0.0)
            # keep headroom for module pumps and a defrost in progress
            budget = (GRID_CAP * 1e3 - W_aux - W_circ - 2.5e3) if sc["cap"] else 1e12
            best = (0, 0.0, None, 0.0, 0.0)
            for k_on in range(1, NMOD + 1):
                for fs in SPEEDS[::-1]:
                    v, ok = pmap(T_air=Ta, RH=rh, T_w_in=T_in, f=fs, ua=1.0)
                    if ok < 0.5:
                        continue
                    Wk = (pmap.get(v, "W_tot") * 1e3 + 350.0) * k_on
                    Qk = pmap.get(v, "Q_c") * 1e3 * k_on
                    if Wk <= budget:
                        if Q_req >= 1e8:
                            score = Qk
                        else:
                            score = -abs(Qk - Q_req) - 0.02 * Wk
                        if best[2] is None or score > best[4]:
                            best = (k_on, fs, v, Qk, score)
                        break
            k_on, fs, _, _, _ = best
            if Q_req <= 0 or k_on == 0:
                k_on, fs = 0, 0.0
            # rotate lead module by run hours
            order = np.argsort(mod_hours)
            new_on = np.zeros(NMOD, bool)
            new_on[order[:k_on]] = True
            H["starts"][i] += int(np.sum(new_on & ~mod_on))
            mod_on = new_on
            Q_tot = W_tot = W_fan = 0.0
            for j in range(NMOD):
                if not mod_on[j]:
                    if Ta > 2:
                        mod_frost[j] = max(0.0, mod_frost[j] - 0.002 * (Ta - 2) * DT)
                    continue
                ua = max(0.5, 1 - 0.5 * min(mod_frost[j] / 10.0, 1))
                v, ok = pmap(T_air=Ta, RH=rh, T_w_in=T_in, f=fs, ua=ua)
                frac = 1.0
                if pmap.get(v, "Te") + 1.5 < 0 and pmap.get(v, "water") > 0:
                    mod_frost[j] += pmap.get(v, "water") * DT
                if mod_frost[j] >= 5.0:
                    E = mod_frost[j] * 338e3 + 1.0e6
                    H["defrosts"][i] += 1
                    H["Q_def"][i] += 0.75 * E / 3.6e6
                    tes.T -= 0.75 * E / (tes.M * CP_W * tes.N)
                    W_tot += 0.25 * E / DT
                    frac = 1 - min(DT, 150 + E / 25e3) / DT
                    mod_frost[j] = 0.0
                mod_hours[j] += frac * DT / 3600
                mod_run[i, j] += frac / SUB
                Q_tot += pmap.get(v, "Q_c") * 1e3 * frac
                W_tot += pmap.get(v, "W_tot") * 1e3 * frac
                W_fan += pmap.get(v, "W_fan") * 1e3 * frac
                if j == order[0]:
                    for ki, kk in enumerate(K):
                        acc[kk][i] += v[ki] * frac
                    H["lead_on"][i] += frac / SUB
            H["frost1"][i] += mod_frost[order[0]] / SUB
            # backup electric boiler only in the direct scenario
            W_backup = 0.0
            if not sc["tes"] and Q_emit > 0 and tes.T[0] < T_set - 1.0:
                W_backup = min(120e3, (T_set - tes.T[0]) * tes.M * tes.N * CP_W / 1200)
            tes.T[0] += W_backup * DT / (tes.M * CP_W)
            m_c = Q_tot / (CP_W * max(T_out_target - tes.T[-1], 4.0)) if Q_tot > 0 else 0.0
            r = tes.step(DT, m_c, 0.0, m_draw, T_ret, 8.0, Q_c=Q_tot if Q_tot > 0 else None)
            W_pump = (k_on * 350.0) + (1500.0 * (m_draw / m_heat) ** 3 if Q_emit > 0 else 0.0) + (800.0 if m_c > 0 and sc["tes"] else 0.0)
            W_site = W_tot + W_pump + W_aux + W_backup
            H["n_on"][i] += k_on / SUB
            H["f_mod"][i] += fs / SUB
            H["Q_hp"][i] += Q_tot * DT / 3.6e6
            H["W_hp"][i] += W_tot * DT / 3.6e6
            H["W_fan"][i] += W_fan * DT / 3.6e6
            H["W_pump"][i] += W_pump * DT / 3.6e6
            H["W_aux"][i] += W_aux * DT / 3.6e6
            H["W_backup"][i] += W_backup * DT / 3.6e6
            H["W_total"][i] += W_site * DT / 3.6e6
            H["over_cap"][i] = max(H["over_cap"][i], W_site / 1e3 - GRID_CAP)
            H["season"][i] = season[i]
            H["cap_limited"][i] += (sc["cap"] and Q_req > 0 and k_on > 0 and best[3] < min(Q_req, 1e8) * 0.98) / SUB
            H["tes_loss"][i] += r["Q_loss"] * DT / 3.6e6
            q_emit_acc += Q_emit
            tr_acc += T_ret
        Q_emit = q_emit_acc / SUB
        z = zone.step(Ta, H_ve, gains[i], phi_sol[i], Q_emit)
        T_room = z["T_air"]
        H["T_room"][i], H["T_op"][i] = z["T_air"], z["T_op"]
        H["Q_need"][i], H["Q_emit"][i] = Q_need / 1e3, Q_emit / 1e3
        H["T_set_flow"][i], H["T_flow"][i], H["T_ret"][i] = T_set, min(T_set, tes.T[0]), tr_acc / SUB
        H["unmet"][i] = max(0.0, 20.0 - z["T_air"]) if occ[i] else 0.0
        H["tes_soc"][i] = tes.soc(35.0, 66.0) * 100
        tes_nodes[i] = tes.T
        if H["lead_on"][i] > 0:
            for kk in K:
                acc[kk][i] /= H["lead_on"][i] * SUB
    info = dict(Q_design=Q_design, H_design=H_design, phi_sol=phi_sol, gains=gains, occ=occ)
    return sc, wx, gr, acc, H, tes_nodes, mod_run, info, F


def export(key, pmap):
    sc, wx, gr, acc, H, tes_nodes, mod_run, info, F = simulate(key, pmap)
    n = len(wx)
    R = Results(key, sc["name"], n)
    on = H["lead_on"] > 0
    Ta = wx["T_amb"].to_numpy()
    for k in acc:
        if k.startswith("sp"):
            sid, fld = k[2:].split("_")
            for i in np.where(~on)[0]:
                st = F.PQ(F.Psat(Ta[i] + 273.15), 1.0)
                acc[k][i] = {"T": st.Tc, "P": st.P / 1e5, "h": st.h / 1e3, "s": st.s / 1e3, "x": np.nan, "m": 0.0, "ex": 0.0}[fld]
        elif k.startswith(("X_", "Ex_")) or k in ("Q_c", "Q_e", "W_comp", "W_fan", "W_tot", "m_ref", "water", "m_air", "fan"):
            acc[k][~on] = 0.0
        else:
            acc[k][~on] = np.nan
    g = "Ambient & grid"
    R.ch("T_amb", Ta, "°C", "Outdoor air temperature", g, 1)
    R.ch("RH", wx.RH, "%", "Outdoor relative humidity", g, 0)
    R.ch("wind", wx.wind10, "m/s", "Wind speed", g, 1)
    R.ch("ghi", wx.ghi, "W/m²", "Global horizontal irradiance", g, 0)
    R.ch("price", gr.price, "p/kWh", "Agile import price", g, 2)
    R.ch("ci", gr.ci, "gCO₂/kWh", "GB grid carbon intensity", g, 0)
    for sid, nm in SP_NAMES.items():
        R.state_point(sid, nm, "Lead module R290", "Propane", {f: acc[f"sp{sid}_{f}"] for f in ("T", "P", "h", "s", "x", "m", "ex")})
    R.state_point("W1", "Store return to modules", "Primary water", "Water",
                  {"T": np.where(on, acc["T_w_out"] - acc["Q_c"] / (MODULE["m_w"] * CP_W / 1e3), np.nan), "P": np.full(n, 3.0),
                   "h": np.nan_to_num(acc["T_w_out"] - acc["Q_c"] / (MODULE["m_w"] * CP_W / 1e3)) * CP_W / 1e3,
                   "m": H["n_on"] * MODULE["m_w"]})
    R.state_point("W2", "Module flow to store", "Primary water", "Water",
                  {"T": acc["T_w_out"], "P": np.full(n, 2.7), "h": np.nan_to_num(acc["T_w_out"]) * CP_W / 1e3, "m": H["n_on"] * MODULE["m_w"]})
    g = "Lead module cycle"
    for k, u, lbl, d in [("Pe", "bar", "Evaporating pressure", 3), ("Pc", "bar", "Condensing pressure", 3), ("Te", "°C", "Evaporating temperature", 1),
                         ("Tc", "°C", "Condensing temperature", 1), ("T_dis", "°C", "Discharge temperature", 1), ("pr", "–", "Pressure ratio", 2),
                         ("lift", "K", "Lift", 1), ("T_air_out", "°C", "Coil air-off temperature", 1)]:
        R.ch(k, acc[k], u, lbl, g, d)
    R.ch("eta_is", acc["eta_is"] * 100, "%", "Isentropic efficiency", g, 1)
    R.ch("cop_mod", acc["COP"], "–", "Module COP (incl. fans)", g, 2)
    R.ch("Q_mod", acc["Q_c"] * H["lead_on"], "kW", "Lead module heat output", g, 1)
    R.ch("frost1", H["frost1"], "kg", "Lead module coil frost", g, 2)
    g = "Cascade"
    R.ch("n_on", H["n_on"], "–", "Modules running", g, 2)
    R.ch("f_mod", np.where(H["n_on"] > 0, H["f_mod"] * 1.0, 0.0), "Hz", "Module compressor speed", g, 1)
    for j in range(NMOD):
        R.ch(f"mod{j + 1}_run", mod_run[:, j] * 100, "%", f"Module {j + 1} run fraction", g, 0)
    R.ch("Q_hp", H["Q_hp"], "kW", "Cascade heat output", g, 1)
    R.ch("W_hp", H["W_hp"], "kW", "Modules electrical (comp + fans)", g, 1)
    R.ch("cop", np.where(H["W_hp"] > 0, H["Q_hp"] / np.maximum(H["W_hp"], 1e-9), np.nan), "–", "Cascade COP", g, 2)
    R.ch("defrosts", H["defrosts"], "1/h", "Defrosts (all modules)", g, 0)
    R.ch("starts", H["starts"], "1/h", "Module starts", g, 0)
    R.ch("cap_limited", H["cap_limited"] * 100, "%", "Output limited by grid cap", g, 0)
    g = "Exergy destruction (lead)"
    for k, lbl in [("X_comp", "Compressor"), ("X_cond", "Condenser"), ("X_evap", "Evaporator"), ("X_eev", "EEV"),
                   ("X_fan", "Fan"), ("Ex_air_out", "Exhaust air"), ("Ex_prod", "Product")]:
        R.ch(k, acc[k] * H["lead_on"], "kW", lbl, g, 2)
    g = "Thermal store"
    R.ch("tes_soc", H["tes_soc"], "%", "Store state of charge (35-66 °C)", g, 0)
    R.ch("tes_loss", H["tes_loss"], "kW", "Store standing loss", g, 2)
    R.ch("season", H["season"], "–", "Heating season (store maintained)", g, 0)
    R.ch("Q_def", H["Q_def"], "kWh", "Defrost heat drawn from store", g, 1)
    nn = tes_nodes.shape[1]
    if nn == 24:
        for j in range(12):
            R.ch(f"tesA_T{j + 1}", tes_nodes[:, j], "°C", f"Store A node {j + 1} (top=1)", "Store A nodes", 1)
            R.ch(f"tesB_T{j + 1}", tes_nodes[:, 12 + j], "°C", f"Store B node {j + 1} (top=1)", "Store B nodes", 1)
    else:
        for j in range(12):
            jj = min(nn - 1, int(j * nn / 12))
            R.ch(f"tesA_T{j + 1}", tes_nodes[:, jj], "°C", f"Buffer node {j + 1} (top=1)", "Store A nodes", 1)
            R.ch(f"tesB_T{j + 1}", np.full(n, np.nan), "°C", f"Store B node {j + 1} (not installed)", "Store B nodes", 1)
    g = "Building"
    R.ch("T_room", H["T_room"], "°C", "Indoor air temperature", g, 2)
    R.ch("T_op", H["T_op"], "°C", "Operative temperature", g, 2)
    R.ch("Q_need", H["Q_need"], "kW", "Heating need", g, 1)
    R.ch("Q_emit", H["Q_emit"], "kW", "Radiator output", g, 1)
    R.ch("T_set_flow", H["T_set_flow"], "°C", "Flow setpoint", g, 1)
    R.ch("T_flow", H["T_flow"], "°C", "Radiator flow temperature", g, 1)
    R.ch("T_ret", H["T_ret"], "°C", "Radiator return temperature", g, 1)
    R.ch("unmet", H["unmet"], "K", "Occupied-hour deficit below 20 °C", g, 2)
    R.ch("occupied", info["occ"].astype(float), "–", "Occupied", g, 0)
    R.ch("phi_sol", info["phi_sol"] / 1e3, "kW", "Solar gains", g, 1)
    R.ch("phi_int", info["gains"] / 1e3, "kW", "Internal gains", g, 1)
    g = "Electrical"
    R.ch("W_pump", H["W_pump"], "kW", "Pumps", g, 2)
    R.ch("W_aux", H["W_aux"], "kW", "Controls, AHU heater batteries", g, 2)
    R.ch("W_backup", H["W_backup"], "kW", "Electric boiler (direct scenario)", g, 1)
    R.ch("W_total", H["W_total"], "kW", "Heating plant electrical demand", g, 1)
    R.ch("grid_cap", np.full(n, GRID_CAP), "kW", "Connection cap", g, 0)
    R.ch("over_cap", np.maximum(H["over_cap"], 0.0), "kW", "Peak above cap (10-min)", g, 1)
    cost = H["W_total"] * gr.price.to_numpy() / 100
    co2 = H["W_total"] * gr.ci.to_numpy() / 1000
    R.ch("cost", cost, "£/h", "Electricity cost", g, 2)
    R.ch("co2", co2, "kg/h", "Operational CO₂", g, 2)
    R.ch("cum_cost", np.cumsum(cost) / 1000, "k£", "Cumulative cost", g, 2)
    R.ch("cum_co2", np.cumsum(co2) / 1000, "t", "Cumulative CO₂", g, 2)
    R.start = int(np.argmax(np.where(np.arange(n) < 24 * 60, H["Q_need"], -1)))

    k = R.kpi
    Q, W = H["Q_hp"].sum(), H["W_total"].sum()
    k("Seasonal COP (modules, H2)", Q / H["W_hp"].sum(), "–", "Performance", 2)
    k("System SPF (all plant electricity)", (Q + H["W_backup"].sum()) / W, "–", "Performance", 2)
    k("Heat delivered to building", H["Q_emit"].sum() / 1000, "MWh", "Energy", 0)
    k("Heat from modules", Q / 1000, "MWh", "Energy", 0)
    k("Store standing losses", H["tes_loss"].sum() / 1000, "MWh", "Energy", 1)
    k("Plant electricity", W / 1000, "MWh", "Energy", 0)
    k("Electric boiler", H["W_backup"].sum() / 1000, "MWh", "Energy", 1)
    k("Design heat loss (−4 °C)", info["Q_design"] / 1000, "kW", "Design", 0)
    k("Peak hourly plant demand", H["W_total"].max(), "kW", "Grid", 1)
    k("Peak 10-min demand", GRID_CAP + max(0.0, H["over_cap"].max()), "kW", "Grid", 1)
    k("Hours above 60 kWe cap", float((H["over_cap"] > 0.5).sum()), "h", "Grid", 0)
    k("Hours output limited by cap", float((H["cap_limited"] > 0.5).sum()), "h", "Grid", 0)
    k("Load factor on 60 kWe connection", 100 * W / (GRID_CAP * 8760), "%", "Grid", 1)
    k("Electricity cost (Agile)", cost.sum() / 1000, "k£", "Cost & carbon", 2)
    k("Average price paid", cost.sum() / W * 100, "p/kWh", "Cost & carbon", 2)
    k("Operational CO₂", co2.sum() / 1000, "t", "Cost & carbon", 1)
    gas = H["Q_emit"].sum() / 0.85
    k("Gas boiler counterfactual cost", gas * grid.GAS_PRICE_P_KWH / 1e5, "k£", "Cost & carbon", 2)
    k("Gas boiler counterfactual CO₂", gas * grid.GAS_CARBON_G_KWH / 1e6, "t", "Cost & carbon", 1)
    k("Unmet occupied hours (<20 °C)", float((H["unmet"] > 0).sum()), "h", "Comfort", 0)
    k("Min occupied indoor temperature", float(H["T_room"][info["occ"]].min()), "°C", "Comfort", 1)
    k("Module starts", H["starts"].sum(), "", "Operation", 0)
    k("Defrost cycles (all modules)", H["defrosts"].sum(), "", "Operation", 0)
    for j in range(NMOD):
        k(f"Module {j + 1} run hours", mod_run[:, j].sum(), "h", "Operation", 0)
    k("Mean store SOC", H["tes_soc"].mean(), "%", "Operation", 0)
    fl = Fluid("Propane")
    paths = [["5", "1", "2", "3", "4", "5"]]
    R.diagrams.append({"type": "ph", "title": "Lead module R290 log P–h", "fluid": "Propane", "dome": fl.dome(70, 233.0), "paths": paths})
    R.diagrams.append({"type": "ts", "title": "Lead module R290 T–s", "fluid": "Propane", "dome": fl.dome(70, 233.0), "paths": paths})
    R.diagrams.append({"type": "profile", "title": "Thermal store profiles", "xLabel": "°C",
                       "series": [{"label": "Store A", "keys": [f"tesA_T{j + 1}" for j in range(12)], "color": "#c2410c"},
                                  {"label": "Store B", "keys": [f"tesB_T{j + 1}" for j in range(12)], "color": "#2f5bd3"}]})
    R.diagrams.append({"type": "bars", "title": "Module run fraction this hour (%)",
                       "items": [{"key": f"mod{j + 1}_run", "label": f"Module {j + 1}"} for j in range(NMOD)]})
    return R, sc


if __name__ == "__main__":
    import time
    t = time.time()
    pm = build_map()
    print("map", "%.3f" % pm.coverage(), "%.0fs" % (time.time() - t))
    for key in (sys.argv[1:] or SCENARIOS):
        t = time.time()
        R, sc = export(key, pm)
        print(key, "%.0fs" % (time.time() - t))
        for kp in R.kpis:
            print(f"  {kp['label']:<40} {kp['value'] if kp['value'] is not None else float('nan'):.2f} {kp['unit']}")
