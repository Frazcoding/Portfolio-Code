"""Thermodynamic property evaluation and component models built on CoolProp.

Units inside this module are SI (K, Pa, J/kg, J/kg/K, kg/s, W). The output layer
converts to engineering units (degC, bar, kJ/kg, kJ/kg/K, kW).
"""
import math
from dataclasses import dataclass

import CoolProp.CoolProp as CP

P0 = 101325.0  # dead-state pressure for exergy


@dataclass
class St:
    T: float        # K
    P: float        # Pa
    h: float        # J/kg
    s: float        # J/kg/K
    rho: float      # kg/m3
    x: float        # thermodynamic quality (h-hl)/(hv-hl); nan above critical pressure

    @property
    def Tc(self):
        return self.T - 273.15


class Fluid:
    """Thin, fast wrapper around a CoolProp AbstractState (bicubic tables)."""

    def __init__(self, name, backend="BICUBIC&HEOS"):
        self.name = name
        self.AS = CP.AbstractState(backend, name)
        self.ASsat = CP.AbstractState(backend, name)
        self.Tcrit = self.AS.T_critical()
        self.Pcrit = self.AS.p_critical()
        self.Tmin = self.AS.Tmin()
        self.M = self.AS.molar_mass()

    # -- saturation ---------------------------------------------------------
    def Psat(self, T):
        self.ASsat.update(CP.QT_INPUTS, 1.0, min(T, self.Tcrit - 0.05))
        return self.ASsat.p()

    def Tsat(self, P):
        self.ASsat.update(CP.PQ_INPUTS, min(P, self.Pcrit * 0.999), 1.0)
        return self.ASsat.T()

    def sat(self, P):
        """Liquid and vapour enthalpy and entropy at pressure P."""
        A = self.ASsat
        P = min(P, self.Pcrit * 0.999)
        A.update(CP.PQ_INPUTS, P, 0.0)
        hl, sl, rl = A.hmass(), A.smass(), A.rhomass()
        A.update(CP.PQ_INPUTS, P, 1.0)
        return hl, A.hmass(), sl, A.smass(), rl, A.rhomass(), A.T()

    def latent(self, P):
        hl, hv, *_ = self.sat(P)
        return hv - hl

    # -- states -------------------------------------------------------------
    def _st(self):
        A = self.AS
        T, P, h = A.T(), A.p(), A.hmass()
        if P < self.Pcrit * 0.999:
            self.ASsat.update(CP.PQ_INPUTS, P, 0.0)
            hl = self.ASsat.hmass()
            self.ASsat.update(CP.PQ_INPUTS, P, 1.0)
            x = (h - hl) / (self.ASsat.hmass() - hl)
        else:
            x = float("nan")
        return St(T, P, h, A.smass(), A.rhomass(), x)

    def PT(self, P, T):
        self.AS.update(CP.PT_INPUTS, P, T)
        return self._st()

    def PH(self, P, h):
        self.AS.update(CP.HmassP_INPUTS, h, P)
        return self._st()

    def PS(self, P, s):
        self.AS.update(CP.PSmass_INPUTS, P, s)
        return self._st()

    def PQ(self, P, q):
        self.AS.update(CP.PQ_INPUTS, min(P, self.Pcrit * 0.999), q)
        return self._st()

    def TQ(self, T, q):
        self.AS.update(CP.QT_INPUTS, q, min(T, self.Tcrit - 0.05))
        return self._st()

    def superheated(self, P, dT_sh):
        """State at P with dT_sh K of superheat.

        Built from saturated-vapour enthalpy plus cp*dT and evaluated with PH
        inputs; PT inputs next to the saturation line are unreliable in the
        bicubic tables."""
        sv = self.PQ(P, 1.0)
        if dT_sh <= 0.01:
            return sv
        A = self.ASsat
        A.update(CP.PQ_INPUTS, min(P, self.Pcrit * 0.999), 1.0)
        cp = A.cpmass()
        st = self.PH(P, sv.h + cp * dT_sh)
        return self.PH(P, sv.h + cp * dT_sh * dT_sh / max(st.T - sv.T, 1e-3))

    def subcooled(self, P, dT_sc):
        sl = self.PQ(P, 0.0)
        if dT_sc <= 0.01:
            return sl
        A = self.ASsat
        A.update(CP.PQ_INPUTS, min(P, self.Pcrit * 0.999), 0.0)
        cp = A.cpmass()
        st = self.PH(P, sl.h - cp * dT_sc)
        return self.PH(P, sl.h - cp * dT_sc * dT_sc / max(sl.T - st.T, 1e-3))

    def cp(self, P, T):
        self.AS.update(CP.PT_INPUTS, P, T)
        return self.AS.cpmass()

    def dead_state(self, T0):
        self.AS.update(CP.PT_INPUTS, P0, T0)
        return self.AS.hmass(), self.AS.smass()

    def dome(self, n=60, T_low=None):
        """Saturation dome in engineering units for P-h and T-s diagrams."""
        T_low = T_low or max(self.Tmin + 1, self.Tcrit - 200)
        pts = []
        for i in range(n + 1):
            T = T_low + (self.Tcrit - 0.5 - T_low) * (i / n) ** 0.7
            self.ASsat.update(CP.QT_INPUTS, 0.0, T)
            hl, sl, P = self.ASsat.hmass(), self.ASsat.smass(), self.ASsat.p()
            self.ASsat.update(CP.QT_INPUTS, 1.0, T)
            pts.append((T - 273.15, P / 1e5, hl / 1e3, self.ASsat.hmass() / 1e3, sl / 1e3, self.ASsat.smass() / 1e3))
        return {
            "T": [round(p[0], 3) for p in pts], "P": [round(p[1], 5) for p in pts],
            "hl": [round(p[2], 3) for p in pts], "hv": [round(p[3], 3) for p in pts],
            "sl": [round(p[4], 5) for p in pts], "sv": [round(p[5], 5) for p in pts],
        }


