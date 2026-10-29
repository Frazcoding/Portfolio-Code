"""'Hass' avocado growth model: hourly canopy photosynthesis, greenhouse CO2 balance, flowering, annual yield.

Runs on hourly climate series (greenhouse output or outdoor weather), after the climate simulation. That works
because the crop does not feed back on the heat balance beyond what greenhouse.py already models (transpiration,
LED heat); CO2 dosing does not change the heat balance.

Structure
  leaf      Farquhar-von Caemmerer-Berry photosynthesis. C3 kinetics and temperature responses from Bernacchi et
            al. (2001, 2003); Jmax/Vcmax = 1.67 (Medlyn et al. 2002). Avocado-specific: Vcmax25 fitted so light-
            and CO2-saturated net assimilation at 25 C, 400 ppm = 23 umol/m2/s (orchard 'Hass', Whiley & Schaffer
            1994); electron-transport quantum yield fitted to an apparent quantum yield of 0.055 (Whiley 1994).
            Chilling (24 h minimum < 10 C) scales capacity and quantum yield by 0.6 (Whiley 1994: 0.055 -> 0.034;
            Whiley et al. 1999: Amax 19.0 -> 10.9). VPD above 1 kPa reduces assimilation (Bower et al. 1978).
            Root restriction (containers) scales capacity (Schaffer & Whiley 2003: potted ~7 vs orchard 23).
  canopy    10 layers, Beer-Lambert PAR profile (k = 0.6), LAI held by pruning.
  CO2       greenhouse air balance per hour: dosing - net canopy uptake + respiration release - ventilation loss,
            integrated exactly for a constant hourly air-change rate.
  carbon    available = canopy net assimilation - wood/root maintenance (Q10 = 2). Fruit dry matter =
            partition x available / glucose cost of fruit. Partition and maintenance are calibrated (calibrate_crop.py)
            so the model reproduces a mature high-density 'Hass' yield under an open-field reference climate.
  flowering floral-induction index from daily mean temperature (Salazar-Garcia et al. 1999; Buttrose & Alexander
            1978): 28 days at <= 8.5 C mean (10/7 C) or ~105 days at 12.5-20.5 C means (15/10 to 23/18 C); none at
            >= 22.5 C (25/20 C). Yield scales with min(1, index).
"""
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from numba import njit

HERE = Path(__file__).resolve().parent
CAL_FILE = HERE / "data" / "crop_calibration.json"
R = 8.314
PAR_PER_W = 0.47 * 4.57
MG_CO2_PER_M3_PPM = 44.01 / 22.414 * 273.15 / 293.15      # mg CO2 per m3 per ppm at 20 C, 1 atm


@dataclass
class LeafParams:
    amax_ref: float = 23.0             # umol/m2/s at 25 C, 400 ppm, saturating light (Whiley & Schaffer 1994)
    phi_app: float = 0.055             # apparent quantum yield, mol CO2/mol photons (Whiley 1994)
    ci_ratio: float = 0.7              # Ci/Ca for well-watered C3 leaves
    theta: float = 0.7                 # curvature of the electron-transport light response
    j_v: float = 1.67                  # Jmax25/Vcmax25 (Medlyn et al. 2002)
    rd_v: float = 0.0055               # Rd25/Vcmax25, set so the light compensation point is ~10 umol/m2/s (Whiley 1994);
                                       # the generic C3 value 0.015 (Collatz et al. 1991) gives ~29
    s_v: float = 650.0                 # entropy terms for the high-temperature decline (Medlyn et al. 2002)
    s_j: float = 650.0
    chill_T: tuple = (10.0, 14.0)      # 24 h minimum: full chilling penalty below, none above (Whiley 1994; Whiley et al. 1999)
    chill_factor: float = 0.6
    vpd_slope: float = 0.25            # fractional loss per kPa above 1 kPa, floor 0.5 (Bower et al. 1978 coupling of g and A)


