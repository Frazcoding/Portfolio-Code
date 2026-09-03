#!/usr/bin/env python3
"""
Climate Data Fetcher Script
===========================

Fetches hourly climate data from Meteostat for 11 UK cities (2014-2024).

Usage:
    python scripts/fetch_climate_data.py

Output:
    - Raw hourly CSV files in data/climate/
    - Station mapping in data/climate/uk_cities_stations.csv

Dependencies:
    - meteostat
    - pandas
    - tqdm
"""

from meteostat import Point, hourly, stations, config
from datetime import datetime
import pandas as pd
import os
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

# Allow large requests (10 years of data)
config.block_large_requests = False

# Configuration
START_DATE = datetime(2014, 1, 1)
END_DATE = datetime(2024, 12, 31, 23, 59)
RAW_DATA_DIR = 'data/climate'
CACHE_DIR = 'data/climate/cache'

# 11 UK Cities
CITIES = [
    {'name': 'London', 'latitude': 51.5074, 'longitude': -0.1278},
    {'name': 'Manchester', 'latitude': 53.4808, 'longitude': -2.2426},
    {'name': 'Birmingham', 'latitude': 52.4862, 'longitude': -1.8904},
    {'name': 'Leeds', 'latitude': 53.7995, 'longitude': -1.5490},
    {'name': 'Glasgow', 'latitude': 55.8642, 'longitude': -4.2518},
    {'name': 'Edinburgh', 'latitude': 55.9533, 'longitude': -3.1883},
    {'name': 'Cardiff', 'latitude': 51.4816, 'longitude': -3.1790},
    {'name': 'Belfast', 'latitude': 54.5973, 'longitude': -5.9301},
    {'name': 'Bristol', 'latitude': 51.4545, 'longitude': -2.5879},
    {'name': 'Newcastle', 'latitude': 54.9783, 'longitude': -1.6177},
    {'name': 'Lerwick', 'latitude': 60.1550, 'longitude': -1.1456},
]


def find_nearest_station(lat: float, lon: float) -> tuple:
    """
    Find the nearest weather station to given coordinates.
    
    Returns:
        tuple: (station_id, station_name, distance_m)
    """
    location = Point(lat, lon)
    nearby = stations.nearby(location, limit=1)
    
    if len(nearby) == 0:
        return None, None, None
    
    station_id = nearby.index[0]
    station_name = nearby.iloc[0]['name']
    distance = nearby.iloc[0]['distance']
    
    return station_id, station_name, distance


