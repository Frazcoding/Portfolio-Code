"""
Solar astronomy and meteorological data ingestion engine.
Provides astronomical twilight triggers, solar position algorithms,
and hourly TMY data loading with offline caching.
"""

import os
import math
import numpy as np
import pandas as pd
from typing import Optional, Tuple
from src.config import CITIES, CityLocation


def calculate_solar_declination_rad(day_of_year: int) -> float:
    """Calculate solar declination angle in radians using Cooper's formulation."""
    return math.radians(23.45 * math.sin(math.radians(360.0 / 365.0 * (284 + day_of_year))))


def calculate_equation_of_time_min(day_of_year: int) -> float:
    """Calculate Equation of Time in minutes (Spencer / standard approximation)."""
    b = math.radians(360.0 * (day_of_year - 81) / 364.0)
    return 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)


def calculate_solar_elevation_deg(
    latitude_deg: float,
    longitude_deg: float,
    day_of_year: int,
    hour: float,
    utc_offset_hours: float = 1.0  # Standard time for Central Europe
) -> Tuple[float, float]:
    """
    Calculate instantaneous solar elevation and zenith angles in degrees.
    
    Returns:
        Tuple[elevation_deg, zenith_deg]
    """
    phi = math.radians(latitude_deg)
    delta = calculate_solar_declination_rad(day_of_year)
    eot_min = calculate_equation_of_time_min(day_of_year)

    # Standard meridian for time zone
    meridian_lon = utc_offset_hours * 15.0
    time_offset_hours = (4.0 * (longitude_deg - meridian_lon) + eot_min) / 60.0
    solar_time_hours = hour + time_offset_hours

    # Hour angle (omega = 0 at solar noon, 15 deg per hour)
    omega = math.radians(15.0 * (solar_time_hours - 12.0))

    # Sine of elevation
    sin_alpha = math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.cos(omega)
    sin_alpha = max(-1.0, min(1.0, sin_alpha))
    alpha_rad = math.asin(sin_alpha)
    elevation_deg = math.degrees(alpha_rad)
    zenith_deg = max(0.0, 90.0 - elevation_deg)

    return elevation_deg, zenith_deg


def calculate_extraterrestrial_radiation(
    latitude_deg: float,
    day_of_year: int,
    hour: float
) -> float:
    """
    Calculate extraterrestrial solar radiation on a horizontal plane (W/m^2)
    for a given hour (FAO-56 formulation for hourly time steps).
    """
    g_sc = 1367.0  # Solar constant (W/m^2)
    # Inverse relative distance Earth-Sun
    d_r = 1.0 + 0.033 * math.cos(2.0 * math.pi * day_of_year / 365.0)
    delta = calculate_solar_declination_rad(day_of_year)
    phi = math.radians(latitude_deg)

    # Solar time hour angle
    omega = math.radians(15.0 * (hour - 12.0))
    sin_alpha = math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.cos(omega)
    
    if sin_alpha <= 0.0:
        return 0.0
    return g_sc * d_r * sin_alpha


def load_weather_data(
    city_key: str = 'bologna',
    data_dir: Optional[str] = None
) -> pd.DataFrame:
    """
    Load hourly 8760 meteorological time-series for the specified city.
    Computes solar elevation, zenith, and civil twilight night indicator.
    
    Columns in output DataFrame:
        - datetime, month, day, hour, day_of_year
        - ghi_w_m2, dni_w_m2, dhi_w_m2
        - temp_air_c, rh_percent, wind_speed_m_s, pressure_pa, precip_mm_h
        - solar_elevation_deg, is_civil_night, is_daylight
    """
    if city_key not in CITIES:
        raise ValueError(f"Unknown city '{city_key}'. Available: {list(CITIES.keys())}")

    city = CITIES[city_key]
    if data_dir is None:
        # Relative to project root
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(base_dir, 'data')

    csv_path = os.path.join(data_dir, f"weather_{city_key}_hourly.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"Cached weather dataset not found at {csv_path}. "
            f"Run data generation pipeline first."
        )

    df = pd.read_csv(csv_path)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df['day_of_year'] = df['datetime'].dt.dayofyear

    # Determine standard UTC offset
    utc_offset = 1.0 if city_key == 'bologna' else 0.0

    # Compute solar elevation and civil twilight for every hour
    elevations = []
    zeniths = []
    for _, row in df.iterrows():
        elev, zen = calculate_solar_elevation_deg(
            latitude_deg=city.latitude,
            longitude_deg=city.longitude,
            day_of_year=int(row['day_of_year']),
            hour=float(row['hour']) + 0.5,  # Mid-hour center
            utc_offset_hours=utc_offset
        )
        elevations.append(round(elev, 2))
        zeniths.append(round(zen, 2))

    df['solar_elevation_deg'] = elevations
    df['solar_zenith_deg'] = zeniths
    # Civil twilight occurs when solar elevation <= -6 degrees
    df['is_civil_night'] = df['solar_elevation_deg'] <= -6.0
    df['is_daylight'] = df['solar_elevation_deg'] > 0.0

    return df

