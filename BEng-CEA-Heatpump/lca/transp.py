"""Crop transpiration for the greenhouse sim (R7, 2026-10-03).

Reduced Penman-Monteith form of Baille et al. (1994) / Stanghellini (1987), used for greenhouse crops:

    lambda*E = A0 * (1 - exp(-k*LAI)) * G + B0 * LAI * VPD            [W/m2 floor]

G = solar radiation inside (W/m2), VPD in kPa, LAI in m2 leaf/m2 floor. The sim's law is
LE = transp_rad * 0.7 * I_in + transp_vpd * VPD, so transp_rad = A0 (1 - exp(-k LAI)) / 0.7 and transp_vpd = B0 LAI.

Sources of the constants (all W/m2/kPa per unit LAI for B0):
  literature range  A 0.12-0.67, B 14-37 g/m2/h/kPa = 9.5-25 W/m2/kPa per LAI (Baille et al. 1994, Sci Hortic 59:217;
                    tabulated by Seginer 1997); k = 0.64 tomato (Stanghellini 1987)
  tomato            A0, B0 fitted to GreenLight (Vanthoor 2011 / Katzin 2021) hourly transpiration on the Caledonian
                    design (LAI 2.56, R2 0.94 for LE = 0.30 I + 53 VPD): A0 = 0.30/(1-exp(-0.64*2.56)), B0 = 53/2.56
  cucumber          A0 = 0.24, B0 = 22-37.6 (mid 30), k = 0.63 (spring) - 0.86 (autumn): Medrano et al. (2005) Sci Hortic
                    105:163-175 (soilless cucumber, Almeria); Nikolaou et al. (2017) Emir J Food Agric 29:911 fitted
                    A 0.10-0.45, B 11-50 on Greek soilless cucumber; LAI of a commercial high-wire crop ~3 (design value)
Validation: `python transp.py` (tomato vs GreenLight, cucumber vs the measured lysimeter data of Nikolaou et al. 2017).
"""
import math

import numpy as np

CROPS = {
    "tomato": dict(A0=0.30 / (1 - math.exp(-0.64 * 2.56)), k=0.64, B0=53.0 / 2.56, lai=2.56,
                   src="fitted to GreenLight tomato (LAI 2.56); k Stanghellini 1987"),
    "cucumber": dict(A0=0.24, k=0.70, B0=30.0, lai=3.0,
                     src="Medrano et al. 2005 (A 0.24, B 22-37.6, k 0.63-0.86); LAI design value 3.0"),
}


# Seasonal LAI (m2 leaf / m2 floor) by day of year.
#  tomato    GreenLight's own growth curve from planting (LAI 0.4 on 1 Jan -> 2.5 by day ~75, plateau 2.57) with our crop
#            calendar (crops.py): crop removed at day 340, house nearly empty ("crop change, ~3 weeks"), new plants from
#            day 355 at LAI 0.3 (GreenLight does not model removal)
#  cucumber  three crops a year (crops.py), transplanted every 120 days (day 1, 121, 241); LAI = min(LAI_design, 0.2 + 0.05 t),
#            t = days after transplanting, 0.05/day from the measured autumn-winter crop of Nikolaou et al. (2017), Table 4
#            (0.4 at 13 d -> 1.9 at 43 d); 5 days of clean-out between crops. PLACEHOLDER SHAPE
TOMATO_LAI = [(1, 0.41), (15, 0.69), (30, 0.93), (45, 1.25), (60, 1.87), (75, 2.44), (90, 2.55), (339, 2.57), (340, 0.05),
              (354, 0.05), (355, 0.3), (366, 0.41)]


def lai_by_doy(crop, doy):
    doy = np.asarray(doy, float)
    if crop == "tomato":
        x, y = zip(*TOMATO_LAI)
        return np.interp(doy, x, y)
    t = (doy - 1) % 120
    lai = np.minimum(CROPS[crop]["lai"], 0.2 + 0.05 * t)
    return np.where(t > 115, 0.0, lai)


