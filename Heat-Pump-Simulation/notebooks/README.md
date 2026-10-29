# Climate Data Notebooks

This directory contains three Jupyter notebooks for fetching, processing, and validating climate data for 11 UK cities.

## 📁 Notebooks

### 1. [01_Climate_Data_Fetcher.ipynb](./01_Climate_Data_Fetcher.ipynb)
**Purpose:** Fetch raw hourly climate data from Meteostat for 11 UK cities (2014-2024)

**What it does:**
- Installs required dependencies (meteostat, pandas, numpy, tqdm)
- Defines 11 UK cities with coordinates (including Lerwick in Shetland Islands)
- Fetches hourly data for each city using Meteostat API
- Saves raw data to CSV files in `data/climate/`

**Output:**
- 11 CSV files with raw hourly climate data
- Each file: `{city_name}_2014-2024_hourly.csv`

**Runtime:** ~30-60 minutes (depends on Meteostat rate limits)

---

### 2. [02_Climate_Data_Processor.ipynb](./02_Climate_Data_Processor.ipynb)
**Purpose:** Process and enrich raw climate data

**What it does:**
- Loads raw CSV files
- Cleans data (missing values, outliers)
- Calculates derived metrics:
  - Solar radiation from sunshine duration (Angstrom-Prescott correlation)
  - Heating Degree Days (HDD) - base 15.5°C
  - Cooling Degree Days (CDD) - base 22.0°C
  - Design temperatures (1% winter, 99% summer percentiles)
- Aggregates monthly statistics
- Saves processed data to CSV files

**Output:**
- Processed hourly data: `data/climate/processed/{city_name}_2014-2024_hourly_processed.csv`
- Monthly statistics: `data/climate/monthly/{city_name}_monthly_stats.csv`

**Runtime:** ~10-15 minutes

---

### 3. [03_Climate_Data_Validation.ipynb](./03_Climate_Data_Validation.ipynb)
**Purpose:** Validate processed data against UK climate standards

**What it does:**
- Validates data against expected UK climate ranges
- Compares design temperatures with CIBSE Guide A guidelines
- Validates HDD values against Degree Days.net expectations
- Checks data quality (completeness, gaps)
- Generates visualizations for comparison
- Produces detailed validation report

**Output:**
- Validation report with pass/fail status for each city
- Comparative visualizations
- Detailed statistics for each city

**Runtime:** ~5-10 minutes

---

## 🌍 Cities Included

| City | Region | Latitude | Longitude | Climate Notes |
|------|--------|----------|-----------|---------------|
| London | South East | 51.5074° N | 0.1278° W | Mild winters, warm summers |
| Manchester | North West | 53.4808° N | 2.2426° W | Cooler, wetter |
| Birmingham | West Midlands | 52.4862° N | 1.8904° W | Continental influence |
| Leeds | Yorkshire | 53.7995° N | 1.5490° W | Cooler northern climate |
| Glasgow | Scotland | 55.8642° N | 4.2518° W | Maritime, cooler |
| Edinburgh | Scotland | 55.9533° N | 3.1883° W | Cooler, windier |
| Cardiff | Wales | 51.4816° N | 3.1790° W | Maritime, mild |
| Belfast | Northern Ireland | 54.5973° N | 5.9301° W | Maritime, cool |
| Bristol | South West | 51.4545° N | 2.5879° W | Mild, wet |
| Newcastle | North East | 54.9783° N | 1.6177° W | Coolest mainland |
| **Lerwick** | **Shetland Islands** | **60.1550° N** | **1.1456° W** | **Far north, cool and windy** |

---

## 📊 Data Structure

### Raw Data (from Notebook 1)
```
data/climate/
├── uk_cities_metadata.csv          # City coordinates and metadata
├── london_2014-2024_hourly.csv
├── manchester_2014-2024_hourly.csv
├── birmingham_2014-2024_hourly.csv
├── leeds_2014-2024_hourly.csv
├── glasgow_2014-2024_hourly.csv
├── edinburgh_2014-2024_hourly.csv
├── cardiff_2014-2024_hourly.csv
├── belfast_2014-2024_hourly.csv
├── bristol_2014-2024_hourly.csv
├── newcastle_2014-2024_hourly.csv
└── lerwick_2014-2024_hourly.csv
```

### Processed Data (from Notebook 2)
```
data/climate/processed/
├── london_2014-2024_hourly_processed.csv
├── manchester_2014-2024_hourly_processed.csv
├── ... (all 11 cities)

data/climate/monthly/
├── london_monthly_stats.csv
├── manchester_monthly_stats.csv
└── ... (all 11 cities)
```

---

## 📦 Dependencies

Run this command before executing the notebooks:

```bash
pip install meteostat pandas numpy tqdm matplotlib seaborn
```

---

## 🚀 Execution Order

1. **Run Notebook 1** - Fetch raw data
2. **Run Notebook 2** - Process and enrich data
3. **Run Notebook 3** - Validate and visualize

---

## 📚 Data Dictionary

### Hourly Data Columns (Raw & Processed)

