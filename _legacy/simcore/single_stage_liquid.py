"""Single-stage vapour-compression heat pump on a liquid source (brine/water evaporator, water condenser).

For low-lift duty (ground or river source to 25-45 C heating water) where a two-stage economised cycle brings no
benefit. Signature matches PerfMap: solve(params, point{T_src_in, T_w_in, f}, guess) -> (outputs, solution).

State points: 1 evaporator outlet, 2 compressor suction, 3 compressor discharge, 4 condenser outlet,
5 evaporator inlet (after EEV). Unknowns (Te, Tc) close the evaporator and condenser balances (fsolve).
"""
import math

from scipy.optimize import fsolve

from . import hx
from .thermo import CompressorMap, Fluid, compress

_F = {}


def _fluid(n):
    if n not in _F:
        _F[n] = Fluid(n)
    return _F[n]


def solve(p, pt, guess=None):
    F = _fluid(p["fluid"])
    Ts = pt["T_src_in"]
    Tw_in = pt["T_w_in"] + 273.15
    f = pt["f"]
    cm = CompressorMap(**p["comp"])
    load = (f / cm.f_nom) ** 1.8
    C_src = p["m_src"] * p["cp_src"]
    eps_e = 1 - math.exp(-p["UA_e"] / C_src)
    eps_c = 1 - math.exp(-p["UA_c"] / (p["m_w"] * hx.CP_W))

    def states(x):
        Te, Tc = x
        Pe, Pc = F.Psat(Te), F.Psat(Tc)
        s1 = F.superheated(Pe, p["SH"])
        s2 = F.PT(Pe - p["dp_suc"] * load, s1.T + p["suction_gain"])
        c = compress(F, cm, s2, Pc + p["dp_dis"] * load, f)
        s4 = F.subcooled(Pc - p["dp_cond"] * load, p["SC"])
        s5 = F.PH(Pe + p["dp_evap"] * load, s4.h)
        return s1, s2, c, s4, s5

    def resid(x):
        s1, s2, c, s4, s5 = states(x)
        q_e = c["m"] * (s1.h - s5.h)
        q_c = c["m"] * (c["st"].h - s4.h)
        q_src = eps_e * C_src * (Ts + 273.15 - x[0])
        q_w = eps_c * p["m_w"] * hx.CP_W * (x[1] - Tw_in)
        return [(q_e - q_src) / 1e4, (q_c - q_w) / 1e4]

    guesses = [guess] if guess is not None else []
    guesses += [[Ts + 273.15 - d1, Tw_in + d2] for d1, d2 in ((6, 6), (10, 9), (4, 4), (15, 13))]
    sol = None
    for g in guesses:
        try:
            s, info, ier, _ = fsolve(resid, g, full_output=True, xtol=1e-8)
        except Exception:
            continue
        if ier == 1 and max(abs(v) for v in info["fvec"]) < 1e-3:
            sol = s
            break
    if sol is None:
        raise RuntimeError("no convergence")
    Te, Tc = sol
    s1, s2, c, s4, s5 = states(sol)
    if c["st"].Tc > p["T_dis_max"] or Tc > F.Tcrit - 3 or Te < 228:
        raise RuntimeError("outside compressor envelope")
    m = c["m"]
    Q_e, Q_c = m * (s1.h - s5.h), m * (c["st"].h - s4.h)
    W_src = p.get("W_src_pump", 0.0)
    W_tot = c["W_elec"] + W_src
    out = {"Q_e": Q_e / 1e3, "Q_c": Q_c / 1e3, "W_comp": c["W_elec"] / 1e3, "W_src": W_src / 1e3, "W_tot": W_tot / 1e3,
           "COP": Q_c / W_tot, "COP_cycle": Q_c / c["W_elec"], "Te": Te - 273.15, "Tc": Tc - 273.15,
           "Pe": F.Psat(Te) / 1e5, "Pc": F.Psat(Tc) / 1e5, "T_dis": c["st"].Tc, "m": m, "eta_is": c["eta_is"],
           "eta_v": c["eta_v"], "pr": c["pr"], "T_w_out": Tw_in - 273.15 + Q_c / (p["m_w"] * hx.CP_W),
           "T_src_out": Ts - Q_e / C_src, "lift": Tc - Te, "carnot": Tc / (Tc - Te), "water": 0.0}
    out["eta_carnot"] = out["COP_cycle"] / out["carnot"]
    return out, list(sol)
