"""UniBoat electric hydrofoil catamaran: powertrain + pumped two-phase R1233zd(E) cooling, full 2023 season.

Boat        Monaco Energy Class catamaran (10 x 4.4 m envelope), 750 kg with pilot, 10 kWh battery cap
Hydro       hull-borne resistance (ITTC-57 friction + Froude-number wave hump), take-off at 7 m/s, foil-borne
            drag from lift/drag ratio (peak ~11 at 12 m/s), strut + air drag, propeller efficiency 0.72
Powertrain  axial-flux PMSM (efficiency map vs load), SiC inverter (conduction + switching losses),
            battery pack (OCV-SOC, R_pack(T) = 0.089 ohm at 25 C, I^2 R heat), 7 kW shore charger
Cooling     pump -> battery plate -> inverter plate -> motor jacket (series) -> seawater condenser -> accumulator.
            Accumulator holds T_sat = T_sea + 8 K (min 25 C); if the condenser cannot reject the load the
            saturation temperature floats up. Pump flow targets exit quality 0.5. All refrigerant states are
            CoolProp solutions; component temperatures are lumped thermal nodes (R_th to the local fluid).
Sessions    training Tue/Thu/Sat (Mar-Oct, ~45 min paced inside the 10 kWh cap): foiling cruise 18 kt, 3 x 60 s sprints at 35 kt;
            Monaco race week 5-8 July: endurance (energy-limited) and sprint. 1 s internal steps, hourly outputs.
A separate 1 s scenario records the 8 July race in full.
"""
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_legacy"))  # frozen simcore v0.1.0

from simcore import weather  # noqa: E402
from simcore.output import Results  # noqa: E402
from simcore.thermo import Fluid  # noqa: E402

RHO_W, NU_W, G = 1025.0, 1.19e-6, 9.81
MASS = 750.0
L_WL, S_WET = 9.6, 6.5            # two slender demi-hulls
E_PACK = 10.0e3 * 3600         # J (10 kWh cap)
R_PACK25 = 0.089
V_NOM = 400.0
SP = {"1": "Pump inlet (subcooled)", "2": "Pump outlet", "3": "Battery plate outlet", "4": "Inverter plate outlet",
      "5": "Motor jacket outlet", "6": "Condenser outlet"}
F = Fluid("R1233zd(E)")


def drag(v, wave_h=0.3):
    """Total resistance (N) and flight state at speed v (m/s)."""
    if v < 0.2:
        return 0.0, 0.0
    if v < 7.0:
        Re = v * L_WL / NU_W
        Cf = 0.075 / (math.log10(Re) - 2) ** 2
        Fn = v / math.sqrt(G * L_WL)
        Cw = 0.0085 * math.exp(-((Fn - 0.5) / 0.18) ** 2) + 0.0012
        R_h = 0.5 * RHO_W * v ** 2 * S_WET * (Cf * 1.25 + Cw) * (1 + 0.15 * wave_h)
        lift_frac = max(0.0, (v - 4.5) / 2.5)
        return R_h * (1 - 0.6 * lift_frac) + lift_frac * MASS * G / 8.0, 0.0
    LD = 11.0 - 0.012 * (v - 12.0) ** 2 * 6.0
    D_foil = MASS * G / max(LD, 6.0)
    D_strut = 0.5 * RHO_W * v ** 2 * 0.012 * 0.009
    D_air = 0.5 * 1.2 * v ** 2 * 1.3
    return D_foil * (1 + 0.08 * wave_h) + D_strut + D_air, 1.0


def motor_eff(P_shaft, P_max=120e3):
    x = max(P_shaft / P_max, 1e-3)
    return 0.955 - 0.06 * (1 - x) ** 6 - 0.025 * x ** 2


def ocv(soc):
    return 360.0 + 60.0 * soc + 8.0 * math.tanh((soc - 0.08) * 20) - 8.0


