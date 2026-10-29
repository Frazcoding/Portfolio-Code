"""Calibrate the avocado carbon model against an open-field reference and check leaf behaviour against measurements.

Reference: mature high-density 'Hass' under the outdoor climate of Mbombela (Nelspruit), South Africa, the region of
the Stassen et al. (1999) high-density trials summarised in Menzel & Le Lagadec (2014) Sci. Hortic. 177:21-36.
Target yield is CarbonParams.target_t_ha (20 t/ha/yr; judgement within the cited range - 23.6 t/ha cumulative over
the first three bearing years at 1667 trees/ha, ~10-12 t/ha in conventional orchards, ~32.5 t/ha energetic ceiling of
Wolstenholme 1986). Writes data/crop_calibration.json.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
sys.path.insert(0, str(HERE.parent))           # repo copy of simcore first (cloud has no ../simcore)
sys.path.insert(0, str(HERE))
from simcore import weather  # noqa: E402
import crop  # noqa: E402

REF_SITE = ("mbombela", -25.47, 30.97, 2, "Mbombela (Nelspruit), South Africa - 'Hass' reference orchard climate")


def leaf_checks(leaf):
    I = np.linspace(0, 2500, 2501)
    a = np.array([leaf.net(x, 25.0, 400.0)[0] for x in I])
    sat = float(I[np.argmax(a >= 0.95 * a.max())])
    comp = float(I[np.argmax(a >= 0)])
    ca = np.linspace(100, 2000, 1901)
    ac = np.array([leaf.net(2000.0, 25.0, x)[0] for x in ca])
    co2_sat = float(ca[np.argmax(ac >= 0.95 * ac.max())])
    T = np.linspace(5, 45, 401)
    aT = np.array([leaf.net(1500.0, t, 400.0)[0] for t in T])
    return dict(vcmax25=leaf.vcmax25, alpha_j=leaf.alpha_j,
                light_sat_95pct_umol=sat, light_sat_measured="1110 (orchard 'Hass', Whiley 1994)",
                light_comp_umol=comp, light_comp_measured="~10 (Whiley 1994)",
                co2_sat_95pct_ppm=co2_sat, co2_sat_measured="1350-1470 (Schaffer & Whiley 2003)",
                T_opt_C=float(T[np.argmax(aT)]), T_opt_measured="20-24 'Edranol', 28-31 'Fuerte' (Schaffer & Whiley 2003)",
                a_800_over_400=leaf.net(1500.0, 25.0, 800.0)[0] / leaf.net(1500.0, 25.0, 400.0)[0])


def main():
    name, lat, lon, off, desc = REF_SITE
    weather.SITES.setdefault(name, (lat, lon, off, desc))
    wx = weather.load(name)
    T, vpd, par = wx["T_amb"].to_numpy(), wx["vpd"].to_numpy(), wx["ghi"].to_numpy() * crop.PAR_PER_W
    cp = crop.CarbonParams()
    raw = crop.simulate(T, vpd, par, outdoor=True, cal={"maint_g_m2_h_20C": 0.0, "partition": 1.0}, cp=cp).annual
    N = raw["net_assim_g_CH2O_m2"]
    maint20 = cp.maint_frac * N / float(np.sum(cp.q10 ** ((T - 20.0) / 10.0)))
    avail = N * (1 - cp.maint_frac)
    fruit_glucose = cp.target_t_ha / 10 * 1e3 * cp.dm_fraction * cp.gr_fruit       # g/m2/yr
    partition = fruit_glucose / (avail * raw["flowering_factor"])
    cal = dict(site=desc, lat=lat, lon=lon, target_t_ha=cp.target_t_ha, maint_frac=cp.maint_frac,
               maint_g_m2_h_20C=maint20, partition=partition, net_assim_t_CH2O_ha=N / 100,
               induction_index=raw["induction_index"], mean_T=float(T.mean()), leaf=leaf_checks(crop.Leaf()))
    check = crop.simulate(T, vpd, par, outdoor=True, cal=cal, cp=cp).annual
    cal["check_yield_t_ha"] = check["yield_t_ha"]
    crop.CAL_FILE.parent.mkdir(exist_ok=True)
    crop.CAL_FILE.write_text(json.dumps(cal, indent=1))
    print(json.dumps(cal, indent=1))


if __name__ == "__main__":
    main()
