"""simcore: shared annual simulation engine for the portfolio projects.

Modules
-------
weather  : real ERA5 hourly weather (Open-Meteo archive), cached per site/year
grid     : GB grid carbon intensity (NESO API) and Octopus Agile prices, hourly
solar    : solar position, plane-of-array irradiance and PV performance
thermo   : CoolProp state evaluation, compressor maps, cycle state points, exergy
hx       : effectiveness-NTU heat exchanger models
storage  : stratified multi-node thermal storage
building : ISO 13790 5R1C hourly zone model
output   : results container, binary viewer export, KPI summary, CSV export
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "cache"
CACHE.mkdir(exist_ok=True)
YEAR = 2023
HOURS = 8760
