"""Greenhouse climate strategies (setpoint calendars). Northern-hemisphere day-of-year; day = global radiation > 20 W/m2.

The crop-led calendar follows the 'Hass' cycle: autumn/winter floral induction by cool temperatures, spring
flowering and fruit set, summer fruit growth and vegetative flush. Each period carries its sources.
"""
from config import Climate, ClimatePeriod

SOURCES = {
    "BA78": "Buttrose & Alexander (1978) Scientia Horticulturae 8:213-217 - 'Fuerte' floral initiation promoted by "
            "18/13 C day/night and short days, not at 25/20 or 30/25 C",
    "SG99": "Salazar-Garcia, Lord & Lovatt (1999) J Amer Soc Hort Sci 124:478-482 - 'Hass' fully committed to flower "
            "after 4 weeks at 10/7 C (83 % inflorescences; 3 weeks 17 %; <= 2 weeks none); also flowers after 3-4 months "
            "at 15/10, 18/15, 20/15 or 23/18 C, not at 25/20 or 30/25 C",
    "SA81": "Sedgley & Annells (1981) Scientia Horticulturae 14:27-33 - 'Hass' sets fruit from 17/12 to 33/28 C; "
            "flowering season 85, 42 and 15 days at 17/12, 25/20 and 33/28 C",
    "SW03": "Schaffer & Whiley (2003) Proc. V World Avocado Congress 335-342 - photosynthesis optimum ~20-24 C "
            "('Edranol'), 28-31 C ('Fuerte'); nights < 10 C cut quantum yield ~40 % and damage PSII; > 12.9 C no damage",
}


def thesis():
    return Climate()


def crop_led(night_induction=12.0, summer_vent=24.0):
    """'Hass' calendar. Nights stay >= 12 C (above the 10-12.9 C chilling-damage band [SW03]) while giving a
    15-18 C daily mean through Oct-Feb, inside the 3-4 month induction regimes of [SG99]/[BA78]."""
    return Climate(
        name="crop_led",
        periods=[
            ClimatePeriod(1, 18.0, 12.0, 24.0, 18.0, "Jan-Feb: induction completes, inflorescence development [SG99, SW03]"),
            ClimatePeriod(60, 22.0, 15.0, 26.0, 20.0, "Mar-May: flowering + fruit set; shorter, warmer flowering is fine "
                                                      "for 'Hass' [SA81]"),
            ClimatePeriod(152, 20.0, 15.0, summer_vent, min(22.0, summer_vent - 2), "Jun-Sep: fruit growth + flush [SW03]"),
            ClimatePeriod(274, 18.0, night_induction, 22.0, 16.0, "Oct-Dec: floral induction, ~18/13 C regime [BA78, SG99]"),
        ],
        rh_vent_start=85.0,
        source="; ".join(SOURCES.values()),
    )


STRATEGIES = {"thesis": thesis, "crop_led": crop_led}
