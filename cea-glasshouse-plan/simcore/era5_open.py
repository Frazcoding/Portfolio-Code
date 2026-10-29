"""Open-Meteo ERA5 open data on AWS (s3://openmeteo, anonymous) as a fallback weather source.

Used by weather.load when the archive API cannot be reached (e.g. a cloud session whose network policy denies
archive-api.open-meteo.com). Same reanalysis as the archive API's ERA5 model (0.25 deg, hourly, UTC), nearest grid
cell, no elevation downscaling; the archive API's default 'best_match' can blend ERA5-Land, so values differ slightly.
Derived columns follow the archive API's definitions: relative humidity (Magnus), surface pressure from mean sea-level
pressure and cell height (barometric, 0.0065 K/m), wind speed/direction from u/v, DNI = direct / cos(zenith at the
middle of the preceding hour), diffuse = shortwave - direct, snowfall cm = water equivalent mm x 0.7, VPD, and FAO-56
hourly reference evapotranspiration.
"""
import datetime as dt

import numpy as np
import pandas as pd

BUCKET = "openmeteo/data/copernicus_era5"
CHUNK_H = 504                                            # hours per chunk file, counted from 1970-01-01 00 UTC
RAW = ("temperature_2m", "dew_point_2m", "pressure_msl", "wind_u_component_10m", "wind_v_component_10m",
       "wind_u_component_100m", "wind_v_component_100m", "wind_gusts_10m", "shortwave_radiation", "direct_radiation",
       "cloud_cover", "precipitation", "snowfall_water_equivalent", "soil_temperature_28_to_100cm",
       "soil_temperature_100_to_255cm")


