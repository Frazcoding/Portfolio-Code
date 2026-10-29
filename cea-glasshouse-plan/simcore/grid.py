"""Hourly GB electricity carbon intensity and wholesale-linked retail prices for a year.

Carbon: NESO Carbon Intensity API, national actual intensity (gCO2/kWh), half-hourly.
Price:  Octopus Agile import tariff, region C (London), p/kWh inc. VAT, half-hourly.
Both are cached as hourly CSV in simcore/cache.
"""
import json
import os
import time
import urllib.request

import numpy as np
import pandas as pd

from . import CACHE, YEAR

AGILE_PRODUCTS = [
    ("AGILE-FLEX-22-11-25", "E-1R-AGILE-FLEX-22-11-25-C"),
    ("AGILE-23-12-06", "E-1R-AGILE-23-12-06-C"),
]
GAS_PRICE_P_KWH = 6.2          # 2023 non-domestic average, p/kWh (DESNZ QEP table 3.4.1)
GAS_CARBON_G_KWH = 182.9       # DESNZ 2023 conversion factor, natural gas gross CV
FLAT_ELEC_P_KWH = 27.0         # 2023 typical non-domestic fixed electricity tariff
STANDING_CHARGE_P_DAY = 45.0


def _get(url, tries=6):
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return json.loads(r.read().decode())
        except OSError:
            if attempt == tries - 1:
                raise
            time.sleep(5 * 2 ** attempt)


def _carbon(year):
    rows = []
    start = pd.Timestamp(f"{year}-01-01T00:00Z")
    end = pd.Timestamp(f"{year + 1}-01-01T00:00Z")
    while start < end:
        stop = min(start + pd.Timedelta(days=14), end)
        url = f"https://api.carbonintensity.org.uk/intensity/{start:%Y-%m-%dT%H:%MZ}/{stop:%Y-%m-%dT%H:%MZ}"
        for r in _get(url)["data"]:
            v = r["intensity"]["actual"] or r["intensity"]["forecast"]
            rows.append((pd.Timestamp(r["from"]), v))
        start = stop
    df = pd.DataFrame(rows, columns=["time", "ci"]).drop_duplicates("time")
    df["time"] = df["time"].dt.tz_convert(None)
    return df


def _agile(year):
    rows = []
    for product, tariff in AGILE_PRODUCTS:
        url = (f"https://api.octopus.energy/v1/products/{product}/electricity-tariffs/{tariff}/"
               f"standard-unit-rates/?period_from={year}-01-01T00:00Z&period_to={year + 1}-01-01T00:00Z&page_size=1500")
        while url:
            d = _get(url)
            rows += [(pd.Timestamp(r["valid_from"]), r["value_inc_vat"]) for r in d["results"]]
            url = d["next"]
    df = pd.DataFrame(rows, columns=["time", "price"]).drop_duplicates("time")
    df["time"] = df["time"].dt.tz_convert(None)
    return df


def load(year=YEAR):
    """Return hourly frame with ci [gCO2/kWh] and price [p/kWh] for 8760 hours."""
    path = CACHE / f"grid_gb_{year}.csv"
    if not path.exists() and os.environ.get("CEA_GRID_SOURCE") == "proxy":     # cloud fallback, see grid_proxy
        path = CACHE / f"grid_gb_{year}_proxy.csv"
        if not path.exists():
            from .grid_proxy import GbGridProxy
            GbGridProxy(year).frame().iloc[:8760].to_csv(path, index=False)
    if not path.exists():
        idx = pd.DataFrame({"time": pd.date_range(f"{year}-01-01", periods=17520, freq="30min")})
        c = idx.merge(_carbon(year), on="time", how="left")
        p = idx.merge(_agile(year), on="time", how="left")
        df = pd.DataFrame({"time": idx["time"], "ci": c["ci"], "price": p["price"]})
        df = df.set_index("time").interpolate(limit_direction="both").resample("1h").mean().reset_index()
        df.iloc[:8760].to_csv(path, index=False)
    df = pd.read_csv(path, parse_dates=["time"])
    df["price"] = np.clip(df["price"], -10, 100)
    return df
