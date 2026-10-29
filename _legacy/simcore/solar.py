"""Solar geometry, transposition (Hay-Davies) and PV performance."""
import numpy as np


def position(times, lat, lon):
    """NOAA solar position for mid-interval of hourly backward-averaged data.

    Returns zenith and azimuth in degrees (azimuth clockwise from north)."""
    t = times - np.timedelta64(30, "m")
    doy = t.dt.dayofyear.to_numpy()
    hr = t.dt.hour.to_numpy() + t.dt.minute.to_numpy() / 60
    g = 2 * np.pi / 365 * (doy - 1 + (hr - 12) / 24)
    eqt = 229.18 * (0.000075 + 0.001868 * np.cos(g) - 0.032077 * np.sin(g)
                    - 0.014615 * np.cos(2 * g) - 0.040849 * np.sin(2 * g))
    dec = (0.006918 - 0.399912 * np.cos(g) + 0.070257 * np.sin(g) - 0.006758 * np.cos(2 * g)
           + 0.000907 * np.sin(2 * g) - 0.002697 * np.cos(3 * g) + 0.00148 * np.sin(3 * g))
    tst = hr * 60 + eqt + 4 * lon
    ha = np.radians(tst / 4 - 180)
    phi = np.radians(lat)
    cz = np.sin(phi) * np.sin(dec) + np.cos(phi) * np.cos(dec) * np.cos(ha)
    zen = np.degrees(np.arccos(np.clip(cz, -1, 1)))
    az = np.degrees(np.arctan2(np.sin(ha), np.cos(ha) * np.sin(phi) - np.tan(dec) * np.cos(phi))) + 180
    return zen, az % 360, doy


def poa(ghi, dni, dhi, zen, az, doy, tilt, surf_az, albedo=0.2):
    """Plane-of-array irradiance components (Hay-Davies). Angles in degrees."""
    z, a = np.radians(zen), np.radians(az)
    b, g = np.radians(tilt), np.radians(surf_az)
    cos_aoi = np.cos(z) * np.cos(b) + np.sin(z) * np.sin(b) * np.cos(a - g)
    cos_aoi = np.where(zen < 90, cos_aoi, 0)
    I0 = 1367 * (1 + 0.033 * np.cos(2 * np.pi * doy / 365))
    Ai = np.clip(dni / I0, 0, 1)
    Rb = np.clip(cos_aoi, 0, None) / np.maximum(np.cos(z), 0.087)
    beam = dni * np.clip(cos_aoi, 0, None)
    diff = dhi * ((1 - Ai) * (1 + np.cos(b)) / 2 + Ai * Rb)
    grnd = ghi * albedo * (1 - np.cos(b)) / 2
    aoi = np.degrees(np.arccos(np.clip(cos_aoi, -1, 1)))
    return beam, diff, grnd, aoi


def iam_ashrae(aoi, b0=0.05):
    c = np.cos(np.radians(np.minimum(aoi, 89.9)))
    return np.clip(1 - b0 * (1 / c - 1), 0, 1)


def pv_dc(beam, diff, grnd, aoi, T_amb, wind, P_stc, gamma=-0.0035, u0=25.0, u1=6.84, losses=0.08):
    """DC power (W) with Faiman cell temperature and IAM; returns (P_dc, T_cell, G_eff)."""
    G = beam * iam_ashrae(aoi) + diff * 0.95 + grnd * 0.9
    Tc = T_amb + G / (u0 + u1 * wind)
    P = P_stc * G / 1000 * (1 + gamma * (Tc - 25)) * (1 - losses)
    return np.clip(P, 0, None), Tc, G


def inverter(P_dc, P_ac_rated, eta_nom=0.965):
    """CEC-style part-load inverter efficiency curve."""
    x = np.clip(P_dc / max(P_ac_rated, 1), 1e-6, None)
    eta = eta_nom * (1 - 0.012 / x - 0.008 * x)
    eta = np.clip(eta, 0, eta_nom)
    return np.minimum(P_dc * eta, P_ac_rated), eta
