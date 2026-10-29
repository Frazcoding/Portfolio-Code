"""Preliminary steel sizing for design.py shapes, so that steel tonnage (the largest embodied-carbon item and a major
cost) responds to span, height and roof form. This is a concept-stage member sizing, NOT the structural design:
no connections, bracing design, load-case envelope, uplift on light covers, or EN 13031-1 class reductions.

Loads (kN/m2 of plan unless stated):
  snow   BS EN 1991-1-3 + UK NA: s_k = 0.15 + (0.1 Z + 0.05) + (A - 100)/525; Ce = Ct = 1 (no heated-glass credit).
         Pitched: mu1 = 0.8 (<= 30 deg), 0.8 (60 - a)/30 (30-60). Multi-span valleys (5.3.4): drifted
         mu2 = 0.8 + 0.8 a_mean/30 <= 1.6 at the valley falling to mu1 at the ridge -> mean (mu1 + mu2)/2 on
         gutters and primaries. Curved (5.3.6): drifted mu3 = 0.2 + 10 h/b (h/b <= 0.18) else 2.0 on one half; the
         arch carries the symmetric part in compression and bends under the one-sided part, M = 1.5 mu3 s_k b L^2/64
  wind   BS EN 1991-1-4 + UK NA, simplified: q_p = 0.613 v_b^2 c_e, c_e ~ 2.0 at 5-10 m (country terrain), net wall
         pressure coefficient 1.3 (0.8 windward + 0.5 leeward), on perimeter columns only
  dead   cover (by glazing type), steel self-weight (iterated), hung crop + installations
  ULS    1.35 G + 1.5 Q (BS EN 1990 6.10); deflection L/200 under characteristic G + S
Members per span (span_w = column spacing across the ridges, bay_w = column spacing along them):
  primary   across the span at every bay line: beam (M = wL^2/8), lattice truss (depth L/10, chords + 60 % web), or
            two-hinged arch for curved profiles (M ~ wL^2/64 under half-span load); lightest that works is used
  secondary along the length between primaries at every valley/gutter line (M = wL^2/8 over bay_w)
  columns   at span edges per bay; interior axial, perimeter axial + wind bending; EN 1993-1-1 buckling curve a
  wall rails  side and gable walls: horizontal rails at 1.5 m spanning bay_w under 1.5 x 1.3 q_p
  bracing   +10 % of the above
Section properties: power-law fits to IPE (EN 10365) and hot-finished SHS (EN 10210) catalogue values (Tata Steel /
SCI 'Blue Book' P363): IPE m = 0.918 Wel^0.607, m = 0.815 Iy^0.438; SHS m = 1.06 Wel^0.645, i = 1.08 m^0.48
(m kg/m, Wel cm3, I cm4, i cm).
"""
import math
from dataclasses import dataclass

FY = 355e3      # kPa, S355
GM0 = 1.0
E = 210e6       # kPa
RHO = 7850.0


@dataclass
class Loads:
    snow_zone: float = 4.0          # UK NA Figure NA.1 zone (to read off the map for the site)
    altitude_m: float = 10.0
    v_b: float = 25.0               # m/s, UK NA basic wind speed (map value x altitude factor), to read off the map
    crop_kN_m2: float = 0.15        # hung high-wire crop + installations (to source: EN 13031-1 / NEN 3859)
    defl_ratio: float = 200.0
    gamma_G: float = 1.35           # BS EN 1990 6.10 (CC2); en13031.py sets the EN 13031-1 values
    gamma_Q: float = 1.5
    snow_factor: float = 1.0        # characteristic snow for a shorter reference period (EN 1991-1-3 Annex D)
    wind_factor: float = 1.0        # c_prob^2 on the peak pressure (EN 1991-1-4 4.2 Note 4)

    @property
    def s_k(self):
        return self.snow_factor * max(0.0, 0.15 + (0.1 * self.snow_zone + 0.05) + (self.altitude_m - 100.0) / 525.0)

    @property
    def q_p(self):
        return self.wind_factor * 0.613 * self.v_b ** 2 * 2.0 / 1e3


COVER_DEAD = {"single_plain": 0.10, "single_2ar": 0.10, "dbl_ar": 0.20, "dbl_ar_lowe": 0.20, "pc_twin": 0.03, "etfe3": 0.03}  # kN/m2


def _mu(alpha):
    return 0.8 if alpha <= 30 else max(0.0, 0.8 * (60 - alpha) / 30)


def _ipe_mass(W_cm3=0.0, I_cm4=0.0):
    return max(0.918 * W_cm3 ** 0.607 if W_cm3 > 0 else 0.0, 0.815 * I_cm4 ** 0.438 if I_cm4 > 0 else 0.0)


def _beam(w_uls, w_sls, L, defl):
    """kg/m of an IPE-like beam for a UDL (kN/m) over L (m)."""
    W = w_uls * L ** 2 / 8 / (FY / GM0) * 1e6                 # cm3
    I = 5 * w_sls * L ** 4 / (384 * E * (L / defl)) * 1e8     # cm4
    return max(_ipe_mass(W, I), 3.0)


