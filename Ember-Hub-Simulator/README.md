# Ember Hub Simulator

Interactive version of the Ember Bristol–London coach charging hub study: change the route, timetable, coach, charging,
driver and cost inputs, pick a hub site, and the fleet, chargers, grid connection, drivers, hub design and annual cost
update at once, with a minute-by-minute simulation of the operating day.

* **Model:** a line-by-line port of the Ember Google Sheet (`HubModel`, tabs "Inputs & Variables" and "Site Selection",
  state of 2026-10-28); `tests/test_sheet_parity.py` pins the sheet's S1–S3 results (S1 Temple Works: 8 coaches,
  2 × 600 kW, 2,000 kVA, 34 drivers, £2,819,401/yr, £322 per trip, rank 1).
* **Operating day:** `DaySimulation` runs the timetable with the sized fleet at 1 min steps (dispatch, route, charger
  queue, charging) and drives the playhead.
* **Hub design:** the final Temple Works design from Ember-Site-Selection (`scripts/hub_design.py`): EMB-HUB-003, 8
  drive-through lanes, and EMB-HUB-005, the 11-lane expansion. The app picks the variant that holds the fleet and flags
  a fleet above 11. Swept paths and clearances come from the design.
* **Map:** the ORS coach route, the ORS dead run from Bristol Coach Station to the hub, the listed sites S1–S3, the QGIS
  screened plots and the design drawn in place (British National Grid frame of `site_frame.py`).
* **Other routes:** search either end (Nominatim); the road route comes from OSRM and the coach time is the car time
  scaled to the sheet's Bristol–Victoria 3:07. Away from Bristol the app screens OSM plots around the new origin with the
  QGIS criteria.

## Quick start

```
uv sync
uv run pytest -q                       # sheet parity, model, design, web API, run folders, notebooks
uv run ember-hub-simulator app          # http://127.0.0.1:8000
uv run ember-hub-simulator run          # results/<date>_baseline/
uv run ember-hub-simulator report       # docs/report.pdf, docs/slides.pdf
uv run python tools/build_static.py     # dist/ + zip: the server-free build for sharing (SHARING.md)
```

Data imports (re-run when the QGIS project changes):

```
uv run python tools/export_gis.py       # route, listed sites, screened plots, substations -> data/bristol_gis.json
uv run python tools/export_design.py    # hub design + ORS dead run -> data/temple_works_design.json
```

simcore is an editable path dependency (`../simcore`); this folder must sit next to the simcore checkout.

## Layout

See `AGENTS.md`. Model description and sheet cell map: `docs/THEORY.md`. Sharing: `SHARING.md`.
