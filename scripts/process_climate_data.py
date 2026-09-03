#!/usr/bin/env python3
"""
Climate Data Processor Script
==============================

Processes raw hourly climate data into heat pump-ready format.

Usage:
    python scripts/process_climate_data.py

Input:
    - Raw hourly CSV files from data/climate/

Output:
    - Processed CSV files in data/climate/processed/
    - Monthly statistics in data/climate/monthly/

Dependencies:
    - pandas
    - numpy
    - tqdm
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

# Configuration
RAW_DATA_DIR = 'data/climate'
PROCESSED_DATA_DIR = 'data/climate/processed'
MONTHLY_DATA_DIR = 'data/climate/monthly'

# HDD/CDD base temperatures
HDD_BASE = 15.5  # °C (UK standard for heating degree days)
CDD_BASE = 22.0  # °C (UK standard for cooling degree days)


def load_raw_data(city_name: str) -> pd.DataFrame:
    """Load raw hourly data for a city."""
    filename = f'{city_name.lower().replace(" ", "_")}_2014-2024_hourly.csv'
    filepath = os.path.join(RAW_DATA_DIR, filename)
    
    if not os.path.exists(filepath):
        print(f'  ⚠️  File not found: {filepath}')
        return pd.DataFrame()
    
    try:
        # Read CSV with all columns
        df = pd.read_csv(filepath, parse_dates=['time'], index_col='time')
        # Handle Parameter enum columns (they might be in the CSV as strings)
        # Convert any enum-like columns to strings
        for col in df.columns:
            if str(type(df[col].iloc[0])).startswith('<Parameter.'):
                df[col] = df[col].astype(str)
        return df
    except Exception as e:
        print(f'  ⚠️  Error loading {filepath}: {e}')
        return pd.DataFrame()


def clean_data(df: pd.DataFrame, city_name: str) -> pd.DataFrame:
    """Clean raw climate data."""
    if df.empty:
        return df
    
    cleaned = df.copy()
    
    # Add city name if not present
    if 'city' not in cleaned.columns:
        cleaned['city'] = city_name
    
    # Add datetime components
    cleaned['year'] = cleaned.index.year
    cleaned['month'] = cleaned.index.month
    cleaned['day'] = cleaned.index.day
    cleaned['hour'] = cleaned.index.hour
    cleaned['day_of_year'] = cleaned.index.dayofyear
    
    # Handle missing values
    # For temperature, humidity, wind, pressure: interpolate
    temp_cols = ['temp', 'rhum', 'wspd', 'pres']
    for col in temp_cols:
        if col in cleaned.columns:
            cleaned[col] = cleaned[col].ffill().bfill()
            cleaned[col] = cleaned[col].interpolate(method='time', limit=48)
    
    # For precipitation and sunshine: fill with 0
    precip_cols = ['prcp', 'tsun']
    for col in precip_cols:
        if col in cleaned.columns:
            cleaned[col] = cleaned[col].fillna(0)
    
    # Remove outliers using IQR method
    for col in ['temp', 'wspd']:
        if col in cleaned.columns:
            Q1 = cleaned[col].quantile(0.01)
            Q3 = cleaned[col].quantile(0.99)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            cleaned = cleaned[(cleaned[col] >= lower_bound) & (cleaned[col] <= upper_bound)]
    
    return cleaned


def calculate_solar_radiation(df: pd.DataFrame, lat: float = 55.0) -> pd.DataFrame:
    """Calculate solar radiation from sunshine duration using Angstrom-Prescott correlation."""
    if 'tsun' not in df.columns:
        return df
    
    result = df.copy()
    
    # Convert sunshine from minutes to hours
    result['sunshine_hours'] = result['tsun'] / 60
    
    # Calculate day of year
    day_of_year = result.index.dayofyear
    
    # Calculate solar geometry
    solar_declination = 23.45 * np.sin(np.radians(360 * (284 + day_of_year) / 365))
    hour_angle = 15 * (12 - result.index.hour)  # Solar noon at 12:00
    
    # Calculate extraterrestrial radiation (Ra) in W/m²
    Ra = 1367 * (1 + 0.033 * np.cos(np.radians(360 * day_of_year / 365))) * \
         np.sin(np.radians(90 - lat + solar_declination)) * \
         np.cos(np.radians(hour_angle))
    Ra = np.maximum(Ra, 0)
    
    # Calculate maximum possible sunshine duration (N) in hours
    N = (24 / np.pi) * np.arccos(-np.tan(np.radians(lat)) * np.tan(np.radians(solar_declination)))
    N = np.maximum(N, 0)
    
    # Angstrom-Prescott correlation with UK coefficients
    a = 0.25
    b = 0.5
    n_N_ratio = result['sunshine_hours'] / N
    n_N_ratio = np.clip(n_N_ratio, 0, 1)
    
    # Calculate global solar radiation in W/m²
    result['solar_rad'] = (a + b * n_N_ratio) * Ra
    
    # For nighttime hours, set solar radiation to 0
    sunrise_hour = 6
    sunset_hour = 18
    result.loc[(result.index.hour < sunrise_hour) | (result.index.hour >= sunset_hour), 'solar_rad'] = 0
    
    return result


def calculate_hdd_cdd(df: pd.DataFrame, hdd_base: float = HDD_BASE, cdd_base: float = CDD_BASE) -> pd.DataFrame:
    """Calculate Heating Degree Days (HDD) and Cooling Degree Days (CDD)."""
    if 'temp' not in df.columns:
        return df
    
    result = df.copy()
    
    # Calculate daily average temperature
    daily_avg = result['temp'].resample('D').mean()
    
    # Calculate daily HDD and CDD
    daily_hdd = np.maximum(0, hdd_base - daily_avg)
    daily_cdd = np.maximum(0, daily_avg - cdd_base)
    
    # Create mapping dictionaries with date() as key
    hdd_map = {ts.date(): val for ts, val in zip(daily_hdd.index, daily_hdd.values)}
    cdd_map = {ts.date(): val for ts, val in zip(daily_cdd.index, daily_cdd.values)}
    
    # Map daily values back to hourly DataFrame
    result['hdd_daily'] = result.index.map(lambda x: hdd_map.get(x.date(), 0))
    result['cdd_daily'] = result.index.map(lambda x: cdd_map.get(x.date(), 0))
    
    # Calculate cumulative annual HDD and CDD
    # Since hdd_daily is the same for all hours in a day, the annual sum
    # should be the sum of unique daily values (not 24x the daily value)
    # We already have hdd_daily and cdd_daily mapped to each hour
    
    # Calculate annual HDD/CDD by summing unique daily values
    # Create a temporary column for date
    result_copy = result.copy()
    result_copy['date_str'] = result_copy.index.date.astype(str)
    daily_unique = result_copy.drop_duplicates(subset=['date_str'])
    daily_unique['year'] = daily_unique.index.year
    
    annual_hdd = daily_unique.groupby('year')['hdd_daily'].sum().to_dict()
    annual_cdd = daily_unique.groupby('year')['cdd_daily'].sum().to_dict()
    
    # Map back to hourly data
    result['hdd_annual'] = result.index.map(lambda x: annual_hdd.get(x.year, 0))
    result['cdd_annual'] = result.index.map(lambda x: annual_cdd.get(x.year, 0))
    
    # Drop any 'time' column if it exists (from groupby)
    if 'time' in result.columns:
        result = result.drop(columns=['time'])
    
    return result


def calculate_design_temperatures(df: pd.DataFrame) -> dict:
    """Calculate design temperatures (1% and 99% percentiles)."""
    if 'temp' not in df.columns:
        return {}
    
    winter_design = df['temp'].quantile(0.01)  # 1% percentile (coldest)
    summer_design = df['temp'].quantile(0.99)  # 99% percentile (hottest)
    avg_temp = df['temp'].mean()
    
    return {
        'winter_design_temp': float(winter_design),
        'summer_design_temp': float(summer_design),
        'avg_temp': float(avg_temp),
        'min_temp': float(df['temp'].min()),
        'max_temp': float(df['temp'].max())
    }


def aggregate_monthly_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate hourly data to monthly statistics."""
    if df.empty:
        return pd.DataFrame()
    
    # Group by year and month
    # Use as_index=False to avoid MultiIndex issues
    df_copy = df.copy()
    df_copy['year'] = df_copy.index.year
    df_copy['month'] = df_copy.index.month
    
    monthly = df_copy.groupby(['year', 'month'], as_index=False).agg({
        'temp': ['mean', 'min', 'max'],
        'rhum': 'mean',
        'wspd': 'mean',
        'solar_rad': 'mean',
        'prcp': 'sum',
        'hdd_daily': 'sum',
        'cdd_daily': 'sum'
    })
    
    # Flatten multi-index columns
    monthly.columns = [
        'year', 'month',
        'avg_temp', 'min_temp', 'max_temp',
        'avg_humidity', 'avg_wind_speed',
        'avg_solar_rad', 'total_precip',
        'hdd_monthly', 'cdd_monthly'
    ]
    
    return monthly


