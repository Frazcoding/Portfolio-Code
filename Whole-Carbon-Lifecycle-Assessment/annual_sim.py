"""Hourly operational year (London 2023) for each WLC scenario + 60-year lifecycle from the project engine.

Operational model (per scenario, from src/config.py fabric and plant parameters):
  zone       ISO 13790 5R1C, 7,500 m2 GIA office: H_tr_w = U_window x 1,368 m2, H_op = U_wall x 1,672 + U_roof x 1,500
             + 0.25 x 1,500 ground; infiltration from q50 / 20; mechanical ventilation 1.4 l/s/m2 occupied with MVHR
  gains      occupancy schedule (people 8, lighting 6 (LED) / 10 (baseline), small power 10 W/m2), solar through glazing
             by orientation (g = 0.62 baseline, 0.40 new) with Hay-Davies transposition
  plant      baseline: gas boiler (eta 0.92) + R410A chiller; others: air-source heat pump (R290 or R32, CoolProp
             single-stage map, weather-compensated 45 C flow) and reversible cooling scaled to the configured SEER
  PV         roof array sized so the annual yield matches the scenario's configured kWh/m2.yr
  carbon     real 2023 GB hourly intensity; gas 182.9 g/kWh
Lifecycle: src/carbon_calculator.py (A1-A5, B1 refrigerant, B4 replacements, B6 DESNZ central trajectory, C1-C4).
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
from simcore.output import Results  # noqa: E402
from simcore.perfmap import PerfMap  # noqa: E402
from src.config import SCENARIO_CONFIGS, BuildingArchetype  # noqa: E402

A = BuildingArchetype()
CORE = HERE.parent / "_legacy" / "simcore"
AX = {"T_air": [-10, -5, -2, 0, 2, 5, 8, 11, 15, 20], "RH": [50, 90], "T_w_in": [25, 30, 35, 40, 45], "f": [30, 50, 70, 90],
      "ua": [0.75, 1.0]}
HP = {"R290": dict(fluid="Propane"), "R32": dict(fluid="R32")}
MODULE = dict(comp=dict(disp_m3h=36.0, f_nom=50, f_min=25, f_max=110, eta_is_max=0.70, pr_opt=3.0, k_pr=0.09, k_f=0.08, f_opt=60,
                        clearance=0.03, n_poly=1.12, leak=0.03, eta_motor=0.93, eta_inv=0.97, q_loss_frac=0.05),
              m_air_nom=3.4, UA_e=7000.0, fan_min=0.35, W_fan_max=1100.0, m_w=1.3, UA_c=6500.0, SH=5.0, SC=3.0, suction_gain=1.0,
              dp_suc=0.05e5, dp_evap=0.10e5, dp_cond=0.08e5, dp_dis=0.06e5, T_dis_max=125.0)


def hp_map(refr):
    p = dict(MODULE, **HP[refr])
    o, _ = cycles.solve(p, dict(T_air=5, RH=80, T_w_in=35, f=50, ua=1.0))
    return PerfMap(f"wlc_ashp_{refr}", CORE / "cycles.py", "solve", p, AX, list(o), deps=[CORE / "hx.py", CORE / "thermo.py"])


def simulate(key, maps):
    cfg = SCENARIO_CONFIGS[key]
    wx = weather.load("london")
    gr = grid.load()
    n = len(wx)
    lat, lon = weather.SITES["london"][:2]
    zen, az, doy = solar.position(wx["time"], lat, lon)
    ghi, dni, dhi = wx.ghi.to_numpy(), wx.dni.to_numpy(), wx.dhi.to_numpy()
    g_val = 0.62 if key == "scenario_1" else 0.40
    phi_sol = np.zeros(n)
    for saz in (0, 90, 180, 270):
        b, d, gg, aoi = solar.poa(ghi, dni, dhi, zen, az, doy, 90, saz)
        phi_sol += A.glazed_facade_area / 4 * g_val * 0.75 * 0.85 * (b * solar.iam_ashrae(aoi) + d + gg)
    hl = wx.hour_local.to_numpy()
    work = wx.is_workday.to_numpy()
    occ = work & (hl >= 8) & (hl < 18)
    light_wm2 = 10.0 if key == "scenario_1" else 6.0
    gains = np.where(occ, (8 + light_wm2 + 10) * A.gia, 2.5 * A.gia)
    H_w = cfg.u_window * A.glazed_facade_area
    H_op = cfg.u_wall * A.opaque_facade_area + cfg.u_roof * A.roof_area + 0.25 * A.ground_slab_area
    vol = A.gia * 3.2
    H_inf = 0.34 * (cfg.q50_air_permeability / 20.0) * vol * 0.6
    H_mech = 1.2 * 1006 * (1.4e-3 * A.gia) * (1 - cfg.mvhr_efficiency)
    Cm = 165e3 if key in ("scenario_1", "scenario_2", "scenario_3") else 110e3
    zone = Zone5R1C(A_f=A.gia, H_tr_w=H_w, H_tr_op=H_op, C_m_per_m2=Cm, theta_m=20.0)
    # PV sized to the configured specific yield
    P1 = np.zeros(n)
    b, d, gg, aoi = solar.poa(ghi, dni, dhi, zen, az, doy, 10, 180)
    P1, Tc, G = solar.pv_dc(b, d, gg, aoi, wx.T_amb.to_numpy(), wx.wind10.to_numpy(), 1000.0)
    pv_kwp = cfg.pv_generation_kwh_per_m2_yr * A.gia / max(P1.sum() / 1000 * 0.965, 1e-9)
    pv = P1 * pv_kwp * 0.965 / 1000                                            # kW AC
    refr = "R290" if cfg.refrigerant_type == "R290" else ("R32" if cfg.refrigerant_type == "R32" else None)
    pm = maps.get(refr)
    names = ["T_room", "T_op", "Q_heat", "Q_cool", "W_heat", "W_cool", "gas", "cop_h", "eer_c", "W_light", "W_power", "W_fans", "W_other",
             "W_total", "pv", "grid_imp", "grid_exp", "T_flow", "co2", "cost", "occ", "lights_on", "unmet_h", "unmet_c", "Te", "Tc_cond"]
    H = {k: np.zeros(n) for k in names}
    Ta_all = wx.T_amb.to_numpy()
    rh = wx.RH.to_numpy()
    T_room = 20.0
    for i in range(n):
        Ta = Ta_all[i]
        o = occ[i]
        sh = 21.0 if (work[i] and 6 <= hl[i] < 18) else 16.0
        sc_ = 24.0 if o else 30.0
        H_ve = H_inf + (H_mech if o else 0.0)
        purge = False
        if cfg.mvhr_efficiency > 0 and T_room > 22.0 and Ta < T_room - 2.0:
            if o:
                H_ve = H_inf + 1.2 * 1006 * (1.4e-3 * A.gia) * 1.6          # summer bypass + boost (free cooling)
            elif T_room > 23.0 and Ta < T_room - 3.0 and 0 <= hl[i] < 6:
                H_ve = H_inf + 0.34 * 2.0 * vol                              # night purge 2 ACH
                purge = True
        Q, _ = zone.demand(Ta, H_ve, gains[i], phi_sol[i], sh, sc_)
        Qh, Qc = max(Q, 0.0), max(-Q, 0.0)
        z = zone.step(Ta, H_ve, gains[i], phi_sol[i], Q)
        T_room = z["T_air"]
        # plant
        W_h = W_c = gas = 0.0
        cop = np.nan
        T_flow = 45.0 - 0.6 * max(0.0, Ta - 0.0) if Qh > 0 else np.nan
        if Qh > 0:
            if pm is None:
                gas = Qh / cfg.heating_cop
            else:
                n_mod = max(1, math.ceil(Qh / 35e3))
                q_mod = Qh / n_mod
                qs = []
                for fs in AX["f"]:
                    v, ok = pm(T_air=Ta, RH=rh[i], T_w_in=max(25.0, T_flow - 7), f=fs, ua=0.9)
                    qs.append((pm.get(v, "Q_c") * 1e3, v))
                qq = np.array([q for q, _ in qs])
                f = float(np.interp(q_mod, qq, AX["f"]))
                v, ok = pm(T_air=Ta, RH=rh[i], T_w_in=max(25.0, T_flow - 7), f=f, ua=0.9)
                cop = pm.get(v, "COP") * (cfg.heating_cop / 3.6) ** 0.0
                W_h = Qh / cop
                H["Te"][i], H["Tc_cond"][i] = pm.get(v, "Te"), pm.get(v, "Tc")
        if Qc > 0:
            carnot = (7 + 273.15) / max(5.0, (Ta + 10) - 7)
            eer = min(9.0, 0.42 * carnot) * cfg.cooling_seer / 4.2
            W_c = Qc / eer
            H["eer_c"][i] = eer
        W_light = (light_wm2 if o else 0.6) * A.gia * (0.55 if ghi[i] > 300 and o else 1.0)
        W_power = (10.0 if o else 2.5) * A.gia
        # supply/extract fans: SFP 1.8 W/(l/s) with MVHR, 1.2 without; night purge at 2 ACH and SFP 1.2
        W_fans = (1.4e-3 * A.gia * (1.8 if cfg.mvhr_efficiency > 0 else 1.2) * 1000 if o else 0.0)             + (2.0 * vol / 3600 * 1000 * 1.2 if purge else 0.0)
        W_other = 1.5 * A.gia
        W = W_h + W_c + W_light + W_power + W_fans + W_other
        imp = max(0.0, W / 1e3 - pv[i])
        exp_ = max(0.0, pv[i] - W / 1e3)
        H["T_room"][i], H["T_op"][i] = z["T_air"], z["T_op"]
        H["Q_heat"][i], H["Q_cool"][i] = Qh / 1e3, Qc / 1e3
        H["W_heat"][i], H["W_cool"][i], H["gas"][i] = W_h / 1e3, W_c / 1e3, gas / 1e3
        H["cop_h"][i] = cop
        H["W_light"][i], H["W_power"][i], H["W_fans"][i], H["W_other"][i] = W_light / 1e3, W_power / 1e3, W_fans / 1e3, W_other / 1e3
        H["W_total"][i] = W / 1e3
        H["pv"][i], H["grid_imp"][i], H["grid_exp"][i] = pv[i], imp, exp_
        H["T_flow"][i] = T_flow
        H["co2"][i] = imp * gr.ci.iat[i] / 1000 + gas / 1e3 * grid.GAS_CARBON_G_KWH / 1000
        H["cost"][i] = imp * gr.price.iat[i] / 100 + gas / 1e3 * 7.5 / 100 - exp_ * 0.05
        H["occ"][i] = float(o)
        H["lights_on"][i] = float(o and ghi[i] < 150)
        H["unmet_h"][i] = max(0.0, 20.0 - z["T_air"]) if o else 0.0
        H["unmet_c"][i] = max(0.0, z["T_air"] - 25.0) if o else 0.0
    return cfg, wx, gr, H, dict(pv_kwp=pv_kwp, phi_sol=phi_sol, H_w=H_w, H_op=H_op, H_inf=H_inf, H_mech=H_mech)


def export_year(key, maps, idx):
    cfg, wx, gr, H, info = simulate(key, maps)
    n = len(wx)
    R = Results(f"{key}_year", f"{cfg.short_name} · operational year (London 2023, hourly)", n)
    g = "Weather & grid"
    R.ch("T_amb", wx.T_amb, "°C", "Outdoor temperature", g, 1)
    R.ch("ghi", wx.ghi, "W/m²", "Global horizontal irradiance", g, 0)
    R.ch("ci", gr.ci, "gCO₂/kWh", "GB grid carbon intensity", g, 0)
    R.ch("price", gr.price, "p/kWh", "Agile price", g, 2)
    g = "Building"
    for k, u, lbl, d in [("T_room", "°C", "Indoor air temperature", 2), ("T_op", "°C", "Operative temperature", 2),
                         ("Q_heat", "kW", "Heating load", 1), ("Q_cool", "kW", "Cooling load", 1), ("occ", "–", "Occupied", 0),
                         ("lights_on", "–", "Electric lighting on (dark & occupied)", 0), ("unmet_h", "K", "Heating deficit (occupied)", 2),
                         ("unmet_c", "K", "Overheating above 25 °C (occupied)", 2)]:
        R.ch(k, H[k], u, lbl, g, d)
    R.ch("phi_sol", info["phi_sol"] / 1e3, "kW", "Solar gains through glazing", g, 1)
    g = "Plant"
    R.ch("W_heat", H["W_heat"], "kW", "Heat pump electricity", g, 1)
    R.ch("gas", H["gas"], "kW", "Boiler gas input", g, 1)
    R.ch("W_cool", H["W_cool"], "kW", "Cooling electricity", g, 1)
    R.ch("cop_h", H["cop_h"], "–", "Heat pump COP (hour)", g, 2)
    R.ch("eer_c", np.where(H["Q_cool"] > 0, H["eer_c"], np.nan), "–", "Cooling EER (hour)", g, 2)
    R.ch("T_flow", H["T_flow"], "°C", "Heating flow temperature", g, 1)
    R.ch("Te", np.where(H["W_heat"] > 0, H["Te"], np.nan), "°C", "HP evaporating temperature", g, 1)
    R.ch("Tc_cond", np.where(H["W_heat"] > 0, H["Tc_cond"], np.nan), "°C", "HP condensing temperature", g, 1)
    g = "Electricity"
    for k, lbl in [("W_light", "Lighting"), ("W_power", "Small power"), ("W_fans", "Ventilation fans"), ("W_other", "Lifts, servers, misc."),
                   ("W_total", "Total demand"), ("pv", "Roof PV (AC)"), ("grid_imp", "Grid import"), ("grid_exp", "Export")]:
        R.ch(k, H[k], "kW", lbl, g, 1)
    R.ch("co2", H["co2"], "kg/h", "Operational CO₂", "Carbon & cost", 1)
    R.ch("cum_co2", np.cumsum(H["co2"]) / 1000, "t", "Cumulative operational CO₂", "Carbon & cost", 2)
    R.ch("cost", H["cost"], "£/h", "Energy cost", "Carbon & cost", 2)
    R.ch("scenario_idx", np.full(n, float(idx)), "–", "Scenario index", "Control", 0)
    R.ch("is_lifecycle", np.zeros(n), "–", "Lifecycle view", "Control", 0)
    R.start = int(np.argmax(np.where(np.arange(n) < 24 * 45, H["Q_heat"], -1)))
    k = R.kpi
    k("Heating demand", H["Q_heat"].sum() / A.gia, "kWh/m²", "Demand", 1)
    k("Cooling demand", H["Q_cool"].sum() / A.gia, "kWh/m²", "Demand", 1)
    k("Peak heating load", H["Q_heat"].max(), "kW", "Demand", 0)
    k("Peak cooling load", H["Q_cool"].max(), "kW", "Demand", 0)
    k("Electricity EUI (gross)", H["W_total"].sum() / A.gia, "kWh/m²", "Energy", 1)
    k("Gas EUI", H["gas"].sum() / A.gia, "kWh/m²", "Energy", 1)
    k("PV yield", H["pv"].sum() / A.gia, "kWh/m²", "Energy", 1)
    k("PV array", info["pv_kwp"], "kWp", "Energy", 0)
    k("Net EUI", (H["gas"].sum() + H["grid_imp"].sum()) / A.gia, "kWh/m²", "Energy", 1)
    k("Configured net EUI (engine)", SCENARIO_CONFIGS[key].net_operational_eui, "kWh/m²", "Energy", 1)
    if np.isfinite(H["cop_h"]).any():
        k("Seasonal heating COP", H["Q_heat"].sum() / max(H["W_heat"].sum(), 1e-9), "–", "Plant", 2)
    k("Seasonal cooling EER", H["Q_cool"].sum() / max(H["W_cool"].sum(), 1e-9), "–", "Plant", 2)
    k("Operational CO₂ 2023", H["co2"].sum() / 1000, "t", "Carbon", 1)
    k("Operational CO₂ intensity", H["co2"].sum() / A.gia, "kgCO₂/m²", "Carbon", 2)
    k("Energy cost 2023", H["cost"].sum() / 1000, "k£", "Cost", 1)
    k("Occupied hours < 20 °C", float((H["unmet_h"] > 0).sum()), "h", "Comfort", 0)
    k("Occupied hours > 25 °C", float((H["unmet_c"] > 0).sum()), "h", "Comfort", 0)
    k("Fabric heat loss coefficient", (info["H_w"] + info["H_op"] + info["H_inf"]) / 1000, "kW/K", "Fabric", 2)
    R.diagrams.append({"type": "bars", "title": "Electricity now (kW)", "items": [
        {"key": kk, "label": lb} for kk, lb in [("W_heat", "Heating"), ("W_cool", "Cooling"), ("W_light", "Lighting"), ("W_power", "Small power"),
                                                ("W_fans", "Fans"), ("pv", "PV")]]})
    return R, cfg, H


def export_lifecycle():
    from src.carbon_calculator import WholeLifeCarbonEngine
    from src.inventory import BuildingInventory
    eng = WholeLifeCarbonEngine(archetype=A)
    inv = BuildingInventory(archetype=A)
    n = 61
    R = Results("lifecycle", "60-year whole-life carbon · all four scenarios (engine)", n, t0=2026, dt=1.0, time_unit="years")
    for j, (key, cfg) in enumerate(SCENARIO_CONFIGS.items(), 1):
        res = eng.calculate_scenario(cfg)
        b6 = np.r_[0.0, np.asarray(res.b6_annual_timeseries["desnz_central"]) / 1000]
        upfront = res.a1_a5_upfront / 1000
        b1 = res.b1_refrigerant_leakage / 60 / 1000
        cum = upfront + np.cumsum(b6 + np.r_[0.0, np.full(60, b1)])
        g = cfg.short_name
        R.ch(f"cum_s{j}", cum, "tCO₂e", f"{g} · cumulative A1-A5 + B1 + B6", "Cumulative carbon", 0)
        R.ch(f"op_s{j}", b6, "tCO₂e/yr", f"{g} · annual operational B6", "Annual operational", 1)
        R.kpi(f"{g} · upfront A1-A5", upfront, "tCO₂e", "Upfront", 0)
        R.kpi(f"{g} · 60-yr WLC (DESNZ central)", res.total_wlc_per_m2("desnz_central") * A.gia / 1000, "tCO₂e", "Whole life", 0)
        R.kpi(f"{g} · WLC intensity", res.total_wlc_per_m2("desnz_central"), "kgCO₂e/m²", "Whole life", 0)
        R.kpi(f"{g} · installed plant", inv.calculate_peak_thermal_load(cfg)["installed_capacity_kw"], "kW", "Plant", 0)
    R.ch("scenario_idx", np.full(n, 2.0), "–", "Scenario index (deep retrofit shown)", "Control", 0)
    R.ch("is_lifecycle", np.ones(n), "–", "Lifecycle view", "Control", 0)
    return R


if __name__ == "__main__":
    import time
    maps = {"R290": hp_map("R290"), "R32": hp_map("R32")}
    for j, key in enumerate(SCENARIO_CONFIGS, 1):
        t = time.time()
        R, cfg, H = export_year(key, maps, j)
        print(key, cfg.short_name, "%.0fs" % (time.time() - t))
        for kp in R.kpis:
            print(f"  {kp['label']:<36} {kp['value']:.2f} {kp['unit']}")
    L = export_lifecycle()
    for kp in L.kpis:
        print(f"  {kp['label']:<44} {kp['value']:.1f} {kp['unit']}")