def _truss(w_uls, w_sls, L, defl):
    d = L / 10.0
    F = w_uls * L ** 2 / 8 / d                                  # kN chord force
    A = F / (FY / GM0)                                          # m2 per chord
    # deflection of a parallel-chord truss ~ beam with I = 2 A (d/2)^2
    I_need = 5 * w_sls * L ** 4 / (384 * E * (L / defl))
    A = max(A, I_need / (2 * (d / 2) ** 2))
    return max(2 * A * RHO * 1.6, 3.0)


def _column(N, M, L):
    """kg/m of an SHS column under axial N (kN) and bending M (kNm), length L (m)."""
    for m in [x * 0.5 for x in range(6, 400)]:
        A = m / RHO                                             # m2
        i = 1.08 * m ** 0.48 / 100                              # m
        W = (m / 1.06) ** (1 / 0.645) / 1e6                     # m3
        lam = L / i / (93.9 * math.sqrt(235 / 355))
        phi = 0.5 * (1 + 0.21 * (lam - 0.2) + lam ** 2)
        chi = min(1.0, 1 / (phi + math.sqrt(phi ** 2 - lam ** 2)))
        if N / (chi * A * FY) + M / (W * FY) <= 1.0:
            return m
    return 200.0


def is_arch(profile, span_w):
    rise = max(z for _, z in profile) - min(z for _, z in profile)
    return len(profile) >= 5 and rise / span_w >= 0.15


def size(d, loads=Loads()):
    """Steel mass (kg) by member group for design d, and the governing loads."""
    segs = [((x1 - x0) * d.span_w, abs(z1 - z0)) for (x0, z0), (x1, z1) in zip(d.profile[:-1], d.profile[1:]) if x1 > x0]
    lens = [math.hypot(a, b) for a, b in segs]
    a_mean = sum(math.degrees(math.atan2(b, a)) * l for (a, b), l in zip(segs, lens)) / sum(lens)
    arch = is_arch(d.profile, d.span_w)
    mu1 = _mu(a_mean)
    multispan = d.n_spans > 1 or any(z <= 1e-6 for _, z in d.profile[1:-1])
    if arch:
        hb = (max(z for _, z in d.profile) - min(z for _, z in d.profile)) / d.span_w
        mu3 = 0.2 + 10 * hb if hb <= 0.18 else 2.0
        S = max(mu1, 0.8) * loads.s_k          # symmetric part (compression in the arch)
        S_asym = mu3 * loads.s_k
    else:
        mu2 = min(1.6, 0.8 + 0.8 * a_mean / 30) if multispan else mu1
        S = 0.5 * (mu1 + mu2) * loads.s_k
        S_asym = 0.0
    n_bays = int(math.ceil(d.length / d.bay_w))
    valleys = sum(1 for (x, z) in d.profile[1:-1] if z <= 1e-6) + 1      # gutter lines per span (+ one edge)
    trib = d.span_w / valleys
    g_self = 0.12
    for _ in range(3):                                          # iterate steel self-weight
        G = COVER_DEAD[d.glazing] + loads.crop_kN_m2 + g_self
        w_uls, w_sls = loads.gamma_G * G + loads.gamma_Q * S, G + S
        Lp = d.span_w
        prim = min(_beam(w_uls * d.bay_w, w_sls * d.bay_w, Lp, loads.defl_ratio),
                   _truss(w_uls * d.bay_w, w_sls * d.bay_w, Lp, loads.defl_ratio))
        if arch:   # bending from the one-sided drift only: M = w L^2/64 == beam formula with w/8
            wa = loads.gamma_Q * S_asym * d.bay_w
            prim = min(prim, _beam(wa / 8, S_asym * d.bay_w / 8, Lp, loads.defl_ratio * 8))
        roof_len = sum(math.hypot((x1 - x0) * d.span_w, z1 - z0) for (x0, z0), (x1, z1) in zip(d.profile[:-1], d.profile[1:]))
        m_prim = prim * roof_len * (n_bays + 1) * d.n_spans
        sec = _beam(w_uls * trib, w_sls * trib, d.bay_w, loads.defl_ratio)
        m_sec = sec * d.length * valleys * d.n_spans
        N = w_uls * d.span_w * d.bay_w
        h = d.gutter_h
        n_cols = (d.n_spans + 1) * (n_bays + 1)
        n_perim = 2 * (d.n_spans + 1) + 2 * (n_bays + 1)
        m_int = _column(N, 0.0, h) * h * (n_cols - n_perim)
        Mw = loads.gamma_Q * 1.3 * loads.q_p * d.bay_w * h ** 2 / 8
        m_per = _column(N / 2, Mw, h) * h * n_perim
        wall_area = 2 * d.length * h + 2 * d.width * h
        rail = _beam(loads.gamma_Q * 1.3 * loads.q_p * 1.5, 1.3 * loads.q_p * 1.5, d.bay_w, loads.defl_ratio)
        m_rail = rail * wall_area / 1.5
        total = 1.10 * (m_prim + m_sec + m_int + m_per + m_rail)
        g_self = total * 9.81 / 1e3 / d.floor
    return dict(steel_kg=total, steel_kg_m2=total / d.floor, primary_kg=m_prim, secondary_kg=m_sec,
                columns_kg=m_int + m_per, rails_kg=m_rail, n_columns=n_cols, column_N_kN=N, snow_kN_m2=S,
                snow_asym_kN_m2=S_asym, q_p=loads.q_p, arch=arch)
