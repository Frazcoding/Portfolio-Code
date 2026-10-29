"""Annual (8760 h) simulation of industrial high-temperature heat pumps at a dairy.

Scenarios
  dairy_butane    effluent sump (30-55 C) -> 95 C process hot water, n-butane (R600) screw HTHP
  dairy_r1234zez  same duty with R1234ze(Z) (fluid comparison, same site model)
  steam_r1233     spray-dryer exhaust recovery loop (~65 C) -> 2.7 bar saturated steam, R1233zd(E)

Site model (15-minute control steps): seasonal milk intake (spring flush), shift and
weekend production pattern, twice-daily CIP, effluent generation and a 100 m3 mixed sump
with level, a stratified 80 m3 hot-water store (95/60 C) or a steam header, and a gas
boiler covering any shortfall. Every refrigerant state is a full CoolProp solution from
the cycle performance map. Real 2023 Cheshire ERA5 weather and GB grid carbon intensity.
"""
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_legacy"))  # frozen simcore v0.1.0
sys.path.insert(0, str(HERE))

from simcore import grid, weather  # noqa: E402
from simcore.hx import CP_W  # noqa: E402
from simcore.output import Results  # noqa: E402
from simcore.perfmap import PerfMap  # noqa: E402
from simcore.storage import StratifiedTank  # noqa: E402
from simcore.thermo import Fluid  # noqa: E402
from model import cycle_econ_ihx as cyc  # noqa: E402
from model.params import DAIRY_BUTANE, DAIRY_R1234ZEZ, STEAM_R1233  # noqa: E402

DT = 900.0
SUB = 4
CAPS = [0.25, 0.4, 0.55, 0.7, 0.85, 1.0]
SP_NAMES = {"1": "Evaporator outlet", "2": "Compressor suction (after IHX)", "3": "Economiser port, main flow",
            "4": "After economiser injection", "5": "Compressor discharge", "6": "Condenser outlet",
            "7": "Economiser branch (after valve)", "8": "Economiser vapour to port", "9": "Liquid after subcooler",
            "10": "Liquid after IHX", "11": "Evaporator inlet"}

SCENARIOS = {
    "dairy_butane": dict(name="Dairy effluent → 95 °C hot water · n-butane (R600) screw HTHP", badge="Dairy R600",
                         params=DAIRY_BUTANE, fluid_label="R600 n-butane", kind="water",
                         axes={"T_src_in": [25, 30, 35, 40, 45, 50, 55, 60], "T_sink_in": [45, 50, 55, 60, 65, 70, 75, 80, 85],
                               "cap": CAPS}),
    "dairy_r1234zez": dict(name="Dairy effluent → 95 °C hot water · R1234ze(Z) screw HTHP", badge="Dairy R1234ze(Z)",
                           params=DAIRY_R1234ZEZ, fluid_label="R1234ze(Z)", kind="water",
                           axes={"T_src_in": [25, 30, 35, 40, 45, 50, 55, 60], "T_sink_in": [45, 50, 55, 60, 65, 70, 75, 80, 85],
                                 "cap": CAPS}),
    "steam_r1233": dict(name="Spray-dryer exhaust → 2.7 bar steam · R1233zd(E) screw HTHP", badge="Steam R1233zd(E)",
                        params=STEAM_R1233, fluid_label="R1233zd(E)", kind="steam",
                        axes={"T_src_in": [40, 45, 50, 55, 60, 65, 70, 75, 80], "T_sink_in": [100, 105, 110], "cap": CAPS}),
}

ELEC_DAY, ELEC_NIGHT = 24.0, 17.0     # p/kWh, 2023 industrial two-rate contract (07-23 / 23-07)
CCL_ELEC, CCL_GAS = 0.775, 0.672      # p/kWh climate change levy 2023/24
BOILER_EFF = 0.88
CAPEX_GBP_PER_KW = {"water": 750.0, "steam": 1100.0}


