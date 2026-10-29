"""Single-stage transcritical CO2 (R744) air-source heat pump with a counterflow water gas cooler.

Signature matches PerfMap: solve(params, point{T_air, RH, T_w_in, f, ua}, guess) -> (outputs, solution).

Circuit: 1 evaporator outlet (superheated), 2 compressor suction (after suction-line dP and heat gain),
3 compressor discharge at the gas-cooler pressure, 4 gas-cooler outlet, 5 evaporator inlet (isenthalpic expansion).

Unlike a subcritical cycle there is no condensing temperature: the high-side pressure is a control variable. Here it
is set to the value that maximises COP at every operating point (golden-section search between `P_gc_min` and
`P_gc_max`, subject to the discharge-temperature limit), which is how CO2 heat-pump controllers are run. The gas
cooler is solved by discretising the counterflow exchanger into equal-enthalpy segments (CO2 properties vary steeply
near the pseudo-critical line, so a single LMTD is not valid) and finding the outlet enthalpy at which the required
UA equals the installed UA. The evaporator uses the same air-coil model (hx.coil_cooling, with frost) as the R717
two-stage cycle, so the two maps are directly comparable.
"""
import math

from scipy.optimize import brentq

from . import hx
from .thermo import CompressorMap, Fluid, compress

_F = {}
NSEG = 10


def _fluid():
    if "CO2" not in _F:
        _F["CO2"] = Fluid("CO2")
    return _F["CO2"]


def _gas_cooler(F, P, h_in, m_r, T_w_in, m_w, UA):
    """Outlet enthalpy of CO2 at pressure P leaving a counterflow gas cooler (water enters at the CO2 outlet end).
    Returns (h_out, T_out, Q, T_w_out)."""
    C_w = m_w * hx.CP_W
    h_min = F.PT(P, T_w_in + 0.05).h          # CO2 cannot leave colder than the incoming water

    def ua_required(h_out):
        Q = m_r * (h_in - h_out)
        ua = 0.0
        T_w = T_w_in                            # water temperature at the CO2-outlet end
        for k in range(NSEG):                   # march from the CO2 outlet towards the inlet
            ha = h_out + (h_in - h_out) * k / NSEG
            hb = h_out + (h_in - h_out) * (k + 1) / NSEG
            Ta, Tb = F.PH(P, ha).T, F.PH(P, hb).T
            dq = m_r * (hb - ha)
            T_w2 = T_w + dq / C_w
            d1, d2 = Ta - T_w, Tb - T_w2
            if d1 <= 0 or d2 <= 0:
                return math.inf                 # temperature cross: needs infinite area
            ua += dq / (d1 if abs(d1 - d2) < 1e-6 else (d1 - d2) / math.log(d1 / d2))
            T_w = T_w2
        return ua

    lo, hi = h_min, h_in - 1.0
    if ua_required(lo) <= UA:                   # exchanger large enough to reach the water inlet temperature
        h_out = lo
    else:
        for _ in range(40):                     # ua_required falls monotonically as h_out rises
            mid = 0.5 * (lo + hi)
            if ua_required(mid) > UA:
                lo = mid
            else:
                hi = mid
        h_out = hi
    Q = m_r * (h_in - h_out)
    return h_out, F.PH(P, h_out).T, Q, T_w_in + Q / C_w


def _cycle(F, p, cm, Te, P_gc, f, Tw_in, m_w):
    load = (f / cm.f_nom) ** 1.8
    Pe = F.Psat(Te)
    s1 = F.superheated(Pe, p["SH"])
    s2 = F.PT(Pe - p["dp_suc"] * load, s1.T + p["suction_gain"])
    c = compress(F, cm, s2, P_gc + p["dp_dis"] * load, f)
    h4, T4, Q_c, Tw_out = _gas_cooler(F, P_gc, c["st"].h, c["m"], Tw_in, m_w, p["UA_gc"])
    s5 = F.PH(Pe + p["dp_evap"] * load, h4)
    return dict(s1=s1, s2=s2, c=c, h4=h4, T4=T4, s5=s5, Q_c=Q_c, Q_e=c["m"] * (s1.h - h4), Tw_out=Tw_out)