def session_profile(kind):
    """Speed set-point series (m/s, 1 Hz) for a session."""
    kt = 0.5144
    if kind == "training":
        seg = [(240, 8 * kt), (60, 14 * kt)]          # paced inside the 10 kWh cap (~45 min)
        for k in range(3):
            seg += [(480, 18 * kt), (60, 35 * kt)]
        seg += [(360, 18 * kt), (300, 8 * kt)]
    elif kind == "endurance":
        seg = [(180, 8 * kt), (3000, 21 * kt), (180, 8 * kt)]
    else:  # sprint / slalom heats
        seg = [(180, 8 * kt)] + [(120, 36 * kt), (240, 6 * kt)] * 4 + [(120, 8 * kt)]
    v = []
    for dur, target in seg:
        v += [target] * dur
    v = np.array(v)
    # first-order speed response (time constant 8 s) for realistic acceleration
    out = np.zeros_like(v)
    for i in range(1, len(v)):
        out[i] = out[i - 1] + (v[i] - out[i - 1]) / 8.0
    return out


def run_session(prof, T_sea, T_air, wave_h, state, record=False):
    """Integrate one session at 1 s. Returns per-second arrays (if record) and updates state in place."""
    n = len(prof)
    keys = ["v", "foil", "D", "P_shaft", "P_elec", "Q_m", "Q_i", "Q_b", "soc", "I", "V", "T_b", "T_i", "T_m", "Tsat", "m_r",
            "x5", "W_pump", "Q_cond", "T_sw_out"] + [f"sp{k}_{f}" for k in SP for f in ("T", "P", "h", "s", "x")]
    rec = {k: np.zeros(n) for k in keys} if record else None
    agg = {k: 0.0 for k in keys}
    mx = {"T_b": -99, "T_i": -99, "T_m": -99, "P_elec": 0, "Q_tot": 0, "Tsat": -99, "v": 0}
    limp = False
    for t in range(n):
        v = prof[t]
        if state["soc"] < 0.05:                       # energy cap reached: limp home hull-borne at 5 kt
            limp = True
        if limp:
            v = min(v, 5 * 0.5144)
        D, foil = drag(v, wave_h)
        P_shaft = D * v / 0.72
        eta_m = motor_eff(P_shaft)
        P_m_in = P_shaft / eta_m
        Q_m = P_m_in - P_shaft
        Q_i = 0.0045 * P_m_in + 120.0 * (P_m_in > 100) + 2.5e-8 * P_m_in ** 2
        P_dc = P_m_in + Q_i + 350.0                                  # + avionics, pump driver
        Vo = ocv(state["soc"])
        R = R_PACK25 * math.exp(0.028 * (25.0 - state["T_b"]))
        I = (Vo - math.sqrt(max(Vo * Vo - 4 * R * P_dc, 1.0))) / (2 * R)
        Q_b = I * I * R
        state["soc"] = max(0.0, state["soc"] - I * 1.0 / (E_PACK / V_NOM))
        Q_tot = Q_b + Q_i + Q_m
        # accumulator / condenser: T_sat set-point, floats up when rejection is limited
        T_set = max(25.0, T_sea + 8.0)
        C_sw = 0.555 * 3990.0
        eps = 1 - math.exp(-1400.0 / C_sw)
        Q_cond_max = eps * C_sw * (T_set - T_sea)
        T_sat = T_set if Q_tot <= Q_cond_max else T_sea + Q_tot / (eps * C_sw)
        T_sat = 0.9 * state["Tsat"] + 0.1 * T_sat                  # accumulator / loop thermal inertia
        state["Tsat"] = T_sat
        Ps = F.Psat(T_sat + 273.15)
        hl, hv, *_ = F.sat(Ps)
        hfg = hv - hl
        m = float(np.clip(Q_tot / (hfg * 0.5), 0.02, 0.15))
        s1 = F.subcooled(Ps, 3.0)
        dp = 26e3 * (m / 0.1076) ** 1.8
        s2 = F.PH(Ps + dp, s1.h + dp / s1.rho / 0.30)
        s3 = F.PH(Ps + dp * 0.6, s2.h + Q_b / m)
        s4 = F.PH(Ps + dp * 0.45, s3.h + Q_i / m)
        s5 = F.PH(Ps + dp * 0.2, s4.h + Q_m / m)
        s6 = F.subcooled(Ps, 3.0)
        W_pump = m / s1.rho * dp / 0.30
        # component lumped nodes (R_th rises when the local fluid is still subcooled)
        def rth(base, st):
            return base * (2.5 if st.x <= 0 else 1.0)
        for key, Q, C, st, base in (("T_b", Q_b, 70e3, s3, 0.35e-3), ("T_i", Q_i, 2.5e3, s4, 4.0e-3), ("T_m", Q_m, 18e3, s5, 0.6e-3)):
            Tf = st.Tc
            Rk = rth(base, st)
            state[key] += (Q - (state[key] - Tf) / Rk) / C
            state[key] = (state[key] * C + Q + Tf / Rk) / (C + 1 / Rk) if False else state[key]
        state["T_b_hull"] = T_air
        vals = {"v": v, "foil": foil, "D": D, "P_shaft": P_shaft, "P_elec": P_dc, "Q_m": Q_m, "Q_i": Q_i, "Q_b": Q_b,
                "soc": state["soc"], "I": I, "V": Vo - I * R, "T_b": state["T_b"], "T_i": state["T_i"], "T_m": state["T_m"],
                "Tsat": T_sat, "m_r": m, "x5": s5.x, "W_pump": W_pump, "Q_cond": Q_tot, "T_sw_out": T_sea + Q_tot / C_sw}
        for k, st in zip(SP, (s1, s2, s3, s4, s5, s6)):
            vals[f"sp{k}_T"], vals[f"sp{k}_P"], vals[f"sp{k}_h"] = st.Tc, st.P / 1e5, st.h / 1e3
            vals[f"sp{k}_s"], vals[f"sp{k}_x"] = st.s / 1e3, st.x
        for k in keys:
            agg[k] += vals[k] / n
            if record:
                rec[k][t] = vals[k]
        for k in ("T_b", "T_i", "T_m", "P_elec", "Tsat", "v"):
            mx[k] = max(mx[k], vals[k])
        mx["Q_tot"] = max(mx["Q_tot"], Q_tot)
    mx["limp"] = limp
    return rec, agg, mx