@dataclass
class CarbonParams:
    gr_fruit: float = 2.22             # g glucose per g fruit DM: Penning de Vries et al. (1974) costs for a fruit DM of
                                       # 55 % lipid, 35 % carbohydrate, 6 % protein, 4 % minerals (composition estimated)
    dm_fraction: float = 0.23          # fruit dry matter at harvest ('Hass' legal minimum 20.8 % in California)
    q10: float = 2.0
    maint_frac: float = 0.25           # wood/root maintenance as a share of reference-site net assimilation (calibration input)
    target_t_ha: float = 20.0          # mature high-density yield used for calibration (see calibrate_crop.py)
    age_ramp: tuple = (0.0, 0.0, 0.2, 0.4, 0.6, 0.8, 1.0)   # share of mature yield, years 1..7+ (Stassen et al. 1999 check)


def _arr(Ea, T):
    return math.exp(Ea * (T - 298.15) / (298.15 * R * T))


def _peak(Ea, Hd, S, T):
    return _arr(Ea, T) * (1 + math.exp((298.15 * S - Hd) / (298.15 * R))) / (1 + math.exp((T * S - Hd) / (R * T)))


@njit(cache=True)
def _arr_nb(Ea, T):
    return math.exp(Ea * (T - 298.15) / (298.15 * 8.314 * T))


@njit(cache=True)
def _peak_nb(Ea, Hd, S, T):
    return _arr_nb(Ea, T) * (1 + math.exp((298.15 * S - Hd) / (298.15 * 8.314))) / (1 + math.exp((T * S - Hd) / (8.314 * T)))


@njit(cache=True)
def _leaf_net_nb(I, Tc, Ca, cap, vpd, vcmax25, alpha_j, ci_ratio, theta, j_v, rd_v, s_v, s_j, vpd_slope):
    """Same arithmetic as Leaf.net (compiled)."""
    T = Tc + 273.15
    kc = 404.9 * _arr_nb(79430.0, T)
    ko = 278.4 * _arr_nb(36380.0, T)
    gs = 42.75 * _arr_nb(37830.0, T)
    vc = vcmax25 * cap * _peak_nb(65330.0, 200000.0, s_v, T)
    jm = vcmax25 * j_v * cap * _peak_nb(43540.0, 200000.0, s_j, T)
    rd = vcmax25 * rd_v * cap * _arr_nb(46390.0, T)
    ci = ci_ratio * Ca
    ac = vc * (ci - gs) / (ci + kc * (1 + 210.0 / ko))
    aI = alpha_j * cap * I
    J = ((aI + jm) - math.sqrt((aI + jm) ** 2 - 4 * theta * aI * jm)) / (2 * theta)
    aj = J / 4 * (ci - gs) / (ci + 2 * gs)
    f_vpd = max(0.5, 1 - vpd_slope * max(vpd - 1.0, 0.0))
    return min(ac, aj) * f_vpd - rd, rd


@njit(cache=True)
def _canopy_net_nb(par_top, Tc, Ca, vpd, cap, k, Ls, dL, lai, vcmax25, alpha_j, ci_ratio, theta, j_v, rd_v, s_v, s_j, vpd_slope):
    if par_top <= 0:
        return -_leaf_net_nb(0.0, Tc, Ca, cap, 0.0, vcmax25, alpha_j, ci_ratio, theta, j_v, rd_v, s_v, s_j, vpd_slope)[1] * lai
    tot = 0.0
    for L in Ls:
        I = k * par_top * math.exp(-k * L)
        tot += _leaf_net_nb(I, Tc, Ca, cap, vpd, vcmax25, alpha_j, ci_ratio, theta, j_v, rd_v, s_v, s_j, vpd_slope)[0] * dL
    return tot


# Interlighting (2026-10-05): LED modules between the rows put light into the lower and middle canopy, where leaves are
# far from saturation, instead of on the saturated top leaves. Absorbed share and vertical placement are PLACEHOLDERS
# until a canopy-absorption source is entered (data/input_register.csv): 90 % absorbed, spread evenly over the lower
# two-thirds of the leaf area. The yield gain this gives is checked against published interlighting trials (+22-31 %
# for one or two rows over top light only, mini-cucumber; CONSTRAINTS.md).
INTER_ABS, INTER_TOP_SKIP = 0.90, 1.0 / 3.0


