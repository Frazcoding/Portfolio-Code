"""Crop library for the multi-crop comparison: UK glasshouse inputs and import-side categories for each crop.

UK side: yield, labour, consumables and CO2 dosing come from the literature (marked by confidence). Heat and electricity
come from the greenhouse simulation run with each crop's own setpoint calendar (run_crops.py), unlit, ground-source
heat pump, 1 ha at Chelmsford. Avocado keeps its own growth model (crop.py) and import benchmark (imports.py).

Import side: farm-stage carbon by production system, from Poore & Nemecek (2018) category means for unheated/field
origins and from the Dutch sector energy monitor for heated glass (NL, BE); transport is computed per origin
(crop_imports.py); prices are Comtrade CIF unit values.
"""
from config import Climate, ClimatePeriod

SOURCES = {
    "CBS": "CBS StatLine table 37738 'Groenteteelt; oogst en teeltoppervlakte per groentesoort', NL glasshouse harvest / "
           "area, mean 2022-2024 (sector average, lit and unlit, all types)",
    "PN18": "Poore & Nemecek (2018) Science 360:987, supply-chain stage means via Our World in Data "
            "'food-emissions-supply-chain' (kg CO2e/kg): farm, processing, packaging",
    "WUR24": "Smit (2025) Energiemonitor van de Nederlandse glastuinbouw 2024, WUR (edepot.wur.nl/702373): "
             "cultivation-related CO2 emission ~37 kg/m2 (sector average incl. ornamentals)",
    "BAR15": "Barbosa et al. (2015) Int J Environ Res Public Health 12:6879 - hydroponic greenhouse lettuce 41 kg/m2/yr "
             "(Arizona, high light); cited in the BEng thesis",
    "SET": "Typical commercial setpoints (Heuvelink ed. 2018 'Tomatoes' CABI; grower guides); to be refined per crop",
    "EST": "Estimate for the screen; replace with sourced values before use in the write-up",
}

# P&N category values (kg CO2e/kg): farm, processing, packaging, land-use change (reported, not added)
PN = {
    "tomatoes": {"farm": 0.7054468, "processing": 0.012381556, "packaging": 0.14567137, "luc": 0.37298727},
    "other_veg": {"farm": 0.17617308, "processing": 0.06040515, "packaging": 0.041747507, "luc": 0.001180576},
    "berries_grapes": {"farm": 0.7178481, "processing": 0.0, "packaging": 0.21109232, "luc": 0.024600998},
}
NL_ENERGY_CO2_M2 = 37.0  # [WUR24]


def _clim(name, periods, src="SET"):
    return Climate(name=name, periods=[ClimatePeriod(*p) for p in periods], source=SOURCES[src])


# Setpoint calendars: (start_doy, heat_day, heat_night, vent_day, vent_night, label)
CLIMATES = {
    "tomato": _clim("tomato", [(1, 19, 17, 23, 20, "year-round truss tomato, planted mid-Dec"),
                               (340, 8, 8, 18, 15, "crop change, ~3 weeks")]),
    "cucumber": _clim("cucumber", [(1, 21, 20, 25, 22, "three crops per year, warm crop")]),
    "pepper": _clim("pepper", [(1, 21, 19, 24, 21, "planted Dec, harvest Mar-Nov"),
                               (330, 8, 8, 18, 15, "crop change")]),
    "aubergine": _clim("aubergine", [(1, 21, 19, 25, 22, "planted Dec, harvest Mar-Nov"),
                                     (330, 8, 8, 18, 15, "crop change")]),
    "lettuce": _clim("lettuce", [(1, 14, 10, 18, 15, "continuous butterhead, cool crop")]),
    "strawberry": _clim("strawberry", [(1, 15, 10, 22, 18, "Jan-Jul forced crop"),
                                       (213, 15, 10, 22, 18, "Aug-Oct second crop"),
                                       (305, 2, 2, 10, 8, "Nov-Dec dormancy, frost protection")]),
    "raspberry": _clim("raspberry", [(1, 2, 2, 8, 6, "dormant long canes"),
                                     (60, 14, 10, 22, 18, "Mar-Jul crop"),
                                     (213, 14, 10, 22, 18, "Aug-Nov primocane crop"),
                                     (335, 2, 2, 8, 6, "dormancy")]),
    "blueberry": _clim("blueberry", [(1, 2, 2, 7, 5, "chilling, frost protection only"),
                                     (60, 12, 8, 22, 18, "Mar-Jun forced crop"),
                                     (182, 5, 5, 24, 20, "Jul-Oct unheated"),
                                     (305, 2, 2, 7, 5, "chilling")]),
    "grape": _clim("grape", [(1, 2, 2, 8, 6, "dormancy"),
                             (60, 15, 12, 25, 20, "Mar-May budbreak to flowering"),
                             (152, 12, 10, 27, 22, "Jun-Sep fruit growth"),
                             (274, 5, 5, 20, 15, "Oct-Nov leaf fall"),
                             (335, 2, 2, 8, 6, "dormancy")]),
}