def schedule(wx):
    t = wx["time"]
    out = []
    for i in range(len(wx)):
        d = t.iat[i]
        if d.month == 7 and d.day in (5, 6, 7, 8) and d.hour in (9, 14):
            out.append((i, "endurance" if d.hour == 9 else "sprint"))
        elif 3 <= d.month <= 10 and d.weekday() in (1, 3, 5) and d.hour == 9 and not (d.month == 7 and 5 <= d.day <= 8):
            out.append((i, "training"))
    return out


def simulate():
    wx = weather.load("monaco", marine=True)
    n = len(wx)
    T_sea = wx["T_sea"].to_numpy()
    T_air = wx["T_amb"].to_numpy()
    waves = wx["wave_h"].fillna(0.3).to_numpy()
    sess = dict(schedule(wx))
    state = {"soc": 1.0, "T_b": 18.0, "T_i": 18.0, "T_m": 18.0, "Tsat": 25.0}
    names = ["v", "foil", "D", "P_shaft", "P_elec", "Q_m", "Q_i", "Q_b", "soc", "I", "V", "T_b", "T_i", "T_m", "Tsat", "m_r", "x5",
             "W_pump", "Q_cond", "T_sw_out", "v_max", "P_max", "T_b_max", "T_i_max", "T_m_max", "Q_max", "session", "charging",
             "E_used", "limp"] + [f"sp{k}_{f}" for k in SP for f in ("T", "P", "h", "s", "x", "m")]
    H = {k: np.full(n, np.nan) for k in names}
    for k in ("v", "foil", "P_elec", "P_shaft", "Q_m", "Q_i", "Q_b", "W_pump", "Q_cond", "session", "charging", "E_used", "I", "D", "limp",
              "v_max", "P_max", "Q_max", "m_r"):
        H[k][:] = 0.0
    race = None
    for i in range(n):
        if i in sess:
            kind = sess[i]
            prof = session_profile(kind)
            state["T_b"] = state["T_i"] = state["T_m"] = T_air[i] + 3.0
            soc0 = state["soc"]
            rec, agg, mx = run_session(prof, T_sea[i], T_air[i], waves[i], state, record=(kind == "sprint" and wx["time"].iat[i].day == 8))
            if rec is not None:
                race = (rec, i)
            frac = len(prof) / 3600.0
            for k, v in agg.items():
                if k in ("v", "foil", "P_elec", "P_shaft", "Q_m", "Q_i", "Q_b", "W_pump", "Q_cond", "I", "D"):
                    H[k][i] = v * min(frac, 1.0)
                else:
                    H[k][i] = v
            for k in SP:
                H[f"sp{k}_m"][i] = agg["m_r"]
            H["v_max"][i], H["P_max"][i], H["Q_max"][i] = mx["v"], mx["P_elec"], mx["Q_tot"]
            H["T_b_max"][i], H["T_i_max"][i], H["T_m_max"][i] = mx["T_b"], mx["T_i"], mx["T_m"]
            H["session"][i] = {"training": 1, "endurance": 2, "sprint": 3}[kind]
            H["E_used"][i] = (soc0 - state["soc"]) * 10.0
            H["limp"][i] = float(mx["limp"])
        else:
            # idle / charging at 7 kW after use; components relax to ambient
            if state["soc"] < 0.995:
                dE = min(7.0 * 0.93, (1 - state["soc"]) * 10.0)
                state["soc"] += dE / 10.0
                H["charging"][i] = dE / 0.93
                Q_b = 7000 * 0.012
                H["Q_b"][i] = Q_b
            for kk in ("T_b", "T_i", "T_m"):
                state[kk] += (T_air[i] + 2.0 - state[kk]) * 0.5
            H["T_b"][i], H["T_i"][i], H["T_m"][i] = state["T_b"], state["T_i"], state["T_m"]
            H["soc"][i] = state["soc"]
            H["Tsat"][i] = max(25.0, T_sea[i] + 8.0)
            Ps = F.Psat(H["Tsat"][i] + 273.15)
            st = F.subcooled(Ps, 3.0)
            for k in SP:
                H[f"sp{k}_T"][i], H[f"sp{k}_P"][i], H[f"sp{k}_h"][i] = st.Tc, st.P / 1e5, st.h / 1e3
                H[f"sp{k}_s"][i], H[f"sp{k}_x"][i], H[f"sp{k}_m"][i] = st.s / 1e3, st.x, 0.0
            H["T_sw_out"][i] = T_sea[i]
            state["Tsat"] = H["Tsat"][i]
    return wx, H, race


