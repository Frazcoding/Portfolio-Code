"""Steady-state single-stage screw heat pump with economiser port and IHX.

Circuit numbering (viewer state points):
  1  evaporator outlet (sat. vapour + small SH)
  2  compressor suction (after IHX vapour side)
  3  economiser-port pressure, compressed main flow (before mixing)
  4  after mixing with economiser vapour (inside compressor)
  5  compressor discharge
  6  condenser outlet (subcooled)
  7  economiser branch after expansion valve (two-phase, P_econ)
  8  economiser vapour to compressor port
  9  main liquid after economiser subcooler
  10 main liquid after IHX liquid side
  11 evaporator inlet (after main EEV)
Secondary: S1/S2 source in/out, K1/K2 sink in/out.

Sink: either sensible water heated to a fixed outlet temperature (variable sink
flow) or boiling feedwater to saturated steam (isothermal sink at T_sat).
Unknowns (Te, Tc) close evaporator and condenser balances (fsolve, warm start).
"""
import math
import sys
from pathlib import Path

from scipy.optimize import fsolve

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_legacy"))  # frozen simcore v0.1.0
from simcore import hx  # noqa: E402
from simcore.thermo import CompressorMap, Fluid, compress, exergy, lmtd  # noqa: E402

_F = {}
SP = [str(i) for i in range(1, 12)]


def _fluid(n):
    if n not in _F:
        _F[n] = Fluid(n)
    return _F[n]


def ex_w(T, T0):
    return hx.CP_W * ((T - T0) - T0 * math.log(T / T0))


