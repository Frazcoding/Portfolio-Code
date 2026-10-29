"""Annual (8760 h) simulation of a two-stage R290 air-source heat pump plant.

Plant: two inverter LP scrolls + inverter HP scroll with open flash economiser,
finned air coil with two EC fans, brazed-plate condenser, stratified space-heating
buffer, stratified DHW cylinder charged through a plate exchanger, 2 x 9 kW
backup elements, weather-compensated radiator circuit, 12-flat residential block
(ISO 13790 5R1C). Real 2023 ERA5 weather, GB grid carbon and Agile prices.

Control runs in 10-minute steps; results are hourly means (power, state) or
hourly sums (energy). Every refrigerant state point is a full CoolProp solution
taken from a performance map of the steady-state cycle solver.
"""
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_legacy"))  # frozen simcore v0.1.0
sys.path.insert(0, str(HERE))

from simcore import grid, solar, weather  # noqa: E402
from simcore.building import Zone5R1C  # noqa: E402
from simcore.hx import CP_W  # noqa: E402
from simcore.output import Results  # noqa: E402
from simcore.perfmap import PerfMap  # noqa: E402
from simcore.storage import StratifiedTank  # noqa: E402
from simcore.thermo import Fluid  # noqa: E402
from model import cycle_two_stage as cyc  # noqa: E402
from model.params import CYCLE  # noqa: E402

AXES = {
    "T_air": [-20, -15, -10, -7, -4, -2, 0, 2, 4, 7, 10, 13, 16, 20, 25, 30],
    "RH": [40, 70, 95],
    "T_w_in": [15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65],
    "f": [25, 35, 50, 65, 80, 100],
    "ua": [0.5, 0.75, 1.0],
}
SPEEDS = np.array(AXES["f"], dtype=float)
SP_NAMES = {
    "1": "Evaporator outlet", "2": "LP suction", "3": "LP discharge", "4": "HP suction (mixed)",
    "5": "HP discharge", "6": "Condenser outlet", "7": "HP EEV outlet", "8": "Flash vapour",
    "9": "Flash liquid", "10": "Evaporator inlet",
}

SCENARIOS = {
    "london": dict(
        site="london", name="London 2023 · 12-flat block · 55 °C design flow", badge="London",
        H_w=290.0, H_op=560.0, ach=0.75, T_flow_design=55.0, T_design=-4.0, buffer_m3=1.0,
        smart=False),
    "london_agile": dict(
        site="london", name="London 2023 · Agile-aware control · fabric pre-heat", badge="London Agile",
        H_w=290.0, H_op=560.0, ach=0.75, T_flow_design=55.0, T_design=-4.0, buffer_m3=1.0,
        smart=True),
    "glasgow": dict(
        site="glasgow", name="Glasgow 2023 · 1960s block · 65 °C design flow", badge="Glasgow",
        H_w=480.0, H_op=980.0, ach=0.9, T_flow_design=65.0, T_design=-5.0, buffer_m3=1.0,
        smart=False),
}

DT = 600.0
SUB = 6
A_F = 960.0
VOL = 2400.0
M_PRIMARY = CYCLE["m_w"]
FROST_MAX = 14.0         # kg on coil at which UA has fallen to 50 % (~0.6 mm on 150 m2 fins)
DEFROST_AT = 7.0         # kg frost triggers reverse-cycle defrost
COIL_METAL_J = 1.6e6     # coil + fin heat capacity raised ~ 8 K in defrost
BACKUP_KW = 18.0


def build_map():
    out_keys, _ = cyc.solve(CYCLE, dict(T_air=2, RH=80, T_w_in=40, f=50, ua=1.0))
    core = HERE.parent / "_legacy" / "simcore"
    return PerfMap("hp_two_stage_r290", HERE / "model" / "cycle_two_stage.py", "solve", CYCLE, AXES,
                   list(out_keys), deps=[core / "hx.py", core / "thermo.py"])