def _channels(R, D, n, wx=None, T_sea=None, hourly=True):
    g = "Conditions"
    if wx is not None:
        R.ch("T_amb", wx.T_amb, "°C", "Air temperature", g, 1)
        R.ch("T_sea", wx.T_sea, "°C", "Sea surface temperature", g, 1)
        R.ch("wave_h", wx.wave_h.fillna(0), "m", "Significant wave height", g, 2)
        R.ch("ghi", wx.ghi, "W/m²", "Irradiance", g, 0)
    g = "Boat"
    R.ch("v", D["v"] / 0.5144, "kt", "Boat speed" + (" (session mean)" if hourly else ""), g, 1)
    R.ch("foil", D["foil"] * 100, "%", "Foil-borne fraction", g, 0)
    R.ch("D", D["D"], "N", "Total resistance", g, 0)
    g = "Powertrain"
    R.ch("P_shaft", D["P_shaft"] / 1e3, "kW", "Shaft power", g, 2)
    R.ch("P_elec", D["P_elec"] / 1e3, "kW", "Battery DC power", g, 2)
    R.ch("soc", D["soc"] * 100, "%", "Battery SOC (10 kWh cap)", g, 1)
    R.ch("I", D["I"], "A", "Pack current", g, 1)
    g = "Heat loads"
    R.ch("Q_b", D["Q_b"] / 1e3, "kW", "Battery heat", g, 3)
    R.ch("Q_i", D["Q_i"] / 1e3, "kW", "SiC inverter heat", g, 3)
    R.ch("Q_m", D["Q_m"] / 1e3, "kW", "Motor heat", g, 3)
    R.ch("Q_cond", D["Q_cond"] / 1e3, "kW", "Condenser rejection", g, 3)
    g = "Component temperatures"
    R.ch("T_b", D["T_b"], "°C", "Battery cells", g, 1)
    R.ch("T_i", D["T_i"], "°C", "Inverter junction", g, 1)
    R.ch("T_m", D["T_m"], "°C", "Motor winding", g, 1)
    g = "Two-phase loop"
    R.ch("Tsat", D["Tsat"], "°C", "Saturation temperature (accumulator)", g, 2)
    R.ch("m_r", D["m_r"] * 1e3, "g/s", "Refrigerant mass flow", g, 1)
    R.ch("x5", D["x5"], "–", "Exit vapour quality", g, 3)
    R.ch("W_pump", D["W_pump"], "W", "Pump electrical power", g, 2)
    R.ch("T_sw_out", D["T_sw_out"], "°C", "Seawater outlet", g, 1)
    for k, nm in SP.items():
        rec = {f: D[f"sp{k}_{f}"] for f in ("T", "P", "h", "s", "x")}
        rec["m"] = D[f"sp{k}_m"] if f"sp{k}_m" in D else D["m_r"]
        R.state_point(k, nm, "R1233zd(E) loop", "R1233zd(E)", rec)