class Era5Point:
    def __init__(self, lat, lon):
        import fsspec
        self.fs = fsspec.filesystem("s3", anon=True)
        self.iy = int(round((lat + 90.0) / 0.25))
        self.ix = int(round((lon + 180.0) / 0.25)) % 1440

    def reader(self, path):
        import omfiles
        return omfiles.OmFileReader.from_fsspec(self.fs, path)

    def height(self):
        return float(self.reader(f"{BUCKET}/static/HSURF.om")[self.iy, self.ix])

    def series(self, var, year):
        path = f"{BUCKET}/{var}/year_{year}.om"
        if self.fs.exists(path):
            return np.asarray(self.reader(path)[self.iy, self.ix, :], float)
        h0 = int((dt.datetime(year, 1, 1) - dt.datetime(1970, 1, 1)).total_seconds() // 3600)
        h1 = int((dt.datetime(year + 1, 1, 1) - dt.datetime(1970, 1, 1)).total_seconds() // 3600)
        from concurrent.futures import ThreadPoolExecutor
        chunks = list(range(h0 // CHUNK_H, (h1 - 1) // CHUNK_H + 1))
        with ThreadPoolExecutor(8) as ex:
            parts = list(ex.map(lambda n: self.chunk(var, n), chunks))
        out = []
        for n, a in zip(chunks, parts):
            lo, hi = max(h0 - n * CHUNK_H, 0), min(h1 - n * CHUNK_H, CHUNK_H)
            out.append(a[lo:hi])
        x = pd.Series(np.concatenate(out))
        if x.isna().any():                                  # a chunk missing from the bucket: interpolate across it
            print(f"era5_open: {var} {year}: {int(x.isna().sum())} h missing, interpolated", flush=True)
        return x.interpolate(limit_direction="both").to_numpy()

    def chunk(self, var, n):
        try:
            return np.asarray(self.reader(f"{BUCKET}/{var}/chunk_{n}.om")[self.iy, self.ix, :], float)
        except FileNotFoundError:
            return np.full(CHUNK_H, np.nan)


class ArchiveFrame:
    """Hourly frame with the archive API's variable names (weather.HOURLY) for one site-year."""

    def __init__(self, lat, lon, year):
        self.lat, self.lon, self.year = lat, lon, year
        self.pt = Era5Point(lat, lon)

    def zenith_cos(self, time):
        t = time - pd.Timedelta(minutes=30)
        doy = t.dt.dayofyear.to_numpy()
        hr = t.dt.hour.to_numpy() + t.dt.minute.to_numpy() / 60.0
        g = 2 * np.pi / 365 * (doy - 1 + (hr - 12) / 24)
        decl = (0.006918 - 0.399912 * np.cos(g) + 0.070257 * np.sin(g) - 0.006758 * np.cos(2 * g)
                + 0.000907 * np.sin(2 * g) - 0.002697 * np.cos(3 * g) + 0.00148 * np.sin(3 * g))
        eqt = 229.18 * (0.000075 + 0.001868 * np.cos(g) - 0.032077 * np.sin(g) - 0.014615 * np.cos(2 * g)
                        - 0.040849 * np.sin(2 * g))
        ha = np.radians((hr * 60 + eqt + 4 * self.lon) / 4 - 180)
        la = np.radians(self.lat)
        return np.sin(la) * np.sin(decl) + np.cos(la) * np.cos(decl) * np.cos(ha)

    @staticmethod
    def et0(T, rh, u10, sw, p_kpa, cosz):
        """FAO-56 hourly Penman-Monteith (mm/h)."""
        es = 0.6108 * np.exp(17.27 * T / (T + 237.3))
        ea = es * rh / 100
        delta = 4098 * es / (T + 237.3) ** 2
        gamma = 0.000665 * p_kpa
        u2 = u10 * 4.87 / np.log(67.8 * 10 - 5.42)
        rs = sw * 0.0036
        rso = np.maximum(0.75 * 1361 * np.clip(cosz, 0, None) * 0.0036, 1e-6)
        rnl = 2.043e-10 * (T + 273.16) ** 4 * (0.34 - 0.14 * np.sqrt(np.clip(ea, 0, None))) * \
            np.where(cosz > 0.05, np.clip(1.35 * np.clip(rs / rso, 0, 1) - 0.35, 0.05, 1.0), 0.5)
        rn = 0.77 * rs - rnl
        g = np.where(rs > 0, 0.1, 0.5) * rn
        cn = np.where(rs > 0, 37.0, 37.0)
        return np.clip((0.408 * delta * (rn - g) + gamma * cn / (T + 273) * u2 * (es - ea))
                       / (delta + gamma * (1 + np.where(rs > 0, 0.24, 0.96) * u2)), 0, None)

    def frame(self):
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(4) as ex:
            r = dict(zip(RAW, ex.map(lambda v: self.pt.series(v, self.year), RAW)))
        n = len(r["temperature_2m"])
        time = pd.Series(pd.date_range(f"{self.year}-01-01", periods=n, freq="1h"))
        T, Td = r["temperature_2m"], r["dew_point_2m"]
        rh = np.clip(100 * np.exp(17.625 * Td / (243.04 + Td)) / np.exp(17.625 * T / (243.04 + T)), 0, 100)
        z = self.pt.height()
        p_sfc = r["pressure_msl"] * (1 - 0.0065 * z / (T + 273.15 + 0.0065 * z)) ** 5.257
        cosz = self.zenith_cos(time)
        direct = np.clip(r["direct_radiation"], 0, None)
        dni = np.where(cosz > 0.035, np.minimum(direct / np.maximum(cosz, 0.035), 1361.0), 0.0)
        es = 0.6108 * np.exp(17.27 * T / (T + 237.3))
        u10 = np.hypot(r["wind_u_component_10m"], r["wind_v_component_10m"])
        u100, v100 = r["wind_u_component_100m"], r["wind_v_component_100m"]
        return pd.DataFrame({
            "time": time, "T_amb": T, "RH": rh, "T_dew": Td, "p_atm": p_sfc / 100.0, "wind10": u10,
            "wind100": np.hypot(u100, v100), "wdir100": (np.degrees(np.arctan2(-u100, -v100)) + 360) % 360,
            "gust10": r["wind_gusts_10m"], "ghi": np.clip(r["shortwave_radiation"], 0, None), "dni": dni,
            "dhi": np.clip(r["shortwave_radiation"] - direct, 0, None), "cloud": r["cloud_cover"],
            "precip": r["precipitation"], "snow": r["snowfall_water_equivalent"] * 0.7,
            "T_soil_1m": r["soil_temperature_28_to_100cm"], "T_soil_2m": r["soil_temperature_100_to_255cm"],
            "et0": self.et0(T, rh, u10, r["shortwave_radiation"], p_sfc / 1000.0, cosz),
            "vpd": np.clip(es * (1 - rh / 100), 0, None)})