def dhw_profile(n_hours, rng):
    """Litres per hour at 55 C for 12 flats (SAP / EN 16147 shaped, stochastic)."""
    base = np.array([4, 2, 1, 1, 2, 8, 40, 95, 80, 45, 30, 28, 32, 26, 20, 22, 30, 50, 75, 80, 62, 45, 25, 10],
                    dtype=float)
    base *= 1200 / base.sum()
    v = np.tile(base, n_hours // 24 + 1)[:n_hours]
    return v * rng.lognormal(0, 0.35, n_hours)


def internal_gains(hour_local):
    prof = np.array([.45, .4, .4, .4, .4, .5, .8, 1.0, .8, .6, .55, .55, .6, .55, .55, .6, .75, 1.0, 1.15,
                     1.15, 1.05, .9, .7, .55])
    return 3.2 * A_F * prof[hour_local]


def radiator(Q_nom, T_flow, T_room, m, n=1.3, dT_nom=50.0):
    """Max output and return temperature of the radiator circuit at constant flow."""
    if T_flow <= T_room + 0.5:
        return 0.0, T_flow
    lo, hi = T_room + 1e-3, T_flow
    for _ in range(40):
        Tr = 0.5 * (lo + hi)
        Q_flow = m * CP_W * (T_flow - Tr)
        d1, d2 = T_flow - T_room, Tr - T_room
        lm = (d1 - d2) / math.log(d1 / d2) if abs(d1 - d2) > 1e-6 else d1
        Q_rad = Q_nom * (lm / dT_nom) ** n
        if Q_flow > Q_rad:
            lo = Tr
        else:
            hi = Tr
    return m * CP_W * (T_flow - Tr), Tr


def simulate(key, pmap):
    sc = SCENARIOS[key]
    wx = weather.load(sc["site"])
    gr = grid.load()
    n = len(wx)
    rng = np.random.default_rng(7)
    lat, lon = weather.SITES[sc["site"]][:2]
    zen, az, doy = solar.position(wx["time"], lat, lon)
    phi_sol = np.zeros(n)
    for surf_az in (0, 90, 180, 270):
        b, d, g, aoi = solar.poa(wx.ghi.to_numpy(), wx.dni.to_numpy(), wx.dhi.to_numpy(), zen, az, doy, 90, surf_az)
        phi_sol += (180 / 4) * 0.6 * 0.75 * 0.8 * (b * solar.iam_ashrae(aoi) + d + g)
    H_ve = 0.34 * sc["ach"] * VOL
    zone = Zone5R1C(A_f=A_F, H_tr_w=sc["H_w"], H_tr_op=sc["H_op"], theta_m=20.0)
    H_total = sc["H_w"] + sc["H_op"] + H_ve
    Q_design = H_total * (21 - sc["T_design"])
    T_fd = sc["T_flow_design"]
    m_heat = Q_design / (CP_W * 10.0)
    Q_rad_nom = Q_design / ((((T_fd - 21) - (T_fd - 10 - 21)) / math.log((T_fd - 21) / (T_fd - 31))) / 50) ** 1.3

    buf = StratifiedTank(sc["buffer_m3"], 1.9 if sc["buffer_m3"] <= 1 else 2.4, nodes=10, U_wall=0.3, T_init=45)
    dhw = StratifiedTank(1.0, 2.0, nodes=10, U_wall=0.25, T_init=55)
    v_dhw = dhw_profile(n, rng)
    T_mains = np.clip(wx["T_soil_1m"].to_numpy() + 1.0, 5, 20)
    gains = internal_gains(wx["hour_local"].to_numpy())
    Ta_all = wx["T_amb"].to_numpy()
    rh_all = wx["RH"].to_numpy()
    price = gr["price"].to_numpy()
    ci = gr["ci"].to_numpy()
    # daily price thresholds for the smart controller
    day = np.arange(n) // 24
    cheap = np.zeros(n, bool)
    dear = np.zeros(n, bool)
    for d in range(day.max() + 1):
        sl = day == d
        p = price[sl]
        hi = np.quantile(p, 0.85)
        # shift only when the intra-day spread pays for the ~2 %/K COP penalty of a 5 K boost
        cheap[sl] = (p <= np.quantile(p, 0.25)) & (p <= 0.7 * hi)
        dear[sl] = ((p >= hi) & (p > 1.25 * p.mean())) | (p > 35)
    F = Fluid(CYCLE["fluid"])

    K = pmap.out_keys
    acc = {k: np.zeros(n) for k in K}
    H = {name: np.zeros(n) for name in [
        "on_frac", "f_cmd", "mode_dhw", "defrosts", "frost_kg", "ua", "Q_c_kwh", "Q_sh_kwh", "Q_dhw_kwh",
        "Q_def_kwh", "W_comp_kwh", "W_fan_kwh", "W_pump_kwh", "W_aux_kwh", "W_backup_kwh", "W_imm_kwh",
        "W_total_kwh", "starts", "T_air_room", "T_op", "T_mass", "Q_need", "Q_emit", "T_flow_set", "T_flow",
        "T_ret", "unmet_K", "buf_loss_kwh", "dhw_loss_kwh", "dhw_draw_l", "dhw_energy_kwh", "T_tap",
        "T_mains", "buf_soc", "buf_mix", "dhw_soc", "map_ok", "Q_e_kwh", "water_kg", "W_def_kwh",
        "blocked", "boost", "buf_in", "buf_out", "dhw_in", "dhw_out", "def_buf", "def_dhw"]}
    T_buf_nodes = np.zeros((n, buf.N))
    T_dhw_nodes = np.zeros((n, dhw.N))

    on = False
    mode = "sh"
    frost = 0.0
    off_time = 1e9
    run_time = 0.0
    legionella_due = False
    legionella_t = 0.0
    T_room = 20.0
    for i in range(n):
        Ta, rh = Ta_all[i], rh_all[i]
        hl = int(wx["hour_local"].iat[i])
        occupied = 7 <= hl < 23
        base_set = 21.0 if 4 <= hl < 23 else 18.0   # optimum start: preheat from 04:00
        boost = sc["smart"] and cheap[i]
        blocked = sc["smart"] and dear[i]
        # price-aware control uses the building fabric (~44 kWh/K) as the store:
        # +1 K pre-heat in cheap hours, coast down 1 K through expensive hours
        set_h = base_set + (1.0 if boost and base_set > 20 else 0.0) - (0.8 if blocked and base_set > 20 else 0.0)
        Q_need, t_free = zone.demand(Ta, H_ve, gains[i], phi_sol[i], set_h, 99.0)
        Q_need = max(0.0, Q_need)
        T_set = 21 + (T_fd - 21) * max(0.0, (21 - Ta) / (21 - sc["T_design"])) ** (1 / 1.3)
        # room-temperature influence (setback recovery / under-heating)
        T_set += min(10.0, 4.0 * max(0.0, set_h - T_room))
        T_set = min(T_fd + 5, max(28.0, T_set)) if Q_need > 0 else 28.0
        buf_target = T_set + (3.0 if boost and Q_need > 0 else 0.0)
        dhw_on_T, dhw_off_T = (50.0, 58.0) if boost else (47.0, 55.0)
        if wx["weekday"].iat[i] == 6 and hl == 2:
            legionella_due = True
            legionella_t = 0.0
        hourly_draw = v_dhw[i]
        Tm = T_mains[i]
        H["T_mains"][i] = Tm
        H["T_flow_set"][i] = T_set
        H["Q_need"][i] = Q_need / 1e3
        H["blocked"][i] = blocked
        H["boost"][i] = boost
        ua = max(0.5, 1 - 0.5 * min(frost / FROST_MAX, 1.0))
        q_emit_sum = tr_sum = tf_sum = 0.0
        for s in range(SUB):
            # --- space-heating draw from buffer through the mixing valve ---
            T_top = buf.T[0]
            T_flow = min(T_set, T_top)
            Qmax, T_ret_max = radiator(Q_rad_nom, T_flow, T_room, m_heat)
            Q_emit = min(Q_need, Qmax)
            T_ret = T_flow - Q_emit / (m_heat * CP_W) if Q_need > 0 else T_flow
            m_draw = 0.0
            if Q_emit > 0 and T_top > T_ret + 0.1:
                m_draw = m_heat * min(1.0, (T_flow - T_ret) / (T_top - T_ret))
            # --- DHW draw (mixed to 45 C at taps) ---
            m_tap = hourly_draw / 3600  # kg/s, hourly mean draw
            T_hot = dhw.T[0]
            m_hot = m_tap * (45 - Tm) / max(T_hot - Tm, 1.0) if T_hot > 45 else m_tap
            # --- mode selection ---
            if mode == "sh" and dhw.T[2] < dhw_on_T and not (blocked and dhw.T[2] > 42):
                mode = "dhw"
            elif mode == "dhw" and dhw.T[-1] > dhw_off_T - 3:
                mode = "sh"
            if mode == "sh":
                want = buf.T[3] < buf_target - 1.0 or (on and buf.T[-1] < buf_target + 2.0)
                if blocked and buf.T[0] > T_set - 6 and T_room > base_set - 1.0:
                    want = False
                T_in = buf.T[-1]
                T_out_target = buf_target + 3.0
            else:
                want = True
                T_in = min(dhw.T[-1] + 4.0, 62.0)
                T_out_target = dhw_off_T + 5.0
            if Q_need <= 0 and mode == "sh" and buf.T[3] > 30:
                want = False
            if not on and want and off_time >= DT:
                on = True
                run_time = 0.0
                H["starts"][i] += 1
            elif on and not want and run_time >= DT:
                on = False
                off_time = 0.0
            # --- heat pump operating point ---
            Q_c = W_tot = 0.0
            vec = None
            f_cmd = 0.0
            defrost_s = 0.0
            if on:
                Q_target = M_PRIMARY * CP_W * max(T_out_target - T_in, 0.5)
                if mode == "dhw":
                    Q_target = 1e9
                qs = []
                vecs = []
                for fs in SPEEDS:
                    v, ok = pmap(T_air=Ta, RH=rh, T_w_in=T_in, f=fs, ua=ua)
                    qs.append(pmap.get(v, "Q_c") * 1e3 * (1 if ok > 0.5 else 0))
                    vecs.append((v, ok))
                qs = np.array(qs)
                if Q_target >= qs[-1]:
                    f_cmd = SPEEDS[-1]
                elif Q_target <= qs[0]:
                    f_cmd = SPEEDS[0]
                else:
                    f_cmd = float(np.interp(Q_target, qs, SPEEDS))
                # stay inside the compressor envelope (discharge temperature / map validity)
                vec, ok = pmap(T_air=Ta, RH=rh, T_w_in=T_in, f=f_cmd, ua=ua)
                while ok < 0.5 and f_cmd > SPEEDS[0]:
                    f_cmd = max(SPEEDS[0], f_cmd - 10)
                    vec, ok = pmap(T_air=Ta, RH=rh, T_w_in=T_in, f=f_cmd, ua=ua)
                H["map_ok"][i] += ok / SUB
                Q_c = pmap.get(vec, "Q_c") * 1e3
                W_tot = pmap.get(vec, "W_tot") * 1e3
                Te = pmap.get(vec, "Te")
                water = pmap.get(vec, "water")
                if Te + 1.5 < 0 and water > 0:
                    frost += water * DT
                elif Ta > 2:
                    frost = max(0.0, frost - 0.002 * (Ta - 2) * DT)
                ua = max(0.5, 1 - 0.5 * min(frost / FROST_MAX, 1.0))
                if frost >= DEFROST_AT:
                    E_def = frost * (334e3 + 2100 * 2) + COIL_METAL_J
                    W_def = E_def / 4.0
                    Q_from_water = E_def - W_def
                    defrost_s = min(DT, 180 + E_def / 30e3)
                    H["defrosts"][i] += 1
                    H["Q_def_kwh"][i] += Q_from_water / 3.6e6
                    H["W_def_kwh"][i] += W_def / 3.6e6
                    H["W_comp_kwh"][i] += W_def / 3.6e6
                    frost = 0.0
                    ua = 1.0
                    # defrost heat is drawn from the store being charged
                    tank = buf if mode == "sh" else dhw
                    tank.T -= Q_from_water / (tank.M * CP_W * tank.N)
                    H["def_buf" if mode == "sh" else "def_dhw"][i] += Q_from_water / 3.6e6
                run_time += DT
                frac = 1 - defrost_s / DT
                for k_i, k in enumerate(K):
                    acc[k][i] += vec[k_i] * frac
                H["on_frac"][i] += frac / SUB
                H["f_cmd"][i] += f_cmd * frac / SUB
                H["mode_dhw"][i] += (mode == "dhw") * frac / SUB
                H["Q_c_kwh"][i] += Q_c * DT * frac / 3.6e6
                H["Q_e_kwh"][i] += pmap.get(vec, "Q_e") * 1e3 * DT * frac / 3.6e6
                H["W_comp_kwh"][i] += (pmap.get(vec, "W_lp") + pmap.get(vec, "W_hp")) * 1e3 * DT * frac / 3.6e6
                H["W_fan_kwh"][i] += pmap.get(vec, "W_fan") * 1e3 * DT * frac / 3.6e6
                H["water_kg"][i] += water * DT * frac
                Q_c *= frac
            else:
                off_time += DT
                if Ta > 2:
                    frost = max(0.0, frost - 0.002 * (Ta - 2) * DT)
            # --- backup heater (buffer) when HP at limit and buffer falling ---
            W_backup = 0.0
            if buf.T[0] < T_set - 1.0 and Q_need > 0 and not blocked and on and (mode == "dhw" or f_cmd >= 95):
                W_backup = BACKUP_KW * 1e3 * min(1.0, (T_set - 1.0 - buf.T[0]) / 4)
            # --- legionella immersion ---
            W_imm = 0.0
            if legionella_due:
                # pasteurise the volume above the element (lowest node excluded), max 3 h
                if dhw.T[:-1].min() < 60 and legionella_t < 3 * 3600:
                    W_imm = 6e3
                    legionella_t += DT
                else:
                    legionella_due = False
            # --- tank updates ---
            if on and mode == "sh":
                rb = buf.step(DT, M_PRIMARY, 0.0, m_draw, T_ret, 15.0, Q_c=Q_c)
                rd = dhw.step(DT, 0.0, 0.0, m_hot, Tm, 15.0)
                H["Q_sh_kwh"][i] += Q_c * DT / 3.6e6
            elif on and mode == "dhw":
                # stratified charging through the plate exchanger: the variable-speed
                # secondary pump delivers a fixed temperature to the top of the cylinder
                m_c = max(Q_c, 1.0) / (CP_W * max(dhw_off_T + 3 - dhw.T[-1], 3.0))
                rd = dhw.step(DT, m_c, 0.0, m_hot, Tm, 15.0, Q_c=Q_c)
                rb = buf.step(DT, 0.0, 0.0, m_draw, T_ret, 15.0)
                H["Q_dhw_kwh"][i] += Q_c * DT / 3.6e6
            else:
                rb = buf.step(DT, 0.0, 0.0, m_draw, T_ret, 15.0)
                rd = dhw.step(DT, 0.0, 0.0, m_hot, Tm, 15.0)
            buf.T[0] += W_backup * DT / (buf.M * CP_W)
            if W_imm:
                # element near the base: heat enters the bottom node and rises by buoyant mixing
                dhw.T[-1] += W_imm * DT / (dhw.M * CP_W)
                for _ in range(dhw.N):
                    inv = np.where(dhw.T[1:] > dhw.T[:-1] + 1e-6)[0]
                    if not len(inv):
                        break
                    j = inv[-1]
                    dhw.T[j] = dhw.T[j + 1] = 0.5 * (dhw.T[j] + dhw.T[j + 1])
            H["buf_in"][i] += (rb["Q_charge"] * DT + W_backup * DT) / 3.6e6
            H["buf_out"][i] += rb["Q_load"] * DT / 3.6e6
            H["dhw_in"][i] += (rd["Q_charge"] * DT + W_imm * DT) / 3.6e6
            H["dhw_out"][i] += rd["Q_load"] * DT / 3.6e6
            H["buf_loss_kwh"][i] += rb["Q_loss"] * DT / 3.6e6
            H["dhw_loss_kwh"][i] += rd["Q_loss"] * DT / 3.6e6
            H["dhw_energy_kwh"][i] += rd["Q_load"] * DT / 3.6e6
            H["W_backup_kwh"][i] += W_backup * DT / 3.6e6
            H["W_imm_kwh"][i] += W_imm * DT / 3.6e6
            # pumps: primary (on), heating circuit (cube law), DHW charge; controls + crankcase
            W_pump = (180.0 if on else 0.0) + 380.0 * (m_draw / m_heat) ** 3 * (Q_need > 0) + (90.0 if mode == "dhw" and on else 0)
            W_aux = 60.0 + (2 * 45.0 if not on and Ta < 10 else 0.0)
            H["W_pump_kwh"][i] += W_pump * DT / 3.6e6
            H["W_aux_kwh"][i] += W_aux * DT / 3.6e6
            q_emit_sum += Q_emit
            tr_sum += T_ret
            tf_sum += T_flow
        Q_emit = q_emit_sum / SUB
        z = zone.step(Ta, H_ve, gains[i], phi_sol[i], Q_emit)
        T_room = z["T_air"]
        H["T_air_room"][i] = z["T_air"]
        H["T_op"][i] = z["T_op"]
        H["T_mass"][i] = z["T_mass"]
        H["Q_emit"][i] = Q_emit / 1e3
        H["T_flow"][i] = tf_sum / SUB
        H["T_ret"][i] = tr_sum / SUB
        H["unmet_K"][i] = max(0.0, base_set - 1.0 - z["T_air"]) if occupied else 0.0
        H["frost_kg"][i] = frost
        H["ua"][i] = ua
        H["dhw_draw_l"][i] = hourly_draw
        H["T_tap"][i] = dhw.T[0]
        H["buf_soc"][i] = buf.soc(25, T_fd + 8) * 100
        H["buf_mix"][i] = buf.mix_number()
        H["dhw_soc"][i] = dhw.soc(Tm, 60) * 100
        T_buf_nodes[i] = buf.T
        T_dhw_nodes[i] = dhw.T
        H["W_total_kwh"][i] = (H["W_comp_kwh"][i] + H["W_fan_kwh"][i] + H["W_pump_kwh"][i] + H["W_aux_kwh"][i]
                               + H["W_backup_kwh"][i] + H["W_imm_kwh"][i])
        if H["on_frac"][i] > 0:
            for k in K:
                acc[k][i] /= H["on_frac"][i] * SUB
            H["f_cmd"][i] /= H["on_frac"][i]
    return sc, wx, gr, acc, H, T_buf_nodes, T_dhw_nodes, F, dict(Q_design=Q_design, H_total=H_total,
                                                                    m_heat=m_heat, phi_sol=phi_sol, gains=gains)


def standstill(F, Ta):
    """Refrigerant equalised at ambient when the unit is off."""
    T = Ta + 273.15
    st = F.PQ(F.Psat(T), 1.0)
    return st


def export(key, pmap):
    sc, wx, gr, acc, H, Tb, Td, F, info = simulate(key, pmap)
    n = len(wx)
    R = Results(key, sc["name"], n)
    on = H["on_frac"] > 0
    Ta = wx["T_amb"].to_numpy()
    # standstill values for idle hours
    idle = {}
    for i in np.where(~on)[0]:
        st = standstill(F, Ta[i])
        idle[i] = st
    for k in acc:
        if k.startswith("sp"):
            sid, fld = k[2:].split("_")
            for i, st in idle.items():
                acc[k][i] = {"T": st.Tc, "P": st.P / 1e5, "h": st.h / 1e3, "s": st.s / 1e3, "x": np.nan,
                             "m": 0.0, "ex": 0.0}[fld]
        elif k in ("Te", "Tc", "Ti"):
            for i in idle:
                acc[k][i] = Ta[i]
        elif k in ("Pe", "Pc", "Pi"):
            for i, st in idle.items():
                acc[k][i] = st.P / 1e5
        else:
            for i in idle:
                acc[k][i] = np.nan if k in ("COP", "COP_cycle", "eta_ex", "eta_carnot", "carnot", "shr",
                                            "eta_is_lp", "eta_is_hp", "eta_v_lp", "eta_v_hp", "pr_lp", "pr_hp",
                                            "approach_c", "approach_e", "x7", "inj_ratio", "f_hp", "lift",
                                            "T_w_out", "T_air_out", "w_out") else 0.0
    of = H["on_frac"]

    # ---- ambient & grid ----
    g = "Ambient & grid"
    R.ch("T_amb", Ta, "°C", "Outdoor air temperature", g, 1)
    R.ch("RH", wx.RH, "%", "Outdoor relative humidity", g, 0)
    R.ch("T_wb", wx.T_wb, "°C", "Outdoor wet-bulb temperature", g, 1)
    R.ch("w_amb", wx.w_amb * 1e3, "g/kg", "Outdoor humidity ratio", g, 2)
    R.ch("ghi", wx.ghi, "W/m²", "Global horizontal irradiance", g, 0)
    R.ch("wind", wx.wind10, "m/s", "Wind speed 10 m", g, 1)
    R.ch("price", gr.price, "p/kWh", "Agile import price (region C)", g, 2)
    R.ch("ci", gr.ci, "gCO₂/kWh", "GB grid carbon intensity", g, 0)

    # ---- refrigerant state points ----
    for sid, nm in SP_NAMES.items():
        rec = {f: acc[f"sp{sid}_{f}"] for f in ("T", "P", "h", "s", "x", "m", "ex")}
        R.state_point(sid, nm, "R290 circuit", "Propane", rec)
    # secondary fluid points
    Tw_in = np.where(on, acc["T_w_out"] - (acc["Q_c"] / (M_PRIMARY * CP_W / 1e3)), np.nan)
    R.state_point("W1", "Condenser water in", "Water primary", "Water",
                  {"T": Tw_in, "P": np.full(n, 2.5), "h": CP_W * Tw_in / 1e3, "m": M_PRIMARY * (of > 0)})
    R.state_point("W2", "Condenser water out", "Water primary", "Water",
                  {"T": acc["T_w_out"], "P": np.full(n, 2.2), "h": CP_W * acc["T_w_out"] / 1e3,
                   "m": M_PRIMARY * (of > 0)})
    R.state_point("A1", "Coil air on", "Air", "Air",
                  {"T": Ta, "P": wx.p_atm / 1e5, "h": wx.h_amb, "m": acc["m_air"]})
    R.state_point("A2", "Coil air off", "Air", "Air",
                  {"T": np.where(on, acc["T_air_out"], Ta), "P": wx.p_atm / 1e5,
                   "h": np.where(on, 1.006 * acc["T_air_out"] + acc["w_out"] / 1e3 * (2501 + 1.86 * acc["T_air_out"]),
                                 wx.h_amb), "m": acc["m_air"]})

    # ---- cycle ----
    g = "Refrigerant cycle"
    R.ch("Pe", acc["Pe"], "bar", "Evaporating pressure (dew, outlet)", g, 3)
    R.ch("Pi", acc["Pi"], "bar", "Intermediate (flash) pressure", g, 3)
    R.ch("Pc", acc["Pc"], "bar", "Condensing pressure (dew, inlet)", g, 3)
    R.ch("Te", acc["Te"], "°C", "Evaporating temperature", g, 1)
    R.ch("Ti", acc["Ti"], "°C", "Intermediate saturation temperature", g, 1)
    R.ch("Tc", acc["Tc"], "°C", "Condensing temperature", g, 1)
    R.ch("lift", acc["lift"], "K", "Temperature lift Tc − Te", g, 1)
    R.ch("x7", acc["x7"], "–", "Flash quality after HP EEV", g, 3)
    R.ch("inj_ratio", acc["inj_ratio"], "–", "Injection ratio ṁ_vap/ṁ_LP", g, 3)
    R.ch("m_lp", acc["m_lp"] * 1e3, "g/s", "LP refrigerant mass flow", g, 1)
    R.ch("m_hp", acc["m_hp"] * 1e3, "g/s", "HP refrigerant mass flow", g, 1)
    R.ch("m_vap", acc["m_vap"] * 1e3, "g/s", "Flash vapour injection flow", g, 1)
    R.ch("pi_float", acc["pi_float"], "–", "Pi floating (HP speed at limit)", g, 2)
    g = "Compressors"
    R.ch("f_lp", H["f_cmd"], "Hz", "LP inverter speed", g, 1)
    R.ch("f_hp", acc["f_hp"], "Hz", "HP inverter speed", g, 1)
    R.ch("pr_lp", acc["pr_lp"], "–", "LP pressure ratio", g, 2)
    R.ch("pr_hp", acc["pr_hp"], "–", "HP pressure ratio", g, 2)
    R.ch("eta_is_lp", acc["eta_is_lp"] * 100, "%", "LP isentropic efficiency", g, 1)
    R.ch("eta_is_hp", acc["eta_is_hp"] * 100, "%", "HP isentropic efficiency", g, 1)
    R.ch("eta_v_lp", acc["eta_v_lp"] * 100, "%", "LP volumetric efficiency", g, 1)
    R.ch("eta_v_hp", acc["eta_v_hp"] * 100, "%", "HP volumetric efficiency", g, 1)
    R.ch("W_lp", acc["W_lp"] * of, "kW", "LP compressor electrical power", g, 2)
    R.ch("W_hp", acc["W_hp"] * of, "kW", "HP compressor electrical power", g, 2)
    R.ch("T_dis_lp", acc["sp3_T"], "°C", "LP discharge temperature", g, 1)
    R.ch("T_dis_hp", acc["sp5_T"], "°C", "HP discharge temperature", g, 1)
    R.ch("Q_shell", acc["Q_shell"] * of, "kW", "Compressor shell heat loss", g, 2)
    R.ch("starts", H["starts"], "1/h", "Compressor starts", g, 0)
    R.ch("on_frac", of * 100, "%", "Run fraction", g, 0)
    g = "Evaporator & defrost"
    R.ch("Q_e", H["Q_e_kwh"], "kW", "Evaporator duty", g, 2)
    R.ch("approach_e", acc["approach_e"], "K", "Air-to-evaporating approach", g, 1)
    R.ch("m_air", acc["m_air"] * of, "kg/s", "Coil air mass flow", g, 2)
    R.ch("fan", acc["fan"] * 100 * (of > 0), "%", "Fan speed", g, 0)
    R.ch("W_fan", H["W_fan_kwh"], "kW", "Fan electrical power", g, 3)
    R.ch("T_air_off", np.where(on, acc["T_air_out"], Ta), "°C", "Coil air-off temperature", g, 1)
    R.ch("shr", acc["shr"], "–", "Coil sensible heat ratio", g, 2)
    R.ch("condensate", H["water_kg"], "kg/h", "Condensate / frost deposition", g, 2)
    R.ch("frost_kg", H["frost_kg"], "kg", "Frost mass on coil", g, 2)
    R.ch("ua_frac", H["ua"] * 100, "%", "Coil UA (frost-degraded)", g, 0)
    R.ch("defrosts", H["defrosts"], "1/h", "Reverse-cycle defrosts", g, 0)
    R.ch("Q_def", H["Q_def_kwh"], "kWh", "Defrost heat drawn from stores", g, 2)
    g = "Condenser & primary"
    R.ch("Q_c", H["Q_c_kwh"], "kW", "Condenser heat output", g, 2)
    R.ch("approach_c", acc["approach_c"], "K", "Condensing-to-water-out approach", g, 1)
    R.ch("T_w_in", Tw_in, "°C", "Primary water to condenser", g, 1)
    R.ch("T_w_out", np.where(on, acc["T_w_out"], np.nan), "°C", "Primary water from condenser", g, 1)
    R.ch("mode_dhw", H["mode_dhw"] * 100, "%", "Time in DHW mode", g, 0)
    g = "Performance"
    cop = np.where(H["W_comp_kwh"] + H["W_fan_kwh"] > 0, H["Q_c_kwh"] / np.maximum(H["W_comp_kwh"] + H["W_fan_kwh"], 1e-9), np.nan)
    R.ch("cop", cop, "–", "Unit COP (incl. fans, defrost)", g, 2)
    R.ch("cop_cycle", acc["COP_cycle"], "–", "Cycle COP (compressors only)", g, 2)
    R.ch("carnot", acc["carnot"], "–", "Carnot COP Tc/(Tc−Te)", g, 2)
    R.ch("eta_carnot", acc["eta_carnot"] * 100, "%", "Second-law (Carnot) efficiency", g, 1)
    R.ch("eta_ex", acc["eta_ex"] * 100, "%", "Exergy efficiency", g, 1)
    cumQ = np.cumsum(H["Q_c_kwh"]) + np.cumsum(H["W_backup_kwh"] + H["W_imm_kwh"])
    cumW = np.cumsum(H["W_total_kwh"])
    R.ch("spf_run", np.where(cumW > 0, cumQ / np.maximum(cumW, 1e-9), np.nan), "–", "Running SPF (H4 boundary)", g, 2)
    g = "Exergy destruction"
    for k, lbl in [("X_lp", "LP compressors"), ("X_hp", "HP compressor"), ("X_cond", "Condenser"),
                   ("X_evap", "Evaporator"), ("X_hpeev", "HP expansion valve"), ("X_lpeev", "LP expansion valve"),
                   ("X_flash", "Flash vessel + mixing"), ("X_lines", "Suction line"), ("X_fan", "Fans"),
                   ("Ex_air_out", "Cold exhaust air (loss)"), ("Ex_prod", "Product exergy to water")]:
        R.ch(k, acc[k] * of, "kW", lbl, g, 3)
    g = "Stores"
    for j in range(Tb.shape[1]):
        R.ch(f"buf_T{j + 1}", Tb[:, j], "°C", f"Buffer node {j + 1} (top=1)", "Buffer tank nodes", 1)
    for j in range(Td.shape[1]):
        R.ch(f"dhw_T{j + 1}", Td[:, j], "°C", f"DHW cylinder node {j + 1} (top=1)", "DHW cylinder nodes", 1)
    R.ch("buf_soc", H["buf_soc"], "%", "Buffer state of charge", g, 0)
    R.ch("buf_mix", H["buf_mix"], "–", "Buffer MIX number", g, 2)
    R.ch("buf_loss", H["buf_loss_kwh"] * 1e3, "W", "Buffer standing loss", g, 0)
    R.ch("dhw_soc", H["dhw_soc"], "%", "DHW state of charge", g, 0)
    R.ch("dhw_loss", H["dhw_loss_kwh"] * 1e3, "W", "DHW standing loss", g, 0)
    R.ch("dhw_draw", H["dhw_draw_l"], "L/h", "DHW draw (55 °C equivalent)", g, 0)
    R.ch("dhw_energy", H["dhw_energy_kwh"], "kW", "DHW energy delivered", g, 2)
    R.ch("T_tap", H["T_tap"], "°C", "DHW outlet temperature", g, 1)
    R.ch("T_mains", H["T_mains"], "°C", "Cold mains temperature", g, 1)
    g = "Building"
    R.ch("T_room", H["T_air_room"], "°C", "Indoor air temperature", g, 2)
    R.ch("T_op", H["T_op"], "°C", "Operative temperature", g, 2)
    R.ch("T_mass", H["T_mass"], "°C", "Building thermal mass temperature", g, 2)
    R.ch("Q_need", H["Q_need"], "kW", "Space-heating need (ideal)", g, 2)
    R.ch("Q_emit", H["Q_emit"], "kW", "Radiator output", g, 2)
    R.ch("T_flow_set", H["T_flow_set"], "°C", "Weather-compensated flow setpoint", g, 1)
    R.ch("T_flow", H["T_flow"], "°C", "Radiator flow temperature", g, 1)
    R.ch("T_ret", H["T_ret"], "°C", "Radiator return temperature", g, 1)
    R.ch("unmet_K", H["unmet_K"], "K", "Comfort deficit below setpoint", g, 2)
    R.ch("phi_sol", info["phi_sol"] / 1e3, "kW", "Solar gains through glazing", g, 2)
    R.ch("phi_int", info["gains"] / 1e3, "kW", "Internal gains", g, 2)
    g = "Electrical"
    R.ch("W_comp", H["W_comp_kwh"], "kW", "Compressors (incl. defrost)", g, 2)
    R.ch("W_pump", H["W_pump_kwh"], "kW", "Pumps", g, 3)
    R.ch("W_aux", H["W_aux_kwh"], "kW", "Controls + crankcase heaters", g, 3)
    R.ch("W_backup", H["W_backup_kwh"], "kW", "Backup elements", g, 2)
    R.ch("W_imm", H["W_imm_kwh"], "kW", "Legionella immersion", g, 2)
    R.ch("W_total", H["W_total_kwh"], "kW", "Total site electrical demand", g, 2)
    cost = H["W_total_kwh"] * gr.price.to_numpy() / 100
    co2 = H["W_total_kwh"] * gr.ci.to_numpy() / 1000
    R.ch("cost", cost, "£/h", "Electricity cost", g, 3)
    R.ch("co2", co2, "kg/h", "Operational CO₂", g, 3)
    R.ch("cum_cost", np.cumsum(cost), "£", "Cumulative cost", g, 0)
    R.ch("cum_co2", np.cumsum(co2) / 1000, "t", "Cumulative CO₂", g, 2)
    R.ch("cum_heat", cumQ / 1000, "MWh", "Cumulative heat delivered", g, 2)
    R.ch("blocked", H["blocked"], "–", "Price-block active", "Control", 0)
    R.ch("boost", H["boost"], "–", "Cheap-price boost active", "Control", 0)
    R.ch("map_ok", H["map_ok"] * 100, "%", "Operating point inside solved map", "Control", 0)

    # start the viewer at the hour of peak condenser output in the coldest week
    R.start = int(np.argmax(np.where(np.arange(n) < 24 * 60, H["Q_c_kwh"] - 0.01 * np.abs(Ta - Ta.min()), -1e9)))
    # ---- KPIs ----
    Qsh, Qdhw = H["Q_sh_kwh"].sum(), H["Q_dhw_kwh"].sum()
    Qhp = H["Q_c_kwh"].sum()
    Wc, Wf, Wp, Wa, Wb, Wi = (H[k].sum() for k in ["W_comp_kwh", "W_fan_kwh", "W_pump_kwh", "W_aux_kwh",
                                                   "W_backup_kwh", "W_imm_kwh"])
    Wt = H["W_total_kwh"].sum()
    Q_use = Qhp + Wb + Wi - H["Q_def_kwh"].sum()
    gas_kwh = (H["Q_emit"].sum() + H["dhw_energy_kwh"].sum()) / 0.88
    k = R.kpi
    k("SCOP (H2: compressors + fans)", Qhp / (Wc + Wf), "–", "Seasonal performance", 2)
    k("SPF H4 (incl. backup, pumps, aux)", Q_use / Wt, "–", "Seasonal performance", 2)
    k("Heat delivered by heat pump", Qhp / 1000, "MWh", "Energy", 1)
    k("  of which space heating", Qsh / 1000, "MWh", "Energy", 1)
    k("  of which DHW", Qdhw / 1000, "MWh", "Energy", 1)
    k("Radiator heat to building", H["Q_emit"].sum() / 1000, "MWh", "Energy", 1)
    k("DHW energy at taps", H["dhw_energy_kwh"].sum() / 1000, "MWh", "Energy", 1)
    k("Store standing losses", (H["buf_loss_kwh"].sum() + H["dhw_loss_kwh"].sum()) / 1000, "MWh", "Energy", 2)
    k("Electricity, total", Wt / 1000, "MWh", "Energy", 1)
    k("  compressors", Wc / 1000, "MWh", "Energy", 1)
    k("  fans / pumps / aux", (Wf + Wp + Wa) / 1000, "MWh", "Energy", 2)
    k("  backup + legionella", (Wb + Wi) / 1000, "MWh", "Energy", 2)
    k("Peak site demand", H["W_total_kwh"].max(), "kW", "Energy", 1)
    k("Electricity cost (Agile)", cost.sum(), "£", "Cost & carbon", 0)
    k("Average price paid", cost.sum() / Wt * 100, "p/kWh", "Cost & carbon", 2)
    k("Agile year-average price", gr.price.mean(), "p/kWh", "Cost & carbon", 2)
    k("Gas boiler counterfactual cost", gas_kwh * grid.GAS_PRICE_P_KWH / 100, "£", "Cost & carbon", 0)
    k("Operational CO₂", co2.sum() / 1000, "t", "Cost & carbon", 2)
    k("Carbon intensity of heat", co2.sum() / Q_use * 1000, "gCO₂/kWh", "Cost & carbon", 0)
    k("Gas boiler counterfactual CO₂", gas_kwh * grid.GAS_CARBON_G_KWH / 1e6, "t", "Cost & carbon", 1)
    k("Design heat loss", info["Q_design"] / 1000, "kW", "Design", 1)
    k("Heat loss coefficient", info["H_total"] / 1000, "kW/K", "Design", 2)
    k("Compressor run hours", H["on_frac"].sum(), "h", "Operation", 0)
    k("Compressor starts", H["starts"].sum(), "", "Operation", 0)
    k("Reverse-cycle defrosts", H["defrosts"].sum(), "", "Operation", 0)
    k("Condensate + frost removed", H["water_kg"].sum() / 1000, "m³", "Operation", 1)
    k("Hours in DHW mode", (H["mode_dhw"] * H["on_frac"]).sum(), "h", "Operation", 0)
    k("Hours at max LP speed", float(((H["f_cmd"] > 95) & on).sum()), "h", "Operation", 0)
    k("Max HP discharge temperature", np.nanmax(np.where(on, acc["sp5_T"], np.nan)), "°C", "Operation", 1)
    k("Min evaporating temperature", np.nanmin(np.where(on, acc["Te"], np.nan)), "°C", "Operation", 1)
    k("Mean injection ratio (running)", np.nanmean(np.where(on, acc["inj_ratio"], np.nan)), "–", "Operation", 3)
    k("Unmet occupied hours (air > 1 K below)", float((H["unmet_K"] > 0).sum()), "h", "Comfort", 0)
    k("Mean operative temp, occupied heating hours", float(np.mean(H["T_op"][(H["Q_need"] > 0) & np.isin(wx["hour_local"], range(7, 23))])), "°C", "Comfort", 1)
    k("Min indoor temperature", H["T_air_room"].min(), "°C", "Comfort", 1)
    k("Min DHW outlet temperature", H["T_tap"].min(), "°C", "Comfort", 1)
    X_keys = ["X_lp", "X_hp", "X_cond", "X_evap", "X_hpeev", "X_lpeev", "X_flash", "X_lines", "X_fan", "Ex_air_out"]
    Xsum = {kk: float(np.nansum(acc[kk] * of)) for kk in X_keys + ["Ex_prod"]}
    k("Annual exergy efficiency", 100 * Xsum["Ex_prod"] / max(1e-9, (Wc + Wf)), "%", "Exergy", 1)
    for kk, lbl in [("X_lp", "LP compressors"), ("X_hp", "HP compressor"), ("X_cond", "Condenser"),
                    ("X_evap", "Evaporator"), ("X_hpeev", "HP EEV"), ("X_lpeev", "LP EEV"), ("X_flash", "Flash + mixing")]:
        k(f"Exergy destroyed · {lbl}", Xsum[kk] / 1000, "MWh", "Exergy", 2)

    fl = Fluid("Propane")
    R.diagrams.append({
        "type": "ph", "title": "R290 log P–h", "fluid": "Propane", "dome": fl.dome(70, 233.0),
        "paths": [["10", "1", "2", "3", "4", "5", "6", "7"], ["7", "9", "10"], ["7", "8", "4"]],
        "labels": list(SP_NAMES)})
    R.diagrams.append({
        "type": "ts", "title": "R290 T–s", "fluid": "Propane", "dome": fl.dome(70, 233.0),
        "paths": [["10", "1", "2", "3", "4", "5", "6", "7"], ["7", "9", "10"], ["7", "8", "4"]]})
    R.diagrams.append({
        "type": "profile", "title": "Store temperature profiles", "xLabel": "°C", "yLabel": "height (top → bottom)",
        "series": [{"label": "Buffer", "keys": [f"buf_T{j + 1}" for j in range(Tb.shape[1])], "color": "#c2410c"},
                   {"label": "DHW", "keys": [f"dhw_T{j + 1}" for j in range(Td.shape[1])], "color": "#2f5bd3"}]})
    R.diagrams.append({
        "type": "bars", "title": "Exergy destruction now (kW)",
        "items": [{"key": kk, "label": lbl} for kk, lbl in [
            ("X_lp", "LP comp"), ("X_hp", "HP comp"), ("X_cond", "Condenser"), ("X_evap", "Evaporator"),
            ("X_hpeev", "HP EEV"), ("X_lpeev", "LP EEV"), ("X_flash", "Flash"), ("X_fan", "Fans"),
            ("Ex_air_out", "Exhaust"), ("Ex_prod", "Product")]]})
    return R, sc


if __name__ == "__main__":
    import time
    t = time.time()
    pm = build_map()
    print("map", pm.data.shape, "coverage %.1f%%" % (pm.coverage() * 100), "%.0fs" % (time.time() - t))
    for key in (sys.argv[1:] or SCENARIOS):
        t = time.time()
        R, sc = export(key, pm)
        print(key, "%.0fs" % (time.time() - t))
        for kp in R.kpis:
            print(f"  {kp['label']:<40} {kp['value']:.3f} {kp['unit']}")
