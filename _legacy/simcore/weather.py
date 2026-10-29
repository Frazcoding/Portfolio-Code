"""Real hourly weather for a full year from the Open-Meteo ERA5 archive.

Data are fetched once and cached as CSV in simcore/cache. All timestamps are UTC.
Derived psychrometric and sky quantities are added so every model works from
the same weather frame.
"""
import json
import time
import urllib.request

import numpy as np
import pandas as pd

from . import CACHE, YEAR

# name: (latitude, longitude, utc offset of local clock in winter [h], description)
SITES = {
    "london": (51.507, -0.128, 0, "London, UK"),
    "glasgow": (55.864, -4.252, 0, "Glasgow, UK"),
    "edinburgh": (55.953, -3.188, 0, "Edinburgh, UK"),
    "chelmsford": (51.736, 0.469, 0, "Chelmsford, Essex, UK"),
    "cheshire": (53.098, -2.441, 0, "Crewe, Cheshire, UK (dairy belt)"),
    "stornoway": (58.209, -6.389, 0, "Stornoway, Isle of Lewis, UK"),
    "monaco": (43.735, 7.425, 1, "Monaco harbour"),
    "bologna": (44.494, 11.343, 1, "Bologna, Italy"),
}

HOURLY = [
    "temperature_2m", "relative_humidity_2m", "dew_point_2m", "surface_pressure",
    "wind_speed_10m", "wind_speed_100m", "wind_direction_100m", "wind_gusts_10m",
    "shortwave_radiation", "direct_normal_irradiance", "diffuse_radiation",
    "cloud_cover", "precipitation", "snowfall", "soil_temperature_28_to_100cm",
    "soil_temperature_100_to_255cm", "et0_fao_evapotranspiration", "vapour_pressure_deficit",
]
RENAME = {
    "temperature_2m": "T_amb", "relative_humidity_2m": "RH", "dew_point_2m": "T_dew",
    "surface_pressure": "p_atm", "wind_speed_10m": "wind10", "wind_speed_100m": "wind100",
    "wind_direction_100m": "wdir100", "wind_gusts_10m": "gust10", "shortwave_radiation": "ghi",
    "direct_normal_irradiance": "dni", "diffuse_radiation": "dhi", "cloud_cover": "cloud",
    "precipitation": "precip", "snowfall": "snow", "soil_temperature_28_to_100cm": "T_soil_1m",
    "soil_temperature_100_to_255cm": "T_soil_2m", "et0_fao_evapotranspiration": "et0",
    "vapour_pressure_deficit": "vpd",
}


def _get(url, tries=6):
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return json.loads(r.read().decode())
        except OSError:
            if attempt == tries - 1:
                raise
            time.sleep(5 * 2 ** attempt)


def _fetch(site, year):
    lat, lon, _, _ = SITES[site]
    url = (
        "https://archive-api.open-meteo.com/v1/archive?"
        f"latitude={lat}&longitude={lon}&start_date={year}-01-01&end_date={year}-12-31"
        f"&hourly={','.join(HOURLY)}&wind_speed_unit=ms&timezone=GMT"
    )
    data = _get(url)
    df = pd.DataFrame(data["hourly"]).rename(columns=RENAME)
    df["time"] = pd.to_datetime(df["time"])
    return df


def _fetch_marine(site, year):
    lat, lon, _, _ = SITES[site]
    url = (
        "https://marine-api.open-meteo.com/v1/marine?"
        f"latitude={lat}&longitude={lon}&start_date={year}-01-01&end_date={year}-12-31"
        "&hourly=sea_surface_temperature,wave_height,wave_period&timezone=GMT"
    )
    data = _get(url)
    df = pd.DataFrame(data["hourly"]).rename(columns={
        "sea_surface_temperature": "T_sea", "wave_height": "wave_h", "wave_period": "wave_T"})
    df["time"] = pd.to_datetime(df["time"])
    return df