def fetch_hourly_data(station_id: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """
    Fetch hourly climate data for a station.
    
    Returns:
        pd.DataFrame: DataFrame with hourly climate data
    """
    data = hourly(station_id, start_date, end_date)
    result = data.fetch()
    return result


def save_to_csv(df: pd.DataFrame, city_name: str, output_dir: str) -> str:
    """
    Save DataFrame to CSV file.
    
    Returns:
        str: Path to the saved CSV file
    """
    os.makedirs(output_dir, exist_ok=True)
    filename = f'{city_name.lower().replace(" ", "_")}_2014-2024_hourly.csv'
    filepath = os.path.join(output_dir, filename)
    
    if df is not None and not df.empty:
        df.to_csv(filepath, index_label='time')
        print(f'  ✅ Saved {len(df)} records to {filepath}')
    else:
        print(f'  ⚠️  No data to save for {city_name}')
    
    return filepath


def create_station_mapping(cities: list) -> pd.DataFrame:
    """
    Create a mapping of cities to their nearest weather stations.
    
    Returns:
        pd.DataFrame: Station mapping DataFrame
    """
    mapping = []
    
    for city in tqdm(cities, desc='Finding stations'):
        station_id, station_name, distance = find_nearest_station(
            city['latitude'], city['longitude']
        )
        
        if station_id:
            mapping.append({
                'city_name': city['name'],
                'city_latitude': city['latitude'],
                'city_longitude': city['longitude'],
                'station_id': station_id,
                'station_name': station_name,
                'distance_m': distance
            })
        else:
            print(f'  ⚠️  No station found for {city["name"]}')
    
    return pd.DataFrame(mapping)


def fetch_all_cities(cities: list, start_date: datetime, end_date: datetime) -> dict:
    """
    Fetch data for all cities.
    
    Returns:
        dict: Dictionary with city names as keys and DataFrames as values
    """
    results = {}
    
    for city in tqdm(cities, desc='Fetching data'):
        city_name = city['name']
        lat = city['latitude']
        lon = city['longitude']
        
        print(f'\n📍 Fetching data for {city_name} ({lat}°N, {lon}°W)...')
        
        # Find nearest station
        station_id, station_name, distance = find_nearest_station(lat, lon)
        
        if station_id is None:
            print(f'  ⚠️  No weather station found')
            results[city_name] = pd.DataFrame()
            continue
        
        print(f'  🏢 Using station: {station_id} ({station_name}), Distance: {distance:,.0f}m')
        
        # Fetch data (with retry logic for rate limits)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                df = fetch_hourly_data(station_id, start_date, end_date)
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                print(f'  ⚠️  Attempt {attempt + 1} failed, retrying...')
                import time
                time.sleep(5)
        
        if df is not None and not df.empty:
            df['city'] = city_name
            df['station_id'] = station_id
            df['station_name'] = station_name
            results[city_name] = df
            print(f'  📊 Data range: {df.index.min()} to {df.index.max()}')
            print(f'  📈 Records: {len(df)}')
        else:
            print(f'  ⚠️  No data returned')
            results[city_name] = pd.DataFrame()
    
    return results


def main():
    """Main function to fetch climate data for all UK cities."""
    print('=' * 70)
    print('🌍 Climate Data Fetcher')
    print('=' * 70)
    print(f'📅 Date range: {START_DATE} to {END_DATE}')
    print(f'🌆 Cities: {len(CITIES)}')
    print()
    
    # Create station mapping
    print('🔍 Finding nearest weather stations...')
    station_mapping = create_station_mapping(CITIES)
    station_mapping_path = os.path.join(RAW_DATA_DIR, 'uk_cities_stations.csv')
    station_mapping.to_csv(station_mapping_path, index=False)
    print(f'✅ Station mapping saved to {station_mapping_path}')
    print()
    
    # Display station mapping
    print('📋 Station Mapping:')
    print('-' * 70)
    print(station_mapping.to_string(index=False))
    print()
    
    # Fetch data for all cities
    print('🚀 Fetching climate data...')
    print('=' * 70)
    results = fetch_all_cities(CITIES, START_DATE, END_DATE)
    
    # Save all data
    print()
    print('💾 Saving data to CSV files...')
    print('=' * 70)
    saved_files = []
    for city_name, df in results.items():
        filepath = save_to_csv(df, city_name, RAW_DATA_DIR)
        if filepath:
            saved_files.append(filepath)
    
    # Summary
    print()
    print('=' * 70)
    print('✅ SUMMARY')
    print('=' * 70)
    total_records = sum(len(df) for df in results.values() if not df.empty)
    expected_records = len(CITIES) * 10 * 365.25 * 24
    completion_pct = (total_records / expected_records) * 100
    
    print(f'Total cities: {len(CITIES)}')
    print(f'Cities with data: {sum(1 for df in results.values() if not df.empty)}')
    print(f'Total hourly records: {total_records:,}')
    print(f'Expected records: {expected_records:,.0f}')
    print(f'Data completion: {completion_pct:.1f}%')
    print()
    print('Saved files:')
    for i, filepath in enumerate(saved_files, 1):
        print(f'  {i}. {os.path.basename(filepath)}')
    print()
    print('✅ Climate data fetching complete!')


if __name__ == '__main__':
    main()