def export_season():
    wx, H, race = simulate()
    n = len(wx)
    R = Results("season", "Monaco 2023 · training season + race week (hourly)", n)
    _channels(R, H, n, wx)
    g = "Season"
    R.ch("session", H["session"], "–", "Session (1 train, 2 endurance, 3 sprint)", g, 0)
    R.ch("v_max", H["v_max"] / 0.5144, "kt", "Session peak speed", g, 1)
    R.ch("P_max", H["P_max"] / 1e3, "kW", "Session peak power", g, 1)
    R.ch("Q_max", H["Q_max"] / 1e3, "kW", "Session peak heat", g, 2)
    R.ch("T_b_max", H["T_b_max"], "°C", "Session peak battery temp", g, 1)
    R.ch("T_i_max", H["T_i_max"], "°C", "Session peak junction temp", g, 1)
    R.ch("T_m_max", H["T_m_max"], "°C", "Session peak winding temp", g, 1)
    R.ch("charging", H["charging"], "kW", "Shore charging", g, 2)
    R.ch("E_used", H["E_used"], "kWh", "Energy per session", g, 2)
    on = H["session"] > 0
    R.start = int(np.argmax(np.where(H["session"] == 3, H["Q_max"], -1)))
    k = R.kpi
    k("Sessions", on.sum(), "", "Season", 0)
    k("On-water hours", on.sum(), "h", "Season", 0)
    k("Energy drawn", H["E_used"].sum(), "kWh", "Season", 1)
    k("Shore charging energy", H["charging"].sum(), "kWh", "Season", 1)
    k("Sessions ending in limp mode (10 kWh cap)", H["limp"].sum(), "", "Season", 0)
    k("Peak battery heat", np.nanmax(H["Q_max"]) / 1e3, "kW", "Thermal", 2)
    k("Max battery temperature", np.nanmax(H["T_b_max"]), "°C", "Thermal", 1)
    k("Max inverter junction", np.nanmax(H["T_i_max"]), "°C", "Thermal", 1)
    k("Max motor winding", np.nanmax(H["T_m_max"]), "°C", "Thermal", 1)
    k("Max saturation temperature", np.nanmax(H["Tsat"]), "°C", "Thermal", 1)
    k("Hours T_sat floated above set-point", float(np.sum(on & (H["Tsat"] > np.maximum(25, wx.T_sea.to_numpy() + 8) + 0.5))), "h", "Thermal", 0)
    k("Mean sea temperature (sessions)", np.nanmean(wx.T_sea.to_numpy()[on]), "°C", "Thermal", 1)
    k("Pump energy", np.nansum(H["W_pump"]) / 1000, "kWh", "Thermal", 3)
    _diagrams(R)
    return R, race, wx


