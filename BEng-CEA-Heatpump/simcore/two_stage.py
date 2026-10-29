"""Generic two-stage vapour-compression cycle with open flash economiser (air or liquid source).

Air source: point = {T_air, RH, T_w_in, f, ua}. Liquid source (brine/water evaporator):
point = {T_src_in, T_w_in, f}; params m_src, cp_src, UA_e.

Refrigerant circuit (numbering used everywhere in the viewer):
  1  evaporator outlet (superheated, EEV holds SH)
  2  LP compressor suction (after suction line dP and heat gain)
  3  LP compressor discharge (intermediate pressure)
  4  HP compressor suction (LP discharge mixed with flash vapour)
  5  HP compressor discharge
  6  condenser outlet (subcooled liquid)
  7  HP EEV outlet, two-phase into flash vessel
  8  flash vessel saturated vapour (injection)
  9  flash vessel saturated liquid
  10 LP EEV outlet / evaporator inlet
Secondary: W1/W2 condenser water in/out, A1/A2 coil air on/off.

Control: the LP pair runs at the commanded speed f. The HP inverter holds the
intermediate pressure at the optimum Pi = k*sqrt(Pe*Pc); its speed then follows
in closed form from the flash-vessel mass balance. If that speed falls outside
the HP inverter range, the HP speed is clamped and Pi floats instead.
Unknowns (Te, Tc[, Ti]) close the evaporator and condenser balances (and the
flash-vessel mass balance in floating mode); scipy.optimize.fsolve, warm start.
"""
import math

from scipy.optimize import fsolve

from . import hx
from .thermo import CompressorMap, Fluid, compress, exergy

_FLUIDS = {}
SP = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]


def _fluid(name):
    if name not in _FLUIDS:
        _FLUIDS[name] = Fluid(name)
    return _FLUIDS[name]


def ex_thermal(cp, T, T0):
    return cp * ((T - T0) - T0 * math.log(T / T0))