def process_city(city_name: str, lat: float, lon: float) -> dict:
    """Full processing pipeline for one city."""
    # Load raw data
    df = load_raw_data(city_name)
    
    if df.empty:
        print(f'  ⚠️  No data found for {city_name}')
        return None
    
    print(f'  🔧 Processing {city_name}...')
    
    # Clean data
    cleaned = clean_data(df, city_name)
    print(f'     Cleaned: {len(cleaned)} records')
    
    # Calculate solar radiation
    with_solar = calculate_solar_radiation(cleaned, lat)
    
    # Calculate HDD and CDD
    with_hdd_cdd = calculate_hdd_cdd(with_solar)
    
    # Calculate design temperatures
    design_temps = calculate_design_temperatures(with_hdd_cdd)
    
    # Aggregate monthly statistics
    monthly_stats = aggregate_monthly_stats(with_hdd_cdd)
    
    # Save processed data
    os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
    os.makedirs(MONTHLY_DATA_DIR, exist_ok=True)
    
    processed_filename = f'{city_name.lower().replace(" ", "_")}_2014-2024_hourly_processed.csv'
    processed_path = os.path.join(PROCESSED_DATA_DIR, processed_filename)
    with_hdd_cdd.to_csv(processed_path)
    
    monthly_filename = f'{city_name.lower().replace(" ", "_")}_monthly_stats.csv'
    monthly_path = os.path.join(MONTHLY_DATA_DIR, monthly_filename)
    monthly_stats.to_csv(monthly_path, index=False)
    
    print(f'     ✅ Saved processed data to {processed_path}')
    print(f'     ✅ Saved monthly stats to {monthly_path}')
    
    return {
        'city': city_name,
        'processed_data': with_hdd_cdd,
        'monthly_stats': monthly_stats,
        'design_temps': design_temps,
        'processed_path': processed_path,
        'monthly_path': monthly_path
    }