def exergy(st, h0, s0, T0):
    """Specific flow exergy, J/kg."""
    return (st.h - h0) - T0 * (st.s - s0)


# ---------------------------------------------------------------------------
# Compressor
# ---------------------------------------------------------------------------
@dataclass
class CompressorMap:
    """Semi-empirical positive-displacement compressor characterisation.

    Isentropic efficiency peaks at the built-in pressure ratio pr_opt and falls
    with over/under-compression; volumetric efficiency follows re-expansion of
    clearance gas plus a leakage term that grows at low speed. Coefficients are
    representative of published scroll/screw maps (e.g. Copeland, Bitzer
    EN12900 polynomials refitted to these forms).
    """
    disp_m3h: float           # swept volume at f_nom
    f_nom: float = 50.0       # Hz
    f_min: float = 25.0
    f_max: float = 100.0
    eta_is_max: float = 0.72
    pr_opt: float = 3.0
    k_pr: float = 0.10        # efficiency loss per (ln pr/pr_opt)^2
    k_f: float = 0.08         # efficiency loss per ((f-f_opt)/f_opt)^2
    f_opt: float = 60.0
    clearance: float = 0.04
    n_poly: float = 1.15
    leak: float = 0.035       # fractional leakage at f_nom, scales with f_nom/f
    eta_motor: float = 0.93
    eta_inv: float = 0.97
    q_loss_frac: float = 0.06  # shell heat loss as fraction of shaft power


def compress(fluid, cmap, st_in, P_out, f):
    """Return outlet state, mass flow and power for one compressor at speed f."""
    pr = max(P_out / st_in.P, 1.01)
    eta_v = max(0.2, 1 - cmap.clearance * (pr ** (1 / cmap.n_poly) - 1) - cmap.leak * (cmap.f_nom / max(f, 1)))
    eta_is = cmap.eta_is_max * (1 - cmap.k_pr * math.log(pr / cmap.pr_opt) ** 2) \
        * (1 - cmap.k_f * ((f - cmap.f_opt) / cmap.f_opt) ** 2)
    eta_is = max(0.3, eta_is)
    vdot = cmap.disp_m3h / 3600 * f / cmap.f_nom
    m = eta_v * vdot * st_in.rho
    st_s = fluid.PS(P_out, st_in.s)
    dh_s = st_s.h - st_in.h
    w_shaft = dh_s / eta_is                         # J/kg delivered to gas + shell loss
    h_out = st_in.h + w_shaft * (1 - cmap.q_loss_frac)
    st_out = fluid.PH(P_out, h_out)
    W_shaft = m * w_shaft
    W_elec = W_shaft / (cmap.eta_motor * cmap.eta_inv)
    return {
        "st": st_out, "m": m, "W_shaft": W_shaft, "W_elec": W_elec, "eta_is": eta_is,
        "eta_v": eta_v, "pr": pr, "Q_loss": m * w_shaft * cmap.q_loss_frac, "vdot": vdot,
    }


def lmtd(dt1, dt2):
    dt1, dt2 = max(dt1, 1e-6), max(dt2, 1e-6)
    if abs(dt1 - dt2) < 1e-6:
        return dt1
    return (dt1 - dt2) / math.log(dt1 / dt2)
