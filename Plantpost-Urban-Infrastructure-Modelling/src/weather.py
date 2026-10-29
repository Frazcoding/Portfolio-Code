"""Solar astronomy and meteorological data ingestion engine."""

import os
import math
import numpy as np
import pandas as pd
from typing import Tuple, Optional
from src.config import CITIES, CityLocation


class SolarAstronomy:
    """Astronomical solar position and twilight calculator."""

    @staticmethod
    def solar_declination_rad(day_of_year: int) -> float:
        # Cooper formulation
        return math.radians(23.45 * math.sin(math.radians(360.0 / 365.0 * (284 + day_of_year))))

    @staticmethod
    def equation_of_time_min(day_of_year: int) -> float:
        b = math.radians(360.0 * (day_of_year - 81) / 364.0)
        return 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)

    @classmethod
    def solar_elevation_deg(
        cls,
        latitude_deg: float,
        longitude_deg: float,
        day_of_year: int,
        hour: float,
        utc_offset_hours: float = 1.0
    ) -> Tuple[float, float]:
        phi = math.radians(latitude_deg)
        delta = cls.solar_declination_rad(day_of_year)
        eot_min = cls.equation_of_time_min(day_of_year)

        meridian_lon = utc_offset_hours * 15.0
        time_offset_hours = (4.0 * (longitude_deg - meridian_lon) + eot_min) / 60.0
        solar_time_hours = hour + time_offset_hours
        omega = math.radians(15.0 * (solar_time_hours - 12.0))

        sin_alpha = math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.cos(omega)
        sin_alpha = max(-1.0, min(1.0, sin_alpha))
        elevation_deg = math.degrees(math.asin(sin_alpha))
        zenith_deg = max(0.0, 90.0 - elevation_deg)
        return elevation_deg, zenith_deg

    @classmethod
    def extraterrestrial_radiation(
        cls,
        latitude_deg: float,
        day_of_year: int,
        hour: float
    ) -> float:
        # FAO-56 extraterrestrial solar flux
        g_sc = 1367.0
        d_r = 1.0 + 0.033 * math.cos(2.0 * math.pi * day_of_year / 365.0)
        delta = cls.solar_declination_rad(day_of_year)
        phi = math.radians(latitude_deg)
        omega = math.radians(15.0 * (hour - 12.0))

        sin_alpha = math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.cos(omega)
        return g_sc * d_r * sin_alpha if sin_alpha > 0.0 else 0.0


class WeatherDataPipeline:
    """Ingestion and meteorological feature engineering pipeline."""

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.data_dir = os.path.join(base_dir, 'data')
        else:
            self.data_dir = data_dir

    def load_weather_data(self, city_key: str = 'bologna') -> pd.DataFrame:
        if city_key not in CITIES:
            raise ValueError(f"Unknown city '{city_key}'. Available: {list(CITIES.keys())}")

        city = CITIES[city_key]
        csv_path = os.path.join(self.data_dir, f"weather_{city_key}_hourly.csv")
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Weather dataset not found at {csv_path}")

        df = pd.read_csv(csv_path)
        df['datetime'] = pd.to_datetime(df['datetime'])
        df['day_of_year'] = df['datetime'].dt.dayofyear

        utc_offset = 1.0 if city_key == 'bologna' else 0.0
        elevations = []
        zeniths = []

        for _, row in df.iterrows():
            elev, zen = SolarAstronomy.solar_elevation_deg(
                latitude_deg=city.latitude,
                longitude_deg=city.longitude,
                day_of_year=int(row['day_of_year']),
                hour=float(row['hour']) + 0.5,
                utc_offset_hours=utc_offset
            )
            elevations.append(round(elev, 2))
            zeniths.append(round(zen, 2))

        df['solar_elevation_deg'] = elevations
        df['solar_zenith_deg'] = zeniths
        df['is_civil_night'] = df['solar_elevation_deg'] <= -6.0
        df['is_daylight'] = df['solar_elevation_deg'] > 0.0
        return df


# Backward-compatible functional aliases
def load_weather_data(city_key: str = 'bologna', data_dir: Optional[str] = None) -> pd.DataFrame:
    return WeatherDataPipeline(data_dir).load_weather_data(city_key)

def calculate_solar_elevation_deg(lat: float, lon: float, doy: int, hr: float, utc_offset: float = 1.0):
    return SolarAstronomy.solar_elevation_deg(lat, lon, doy, hr, utc_offset)

def calculate_solar_declination_rad(doy: int) -> float:
    return SolarAstronomy.solar_declination_rad(doy)

def calculate_equation_of_time_min(doy: int) -> float:
    return SolarAstronomy.equation_of_time_min(doy)
