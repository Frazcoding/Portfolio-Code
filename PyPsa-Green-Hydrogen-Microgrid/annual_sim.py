"""Annual (8760 h) island wind-hydrogen microgrid simulation (Isle of Lewis, ERA5 2023).

Wind farm   3 x 6.2 MW turbines (170 m rotor, 115 m hub): ERA5 100 m wind sheared to hub (alpha 0.14),
            air-density correction, manufacturer-style power curve (cut-in 3, rated 11.5, cut-out 25 m/s
            with high-wind ride-through ramp), 6 % wake + 3 % availability losses, rotor speed
Island      demand 3.0-6.5 MW (diurnal, weekly, heating-driven seasonal), 5 MW subsea interconnector
Dispatch    wind -> island demand -> electrolysers (min 10 % per stack) -> export -> curtailment;
            deficit -> import -> diesel station (unserved)
PEM         4 x 2 MW stacks (412 cells x 1250 cm2): reversible voltage (T, P), Butler-Volmer activation,
            Nafion 115 ohmic loss (Springer conductivity), mass-transport term, Faradaic crossover,
            lumped stack thermal model (cooling to 65 C), 4 uV/h degradation, 3.5 % rectifier, BOP
Compression 30 -> 350 bar, two intercooled stages (CoolProp hydrogen), dryer and aftercooler
Storage     188.5 m3 at up to 350 bar; pressure from real-gas density and gas temperature
Ferry       nightly bunkering of up to 1.2 t (26.7 kg/min cascade + booster); shortfall burned as MGO
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

F_C = 96485.0
R_G = 8.314
HHV = 39.41          # kWh/kg
LHV = 33.33
SCENARIOS = {
    "base": dict(name="Lewis 2023 · 3 × 6.2 MW wind · 8 MW PEM · 5 MW interconnector", badge="Base case", n_wtg=3, stacks=4, cable=5.0),
    "weak_grid": dict(name="Lewis 2023 · same plant · 2 MW interconnector (constrained grid)", badge="2 MW cable", n_wtg=3, stacks=4, cable=2.0),
    "half_pem": dict(name="Lewis 2023 · 3 × 6.2 MW wind · 4 MW PEM · 5 MW interconnector", badge="4 MW PEM", n_wtg=3, stacks=2, cable=5.0),
}
N_CELL, A_CELL = 412, 1250.0          # cells per stack, cm2
P_STACK = 2.0e6
V_STORE = 188.5
P_MAX, P_MIN = 350e5, 30e5
FERRY_KG = 1200.0


def power_curve(v):
    """Per-unit power of a 6.2 MW class turbine vs hub wind speed (air density 1.225)."""
    v = np.asarray(v, float)
    p = np.clip((v ** 3 - 3.0 ** 3) / (11.5 ** 3 - 3.0 ** 3), 0, 1)
    p = np.where(v < 3.0, 0.0, p)
    p = np.where((v > 22.0) & (v <= 27.0), 1 - (v - 22.0) / 5.0 * 0.8, p)      # high-wind ride-through ramp
    return np.where(v > 27.0, 0.0, p)


def rotor_rpm(v):
    return np.where(v < 3.0, 0.0, np.clip(4.5 + (10.6 - 4.5) * (v - 3.0) / 6.5, 4.5, 10.6))


def cell_voltage(j, T, deg):
    """PEM cell voltage at current density j [A/cm2] and temperature T [K]."""
    E0 = 1.229 - 0.9e-3 * (T - 298.15) + R_G * T / (2 * F_C) * math.log(30.0 * math.sqrt(1.0) / 1.0)
    j0 = 1.0e-7 * math.exp(-52000 / R_G * (1 / T - 1 / 353.15)) * 50      # Ir anode, Arrhenius
    V_act = R_G * T / (0.5 * 2 * F_C) * math.asinh(j / (2 * j0))
    lam = 21.0
    sigma = (0.005139 * lam - 0.00326) * math.exp(1268 * (1 / 303.0 - 1 / T))
    R_ohm = 0.0127 / sigma + 0.035                                          # Nafion 115 + contact, ohm cm2
    V_ohm = j * R_ohm
    V_mt = 0.06 * (j / 2.4) ** 4
    return E0 + V_act + V_ohm + V_mt + deg, dict(E0=E0, V_act=V_act, V_ohm=V_ohm, V_mt=V_mt)


def solve_j(P_cell, T, deg):
    lo, hi = 1e-4, 3.0
    for _ in range(40):
        j = 0.5 * (lo + hi)
        V, _ = cell_voltage(j, T, deg)
        if V * j * A_CELL > P_cell:
            hi = j
        else:
            lo = j
    return j


def stack_temp(T, q, Ta, UA, C=6.0e6, dt=3600.0, T_set=338.15, K_cool=4.0e5):
    """Backward-Euler stack temperature; the glycol cooling loop engages above the 65 C setpoint."""
    Tn = (T * C / dt + q + UA * Ta) / (C / dt + UA)
    if Tn > T_set:
        Tn = (T * C / dt + q + UA * Ta + K_cool * T_set) / (C / dt + UA + K_cool)
    return Tn


def store_pressure(fl, M, T):
    """Real-gas pressure of the stored hydrogen from density and temperature (CoolProp)."""
    import CoolProp.CoolProp as CPm
    fl.AS.update(CPm.DmassT_INPUTS, max(M, 1.0) / V_STORE, T)
    return fl.AS.p()


def simulate(key):
    sc = SCENARIOS[key]
    wx = weather.load("stornoway", marine=True)
    n = len(wx)
    H2 = Fluid("Hydrogen")
    T_amb = wx.T_amb.to_numpy()
    rho = wx.rho_air.to_numpy()
    v100 = wx.wind100.to_numpy()
    v_hub = v100 * (115.0 / 100.0) ** 0.14
    v_eq = v_hub * (rho / 1.225) ** (1 / 3)
    rng = np.random.default_rng(21)
    wtg = []
    for k in range(sc["n_wtg"]):
        jitter = 1 + 0.04 * rng.standard_normal(n)                          # spatial variability across the farm
        pu = power_curve(v_eq * jitter)
        avail = rng.random(n) > 0.03
        wtg.append(6.2 * pu * 0.94 * avail)
    P_wind = np.sum(wtg, axis=0)
    hl = wx.hour_local.to_numpy()
    wd = wx.weekday.to_numpy()
    diurnal = np.array([.72, .68, .66, .65, .66, .72, .85, .97, 1.0, .98, .96, .95, .94, .93, .93, .96, 1.04, 1.12, 1.14, 1.1, 1.02, .93, .84, .77])
    demand = (3.3 + 0.11 * np.maximum(0, 15.5 - T_amb)) * diurnal[hl] * np.where(wd >= 5, 0.94, 1.0)
    stacks = sc["stacks"]
    T_st = np.full(stacks, 30.0 + 273.15)
    run_h = np.zeros(stacks)
    M = V_STORE * 9.0                                                    # start with ~1.7 t (~130 bar)
    T_gas = 288.15
    ferry_soc = 0.3
    names = ["P_wind", "demand", "P_ely", "P_bop", "P_comp", "export", "import_", "curtail", "unserved", "h2_rate", "h2_ferry",
             "mgo_l", "store_P", "store_T", "store_kg", "ferry_soc", "water", "o2", "q_heat", "spec_e", "eta_hhv", "n_on",
             "j_mean", "V_cell", "T_stack", "bunker", "V_E0", "V_act", "V_ohm", "V_mt", "eta_F"]
    H = {k: np.zeros(n) for k in names}
    per_stack = {f"j{s}": np.zeros(n) for s in range(stacks)}
    per_stack.update({f"Tst{s}": np.zeros(n) for s in range(stacks)})
    comp_sp = {f"C{k}_{f}": np.zeros(n) for k in range(1, 9) for f in ("T", "P", "h", "s", "m")}
    for i in range(n):
        surplus = P_wind[i] - demand[i]
        deg = 4e-6 * run_h.mean()
        # storage headroom limits electrolysis
        P_now = store_pressure(H2, M, T_gas)
        headroom_kg = max(0.0, V_STORE * H2.PT(P_MAX, T_gas).rho - M)
        P_ely_avail = max(0.0, surplus) if surplus > 0 else 0.0
        # electrolyser staging: stacks on in order, each 10-100 %
        P_target = min(P_ely_avail * 1e6, stacks * P_STACK)
        max_by_store = headroom_kg / 1.0 * 55.0e3                            # W that would fill the store in 1 h
        P_target = min(P_target, max_by_store)
        n_on = int(min(stacks, math.ceil(P_target / P_STACK - 1e-9))) if P_target > 0.1 * P_STACK else 0
        h2 = 0.0
        P_dc = 0.0
        q_heat = 0.0
        js, Vs = [], []
        parts = dict(E0=0, V_act=0, V_ohm=0, V_mt=0)
        etaF_acc = 0.0
        for s in range(stacks):
            on = s < n_on
            if on:
                Ps = P_target / n_on
                j = solve_j(Ps / N_CELL, T_st[s], deg)
                V, pr = cell_voltage(j, T_st[s], deg)
                I = j * A_CELL
                etaF = max(0.5, 1 - 0.003 / max(j, 1e-3) * 30 / 30)
                h2_s = N_CELL * I / (2 * F_C) * 2.016e-3 * etaF * 3600          # kg/h
                q = (V - 1.481) * I * N_CELL
                T_st[s] = stack_temp(T_st[s], q, T_amb[i] + 273.15, 4500.0)
                run_h[s] += 1
                h2 += h2_s
                P_dc += Ps
                q_heat += max(q, 0)
                js.append(j)
                Vs.append(V)
                for kk in parts:
                    parts[kk] += pr[kk]
                etaF_acc += etaF
                per_stack[f"j{s}"][i] = j
            else:
                T_st[s] = stack_temp(T_st[s], 0.0, T_amb[i] + 273.15, 2500.0)
            per_stack[f"Tst{s}"][i] = T_st[s] - 273.15
        P_rect = P_dc / 0.965
        P_bop = (0.05 * P_dc + 25e3 * n_on) if n_on else 8e3 * stacks
        # compression 30 -> 350 bar in two intercooled stages
        P_comp = 0.0
        m = h2 / 3600
        pr_stage = math.sqrt(P_MAX / P_MIN)
        st1 = H2.PT(30e5, 333.15)                     # stack outlet (wet)
        st2 = H2.PT(29.5e5, 303.15)                   # after dryer
        p_mid = 29.5e5 * pr_stage
        st3s = H2.PS(p_mid, st2.s)
        st3 = H2.PH(p_mid, st2.h + (st3s.h - st2.h) / 0.72)
        st4 = H2.PT(p_mid - 1e5, 308.15)
        p_out = max(P_now, p_mid * 1.05) + 5e5
        st5s = H2.PS(p_out, st4.s)
        st5 = H2.PH(p_out, st4.h + (st5s.h - st4.h) / 0.72)
        st6 = H2.PT(p_out - 2e5, 308.15)
        if m > 0:
            P_comp = m * ((st3.h - st2.h) + (st5.h - st4.h)) / 0.93
        M += h2
        # bunkering at 18:00 if the ferry needs fuel
        bunk = 0.0
        if hl[i] == 18:
            need = FERRY_KG * (1 - ferry_soc) / 0.85
            min_kg = V_STORE * H2.PT(P_MIN + 20e5, T_gas).rho
            bunk = max(0.0, min(need, M - min_kg, 26.7 * 60))
            M -= bunk
            ferry_soc = min(1.0, ferry_soc + bunk * 0.85 / FERRY_KG)
            short = max(0.0, need - bunk)
            H["mgo_l"][i] = short * LHV * 0.5 / 0.40 / 10.0                  # MGO litres equivalent (FC 50 % vs engine 40 %)
        # ferry uses ~2 crossings per day
        if hl[i] in (8, 13):
            ferry_soc = max(0.0, ferry_soc - 0.425)
        # gas temperature relaxes to ambient; filling heats it
        T_gas += (T_amb[i] + 273.15 - T_gas) / 30.0 + (h2 / max(M, 1)) * 12.0
        P_now = store_pressure(H2, M, T_gas)
        # grid balance
        load_total = demand[i] + (P_rect + P_bop + P_comp) / 1e6
        bal = P_wind[i] - load_total
        exp_ = min(max(bal, 0.0), sc["cable"])
        cur = max(0.0, bal - exp_)
        imp = min(max(-bal, 0.0), sc["cable"])
        uns = max(0.0, -bal - imp)
        H["P_wind"][i], H["demand"][i], H["P_ely"][i], H["P_bop"][i], H["P_comp"][i] = P_wind[i], demand[i], P_rect / 1e6, P_bop / 1e6, P_comp / 1e6
        H["export"][i], H["import_"][i], H["curtail"][i], H["unserved"][i] = exp_, imp, cur, uns
        H["h2_rate"][i], H["bunker"][i] = h2, bunk
        H["store_P"][i], H["store_T"][i], H["store_kg"][i] = P_now / 1e5, T_gas - 273.15, M
        H["ferry_soc"][i] = ferry_soc * 100
        H["water"][i] = h2 * 9.0 * 1.12
        H["o2"][i] = h2 * 7.94
        H["q_heat"][i] = q_heat / 1e6
        H["spec_e"][i] = (P_rect + P_bop + P_comp) / 1e3 / h2 if h2 > 0 else np.nan
        H["eta_hhv"][i] = h2 * HHV / ((P_rect + P_bop) / 1e3) * 100 if h2 > 0 else np.nan
        H["n_on"][i] = n_on
        H["j_mean"][i] = np.mean(js) if js else 0.0
        H["V_cell"][i] = np.mean(Vs) if Vs else np.nan
        H["T_stack"][i] = (np.mean(T_st) - 273.15)
        for kk in parts:
            H[{"E0": "V_E0", "V_act": "V_act", "V_ohm": "V_ohm", "V_mt": "V_mt"}[kk]][i] = parts[kk] / n_on if n_on else np.nan
        H["eta_F"][i] = etaF_acc / n_on * 100 if n_on else np.nan
        for k, st, mm in ((1, st1, m), (2, st2, m), (3, st3, m), (4, st4, m), (5, st5, m), (6, st6, m)):
            comp_sp[f"C{k}_T"][i], comp_sp[f"C{k}_P"][i] = st.Tc, st.P / 1e5
            comp_sp[f"C{k}_h"][i], comp_sp[f"C{k}_s"][i], comp_sp[f"C{k}_m"][i] = st.h / 1e3, st.s / 1e3, mm
        stS = H2.PT(max(P_now, 2e5), T_gas)
        comp_sp["C7_T"][i], comp_sp["C7_P"][i], comp_sp["C7_h"][i], comp_sp["C7_s"][i] = stS.Tc, stS.P / 1e5, stS.h / 1e3, stS.s / 1e3
        comp_sp["C7_m"][i] = m
        comp_sp["C8_T"][i], comp_sp["C8_P"][i], comp_sp["C8_h"][i], comp_sp["C8_s"][i] = stS.Tc, stS.P / 1e5, stS.h / 1e3, stS.s / 1e3
        comp_sp["C8_m"][i] = bunk / 3600
    return sc, wx, H, wtg, v_hub, per_stack, comp_sp


def export(key):
    sc, wx, H, wtg, v_hub, per_stack, comp_sp = simulate(key)
    n = len(wx)
    R = Results(key, sc["name"], n)
    g = "Weather & sea"
    R.ch("T_amb", wx.T_amb, "°C", "Air temperature", g, 1)
    R.ch("wind100", wx.wind100, "m/s", "ERA5 100 m wind", g, 1)
    R.ch("v_hub", v_hub, "m/s", "Hub-height wind (115 m)", g, 1)
    R.ch("wdir", wx.wdir100, "°", "Wind direction", g, 0)
    R.ch("rho_air", wx.rho_air, "kg/m³", "Air density", g, 3)
    R.ch("ghi", wx.ghi, "W/m²", "Global horizontal irradiance", g, 0)
    if "wave_h" in wx:
        R.ch("wave_h", wx.wave_h, "m", "Significant wave height", g, 2)
        R.ch("T_sea", wx.T_sea, "°C", "Sea surface temperature", g, 1)
    g = "Wind farm"
    for k, w in enumerate(wtg):
        R.ch(f"wtg{k + 1}", w, "MW", f"Turbine {k + 1} output", g, 2)
        R.ch(f"rpm{k + 1}", rotor_rpm(v_hub) * (w > 0.01), "rpm", f"Turbine {k + 1} rotor speed", g, 1)
    R.ch("P_wind", H["P_wind"], "MW", "Wind farm output", g, 2)
    R.ch("cf", H["P_wind"] / (6.2 * len(wtg)) * 100, "%", "Capacity factor (hour)", g, 1)
    g = "Island grid"
    R.ch("demand", H["demand"], "MW", "Island demand", g, 2)
    R.ch("export", H["export"], "MW", "Export to mainland", g, 2)
    R.ch("import_", H["import_"], "MW", "Import from mainland", g, 2)
    R.ch("curtail", H["curtail"], "MW", "Curtailed wind", g, 2)
    R.ch("unserved", H["unserved"], "MW", "Diesel station dispatch", g, 2)
    g = "PEM electrolysis"
    R.ch("P_ely", H["P_ely"], "MW", "Electrolyser AC power", g, 2)
    R.ch("P_bop", H["P_bop"], "MW", "Balance of plant", g, 3)
    R.ch("n_on", H["n_on"], "–", "Stacks running", g, 0)
    R.ch("j_mean", H["j_mean"], "A/cm²", "Mean current density", g, 3)
    R.ch("V_cell", H["V_cell"], "V", "Mean cell voltage", g, 3)
    R.ch("V_E0", H["V_E0"], "V", "Reversible voltage", g, 3)
    R.ch("V_act", H["V_act"], "V", "Activation overpotential", g, 3)
    R.ch("V_ohm", H["V_ohm"], "V", "Ohmic overpotential", g, 3)
    R.ch("V_mt", H["V_mt"], "V", "Mass-transport overpotential", g, 4)
    R.ch("eta_F", H["eta_F"], "%", "Faradaic efficiency", g, 2)
    R.ch("T_stack", H["T_stack"], "°C", "Mean stack temperature", g, 1)
    for s in range(len([k for k in per_stack if k.startswith("j")])):
        R.ch(f"j{s + 1}", per_stack[f"j{s}"], "A/cm²", f"Stack {s + 1} current density", "Stacks", 3)
        R.ch(f"Tst{s + 1}", per_stack[f"Tst{s}"], "°C", f"Stack {s + 1} temperature", "Stacks", 1)
    R.ch("h2_rate", H["h2_rate"], "kg/h", "Hydrogen production", g, 1)
    R.ch("spec_e", H["spec_e"], "kWh/kg", "Specific energy (system)", g, 2)
    R.ch("eta_hhv", H["eta_hhv"], "%", "Efficiency (HHV, stack + BOP)", g, 1)
    R.ch("q_heat", H["q_heat"], "MW", "Recoverable stack heat", g, 3)
    R.ch("water", H["water"], "L/h", "Deionised water consumption", g, 0)
    R.ch("o2", H["o2"], "kg/h", "Oxygen co-product", g, 0)
    names = ["Stack outlet (wet)", "After dryer", "Stage 1 discharge", "After intercooler", "Stage 2 discharge", "After aftercooler",
             "Storage vessel gas", "Bunkering to ferry"]
    for k in range(1, 9):
        R.state_point(f"C{k}", names[k - 1], "Hydrogen train", "Hydrogen",
                      {f: comp_sp[f"C{k}_{f}"] for f in ("T", "P", "h", "s", "m")})
    g = "Compression & storage"
    R.ch("P_comp", H["P_comp"], "MW", "Compressor power", g, 3)
    R.ch("store_P", H["store_P"], "bar", "Storage pressure", g, 1)
    R.ch("store_T", H["store_T"], "°C", "Storage gas temperature", g, 1)
    R.ch("store_kg", H["store_kg"], "kg", "Hydrogen inventory", g, 0)
    R.ch("store_soc", (H["store_kg"] - H["store_kg"].min()) / max(1.0, H["store_kg"].max() - H["store_kg"].min()) * 100, "%",
         "Inventory (relative)", g, 0)
    g = "Ferry"
    R.ch("bunker", H["bunker"], "kg/h", "Hydrogen bunkered", g, 0)
    R.ch("ferry_soc", H["ferry_soc"], "%", "Ferry tank state", g, 0)
    R.ch("mgo_l", H["mgo_l"], "L", "Marine gas oil burned (shortfall)", g, 0)
    R.ch("cum_h2", np.cumsum(H["h2_rate"]) / 1000, "t", "Cumulative hydrogen", g, 1)
    R.start = int(np.argmax(np.where(np.arange(n) < 24 * 60, H["P_ely"], -1)))
    k = R.kpi
    E_w = H["P_wind"].sum()
    k("Wind generation", E_w, "MWh", "Energy", 0)
    k("Wind capacity factor", E_w / (6.2 * len(wtg) * n) * 100, "%", "Energy", 1)
    k("Island demand", H["demand"].sum(), "MWh", "Energy", 0)
    k("Electrolyser energy", H["P_ely"].sum(), "MWh", "Energy", 0)
    k("Export", H["export"].sum(), "MWh", "Energy", 0)
    k("Import", H["import_"].sum(), "MWh", "Energy", 0)
    k("Curtailment", H["curtail"].sum(), "MWh", "Energy", 0)
    k("Diesel station energy", H["unserved"].sum(), "MWh", "Energy", 1)
    k("Hydrogen produced", H["h2_rate"].sum() / 1000, "t", "Hydrogen", 1)
    k("Electrolyser capacity factor", H["P_ely"].sum() / (sc["stacks"] * 2.0 * n) * 100, "%", "Hydrogen", 1)
    k("Mean specific energy", np.nansum(H["P_ely"] + H["P_bop"] + H["P_comp"]) * 1000 / H["h2_rate"].sum(), "kWh/kg", "Hydrogen", 2)
    k("Mean cell voltage (running)", np.nanmean(H["V_cell"]), "V", "Hydrogen", 3)
    k("Stack degradation (voltage)", 4e-6 * (H["n_on"] > 0).sum() * 1000, "mV", "Hydrogen", 1)
    k("Water consumed", H["water"].sum() / 1000, "m³", "Hydrogen", 0)
    k("Recoverable heat", H["q_heat"].sum(), "MWh", "Hydrogen", 0)
    k("Hydrogen bunkered", H["bunker"].sum() / 1000, "t", "Ferry", 1)
    k("Ferry demand met by H₂", 100 * H["bunker"].sum() / (FERRY_KG / 0.85 * 365 * 0.85), "%", "Ferry", 1)
    k("MGO burned (shortfall)", H["mgo_l"].sum() / 1000, "m³", "Ferry", 1)
    co2_avoid = H["bunker"].sum() * LHV * 0.5 / 0.40 / 10.0 * 2.68 / 1000
    k("Ferry CO₂ avoided", co2_avoid, "t", "Ferry", 0)
    capex = sc["stacks"] * 2000 * 1400 + 3.5e6 + 2.5e6
    crf = 0.08 / (1 - 1.08 ** -20)
    opex = 0.03 * capex
    elec_cost = H["P_ely"].sum() * 45 + H["P_comp"].sum() * 45
    lcoh = (capex * crf + opex + elec_cost) / max(H["h2_rate"].sum(), 1)
    k("LCOH (8 % WACC, 20 yr, £45/MWh)", lcoh, "£/kg", "Economics", 2, note="indicative: £1,400/kW PEM, £3.5 M compression, £2.5 M storage")
    k("Min storage pressure", H["store_P"].min(), "bar", "Storage", 0)
    k("Max storage pressure", H["store_P"].max(), "bar", "Storage", 0)
    R.diagrams.append({"type": "bars", "title": "Cell voltage breakdown now (V)", "items": [
        {"key": "V_E0", "label": "Reversible"}, {"key": "V_act", "label": "Activation"}, {"key": "V_ohm", "label": "Ohmic"},
        {"key": "V_mt", "label": "Transport"}]})
    R.diagrams.append({"type": "profile", "title": "Hydrogen train temperature (stack → ferry)", "xLabel": "°C",
                       "series": [{"label": "T", "keys": [f"C{k}_T" for k in range(1, 9)], "color": "#c2410c"}]})
    R.diagrams.append({"type": "bars", "title": "Power balance now (MW)", "items": [
        {"key": "P_wind", "label": "Wind"}, {"key": "demand", "label": "Island"}, {"key": "P_ely", "label": "PEM"},
        {"key": "export", "label": "Export"}, {"key": "import_", "label": "Import"}, {"key": "curtail", "label": "Curtail"}]})
    return R, sc


if __name__ == "__main__":
    import time
    for key in (sys.argv[1:] or SCENARIOS):
        t = time.time()
        R, sc = export(key)
        print(key, "%.0fs" % (time.time() - t))
        for kp in R.kpis:
            print(f"  {kp['label']:<40} {kp['value']:.2f} {kp['unit']}")