# UK glasshouse and import-side parameters per crop.
# yield kg/m2/yr (central, low, high); labour h/m2/yr; consumables kg CO2e/m2/yr (fertiliser, substrate, plastics);
# co2_dose kg/m2/yr; pack_gbp GBP/kg; hs codes; pn category; heated_origins = origins treated as heated glass
CROPS = {
    "tomato": dict(name="Tomato", yield_=(48.0, 41.0, 60.0), yield_src="CBS", labour=0.9, consumables=2.5, co2_dose=25.0,
                   pack_gbp=0.15, hs="070200", pn="tomatoes", heated_origins=("NLD", "BEL")),
    "cucumber": dict(name="Cucumber", yield_=(65.0, 64.0, 80.0), yield_src="CBS", labour=0.8, consumables=2.5,
                     co2_dose=25.0, pack_gbp=0.10, hs="070700", pn="other_veg", heated_origins=("NLD", "BEL")),
    "pepper": dict(name="Sweet pepper", yield_=(26.4, 25.9, 30.0), yield_src="CBS", labour=0.75, consumables=2.5,
                   co2_dose=25.0, pack_gbp=0.15, hs="070960", pn="other_veg", heated_origins=("NLD", "BEL")),
    "aubergine": dict(name="Aubergine", yield_=(48.9, 48.0, 50.0), yield_src="CBS", labour=0.9, consumables=2.5,
                      co2_dose=25.0, pack_gbp=0.15, hs="070930", pn="other_veg", heated_origins=("NLD", "BEL")),
    "lettuce": dict(name="Lettuce", yield_=(20.0, 12.0, 41.0), yield_src="BAR15", labour=0.35, consumables=1.0,
                    co2_dose=10.0, pack_gbp=0.10, hs="070511,070519", pn="other_veg", heated_origins=()),
    "strawberry": dict(name="Strawberry", yield_=(11.1, 10.5, 11.8), yield_src="CBS", labour=0.8, consumables=2.5,
                       co2_dose=10.0, pack_gbp=0.50, hs="081010", pn="berries_grapes", heated_origins=()),
    "raspberry": dict(name="Raspberry", yield_=(3.0, 2.0, 4.0), yield_src="EST", labour=1.0, consumables=2.5,
                      co2_dose=0.0, pack_gbp=0.60, hs="081020", pn="berries_grapes", heated_origins=()),
    "blueberry": dict(name="Blueberry", yield_=(2.5, 2.0, 3.0), yield_src="EST", labour=0.6, consumables=2.0,
                      co2_dose=0.0, pack_gbp=0.50, hs="081040", pn="berries_grapes", heated_origins=()),
    "grape": dict(name="Table grape", yield_=(2.5, 2.2, 2.9), yield_src="EST", labour=0.4, consumables=0.1,
                  co2_dose=0.0, pack_gbp=0.25, hs="080610", pn="berries_grapes", heated_origins=()),
}
YIELD_NOTES = {
    "raspberry": "1.5-2.5 kg/plant in Dutch glass ('Kwanza', Philips hortiblog); vertical farm 2.5 kg/m2 per 18-week cycle",
    "blueberry": "Substrate under protection 20-30 t/ha (hortidaily 2020); Teagasc tunnel ~20 t/ha",
    "grape": "Soilless greenhouse table grape 21.7-29.4 t/ha under Mediterranean conditions (researchgate.net/publication/256547182; authors to confirm)",
    "lettuce": "Glasshouse soil/NFT, UK unlit winter; 41 kg/m2 is a high-light hydroponic upper bound [BAR15]",
    "strawberry": "NL 'onder glas en tunnels' (glass + tunnel mix) [CBS]",
}
LABOUR_NOTE = ("Labour h/m2/yr are estimates: glasshouse fruit vegetables ~0.75-1.0 (harvest + crop work), berries "
               "harvest-heavy, grapes and lettuce lower")


def farm_import(crop, iso3):
    """Farm-stage kg CO2e/kg for an origin: (central, low, high, system, source)."""
    c = CROPS[crop]
    pn = PN[c["pn"]]
    if iso3 in c["heated_origins"]:
        y = c["yield_"][0]
        central = NL_ENERGY_CO2_M2 / y + PN["other_veg"]["farm"]
        return (central, 0.7 * NL_ENERGY_CO2_M2 / y + 0.1, 1.3 * NL_ENERGY_CO2_M2 / y + 0.3, "heated glass",
                "WUR24 sector energy CO2 / CBS yield + PN18 'other vegetables' farm stage for non-energy inputs")
    lo = {"tomatoes": 0.3, "other_veg": 0.1, "berries_grapes": 0.3}[c["pn"]]
    hi = {"tomatoes": 1.0, "other_veg": 0.4, "berries_grapes": 1.2}[c["pn"]]
    note = " (global mean includes heated production: high for Mediterranean tunnels)" if c["pn"] == "tomatoes" else ""
    return (pn["farm"], lo, hi, "unheated / field", f"PN18 '{c['pn']}' farm-stage global mean{note}")