| Column | Unit | Description | Source |
|--------|------|-------------|--------|
| `time` | ISO8601 | Timestamp (hourly) | Meteostat |
| `temp` | °C | Air temperature | Meteostat |
| `dwpt` | °C | Dew point temperature | Meteostat |
| `rhum` | % | Relative humidity | Meteostat |
| `wspd` | m/s | Wind speed | Meteostat |
| `wdir` | ° | Wind direction | Meteostat |
| `pres` | hPa | Atmospheric pressure | Meteostat |
| `tsun` | min | Sunshine duration | Meteostat |
| `precip` | mm | Precipitation | Meteostat |
| `solar_rad` | W/m² | Calculated solar radiation | Angstrom-Prescott |
| `hdd_daily` | °C·day | Daily Heating Degree Days | Calculated |
| `cdd_daily` | °C·day | Daily Cooling Degree Days | Calculated |
| `hdd_annual` | °C·day | Annual HDD (cumulative) | Calculated |
| `cdd_annual` | °C·day | Annual CDD (cumulative) | Calculated |
| `year` | int | Year | Derived |
| `month` | int | Month (1-12) | Derived |
| `day` | int | Day of month | Derived |
| `hour` | int | Hour of day | Derived |
| `day_of_year` | int | Day of year (1-366) | Derived |
| `city` | str | City name | Metadata |

### Monthly Statistics Columns

| Column | Unit | Description |
|--------|------|-------------|
| `year` | int | Year |
| `month` | int | Month (1-12) |
| `avg_temp` | °C | Average temperature |
| `min_temp` | °C | Minimum temperature |
| `max_temp` | °C | Maximum temperature |
| `avg_humidity` | % | Average relative humidity |
| `avg_wind_speed` | m/s | Average wind speed |
| `avg_solar_rad` | W/m² | Average solar radiation |
| `total_precip` | mm | Total precipitation |
| `hdd_monthly` | °C·day | Monthly HDD total |
| `cdd_monthly` | °C·day | Monthly CDD total |

---

## 🔍 Validation Standards

### Temperature Ranges (UK)
- **Minimum:** -15°C to 40°C
- **Average:** -5°C to 30°C

### Humidity Ranges
- **Range:** 0-100%
- **Average:** 50-90%

### Wind Speed Ranges
- **Range:** 0-50 m/s
- **Average:** 0-25 m/s

### Pressure Ranges
- **Range:** 950-1050 hPa
- **Average:** 980-1030 hPa

### Solar Radiation Ranges
- **Range:** 0-1200 W/m²
- **Average:** 0-800 W/m²

### HDD Expectations (Annual)
| City | Expected HDD Range (°C·days) |
|------|-----------------------------|
| London | 2000-2500 |
| Manchester | 2500-3000 |
| Birmingham | 2400-2800 |
| Leeds | 2600-3100 |
| Glasgow | 2800-3300 |
| Edinburgh | 2800-3300 |
| Cardiff | 2000-2500 |
| Belfast | 2500-3000 |
| Bristol | 2000-2500 |
| Newcastle | 2800-3300 |
| Lerwick | 3200-3700 |

---

## 🎯 Design Temperature Standards (CIBSE Guide A)

| City | Winter Design (°C) | Summer Design (°C) |
|------|---------------------|---------------------|
| London | -3.0 | 31.0 |
| Manchester | -5.0 | 28.0 |
| Birmingham | -5.0 | 29.0 |
| Leeds | -6.0 | 28.0 |
| Glasgow | -7.0 | 27.0 |
| Edinburgh | -7.0 | 26.0 |
| Cardiff | -4.0 | 29.0 |
| Belfast | -5.0 | 27.0 |
| Bristol | -4.0 | 29.0 |
| Newcastle | -7.0 | 27.0 |
| Lerwick | -8.0 | 23.0 |

---

## 📖 Sources & References

### Primary Data Source
- [Meteostat](https://meteostat.net) - Free historical weather data
- [Meteostat Python Library](https://dev.meteostat.net/python/)
- Data sources: NOAA, ECAD, and other meteorological services
- License: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

### Validation References
- [CIBSE Guide A: Environmental Design](https://www.cibse.org/knowledge/knowledge-items/detail?article=Guide_A_Environmental_design)
- [Met Office UK Climate Averages](https://www.metoffice.gov.uk/research/climate/maps-and-data/uk-and-regional-series)
- [Degree Days.net](https://www.degreedays.net/)

### UK Climate Information
- [UK Climate Projections](https://www.metoffice.gov.uk/research/climate/seasonal-to-decadal/long-range/uk-climate-projections)
- [Climate Data Online](https://www.metoffice.gov.uk/public/weather/climate-historic/#?tab=climateDataOnline)

---

## 💡 Tips

1. **Run notebooks in order** - Each notebook depends on the output of the previous one
2. **Check file paths** - Ensure `data/climate/` directory exists
3. **Monitor progress** - Data fetching may take time due to rate limits
4. **Review validation** - Check the validation report for any warnings
5. **Backup data** - Consider backing up the CSV files after processing

---

## ❓ Troubleshooting

### Common Issues

1. **Meteostat rate limits**
   - Solution: Wait and retry, or use caching
   - Meteostat has a free tier with rate limits

2. **Missing files**
   - Solution: Ensure Notebook 1 completed successfully
   - Check that all CSV files exist in `data/climate/`

3. **Memory issues**
   - Solution: Process cities one at a time
   - Close other applications to free up memory

4. **Dependency errors**
   - Solution: Run `pip install meteostat pandas numpy tqdm matplotlib seaborn`
   - Ensure you're using Python 3.7+

---

## 🔄 Re-running the Pipeline

To update the climate data with a new time period:

1. Update the date range in Notebook 1
2. Re-run all three notebooks in order
3. New CSV files will overwrite the old ones

---

## 📞 Support

For questions or issues with the climate data notebooks:
- Check the validation report in Notebook 3
- Review the sources listed above
- Ensure all dependencies are installed