def floor_light_frac(lai):
    """Share of the light entering the house that the floor absorbs under a canopy of this LAI (GreenLight / Vanthoor
    2011): half PAR with extinction 0.7 and floor reflectance 0.65, half NIR with extinction 0.27 and floor reflectance 0.5."""
    lai = np.asarray(lai, float)
    return 0.5 * (1 - 0.65) * np.exp(-0.7 * lai) + 0.5 * (1 - 0.5) * np.exp(-0.27 * lai)


def hourly_coeffs(crop, doy_hours):
    """Hourly (transp_rad, transp_vpd) arrays for Envelope.transp_hourly from a day-of-year array."""
    p = CROPS[crop]
    lai = lai_by_doy(crop, doy_hours)
    return p["A0"] * (1 - np.exp(-p["k"] * lai)) / 0.7, p["B0"] * lai


def coeffs(crop, lai=None, A0=None, B0=None):
    """(transp_rad, transp_vpd) for the Envelope options."""
    p = CROPS[crop]
    lai = p["lai"] if lai is None else lai
    A0 = p["A0"] if A0 is None else A0
    B0 = p["B0"] if B0 is None else B0
    return A0 * (1 - math.exp(-p["k"] * lai)) / 0.7, B0 * lai


def predict(crop, G, vpd, lai=None, A0=None, B0=None, k=None):
    p = CROPS[crop]
    lai = p["lai"] if lai is None else lai
    A0 = p["A0"] if A0 is None else A0
    B0 = p["B0"] if B0 is None else B0
    k = p["k"] if k is None else k
    return A0 * (1 - math.exp(-k * lai)) * G + B0 * lai * vpd


# Nikolaou et al. (2017) Emir J Food Agric 29(12):911-921, Tables 1-4, no-cooling compartments (NC), measured by weighing
# lysimeter. Inside radiation G is the daylight mean (Table 2); VPD in Table 1 is the 10:00-14:00 mean, so the daylight-mean
# VPD is bracketed at 0.6-1.0 of it; LAI is the mean over the periods (Table 4); k per season as in the paper.
NIKOLAOU = {
    "AW 2014 (autumn-winter), 15-60 DAT": dict(G=(346 + 274 + 235 + 198) / 4, vpd_mid=(2.5 + 2.0 + 1.3 + 1.3) / 4, lai=1.6,
                                              k=0.86, measured=104.0),
    "SP 2015 (spring), 15-60 DAT": dict(G=(374 + 422 + 472 + 491) / 4, vpd_mid=(2.7 + 2.7 + 2.6 + 2.6) / 4, lai=0.95,
                                         k=0.63, measured=130.5),
}


def validate_cucumber():
    print("Cucumber vs measured lysimeter transpiration (Nikolaou et al. 2017, NC compartments; W/m2, mean over DAT 15-60)")
    print("Parameters are Medrano et al. (2005), an independent data set: A0 0.24, B0 22 (low radiation) / 37.6 (high)")
    for name, d in NIKOLAOU.items():
        B_lo, B_hi = (22.0, 22.0) if name.startswith("AW") else (30.0, 37.6)
        lo = predict("cucumber", d["G"], 0.6 * d["vpd_mid"], d["lai"], B0=B_lo, k=d["k"])
        hi = predict("cucumber", d["G"], 1.0 * d["vpd_mid"], d["lai"], B0=B_hi, k=d["k"])
        mid = 0.5 * (lo + hi)
        print(f"  {name}: G {d['G']:.0f}, VPD(10-14h) {d['vpd_mid']:.1f}, LAI {d['lai']}: predicted {lo:.0f}-{hi:.0f} "
              f"(mid {mid:.0f}), measured {d['measured']:.0f} ({'inside range' if lo <= d['measured'] <= hi else 'outside range'}; "
              f"mid error {100 * (mid / d['measured'] - 1):+.0f} %)")


if __name__ == "__main__":
    for c in CROPS:
        print(c, {k: round(v, 3) if isinstance(v, float) else v for k, v in CROPS[c].items()}, "->", coeffs(c))
    validate_cucumber()