@njit(cache=True)
def _canopy_net_inter_nb(par_top, par_inter, Tc, Ca, vpd, cap, k, Ls, dL, lai, vcmax25, alpha_j, ci_ratio, theta, j_v, rd_v,
                         s_v, s_j, vpd_slope, inter_abs, top_skip):
    lit_lai = lai * (1.0 - top_skip)
    tot = 0.0
    for L in Ls:
        I = k * par_top * math.exp(-k * L)
        if L >= lai * top_skip and lit_lai > 0:
            I += par_inter * inter_abs / lit_lai
        tot += _leaf_net_nb(I, Tc, Ca, cap, vpd, vcmax25, alpha_j, ci_ratio, theta, j_v, rd_v, s_v, s_j, vpd_slope)[0] * dL
    return tot


class Leaf:
    def __init__(self, lp=None):
        self.p = lp or LeafParams()
        self.vcmax25 = self._fit_vcmax()
        ci = self.p.ci_ratio * 400.0
        gs = 42.75
        self.alpha_j = self.p.phi_app * 4 * (ci + 2 * gs) / (ci - gs)

    def _fit_vcmax(self):
        lo, hi = 10.0, 400.0
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            self.vcmax25 = mid
            self.alpha_j = 0.5
            a = self.net(2000.0, 25.0, 400.0)[0]
            lo, hi = (mid, hi) if a < self.p.amax_ref else (lo, mid)
        return 0.5 * (lo + hi)

    def net(self, I, Tc, Ca, cap=1.0, vpd=0.0):
        """Net leaf assimilation, umol CO2/m2 leaf/s, for absorbed PAR I (umol/m2/s)."""
        p = self.p
        T = Tc + 273.15
        kc = 404.9 * _arr(79430, T)
        ko = 278.4 * _arr(36380, T)
        gs = 42.75 * _arr(37830, T)
        vc = self.vcmax25 * cap * _peak(65330, 200000, p.s_v, T)
        jm = self.vcmax25 * p.j_v * cap * _peak(43540, 200000, p.s_j, T)
        rd = self.vcmax25 * p.rd_v * cap * _arr(46390, T)
        ci = p.ci_ratio * Ca
        ac = vc * (ci - gs) / (ci + kc * (1 + 210.0 / ko))
        aI = self.alpha_j * cap * I
        J = ((aI + jm) - math.sqrt((aI + jm) ** 2 - 4 * p.theta * aI * jm)) / (2 * p.theta)
        aj = J / 4 * (ci - gs) / (ci + 2 * gs)
        f_vpd = max(0.5, 1 - p.vpd_slope * max(vpd - 1.0, 0.0))
        return min(ac, aj) * f_vpd - rd, rd


class Canopy:
    def __init__(self, lai=3.0, k=0.6, root=1.0, leaf=None, layers=10):
        self.leaf = leaf or Leaf()
        self.lai, self.k, self.root = lai, k, root
        dL = lai / layers
        self.L = (np.arange(layers) + 0.5) * dL
        self.dL = dL
        self.interception = 1 - math.exp(-k * lai)

    def net(self, par_top, Tc, Ca, vpd, tmin24, par_inter=0.0):
        """Net canopy CO2 exchange, umol/m2 ground/s (+ = uptake). Includes leaf respiration day and night.
        par_inter: interlighting PAR, umol/m2 ground/s, absorbed inside the canopy (0 = top light only, unchanged)."""
        lo, hi = self.leaf.p.chill_T
        chill = self.leaf.p.chill_factor + (1 - self.leaf.p.chill_factor) * min(1.0, max(0.0, (tmin24 - lo) / (hi - lo)))
        cap = self.root * chill
        p = self.leaf.p
        if par_inter > 0:
            return _canopy_net_inter_nb(par_top, par_inter, Tc, Ca, vpd, cap, self.k, self.L, self.dL, self.lai,
                                        self.leaf.vcmax25, self.leaf.alpha_j, p.ci_ratio, p.theta, p.j_v, p.rd_v, p.s_v,
                                        p.s_j, p.vpd_slope, INTER_ABS, INTER_TOP_SKIP)
        return _canopy_net_nb(par_top, Tc, Ca, vpd, cap, self.k, self.L, self.dL, self.lai, self.leaf.vcmax25,
                              self.leaf.alpha_j, p.ci_ratio, p.theta, p.j_v, p.rd_v, p.s_v, p.s_j, p.vpd_slope)