def build_map(key):
    sc = SCENARIOS[key]
    p = sc["params"]
    pt = {k: v[len(v) // 2] for k, v in sc["axes"].items()}
    pt["cap"] = 1.0
    o, _ = cyc.solve(p, pt)
    core = HERE.parent / "_legacy" / "simcore"
    return PerfMap(f"hthp_{key}", HERE / "model" / "cycle_econ_ihx.py", "solve", p, sc["axes"], list(o),
                   deps=[core / "hx.py", core / "thermo.py"])


def production(wx):
    """Hourly production intensity (0..1.3) and seasonal milk factor."""
    doy = wx["doy"].to_numpy()
    hl = wx["hour_local"].to_numpy()
    wd = wx["weekday"].to_numpy()
    season = 1 + 0.22 * np.cos(2 * np.pi * (doy - 135) / 365)
    prod = np.where(wd < 5, np.where((hl >= 5) & (hl < 23), 1.0, 0.18), np.where((hl >= 6) & (hl < 18), 0.6, 0.15))
    prod = prod * np.where((hl == 13) | (hl == 21), 0.8, 1.0)          # shift change dips
    cip = ((hl == 14) | (hl == 22)) & (wd < 6)
    return prod * season, season, cip


def simulate(key, pmap):
    sc = SCENARIOS[key]
    p = sc["params"]
    steam = sc["kind"] == "steam"
    wx = weather.load("cheshire")
    gr = grid.load()
    n = len(wx)
    rng = np.random.default_rng(11)
    prod, season, cip = production(wx)
    Ta = wx["T_amb"].to_numpy()
    hl = wx["hour_local"].to_numpy()
    tariff = np.where((hl >= 7) & (hl < 23), ELEC_DAY, ELEC_NIGHT) + CCL_ELEC
    K = pmap.out_keys
    acc = {k: np.zeros(n) for k in K}
    names = ["on_frac", "cap", "Q_hp", "W_hp", "W_aux", "Q_boiler", "gas_kwh", "Q_dem", "Q_src", "starts", "src_level",
             "T_sump", "eff_flow", "T_eff", "overflow_kwh", "Q_store_loss", "store_soc", "T_deliv", "unmet",
             "T_loop", "Q_recov", "dryer", "steam_kgh", "map_ok", "src_limited", "T_sink_in"]
    H = {k: np.zeros(n) for k in names}
    store_nodes = np.zeros((n, 12))
    caps = np.array(CAPS)
    # --- plant state
    sump_V, sump_T = 50.0, 40.0                       # m3, C
    store = StratifiedTank(80.0, 7.0, nodes=12, U_wall=0.3, T_init=80.0)
    T_loop = 60.0                                     # steam case: recovery loop temperature
    on = False
    for i in range(n):
        pr = prod[i]
        for s in range(SUB):
            # ------------------------------------------------ source side
            if not steam:
                eff_flow = (32.0 * pr + (14.0 if cip[i] else 0.0)) * (1 + 0.08 * rng.standard_normal())  # m3/h
                eff_flow = max(2.0, eff_flow)
                T_eff = 37.5 + 6.5 * min(pr, 1.2) + 0.12 * (Ta[i] - 10) + (12.0 if cip[i] else 0.0) + rng.normal(0, 0.6)
                V_in = eff_flow * DT / 3600
                sump_T = (sump_V * sump_T + V_in * T_eff) / (sump_V + V_in)
                sump_V += V_in
                # ground losses of the buried sump (UA 350 W/K to 10 C)
                sump_T -= 350 * (sump_T - 10.0) * DT / (sump_V * 990 * CP_W)
                src_ok = sump_V > 15.0
                T_src = sump_T
            else:
                dryer = 1.0 if (3 <= wx["month"].iat[i] <= 10 and wx["weekday"].iat[i] < 6) else (
                    0.55 if wx["weekday"].iat[i] < 5 else 0.0)
                T_exh = 82.0 + 0.25 * (Ta[i] - 10) if dryer > 0 else max(Ta[i], 20.0)
                Q_rec = 38e3 * dryer * max(0.0, T_exh - T_loop)          # run-around coil UA 38 kW/K
                src_ok = T_loop > 48.0
                T_src = T_loop
            # ------------------------------------------------ sink side / demand
            if not steam:
                Q_dem = (560e3 * pr + (380e3 if cip[i] else 0.0)) * (1 + 0.05 * rng.standard_normal())
                Q_dem = max(40e3, Q_dem)
                T_ret = 58.0 + 4.0 * (pr > 0.5) + rng.normal(0, 0.8)
                T_sink_in = store.T[-1]
                soc = store.soc(60.0, 95.0)
                want = soc < 0.85 or (on and soc < 0.97)
            else:
                Q_dem = (900e3 * pr + (200e3 if cip[i] else 0.0)) * (1 + 0.05 * rng.standard_normal())
                T_sink_in = 105.0
                want = True
            if not on and want and src_ok:
                on = True
                H["starts"][i] += 1
            elif on and (not want or not src_ok):
                on = False
            Q_hp = W_hp = 0.0
            cap = 0.0
            if on:
                if steam:
                    Q_target = Q_dem
                else:
                    deficit = (0.97 - store.soc(60.0, 95.0)) * store.V * 990 * CP_W * 35 / (3 * 3600)
                    Q_target = max(0.0, Q_dem + deficit)
                qs = []
                for c in caps:
                    v, ok = pmap(T_src_in=T_src, T_sink_in=T_sink_in, cap=c)
                    qs.append(pmap.get(v, "Q_c") * 1e3)
                qs = np.array(qs)
                cap = float(np.interp(Q_target, qs, caps)) if Q_target < qs[-1] else 1.0
                if Q_target < qs[0] * 0.6 and not steam:
                    cap = caps[0]
                vec, ok = pmap(T_src_in=T_src, T_sink_in=T_sink_in, cap=cap)
                H["map_ok"][i] += ok / SUB
                Q_hp = pmap.get(vec, "Q_c") * 1e3
                W_hp = pmap.get(vec, "W_el") * 1e3
                Q_e = pmap.get(vec, "Q_e") * 1e3
                for ki, k in enumerate(K):
                    acc[k][i] += vec[ki]
                H["on_frac"][i] += 1 / SUB
                H["cap"][i] += cap * 100 / SUB
                if not steam:
                    T_out = pmap.get(vec, "T_src_out")
                    V_out = p["m_src"] / 990 * DT
                    sump_V -= V_out
                    H["Q_src"][i] += Q_e * DT / 3.6e6
                else:
                    H["Q_src"][i] += Q_e * DT / 3.6e6
            else:
                Q_e = 0.0
            H["T_sink_in"][i] += T_sink_in / SUB
            # ------------------------------------------------ update source states
            if not steam:
                if sump_V > 100.0:
                    H["overflow_kwh"][i] += (sump_V - 100.0) * 990 * CP_W * (sump_T - 20.0) / 3.6e6
                    sump_V = 100.0
                sump_V = max(sump_V, 2.0)
                H["src_level"][i] += sump_V / SUB
                H["T_sump"][i] += sump_T / SUB
                H["eff_flow"][i] += eff_flow / SUB
                H["T_eff"][i] += T_eff / SUB
                H["src_limited"][i] += (not src_ok) / SUB
            else:
                C_loop = 30e3 * CP_W                                      # 30 m3 loop + buffer
                T_loop += (Q_rec - Q_e - 2.5e3 * (T_loop - Ta[i])) * DT / C_loop
                H["T_loop"][i] += T_loop / SUB
                H["Q_recov"][i] += Q_rec * DT / 3.6e6
                H["dryer"][i] += dryer * 100 / SUB
                H["src_limited"][i] += (not src_ok) / SUB
            # ------------------------------------------------ sink / store
            if not steam:
                m_load = Q_dem / (CP_W * max(95.0 - T_ret, 5.0))
                m_c = Q_hp / (CP_W * max(95.0 - store.T[-1], 3.0)) if Q_hp > 0 else 0.0
                r = store.step(DT, m_c, 95.0, m_load, T_ret, 12.0)
                T_top = store.T[0]
                Q_boil = max(0.0, m_load * CP_W * (95.0 - T_top))       # boiler trims delivery to 95 C
                H["Q_store_loss"][i] += r["Q_loss"] * DT / 3.6e6
                H["T_deliv"][i] += T_top / SUB
            else:
                Q_boil = max(0.0, Q_dem - Q_hp)
                hg_hfw = 2720e3 - 440e3
                H["steam_kgh"][i] += Q_hp / hg_hfw * 3600 / SUB
            H["Q_hp"][i] += Q_hp * DT / 3.6e6
            H["W_hp"][i] += W_hp * DT / 3.6e6
            H["Q_dem"][i] += Q_dem * DT / 3.6e6
            H["Q_boiler"][i] += Q_boil * DT / 3.6e6
            H["gas_kwh"][i] += Q_boil / BOILER_EFF * DT / 3.6e6
            # auxiliaries: source pump 7.5 kW, sink pump 5.5 kW, oil pump/cooler 3 kW, controls 1 kW
            W_aux = (16e3 if on else 0.0) + 1e3 + (4e3 if steam and on else 0.0)
            H["W_aux"][i] += W_aux * DT / 3.6e6
        if not steam:
            store_nodes[i] = store.T
            H["store_soc"][i] = store.soc(60.0, 95.0) * 100
        if H["on_frac"][i] > 0:
            for k in K:
                acc[k][i] /= H["on_frac"][i] * SUB
            H["cap"][i] /= H["on_frac"][i]
    return sc, wx, gr, acc, H, store_nodes, prod, tariff


def export(key, pmap):
    sc, wx, gr, acc, H, store_nodes, prod, tariff = simulate(key, pmap)
    p = sc["params"]
    steam = sc["kind"] == "steam"
    n = len(wx)
    R = Results(key, sc["name"], n)
    on = H["on_frac"] > 0
    of = H["on_frac"]
    F = Fluid(p["fluid"])
    Ta = wx["T_amb"].to_numpy()
    for k in acc:
        if k.startswith("sp"):
            sid, fld = k[2:].split("_")
            for i in np.where(~on)[0]:
                st = F.PQ(F.Psat(max(Ta[i], 5) + 273.15 + 10), 1.0)
                acc[k][i] = {"T": st.Tc, "P": st.P / 1e5, "h": st.h / 1e3, "s": st.s / 1e3, "x": np.nan, "m": 0.0,
                             "ex": 0.0}[fld]
        elif k not in ("Q_c", "Q_e", "W_el", "W_shaft", "Q_ihx", "Q_econ") and not k.startswith(("X_", "Ex_")):
            acc[k][~on] = np.nan
        else:
            acc[k][~on] = 0.0
    g = "Ambient & tariffs"
    R.ch("T_amb", Ta, "°C", "Outdoor air temperature", g, 1)
    R.ch("RH", wx.RH, "%", "Outdoor relative humidity", g, 0)
    R.ch("tariff", tariff, "p/kWh", "Electricity tariff incl. CCL", g, 2)
    R.ch("ci", gr.ci, "gCO₂/kWh", "GB grid carbon intensity", g, 0)
    for sid, nm in SP_NAMES.items():
        R.state_point(sid, nm, f"{sc['fluid_label']} circuit", p["fluid"],
                      {f: acc[f"sp{sid}_{f}"] for f in ("T", "P", "h", "s", "x", "m", "ex")})
    if steam:
        R.state_point("S1", "Recovery loop to evaporator", "Source loop", "Water",
                      {"T": H["T_loop"], "P": np.full(n, 3.0), "h": CP_W * H["T_loop"] / 1e3, "m": np.where(on, p["m_src"], 0.0)})
        R.state_point("K2", "Saturated steam to header", "Steam", "Water",
                      {"T": np.full(n, 130.0), "P": np.full(n, 2.70), "h": np.full(n, 2720.0), "m": H["steam_kgh"] / 3600})
        R.state_point("K1", "Feedwater from deaerator", "Steam", "Water",
                      {"T": np.full(n, 105.0), "P": np.full(n, 4.0), "h": np.full(n, 440.2), "m": H["steam_kgh"] / 3600})
    else:
        R.state_point("S1", "Effluent from sump", "Effluent", "Water",
                      {"T": H["T_sump"], "P": np.full(n, 2.5), "h": CP_W * H["T_sump"] / 1e3, "m": np.where(on, p["m_src"], 0.0)})
        R.state_point("K1", "Store return to condenser", "Process water", "Water",
                      {"T": H["T_sink_in"], "P": np.full(n, 4.0), "h": CP_W * H["T_sink_in"] / 1e3, "m": acc["m_sink"]})
        R.state_point("K2", "Hot water to store top", "Process water", "Water",
                      {"T": np.where(on, 95.0, np.nan), "P": np.full(n, 3.7), "h": np.full(n, CP_W * 95 / 1e3), "m": acc["m_sink"]})
    R.state_point("S2", "Source return", "Source loop" if steam else "Effluent", "Water",
                  {"T": acc["T_src_out"], "P": np.full(n, 2.2), "h": CP_W * np.nan_to_num(acc["T_src_out"]) / 1e3,
                   "m": np.where(on, p["m_src"], 0.0)})
    g = "Refrigerant cycle"
    for k, u, lbl, d in [("Pe", "bar", "Evaporating pressure", 3), ("Pm", "bar", "Economiser-port pressure", 3),
                         ("Pc", "bar", "Condensing pressure", 3), ("Te", "°C", "Evaporating temperature", 1),
                         ("Tm", "°C", "Economiser saturation temperature", 1), ("Tc", "°C", "Condensing temperature", 1),
                         ("lift", "K", "Temperature lift", 1), ("econ_frac", "–", "Economiser flow ratio ṁ_e/ṁ", 3),
                         ("approach_e", "K", "Evaporator approach", 2), ("approach_c", "K", "Condenser approach", 2)]:
        R.ch(k, acc[k], u, lbl, g, d)
    R.ch("m_ref", acc["m_ref"], "kg/s", "Suction mass flow", g, 3)
    R.ch("m_econ", acc["m_econ"], "kg/s", "Economiser injection flow", g, 3)
    R.ch("Q_ihx", acc["Q_ihx"] * of, "kW", "IHX duty", g, 1)
    R.ch("Q_econ", acc["Q_econ"] * of, "kW", "Economiser subcooler duty", g, 1)
    g = "Compressor"
    R.ch("cap", np.where(on, H["cap"], 0.0), "%", "Slide-valve / VFD capacity", g, 0)
    R.ch("pr", acc["pr"], "–", "Overall pressure ratio", g, 2)
    R.ch("eta_is", acc["eta_is"] * 100, "%", "Isentropic efficiency", g, 1)
    R.ch("eta_v", acc["eta_v"] * 100, "%", "Volumetric efficiency", g, 1)
    R.ch("T_dis", acc["T_dis"], "°C", "Discharge temperature", g, 1)
    R.ch("W_hp", H["W_hp"], "kW", "Compressor electrical power", g, 1)
    R.ch("starts", H["starts"], "1/h", "Starts", g, 0)
    R.ch("on_frac", of * 100, "%", "Run fraction", g, 0)
    g = "Heat balance"
    R.ch("Q_hp", H["Q_hp"], "kW", "Heat pump heat delivered", g, 1)
    R.ch("Q_src", H["Q_src"], "kW", "Waste heat recovered", g, 1)
    R.ch("Q_dem", H["Q_dem"], "kW", "Process heat demand", g, 1)
    R.ch("Q_boiler", H["Q_boiler"], "kW", "Gas boiler top-up", g, 1)
    R.ch("hp_share", np.where(H["Q_dem"] > 0, 100 * np.minimum(H["Q_hp"], H["Q_dem"]) / np.maximum(H["Q_dem"], 1e-9), 0), "%",
         "Heat pump share of demand", g, 0)
    R.ch("W_aux", H["W_aux"], "kW", "Pumps, oil system, controls", g, 2)
    R.ch("cop", np.where(H["W_hp"] > 0, H["Q_hp"] / np.maximum(H["W_hp"], 1e-9), np.nan), "–", "COP (compressor)", "Performance", 2)
    R.ch("cop_sys", np.where(H["W_hp"] > 0, H["Q_hp"] / np.maximum(H["W_hp"] + H["W_aux"], 1e-9), np.nan), "–",
         "System COP (incl. auxiliaries)", "Performance", 2)
    R.ch("carnot", acc["carnot"], "–", "Carnot COP", "Performance", 2)
    R.ch("eta_carnot", acc["eta_carnot"] * 100, "%", "Second-law efficiency", "Performance", 1)
    R.ch("eta_ex", acc["eta_ex"] * 100, "%", "Exergy efficiency", "Performance", 1)
    g = "Exergy destruction"
    for k, lbl in [("X_comp", "Compressor"), ("X_cond", "Condenser / steam generator"), ("X_evap", "Evaporator"),
                   ("X_econ", "Economiser"), ("X_ihx", "IHX"), ("X_valves", "Expansion valves"), ("X_mix", "Port mixing"),
                   ("Ex_prod", "Product exergy"), ("Ex_src", "Source exergy in")]:
        R.ch(k, acc[k] * of, "kW", lbl, g, 2)
    g = "Site"
    R.ch("production", prod * 100, "%", "Production intensity", g, 0)
    if steam:
        R.ch("T_loop", H["T_loop"], "°C", "Recovery loop temperature", g, 1)
        R.ch("Q_recov", H["Q_recov"], "kW", "Exhaust heat recovered by coil", g, 1)
        R.ch("dryer", H["dryer"], "%", "Spray dryer load", g, 0)
        R.ch("steam_kgh", H["steam_kgh"], "kg/h", "Steam from heat pump", g, 0)
    else:
        R.ch("T_sump", H["T_sump"], "°C", "Effluent sump temperature", g, 1)
        R.ch("src_level", H["src_level"], "m³", "Sump volume", g, 1)
        R.ch("eff_flow", H["eff_flow"], "m³/h", "Effluent generation", g, 1)
        R.ch("T_eff", H["T_eff"], "°C", "Effluent temperature from process", g, 1)
        R.ch("T_src_out", acc["T_src_out"], "°C", "Effluent discharge temperature", g, 1)
        R.ch("overflow", H["overflow_kwh"], "kWh", "Heat lost in sump overflow", g, 1)
        R.ch("store_soc", H["store_soc"], "%", "Hot-water store state of charge", g, 0)
        R.ch("T_deliv", H["T_deliv"], "°C", "Store top temperature", g, 1)
        R.ch("store_loss", H["Q_store_loss"], "kW", "Store standing loss", g, 2)
        for j in range(store_nodes.shape[1]):
            R.ch(f"st_T{j + 1}", store_nodes[:, j], "°C", f"Store node {j + 1} (top=1)", "Store nodes", 1)
    R.ch("src_limited", H["src_limited"] * 100, "%", "Source unavailable", g, 0)
    R.ch("layout", np.full(n, 1.0 if steam else 0.0), "–", "Layout (0 dairy water, 1 steam)", "Control", 0)
    g = "Cost & carbon"
    W_tot = H["W_hp"] + H["W_aux"]
    gas_price = grid.GAS_PRICE_P_KWH + CCL_GAS
    cost_e = W_tot * tariff / 100
    cost_g = H["gas_kwh"] * gas_price / 100
    co2_e = W_tot * gr.ci.to_numpy() / 1000
    co2_g = H["gas_kwh"] * grid.GAS_CARBON_G_KWH / 1000
    base_gas = H["Q_dem"] / BOILER_EFF
    R.ch("cost_e", cost_e, "£/h", "Electricity cost", g, 2)
    R.ch("cost_g", cost_g, "£/h", "Gas cost", g, 2)
    R.ch("co2", co2_e + co2_g, "kg/h", "Site heat CO₂ (elec + gas)", g, 1)
    R.ch("co2_saved", base_gas * grid.GAS_CARBON_G_KWH / 1000 - co2_e - co2_g, "kg/h", "CO₂ avoided vs gas-only", g, 1)
    R.ch("cum_saving", np.cumsum(base_gas * gas_price / 100 - cost_e - cost_g), "£", "Cumulative saving vs gas-only", g, 0)
    R.ch("cum_co2_saved", np.cumsum(base_gas * grid.GAS_CARBON_G_KWH / 1000 - co2_e - co2_g) / 1000, "t",
         "Cumulative CO₂ avoided", g, 1)
    R.start = int(np.argmax(np.where(on & (np.arange(n) > 24 * 120), H["Q_hp"], -1)))

    k = R.kpi
    Qhp, Whp, Wa = H["Q_hp"].sum(), H["W_hp"].sum(), H["W_aux"].sum()
    k("Seasonal COP (compressor)", Qhp / Whp, "–", "Performance", 2)
    k("Seasonal system COP (incl. aux)", Qhp / (Whp + Wa), "–", "Performance", 2)
    k("Mean exergy efficiency (running)", np.nanmean(acc["eta_ex"][on]) * 100, "%", "Performance", 1)
    k("Heat pump heat delivered", Qhp / 1000, "MWh", "Energy", 0)
    k("Waste heat recovered", H["Q_src"].sum() / 1000, "MWh", "Energy", 0)
    k("Process heat demand", H["Q_dem"].sum() / 1000, "MWh", "Energy", 0)
    k("Heat pump coverage of demand", 100 * min(Qhp, H["Q_dem"].sum()) / H["Q_dem"].sum(), "%", "Energy", 1)
    k("Boiler top-up heat", H["Q_boiler"].sum() / 1000, "MWh", "Energy", 0)
    k("Electricity (HP + aux)", (Whp + Wa) / 1000, "MWh", "Energy", 0)
    k("Gas displaced", (base_gas.sum() - H["gas_kwh"].sum()) / 1000, "MWh", "Energy", 0)
    k("Run hours", of.sum(), "h", "Operation", 0)
    k("Starts", H["starts"].sum(), "", "Operation", 0)
    k("Mean capacity when running", np.mean(H["cap"][on]), "%", "Operation", 0)
    k("Max discharge temperature", np.nanmax(acc["T_dis"]), "°C", "Operation", 1)
    k("Hours source-limited", (H["src_limited"] > 0.5).sum(), "h", "Operation", 0)
    if not steam:
        k("Mean effluent discharge temp (running)", np.nanmean(acc["T_src_out"][on]), "°C", "Operation", 1)
        k("Heat lost to sump overflow", H["overflow_kwh"].sum() / 1000, "MWh", "Operation", 1)
    else:
        k("Steam raised by heat pump", H["steam_kgh"].sum() / 1000, "t", "Operation", 0)
    saving = (base_gas * gas_price / 100).sum() - cost_e.sum() - cost_g.sum()
    k("Energy cost, gas-only baseline", (base_gas * gas_price / 100).sum() / 1000, "k£", "Economics", 1)
    k("Energy cost with heat pump", (cost_e.sum() + cost_g.sum()) / 1000, "k£", "Economics", 1)
    k("Annual saving", saving / 1000, "k£", "Economics", 1)
    p_e = (cost_e.sum() * 100) / max(W_tot.sum(), 1e-9)
    k("Electricity / gas price ratio", p_e / gas_price, "–", "Economics", 2,
      note="consumption-weighted electricity price over gas price incl. CCL")
    k("Break-even system COP vs boiler", p_e / gas_price * BOILER_EFF, "–", "Economics", 2)
    capex = CAPEX_GBP_PER_KW[sc["kind"]] * p["Q_design"] / 1000
    k("Installed cost (estimate)", capex / 1000, "k£", "Economics", 0, note="£/kW benchmark, not a quotation")
    k("Simple payback", capex / saving if saving > 0 else float("nan"), "years", "Economics", 1)
    k("CO₂, gas-only baseline", (base_gas * grid.GAS_CARBON_G_KWH / 1e6).sum(), "t", "Carbon", 0)
    k("CO₂ with heat pump", (co2_e.sum() + co2_g.sum()) / 1000, "t", "Carbon", 0)
    k("CO₂ avoided", (base_gas * grid.GAS_CARBON_G_KWH / 1e6).sum() - (co2_e.sum() + co2_g.sum()) / 1000, "t", "Carbon", 0)
    for kk, lbl in [("X_comp", "compressor"), ("X_cond", "condenser"), ("X_evap", "evaporator"), ("X_valves", "valves"),
                    ("X_econ", "economiser")]:
        k(f"Exergy destroyed · {lbl}", np.nansum(acc[kk] * of) / 1000, "MWh", "Exergy", 1)

    fl = Fluid(p["fluid"])
    paths = [["11", "1", "2", "3", "4", "5", "6", "9", "10", "11"], ["6", "7", "8", "4"]]
    R.diagrams.append({"type": "ph", "title": f"{sc['fluid_label']} log P–h", "fluid": p["fluid"],
                       "dome": fl.dome(70, max(fl.Tmin + 1, 263.0)), "paths": paths})
    R.diagrams.append({"type": "ts", "title": f"{sc['fluid_label']} T–s", "fluid": p["fluid"],
                       "dome": fl.dome(70, max(fl.Tmin + 1, 263.0)), "paths": paths})
    if not steam:
        R.diagrams.append({"type": "profile", "title": "Hot-water store profile", "xLabel": "°C",
                           "series": [{"label": "Store", "keys": [f"st_T{j + 1}" for j in range(12)], "color": "#c2410c"}]})
    R.diagrams.append({"type": "bars", "title": "Exergy flows now (kW)", "items": [
        {"key": kk, "label": lb} for kk, lb in [("Ex_src", "Source in"), ("X_comp", "Compressor"), ("X_cond", "Condenser"),
                                                ("X_evap", "Evaporator"), ("X_econ", "Economiser"), ("X_ihx", "IHX"),
                                                ("X_valves", "Valves"), ("Ex_prod", "Product")]]})
    return R, sc


if __name__ == "__main__":
    import time
    for key in (sys.argv[1:] or SCENARIOS):
        t = time.time()
        pm = build_map(key)
        print(key, "map coverage %.3f" % pm.coverage(), "%.0fs" % (time.time() - t))
        R, sc = export(key, pm)
        print("  sim %.0fs" % (time.time() - t))
        for kp in R.kpis:
            print(f"  {kp['label']:<42} {kp['value'] if kp['value'] is not None else float('nan'):.2f} {kp['unit']}")