def main():
    """Main function to process climate data for all UK cities."""
    print('=' * 70)
    print('🔧 Climate Data Processor')
    print('=' * 70)
    
    # Load city metadata
    metadata_path = os.path.join(RAW_DATA_DIR, 'uk_cities_metadata.csv')
    cities_df = pd.read_csv(metadata_path)
    cities = cities_df.to_dict('records')
    
    print(f'🌆 Cities to process: {len(cities)}')
    print()
    
    # Process all cities
    print('🚀 Processing climate data...')
    print('=' * 70)
    
    results = {}
    for city in tqdm(cities, desc='Processing cities'):
        city_name = city['city_name']
        lat = city['latitude']
        lon = city['longitude']
        
        result = process_city(city_name, lat, lon)
        if result:
            results[city_name] = result
    
    print()
    print('=' * 70)
    print('✅ SUMMARY')
    print('=' * 70)
    print(f'Total cities processed: {len(results)}')
    
    # Display design temperatures
    print('\n🌡️  Design Temperatures:')
    print('-' * 70)
    print(f"{'City':<15} {'Avg (°C)':<10} {'Min (°C)':<10} {'Max (°C)':<10} {'Winter (°C)':<12} {'Summer (°C)':<12}")
    print('-' * 70)
    for city_name, result in results.items():
        dt = result['design_temps']
        print(f"{city_name:<15} {dt['avg_temp']:<10.1f} {dt['min_temp']:<10.1f} {dt['max_temp']:<10.1f} {dt['winter_design_temp']:<12.1f} {dt['summer_design_temp']:<12.1f}")
    
    # Display HDD summary
    print('\n🔥 HDD Summary (Annual Average):')
    print('-' * 70)
    print(f"{'City':<15} {'Avg HDD (°C·days)':<15} {'Avg CDD (°C·days)':<15}")
    print('-' * 70)
    for city_name, result in results.items():
        df = result['processed_data']
        if 'hdd_annual' in df.columns:
            avg_hdd = df.groupby(df.index.year)['hdd_annual'].mean().mean()
            avg_cdd = df.groupby(df.index.year)['cdd_annual'].mean().mean()
            print(f"{city_name:<15} {avg_hdd:<15.0f} {avg_cdd:<15.0f}")
    
    # List output files
    print('\n📁 Output Files:')
    print('-' * 70)
    processed_files = [f for f in os.listdir(PROCESSED_DATA_DIR) if f.endswith('_processed.csv')]
    monthly_files = [f for f in os.listdir(MONTHLY_DATA_DIR) if f.endswith('_monthly_stats.csv')]
    
    print(f'Processed Hourly Data: {len(processed_files)} files')
    for f in processed_files:
        filepath = os.path.join(PROCESSED_DATA_DIR, f)
        size = os.path.getsize(filepath) / 1024 / 1024  # MB
        print(f'  - {f} ({size:.1f} MB)')
    
    print(f'\nMonthly Statistics: {len(monthly_files)} files')
    for f in monthly_files:
        filepath = os.path.join(MONTHLY_DATA_DIR, f)
        size = os.path.getsize(filepath) / 1024  # KB
        print(f'  - {f} ({size:.1f} KB)')
    
    print('\n✅ Climate data processing complete!')


if __name__ == '__main__':
    main()