def solve(p, pt, guess=None):
    F = _fluid(p["fluid"])
    liquid = p.get("source") == "liquid"
    Ta_c = pt["T_src_in"] if liquid else pt["T_air"]
    Ta = Ta_c + 273.15
    T0 = p.get("T0", Ta)
    rh = 0.5 if liquid else pt["RH"] / 100
    p_atm = 101325.0
    pv = rh * hx.psat_w(Ta_c)
    w_in = 0.62198 * pv / (p_atm - pv)
    Tw_in = pt["T_w_in"] + 273.15
    f = pt["f"]
    ua = 1.0 if liquid else pt["ua"]
    lp = CompressorMap(**p["lp"])
    hpm = CompressorMap(**p["hp"])
    f_hp = f * p["hp_speed_ratio"]
    fan = p["fan_min"] + (1 - p["fan_min"]) * (f - lp.f_min) / (lp.f_max - lp.f_min)
    fan = min(1.0, max(p["fan_min"], fan))
    if liquid:
        fan = 1.0
        m_air = p["m_src"]
        UA_e = p["UA_e"]
    else:
        m_air = p["m_air_nom"] * fan
        UA_e = p["UA_e"] * ua * fan ** 0.6

    def source_duty(T_ref):
        if liquid:
            C = p["m_src"] * p["cp_src"]
            q = (1 - math.exp(-UA_e / C)) * C * (Ta_c - T_ref)
            return q, Ta_c - q / C, w_in, 0.0, 1.0
        return hx.coil_cooling(Ta_c, w_in, m_air, UA_e, T_ref, p_atm)
    m_w = p["m_w"]
    UA_c = p["UA_c"]
    SH, SC = p["SH"], p["SC"]
    load = (f / lp.f_nom) ** 1.8

    mode = {"floating": False, "f_hp": f_hp}

    def states(x):
        Te, Tc = x[0], x[1]
        Pe = F.Psat(Te)
        Pc = F.Psat(Tc)
        Pi = F.Psat(x[2]) if mode["floating"] else p["pi_factor"] * math.sqrt(Pe * Pc)
        s1 = F.superheated(Pe, SH)
        s2 = F.PT(Pe - p["dp_suc"] * load, s1.T + p["suction_gain"])
        c_lp = compress(F, lp, s2, Pi, f)
        s3 = c_lp["st"]
        s8 = F.PQ(Pi, 1.0)
        s9 = F.PQ(Pi, 0.0)
        Pc_out = Pc - p["dp_cond"] * load
        s6 = F.subcooled(Pc_out, SC)
        s7 = F.PH(Pi, s6.h)
        x7 = min(0.95, max(0.0, (s6.h - s9.h) / (s8.h - s9.h)))
        m_lp = c_lp["m"]
        if p.get("intercooler") == "open":
            # LP discharge bubbles through the intermediate liquid: HP suction is saturated vapour and the
            # vessel balance m_hp*h7 + m_lp*h3 = m_lp*h9 + m_hp*h8 sets the HP flow (classic NH3 two-stage)
            m_hp = m_lp * (s3.h - s9.h) / max(s8.h - s6.h, 1.0)
            s4 = s8
        else:
            m_hp = m_lp / (1 - x7)
            s4 = F.PH(Pi, (m_lp * s3.h + (m_hp - m_lp) * s8.h) / m_hp)
        if mode["floating"]:
            fh = mode["f_hp"]
        else:
            # m = (A*f - leak*f_nom) * disp/f_nom * rho  ->  speed for the required m_hp
            pr = (Pc + p["dp_dis"] * load) / Pi
            A = 1 - hpm.clearance * (pr ** (1 / hpm.n_poly) - 1)
            fh = (m_hp / (hpm.disp_m3h / 3600 / hpm.f_nom * s4.rho) + hpm.leak * hpm.f_nom) / A
            fh = min(max(fh, 1.0), 300.0)
        c_hp = compress(F, hpm, s4, Pc + p["dp_dis"] * load, fh)
        s5 = c_hp["st"]
        s10 = F.PH(Pe + p["dp_evap"] * load, s9.h)
        return locals()

    def resid(x):
        d = states(x)
        Te = x[0]
        T_ref = 0.5 * (Te + F.Tsat(d["s10"].P)) - 273.15
        q_air = source_duty(T_ref)[0]
        Q_e = d["m_lp"] * (d["s1"].h - d["s10"].h)
        Q_c = d["m_hp"] * (d["s5"].h - d["s6"].h)
        eps_c = 1 - math.exp(-UA_c / (m_w * hx.CP_W))
        Q_cw = eps_c * m_w * hx.CP_W * (x[1] - Tw_in)
        r = [(Q_e - q_air) / 1e4, (Q_c - Q_cw) / 1e4]
        if mode["floating"]:
            r.append((d["c_hp"]["m"] - d["m_hp"]) / max(d["m_hp"], 1e-3))
        return r

    def run(n):
        guesses = [guess[:n]] if guess is not None and len(guess) >= n else []
        for dte, dtc in [(9, 7), (14, 10), (6, 5), (20, 14)]:
            Te0, Tc0 = Ta - dte, Tw_in + dtc
            guesses.append([Te0, Tc0, F.Tsat(math.sqrt(F.Psat(Te0) * F.Psat(Tc0)))][:n])
        msg = "no guess"
        for g in guesses:
            try:
                sol, info, ier, msg = fsolve(resid, g, full_output=True, xtol=1e-7)
            except Exception as e:  # CoolProp out of range during iteration
                ier, msg = 0, str(e)
            if ier == 1 and max(abs(v) for v in info["fvec"]) < 1e-3:
                return list(sol)
        raise RuntimeError(msg)

    sol = run(2)
    d = states(sol)
    fh = d["fh"]
    if not (hpm.f_min <= fh <= hpm.f_max):
        mode["floating"] = True
        mode["f_hp"] = min(max(fh, hpm.f_min), hpm.f_max)
        sol = run(3)
        d = states(sol)
    Te, Tc = sol[0], sol[1]
    Ti = F.Tsat(d["Pi"])
    T_ref = 0.5 * (Te + F.Tsat(d["s10"].P)) - 273.15
    q_air, Ta_out_c, w_out, water, shr = source_duty(T_ref)
    m_lp, m_hp = d["m_lp"], d["m_hp"]
    m_vap = m_hp - m_lp
    Q_e = m_lp * (d["s1"].h - d["s10"].h)
    Q_c = m_hp * (d["s5"].h - d["s6"].h)
    Tw_out = Tw_in + Q_c / (m_w * hx.CP_W)
    W_fan = p["W_fan_max"] * fan ** 3 if not liquid else p.get("W_src_pump", 0.0)
    W_lp, W_hp = d["c_lp"]["W_elec"], d["c_hp"]["W_elec"]
    W_tot = W_lp + W_hp + W_fan
    if d["s5"].Tc > p["T_dis_max"] or Tc > F.Tcrit - 3 or Te < 228:
        raise RuntimeError("outside compressor envelope")

    h0, s0 = F.dead_state(T0)
    st = {k: d[f"s{k}"] for k in SP}
    ex = {k: exergy(v, h0, s0, T0) for k, v in st.items()}
    m = {"1": m_lp, "2": m_lp, "3": m_lp, "4": m_hp, "5": m_hp, "6": m_hp, "7": m_hp,
         "8": m_vap, "9": m_lp, "10": m_lp}
    exw1 = ex_thermal(hx.CP_W, Tw_in, T0)
    exw2 = ex_thermal(hx.CP_W, Tw_out, T0)
    exa2 = ex_thermal(p["cp_src"] if liquid else hx.CP_A, Ta_out_c + 273.15, T0)
    exa1 = ex_thermal(p["cp_src"] if liquid else hx.CP_A, Ta, T0)
    X = {
        "X_lp": W_lp - m_lp * (ex["3"] - ex["2"]),
        "X_hp": W_hp - m_hp * (ex["5"] - ex["4"]),
        "X_cond": m_hp * (ex["5"] - ex["6"]) - m_w * (exw2 - exw1),
        "X_evap": m_lp * (ex["10"] - ex["1"]) + m_air * (exa1 - exa2),
        "X_hpeev": m_hp * (ex["6"] - ex["7"]),
        "X_lpeev": m_lp * (ex["9"] - ex["10"]),
        "X_flash": m_hp * ex["7"] + m_lp * ex["3"] - m_lp * ex["9"] - m_hp * ex["4"],
        "X_lines": m_lp * (ex["1"] - ex["2"]),
        "X_fan": W_fan,
        "Ex_air_out": m_air * exa2,
        "Ex_src_in": m_air * exa1,
        "Ex_prod": m_w * (exw2 - exw1),
    }
    out = {
        "Q_e": Q_e / 1e3, "Q_c": Q_c / 1e3, "W_lp": W_lp / 1e3, "W_hp": W_hp / 1e3, "W_fan": W_fan / 1e3,
        "W_tot": W_tot / 1e3, "COP": Q_c / W_tot, "COP_cycle": Q_c / (W_lp + W_hp),
        "m_lp": m_lp, "m_hp": m_hp, "m_vap": m_vap, "inj_ratio": m_vap / m_lp,
        "Te": Te - 273.15, "Tc": Tc - 273.15, "Ti": Ti - 273.15,
        "Pe": F.Psat(Te) / 1e5, "Pc": F.Psat(Tc) / 1e5, "Pi": F.Psat(Ti) / 1e5,
        "eta_is_lp": d["c_lp"]["eta_is"], "eta_is_hp": d["c_hp"]["eta_is"],
        "eta_v_lp": d["c_lp"]["eta_v"], "eta_v_hp": d["c_hp"]["eta_v"],
        "pr_lp": d["c_lp"]["pr"], "pr_hp": d["c_hp"]["pr"],
        "Q_shell": (d["c_lp"]["Q_loss"] + d["c_hp"]["Q_loss"]) / 1e3,
        "T_air_out": Ta_out_c, "w_out": w_out * 1e3, "water": water, "shr": shr, "m_air": m_air, "fan": fan,
        "T_w_out": Tw_out - 273.15, "x7": d["x7"],
        "approach_c": Tc - Tw_out, "approach_e": Ta - Te,
        "eta_ex": X["Ex_prod"] / (W_tot + X["Ex_src_in"]), "f_hp": d["fh"], "pi_float": float(mode["floating"]),
        "lift": Tc - Te, "carnot": Tc / (Tc - Te),
    }
    out["eta_carnot"] = out["COP_cycle"] / out["carnot"]
    out.update({k: v / 1e3 for k, v in X.items()})
    for k in SP:
        s = st[k]
        out[f"sp{k}_T"] = s.Tc
        out[f"sp{k}_P"] = s.P / 1e5
        out[f"sp{k}_h"] = s.h / 1e3
        out[f"sp{k}_s"] = s.s / 1e3
        out[f"sp{k}_x"] = s.x
        out[f"sp{k}_m"] = m[k]
        out[f"sp{k}_ex"] = ex[k] / 1e3
    return out, list(sol) + ([] if mode["floating"] else [Ti])