def export_race(race, wx):
    rec, i0 = race
    n = len(rec["v"])
    t0 = wx["time"].iat[i0].strftime("%Y-%m-%dT%H:%M:%SZ")
    R = Results("race", "Monaco 8 July 2023 · sprint heats at 1 s resolution", n, t0=t0, dt=1.0)
    rec = dict(rec)
    for k in SP:
        rec[f"sp{k}_m"] = rec["m_r"]
    _channels(R, rec, n, hourly=False)
    R.ch("T_sea", np.full(n, float(wx["T_sea"].iat[i0])), "°C", "Sea surface temperature", "Conditions", 1)
    R.ch("wave_h", np.full(n, float(np.nan_to_num(wx["wave_h"].iat[i0], nan=0.3))), "m", "Significant wave height", "Conditions", 2)
    R.ch("T_amb", np.full(n, float(wx["T_amb"].iat[i0])), "°C", "Air temperature", "Conditions", 1)
    k = R.kpi
    k("Peak speed", rec["v"].max() / 0.5144, "kt", "Race", 1)
    k("Peak DC power", rec["P_elec"].max() / 1e3, "kW", "Race", 1)
    k("Peak total heat", (rec["Q_b"] + rec["Q_i"] + rec["Q_m"]).max() / 1e3, "kW", "Race", 2)
    k("Energy used", (rec["P_elec"].sum()) / 3.6e6, "kWh", "Race", 2)
    k("Max battery temperature", rec["T_b"].max(), "°C", "Race", 1)
    k("Max inverter junction", rec["T_i"].max(), "°C", "Race", 1)
    k("Max motor winding", rec["T_m"].max(), "°C", "Race", 1)
    k("Peak refrigerant flow", rec["m_r"].max() * 1e3, "g/s", "Race", 1)
    k("Max exit quality", rec["x5"].max(), "–", "Race", 3)
    R.start = int(np.argmax(rec["P_elec"]))
    _diagrams(R)
    return R


def _diagrams(R):
    paths = [["1", "2", "3", "4", "5", "6", "1"]]
    R.diagrams.append({"type": "ph", "title": "R1233zd(E) log P–h (loop)", "fluid": "R1233zd(E)", "dome": F.dome(70, 263.0), "paths": paths})
    R.diagrams.append({"type": "bars", "title": "Heat loads now (kW)", "items": [
        {"key": "Q_b", "label": "Battery"}, {"key": "Q_i", "label": "Inverter"}, {"key": "Q_m", "label": "Motor"}, {"key": "Q_cond", "label": "Condenser"}]})
    R.diagrams.append({"type": "profile", "title": "Loop temperature (pump → condenser)", "xLabel": "°C",
                       "series": [{"label": "T", "keys": [f"{k}_T" for k in SP], "color": "#c2410c"}]})


if __name__ == "__main__":
    import time
    t = time.time()
    R, race, wx = export_season()
    print("season %.0fs" % (time.time() - t))
    for kp in R.kpis:
        print(f"  {kp['label']:<44} {kp['value']:.2f} {kp['unit']}")
    Rr = export_race(race, wx)
    for kp in Rr.kpis:
        print(f"  {kp['label']:<44} {kp['value']:.2f} {kp['unit']}")