def load(site, year=YEAR, marine=False):
    """Return an 8760-row DataFrame of observed and derived hourly weather."""
    path = CACHE / f"weather_{site}_{year}.csv"
    if not path.exists():
        _fetch(site, year).to_csv(path, index=False)
    df = pd.read_csv(path, parse_dates=["time"])
    if marine:
        mpath = CACHE / f"marine_{site}_{year}.csv"
        if not mpath.exists():
            _fetch_marine(site, year).to_csv(mpath, index=False)
        df = df.merge(pd.read_csv(mpath, parse_dates=["time"]), on="time", how="left")
    df = df.iloc[:8760].reset_index(drop=True)
    df = df.interpolate(limit_direction="both")
    df["p_atm"] = df["p_atm"] * 100.0  # hPa -> Pa
    _derive(df, site)
    return df


def _derive(df, site):
    T = df["T_amb"].to_numpy()
    rh = np.clip(df["RH"].to_numpy(), 1, 100) / 100
    p = df["p_atm"].to_numpy()
    psat = 610.94 * np.exp(17.625 * T / (T + 243.04))
    pv = rh * psat
    df["w_amb"] = 0.62198 * pv / (p - pv)                          # kg/kg dry air
    df["h_amb"] = 1.006 * T + df["w_amb"] * (2501 + 1.86 * T)        # kJ/kg dry air
    df["rho_air"] = (p - pv) / (287.05 * (T + 273.15)) + pv / (461.5 * (T + 273.15))
    # Stull (2011) wet-bulb approximation, valid for RH 5-99 %, T -20..50 C
    rhp = rh * 100
    df["T_wb"] = (T * np.arctan(0.151977 * np.sqrt(rhp + 8.313659)) + np.arctan(T + rhp)
                  - np.arctan(rhp - 1.676331) + 0.00391838 * rhp ** 1.5 * np.arctan(0.023101 * rhp)
                  - 4.686035)
    # Clear-sky emissivity (Berdahl-Martin) corrected for cloud (Kasten-Czeplak)
    Td = df["T_dew"].to_numpy()
    eps_clear = 0.711 + 0.56 * (Td / 100) + 0.73 * (Td / 100) ** 2
    c = df["cloud"].to_numpy() / 100
    eps = np.clip(eps_clear * (1 + 0.0224 * c * 10 - 0.0035 * (c * 10) ** 2 + 0.00028 * (c * 10) ** 3), 0.5, 1.0)
    df["T_sky"] = (T + 273.15) * eps ** 0.25 - 273.15
    t = df["time"]
    df["hour_utc"] = t.dt.hour
    df["doy"] = t.dt.dayofyear
    df["month"] = t.dt.month
    offset = SITES[site][2]
    local = t + pd.to_timedelta(offset, unit="h")
    # European summer time: last Sunday of March to last Sunday of October
    dst = (local >= _last_sunday(local.dt.year.iloc[0], 3)) & (local < _last_sunday(local.dt.year.iloc[0], 10))
    local = local + pd.to_timedelta(dst.astype(int), unit="h")
    df["hour_local"] = local.dt.hour
    df["weekday"] = local.dt.weekday
    df["is_workday"] = (df["weekday"] < 5) & ~local.dt.normalize().isin(_uk_holidays(local.dt.year.iloc[0]))


def _last_sunday(year, month):
    d = pd.Timestamp(year=year, month=month + 1, day=1) - pd.Timedelta(days=1)
    return d - pd.Timedelta(days=(d.weekday() + 1) % 7)


def _uk_holidays(year):
    days = {2023: ["2023-01-02", "2023-04-07", "2023-04-10", "2023-05-01", "2023-05-08",
                   "2023-05-29", "2023-08-28", "2023-12-25", "2023-12-26"]}
    return pd.to_datetime(days.get(year, []))


def site_info(site):
    lat, lon, off, desc = SITES[site]
    return {"lat": lat, "lon": lon, "utc_offset": off, "desc": desc}
