"""Proxy GB grid price and carbon-intensity SHAPES for a year, used only when CEA_GRID_SOURCE=proxy (a cloud session
whose network policy denies api.carbonintensity.org.uk and api.octopus.energy).

Callers rescale both series to sourced annual means (energy_grid.inputs: DESNZ price, grid_2025 carbon), so only the
hourly shape matters. Shape model (PLACEHOLDER, not a forecast of 2023 prices):
  * wind: ERA5 100 m wind at six GB onshore/offshore wind areas (era5_open), cubic power curve 3-12 m/s, cut-out 25 m/s;
  * solar: ERA5 shortwave at a southern England point;
  * demand: GB daily profile (night trough, 08-09 h and 17-19 h peaks), weekends x0.9, winter +18 %;
  * residual = demand - 0.35 x wind - 0.06 x solar (shares of demand); wholesale follows residual^1.5 (gas at the
    margin); Agile-style retail = 2.2 x wholesale + a 16-19 h peak adder; carbon = gas share of the residual.
"""
import numpy as np
import pandas as pd

from .era5_open import Era5Point

WIND_AREAS = ((57.5, -4.0), (55.7, -3.5), (54.0, 1.5), (53.8, -3.6), (51.9, 1.9), (52.5, -3.7))
SOLAR_POINT = (51.5, -1.0)


class GbGridProxy:
    def __init__(self, year):
        self.year = year

    def wind_pu(self):
        pu = []
        for lat, lon in WIND_AREAS:
            p = Era5Point(lat, lon)
            v = np.hypot(p.series("wind_u_component_100m", self.year), p.series("wind_v_component_100m", self.year))
            u = np.clip((v ** 3 - 27.0) / (12.0 ** 3 - 27.0), 0, 1)
            pu.append(np.where((v < 3) | (v > 25), 0.0, u))
        return np.mean(pu, axis=0)

    def demand(self, time):
        h = time.dt.hour.to_numpy()
        daily = 0.75 + 0.15 * np.exp(-((h - 8.5) / 2.0) ** 2) + 0.25 * np.exp(-((h - 17.5) / 1.8) ** 2) \
            + 0.12 * ((h >= 9) & (h <= 16)) - 0.12 * ((h >= 1) & (h <= 5))
        week = np.where(time.dt.weekday.to_numpy() >= 5, 0.9, 1.0)
        season = 1 + 0.18 * np.cos(2 * np.pi * (time.dt.dayofyear.to_numpy() - 15) / 365)
        d = daily * week * season
        return d / d.mean()

    def frame(self):
        wind = self.wind_pu()
        time = pd.Series(pd.date_range(f"{self.year}-01-01", periods=len(wind), freq="1h"))
        solar = np.clip(Era5Point(*SOLAR_POINT).series("shortwave_radiation", self.year), 0, None)
        resid = np.clip(self.demand(time) - 0.35 * wind / wind.mean() - 0.06 * solar / solar.mean(), 0.05, None)
        wholesale = resid ** 1.5
        h = time.dt.hour.to_numpy()
        price = 2.2 * wholesale / wholesale.mean() * 10.0 + np.where((h >= 16) & (h < 19), 12.0, 0.0)
        ci = 30.0 + 350.0 * resid / (resid + 0.35 * wind / wind.mean() + 0.3)
        return pd.DataFrame({"time": time, "ci": ci, "price": price})