def solve(p, pt, guess=None):
    F = _fluid(p["fluid"])
    W = _fluid("Water")
    Ts_in = pt["T_src_in"] + 273.15
    Tk_in = pt["T_sink_in"] + 273.15
    cap = pt["cap"]
    T0 = p.get("T0", 288.15)
    cm = CompressorMap(**p["comp"])
    f = cm.f_nom * cap
    m_src = p["m_src"]
    steam = p["sink"] == "steam"
    Tk_out = (p["T_steam"] if steam else p["T_sink_out"]) + 273.15

    def states(x):
        Te, Tc = x
        Pe, Pc = F.Psat(Te), F.Psat(Tc)
        Pm = p["econ_ratio"] * math.sqrt(Pe * Pc)
        s1 = F.superheated(Pe, p["SH"])
        s6 = F.subcooled(Pc - p["dp_cond"], p["SC"])
        # economiser (closed subcooler): main liquid cooled to T_sat(Pm) + approach
        Tm_sat = F.Tsat(Pm)
        s7 = F.PH(Pm, s6.h)
        P6 = Pc - p["dp_cond"]
        T9 = min(s6.T, Tm_sat + p["econ_dT"])
        s9 = F.subcooled(P6, F.Tsat(P6) - T9)
        s8 = F.superheated(Pm, 3.0)
        # IHX: liquid 9 -> 10 heats suction 1 -> 2 (effectiveness on vapour side)
        dT2 = p["ihx_eps"] * (s9.T - s1.T)
        Ps = Pe - p["dp_suc"]
        s2 = F.superheated(Ps, s1.T + dT2 - F.Tsat(Ps))
        q_ihx = s2.h - s1.h
        s10 = F.PH(s9.P, s9.h - q_ihx)
        s11 = F.PH(Pe + p["dp_evap"], s10.h)
        c1 = compress(F, cm, s2, Pm, f)
        m = c1["m"]
        s3 = c1["st"]
        m_e = m * (s6.h - s9.h) / max(s8.h - s7.h, 1.0)
        s4 = F.PH(Pm, (m * s3.h + m_e * s8.h) / (m + m_e))
        # second stage of the same screw: volumetric flow is set by the first stage; efficiency only
        cm2 = CompressorMap(**dict(p["comp"], disp_m3h=1e6))
        c2 = compress(F, cm2, s4, Pc + p["dp_dis"], f)
        s5 = F.PH(Pc + p["dp_dis"], s4.h + (c2["st"].h - s4.h))
        return locals()

    def sink_duty(Tc, Q):
        # sink-side film coefficient falls with the (variable) sink flow at part load
        ua = p["UA_c"] * max(0.15, Q / p["Q_design"]) ** 0.6
        if steam:
            return ua * (Tc - Tk_out)
        return ua * lmtd(Tc - Tk_out, Tc - Tk_in)

    def resid(x):
        d = states(x)
        Q_e = d["m"] * (d["s1"].h - d["s11"].h)
        ntu = p["UA_e"] / (m_src * hx.CP_W)
        Q_es = (1 - math.exp(-ntu)) * m_src * hx.CP_W * (Ts_in - x[0])
        mt = d["m"] + d["m_e"]
        Q_c = mt * (d["s5"].h - d["s6"].h)
        ua = p["UA_c"] * max(0.15, Q_c / p["Q_design"]) ** 0.6
        if steam:
            r2 = (Q_c - ua * (x[1] - Tk_out)) / 1e5
        else:
            # two-zone counterflow condenser: desuperheating heats the water from T_mid to the outlet,
            # condensing + subcooling heats it from the inlet to T_mid. Gas-side zone has ~1/3 the U.
            m_w = Q_c / (hx.CP_W * (Tk_out - Tk_in))
            hg = F.PQ(d["Pc"], 1.0).h
            Q_ds = mt * max(d["s5"].h - hg, 0.0)
            Q_cd = Q_c - Q_ds
            T_mid = Tk_out - Q_ds / (m_w * hx.CP_W)
            gap1, gap2 = x[1] - T_mid, d["s5"].T - Tk_out
            if gap1 < 0.05 or gap2 < 0.05:
                r2 = -(min(gap1, gap2) - 0.05) * 1.0 - 0.5
            else:
                ua_req = Q_cd / lmtd(x[1] - T_mid, x[1] - Tk_in) + 3.0 * Q_ds / lmtd(d["s5"].T - Tk_out, x[1] - T_mid)
                r2 = (ua - ua_req) / p["UA_c"]
        return [(Q_e - Q_es) / 1e5, r2]

    guesses = [guess] if guess else []
    guesses += [[Ts_in - dte, Tk_out + dtc] for dte, dtc in [(8, 6), (12, 9), (5, 4), (16, 12), (8, 0.5), (8, -3)]]
    msg = ""
    for g in guesses:
        try:
            sol, info, ier, msg = fsolve(resid, g, full_output=True, xtol=1e-8)
        except Exception as e:
            ier, msg = 0, str(e)
        if ier == 1 and max(abs(v) for v in info["fvec"]) < 1e-4 and sol[0] < Ts_in - 0.1 and sol[1] > Tk_in + 2:
            break
    else:
        raise RuntimeError(msg)
    d = states(sol)
    Te, Tc = sol
    m, m_e = d["m"], d["m_e"]
    mt = m + m_e
    Q_e = m * (d["s1"].h - d["s11"].h)
    Q_c = mt * (d["s5"].h - d["s6"].h)
    W_shaft = m * (d["s3"].h - d["s2"].h) + mt * (d["s5"].h - d["s4"].h)
    W_el = W_shaft / (cm.eta_motor * cm.eta_inv)
    Ts_out = Ts_in - Q_e / (m_src * hx.CP_W)
    if steam:
        hfw = W.PT(4e5, Tk_in).h
        hg = W.PQ(W.Psat(Tk_out), 1.0).h
        m_sink = Q_c / (hg - hfw)
    else:
        m_sink = Q_c / (hx.CP_W * (Tk_out - Tk_in))
    if d["s5"].Tc > p["T_dis_max"] or Tc > F.Tcrit - 4:
        raise RuntimeError("envelope")
    h0, s0 = F.dead_state(T0)
    st = {k: d[f"s{k}"] for k in SP}
    ex = {k: exergy(v, h0, s0, T0) for k, v in st.items()}
    mm = {"1": m, "2": m, "3": m, "4": mt, "5": mt, "6": mt, "7": m_e, "8": m_e, "9": m, "10": m, "11": m}
    exs_in, exs_out = ex_w(Ts_in, T0), ex_w(Ts_out, T0)
    if steam:
        Wh0, Ws0 = W.dead_state(T0)
        sfw = W.PT(4e5, Tk_in)
        sg = W.PQ(W.Psat(Tk_out), 1.0)
        exk_in, exk_out = exergy(sfw, Wh0, Ws0, T0), exergy(sg, Wh0, Ws0, T0)
    else:
        exk_in, exk_out = ex_w(Tk_in, T0), ex_w(Tk_out, T0)
    X = {
        "X_comp": W_el - (m * (ex["3"] - ex["2"]) + mt * (ex["5"] - ex["4"]) + m_e * (ex["4"] - ex["8"]) * 0 ) + 0.0,
        "X_cond": mt * (ex["5"] - ex["6"]) - m_sink * (exk_out - exk_in),
        "X_evap": m * (ex["11"] - ex["1"]) + m_src * (exs_in - exs_out),
        "X_econ": m * (ex["6"] - ex["9"]) + m_e * (ex["7"] - ex["8"]),
        "X_ihx": m * (ex["9"] - ex["10"]) + m * (ex["1"] - ex["2"]),
        "X_valves": m_e * (ex["6"] - ex["7"]) + m * (ex["10"] - ex["11"]),
        "X_mix": m * ex["3"] + m_e * ex["8"] - mt * ex["4"],
        "Ex_prod": m_sink * (exk_out - exk_in),
        "Ex_src": m_src * (exs_in - exs_out),
    }
    # compressor exergy destruction closes the balance: W + Ex_src = Ex_prod + sum(X)
    X["X_comp"] = W_el + X["Ex_src"] - X["Ex_prod"] - sum(v for k, v in X.items() if k.startswith("X_") and k != "X_comp")
    out = {
        "Q_e": Q_e / 1e3, "Q_c": Q_c / 1e3, "W_el": W_el / 1e3, "W_shaft": W_shaft / 1e3, "COP": Q_c / W_el,
        "Te": Te - 273.15, "Tc": Tc - 273.15, "Tm": F.Tsat(d["Pm"]) - 273.15,
        "Pe": F.Psat(Te) / 1e5, "Pc": F.Psat(Tc) / 1e5, "Pm": d["Pm"] / 1e5,
        "m_ref": m, "m_econ": m_e, "econ_frac": m_e / m, "q_ihx": d["q_ihx"] / 1e3, "Q_ihx": m * d["q_ihx"] / 1e3,
        "Q_econ": m * (d["s6"].h - d["s9"].h) / 1e3,
        "eta_is": d["c1"]["eta_is"], "eta_v": d["c1"]["eta_v"], "pr": d["Pc"] / d["Pe"],
        "T_src_out": Ts_out - 273.15, "m_sink": m_sink, "T_dis": d["s5"].Tc,
        "lift": Tc - Te, "carnot": Tc / (Tc - Te), "eta_ex": X["Ex_prod"] / (W_el + X["Ex_src"]),
        "approach_e": Ts_out - Te, "approach_c": Tc - Tk_out,
    }
    out["eta_carnot"] = (Q_c / W_shaft) / out["carnot"]
    out.update({k: v / 1e3 for k, v in X.items()})
    for k in SP:
        s = st[k]
        out[f"sp{k}_T"], out[f"sp{k}_P"], out[f"sp{k}_h"] = s.Tc, s.P / 1e5, s.h / 1e3
        out[f"sp{k}_s"], out[f"sp{k}_x"], out[f"sp{k}_m"], out[f"sp{k}_ex"] = s.s / 1e3, s.x, mm[k], ex[k] / 1e3
    return out, list(sol)