def solve(p, pt, guess=None):
    F = _fluid()
    Ta_c = pt["T_air"]
    rh = pt["RH"] / 100
    p_atm = 101325.0
    pv = rh * hx.psat_w(Ta_c)
    w_in = 0.62198 * pv / (p_atm - pv)
    Tw_in = pt["T_w_in"] + 273.15
    f, ua = pt["f"], pt["ua"]
    cm = CompressorMap(**p["comp"])
    fan = p["fan_min"] + (1 - p["fan_min"]) * (f - cm.f_min) / (cm.f_max - cm.f_min)
    fan = min(1.0, max(p["fan_min"], fan))
    m_air = p["m_air_nom"] * fan
    UA_e = p["UA_e"] * ua * fan ** 0.6
    m_w = p["m_w"]
    W_fan = p["W_fan_max"] * fan ** 3

    def at_pressure(P_gc):
        """Evaporator balance closed for Te at a given gas-cooler pressure; returns the cycle dict."""
        def resid(Te):
            d = _cycle(F, p, cm, Te, P_gc, f, Tw_in, m_w)
            q_air = hx.coil_cooling(Ta_c, w_in, m_air, UA_e, Te - 273.15, p_atm)[0]
            return (d["Q_e"] - q_air) / 1e4
        Te = brentq(resid, Ta_c + 273.15 - 40.0, Ta_c + 273.15 - 0.3, xtol=1e-4)
        d = _cycle(F, p, cm, Te, P_gc, f, Tw_in, m_w)
        d["Te"] = Te
        d["W_tot"] = d["c"]["W_elec"] + W_fan
        d["COP"] = d["Q_c"] / d["W_tot"]
        d["ok"] = d["c"]["st"].Tc <= p["T_dis_max"]
        return d

    cache = {}

    def neg_cop(P):
        if P not in cache:
            try:
                d = at_pressure(P)
                cache[P] = (-d["COP"] if d["ok"] else 0.0, d)
            except Exception:
                cache[P] = (0.0, None)
        return cache[P][0]

    # golden-section search for the COP-optimal gas-cooler pressure
    a, b = p["P_gc_min"], p["P_gc_max"]
    g = (math.sqrt(5) - 1) / 2
    x1, x2 = b - g * (b - a), a + g * (b - a)
    f1, f2 = neg_cop(x1), neg_cop(x2)
    while b - a > 0.5e5:
        if f1 < f2:
            b, x2, f2 = x2, x1, f1
            x1 = b - g * (b - a)
            f1 = neg_cop(x1)
        else:
            a, x1, f1 = x1, x2, f2
            x2 = a + g * (b - a)
            f2 = neg_cop(x2)
    best = min((v for v in cache.values() if v[1] is not None and v[0] < 0), key=lambda v: v[0], default=None)
    if best is None:
        raise RuntimeError("no feasible gas-cooler pressure")
    d = best[1]
    P_gc = d["c"]["st"].P - p["dp_dis"] * (f / cm.f_nom) ** 1.8
    Te = d["Te"]
    q_air, Ta_out_c, w_out, water, shr = hx.coil_cooling(Ta_c, w_in, m_air, UA_e, Te - 273.15, p_atm)
    c = d["c"]
    out = {"Q_e": d["Q_e"] / 1e3, "Q_c": d["Q_c"] / 1e3, "W_comp": c["W_elec"] / 1e3, "W_fan": W_fan / 1e3,
           "W_tot": d["W_tot"] / 1e3, "COP": d["COP"], "COP_cycle": d["Q_c"] / c["W_elec"],
           "Te": Te - 273.15, "Pe": F.Psat(Te) / 1e5, "P_gc": P_gc / 1e5, "T_dis": c["st"].Tc,
           "T_gc_out": d["T4"] - 273.15, "approach_gc": d["T4"] - Tw_in, "T_w_out": d["Tw_out"] - 273.15,
           "m": c["m"], "eta_is": c["eta_is"], "eta_v": c["eta_v"], "pr": c["pr"],
           "T_air_out": Ta_out_c, "w_out": w_out * 1e3, "water": water, "shr": shr, "m_air": m_air, "fan": fan}
    return out, [Te, P_gc]