def induction_rate(T_mean_day):
    """Fraction of full floral induction gained per day at a given daily mean temperature (see module docstring)."""
    return float(np.interp(T_mean_day, [8.5, 12.5, 20.5, 22.5], [1 / 28, 1 / 105, 1 / 105, 0.0]))


def load_calibration():
    if CAL_FILE.exists():
        return json.loads(CAL_FILE.read_text())
    return None


@dataclass
class CropResult:
    hourly: dict = field(default_factory=dict)
    annual: dict = field(default_factory=dict)


def simulate(T_air, vpd, par_top, *, ach=None, volume=None, area=None, vent_pct=None, co2cfg=None, crop=None,
             outdoor=False, cal=None, cp=None, lai_h=None, leaf=None, annual=False, heat_stress=None, par_inter=None):
    """Hourly crop + CO2 run.

    T_air, vpd (kPa), par_top (umol/m2/s at canopy top, sun + LED) are hourly arrays.
    Greenhouse runs also pass ach (1/h), volume (m3), area (m2), vent_pct (%), co2cfg (config.CO2), crop (config.Crop).
    lai_h: hourly LAI (annual crops with a growth schedule; maintenance scales with LAI/crop.lai); leaf: LeafParams-based Leaf;
    annual=True: annual crop, no floral-induction limit (avocado flowering index skipped).
    heat_stress: (T_mean_limit C, loss per K above it, floor) daily fruit-set factor on the daily mean air temperature.
    outdoor=True holds CO2 at ambient (calibration against open-field orchards).
    """
    cp = cp or CarbonParams()
    cal = cal if cal is not None else load_calibration()
    lai = crop.lai if crop else 3.0
    k = crop.k_ext if crop else 0.6
    root = crop.root() if crop else 1.0
    leaf_obj = leaf or Leaf()
    can = Canopy(lai, k, root, leaf=leaf_obj)
    canopies = {}

    def can_at(i):
        if lai_h is None:
            return can
        key = round(float(lai_h[i]) * 20) / 20
        if key not in canopies:
            canopies[key] = Canopy(max(key, 0.05), k, root, leaf=leaf_obj)
        return canopies[key]
    n = len(T_air)
    T_air, vpd, par_top = map(np.asarray, (T_air, vpd, par_top))
    pin = np.zeros(n) if par_inter is None else np.asarray(par_inter, float)
    tmin24 = np.array([T_air[max(0, i - 23):i + 1].min() for i in range(n)])
    c_out = co2cfg.outdoor_ppm if co2cfg else 420.0
    maint20 = cal["maint_g_m2_h_20C"] if cal else 0.0          # g CH2O/m2/h at 20 C
    A_net = np.zeros(n)        # umol/m2/s
    ppm = np.full(n, c_out)
    dose = np.zeros(n)         # kg CO2/m2/h
    maint = maint20 * cp.q10 ** ((T_air - 20.0) / 10.0)       # g CH2O/m2/h
    if lai_h is not None:
        maint = maint * (np.asarray(lai_h, float) / lai)
    C = c_out
    for i in range(n):
        if outdoor or co2cfg is None:
            A_net[i] = can_at(i).net(par_top[i], T_air[i], c_out, vpd[i], tmin24[i], pin[i])
            continue
        G = ach[i] * volume / area                              # m3 air exchanged per m2 floor per hour
        H = volume / area                                       # m3 air per m2 floor
        resp = maint[i] * 44.0 / 30.0                           # g CO2/m2/h released by wood/roots
        # target concentration from vent opening
        v = vent_pct[i]
        f = min(1.0, max(0.0, (v - co2cfg.vent_closed) / (co2cfg.vent_open - co2cfg.vent_closed)))
        target = co2cfg.setpoint_closed + f * (co2cfg.setpoint_open - co2cfg.setpoint_closed)
        Cm = C
        for _it in range(2):
            a = can_at(i).net(par_top[i], T_air[i], Cm, vpd[i], tmin24[i], pin[i])
            up = a * 3600 * 44.01e-6                            # g CO2/m2/h taken up (+)
            d = 0.0
            if co2cfg.enrich and par_top[i] + pin[i] > 0 and a > 0:
                # dose that holds the target at steady state, capped by capacity
                need = G * (target - c_out) * MG_CO2_PER_M3_PPM / 1e3 + up - resp
                d = min(max(need, 0.0), co2cfg.capacity_kg_m2_h * 1e3)
            S = (d - up + resp) * 1e3 / MG_CO2_PER_M3_PPM       # ppm*m3 per m2 per h
            if G > 1e-9:
                Cs = c_out + S / G
                C_end = Cs + (C - Cs) * math.exp(-G / H)
                Cm = Cs + (C - Cs) * (1 - math.exp(-G / H)) * H / G
            else:
                C_end = C + S / H
                Cm = 0.5 * (C + C_end)
            Cm = max(Cm, 50.0)
        A_net[i], dose[i], ppm[i] = a, d / 1e3, Cm
        C = max(C_end, 50.0)
    gross_net_g = A_net * 3600 * 30.03e-6                       # g CH2O/m2/h
    avail = gross_net_g.sum() - maint.sum()
    Td = T_air[: (n // 24) * 24].reshape(-1, 24).mean(axis=1)
    induction = float(sum(induction_rate(t) for t in Td))
    f_flower = 1.0 if annual else min(1.0, induction)
    pf = cal["partition"] if cal else 0.0
    if heat_stress is None:
        fruit_dm = max(avail, 0.0) * pf / cp.gr_fruit * f_flower    # g DM/m2/yr
        stress_mean = 1.0
    else:
        nd = n // 24
        day_net = gross_net_g[: nd * 24].reshape(-1, 24).sum(axis=1) - maint[: nd * 24].reshape(-1, 24).sum(axis=1)
        t_lim, per_k, floor = heat_stress
        f_d = np.maximum(floor, 1.0 - per_k * np.maximum(Td - t_lim, 0.0))
        tot = day_net.sum()
        fruit_dm = max(float((day_net * f_d).sum()) if tot > 0 else 0.0, 0.0) * pf / cp.gr_fruit * f_flower
        stress_mean = float((day_net * f_d).sum() / tot) if tot > 0 else 1.0
    fresh = fruit_dm / cp.dm_fraction / 1e3                     # kg/m2/yr
    annual = dict(net_assim_g_CH2O_m2=gross_net_g.sum(), maint_g_CH2O_m2=maint.sum(), available_g_CH2O_m2=avail,
                  induction_index=induction, flowering_factor=f_flower, fruit_dm_g_m2=fruit_dm,
                  yield_kg_m2=fresh, heat_stress_factor=stress_mean, yield_t_ha=fresh * 10, interception=can.interception,
                  co2_dosed_kg_m2=dose.sum(), mean_ppm_day=float(ppm[par_top > 0].mean()) if (par_top > 0).any() else c_out,
                  hours_above_35=int((T_air > 35).sum()), hours_chill=int((tmin24 < 10).sum()))
    return CropResult(hourly=dict(A_net=A_net, ppm=ppm, dose=dose, maint=maint), annual=annual)


def from_greenhouse(H, meta, cfg, cal=None):
    """Crop run on greenhouse.simulate() output."""
    par = (H["PAR_nat"] + H["PAR_led"])
    return simulate(H["T_air_mean"], H["VPD"], par, ach=H["ach"], volume=meta["volume_m3"], area=meta["area_m2"],
                    vent_pct=H["vent"], co2cfg=cfg.co2, crop=cfg.crop, cal=cal)


def yield_profile(mature_kg_m2, years=30, cp=None):
    cp = cp or CarbonParams()
    ramp = list(cp.age_ramp) + [cp.age_ramp[-1]] * max(0, years - len(cp.age_ramp))
    return np.array(ramp[:years]) * mature_kg_m2
