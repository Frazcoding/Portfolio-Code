"""Generic single-stage air-source heat pump cycle (inverter compressor, air coil, plate condenser).

State points:
  1 evaporator outlet   2 compressor suction   3 compressor discharge
  4 condenser outlet    5 evaporator inlet (after EEV)
Unknowns (Te, Tc) close the coil and condenser balances (fsolve). Signature matches PerfMap:
solve(params, point{T_air, RH, T_w_in, f, ua}, guess) -> (outputs, solution)
"""
import math

from scipy.optimize import fsolve

from . import hx
from .thermo import CompressorMap, Fluid, compress, exergy

_F = {}
SP = ["1", "2", "3", "4", "5"]


def _fluid(n):
    if n not in _F:
        _F[n] = Fluid(n)
    return _F[n]


def ex_thermal(cp, T, T0):
    return cp * ((T - T0) - T0 * math.log(T / T0))


def solve(p, pt, guess=None):
    F = _fluid(p["fluid"])
    Ta_c = pt["T_air"]
    Ta = Ta_c + 273.15
    T0 = Ta
    pv = pt["RH"] / 100 * hx.psat_w(Ta_c)
    w_in = 0.62198 * pv / (101325.0 - pv)
    Tw_in = pt["T_w_in"] + 273.15
    f = pt["f"]
    cm = CompressorMap(**p["comp"])
    fan = min(1.0, max(p["fan_min"], p["fan_min"] + (1 - p["fan_min"]) * (f - cm.f_min) / (cm.f_max - cm.f_min)))
    m_air = p["m_air_nom"] * fan
    UA_e = p["UA_e"] * pt["ua"] * fan ** 0.6
    m_w, UA_c = p["m_w"], p["UA_c"]
    load = (f / cm.f_nom) ** 1.8

    def states(x):
        Te, Tc = x
        Pe, Pc = F.Psat(Te), F.Psat(Tc)
        s1 = F.superheated(Pe, p["SH"])
        s2 = F.superheated(Pe - p["dp_suc"] * load, p["SH"] + p["suction_gain"])
        c = compress(F, cm, s2, Pc + p["dp_dis"] * load, f)
        s3 = c["st"]
        s4 = F.subcooled(Pc - p["dp_cond"] * load, p["SC"])
        s5 = F.PH(Pe + p["dp_evap"] * load, s4.h)
        return locals()

    def resid(x):
        d = states(x)
        T_ref = 0.5 * (x[0] + F.Tsat(d["s5"].P)) - 273.15
        q_air = hx.coil_cooling(Ta_c, w_in, m_air, UA_e, T_ref)[0]
        m = d["c"]["m"]
        Q_e = m * (d["s1"].h - d["s5"].h)
        Q_c = m * (d["s3"].h - d["s4"].h)
        Q_cw = (1 - math.exp(-UA_c / (m_w * hx.CP_W))) * m_w * hx.CP_W * (x[1] - Tw_in)
        return [(Q_e - q_air) / 1e4, (Q_c - Q_cw) / 1e4]

    guesses = ([guess] if guess else []) + [[Ta - a, Tw_in + b] for a, b in [(8, 6), (12, 9), (5, 4), (18, 12)]]
    msg = ""
    for g in guesses:
        try:
            sol, info, ier, msg = fsolve(resid, g, full_output=True, xtol=1e-8)
        except Exception as e:
            ier, msg = 0, str(e)
        if ier == 1 and max(abs(v) for v in info["fvec"]) < 1e-4 and sol[0] < Ta and sol[1] > Tw_in:
            break
    else:
        raise RuntimeError(msg)
    d = states(sol)
    Te, Tc = sol
    m = d["c"]["m"]
    T_ref = 0.5 * (Te + F.Tsat(d["s5"].P)) - 273.15
    q_air, Ta_out, w_out, water, shr = hx.coil_cooling(Ta_c, w_in, m_air, UA_e, T_ref)
    Q_e = m * (d["s1"].h - d["s5"].h)
    Q_c = m * (d["s3"].h - d["s4"].h)
    W_c = d["c"]["W_elec"]
    W_fan = p["W_fan_max"] * fan ** 3
    Tw_out = Tw_in + Q_c / (m_w * hx.CP_W)
    if d["s3"].Tc > p["T_dis_max"] or Tc > F.Tcrit - 3:
        raise RuntimeError("envelope")
    h0, s0 = F.dead_state(T0)
    st = {k: d[f"s{k}"] for k in SP}
    ex = {k: exergy(v, h0, s0, T0) for k, v in st.items()}
    exw1, exw2 = ex_thermal(hx.CP_W, Tw_in, T0), ex_thermal(hx.CP_W, Tw_out, T0)
    exa2 = ex_thermal(hx.CP_A, Ta_out + 273.15, T0)
    X = {"X_comp": W_c - m * (ex["3"] - ex["2"]), "X_cond": m * (ex["3"] - ex["4"]) - m_w * (exw2 - exw1),
         "X_evap": m * (ex["5"] - ex["1"]) - m_air * exa2, "X_eev": m * (ex["4"] - ex["5"]), "X_lines": m * (ex["1"] - ex["2"]),
         "X_fan": W_fan, "Ex_air_out": m_air * exa2, "Ex_prod": m_w * (exw2 - exw1)}
    out = {"Q_e": Q_e / 1e3, "Q_c": Q_c / 1e3, "W_comp": W_c / 1e3, "W_fan": W_fan / 1e3, "W_tot": (W_c + W_fan) / 1e3,
           "COP": Q_c / (W_c + W_fan), "m_ref": m, "Te": Te - 273.15, "Tc": Tc - 273.15, "Pe": F.Psat(Te) / 1e5,
           "Pc": F.Psat(Tc) / 1e5, "pr": d["c"]["pr"], "eta_is": d["c"]["eta_is"], "eta_v": d["c"]["eta_v"],
           "T_dis": d["s3"].Tc, "T_air_out": Ta_out, "w_out": w_out * 1e3, "water": water, "shr": shr, "fan": fan,
           "m_air": m_air, "T_w_out": Tw_out - 273.15, "lift": Tc - Te, "carnot": Tc / (Tc - Te),
           "eta_ex": X["Ex_prod"] / (W_c + W_fan)}
    out["eta_carnot"] = (Q_c / W_c) / out["carnot"]
    out.update({k: v / 1e3 for k, v in X.items()})
    mm = dict.fromkeys(SP, m)
    for k in SP:
        s = st[k]
        out[f"sp{k}_T"], out[f"sp{k}_P"], out[f"sp{k}_h"] = s.Tc, s.P / 1e5, s.h / 1e3
        out[f"sp{k}_s"], out[f"sp{k}_x"], out[f"sp{k}_m"], out[f"sp{k}_ex"] = s.s / 1e3, s.x, mm[k], ex[k] / 1e3
    return out, list(sol)
