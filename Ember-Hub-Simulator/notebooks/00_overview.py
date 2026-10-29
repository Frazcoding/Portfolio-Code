# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # 00 Overview: Ember Hub Simulator
#
# Ember Bristol-London coach charging hub: operations, cost and site layout simulator (Sim Workbench project).
#
# | Layer | Where | Role |
# |---|---|---|
# | Engine | `simcore` | run folders and unit conversion (this is an operations / cost model, not physics) |
# | Model | `src/ember_hub_simulator/model.py` | `HubModel` (Ember sheet port), `DaySimulation` (operating day) |
# | Layout | `src/ember_hub_simulator/layout.py` | parametric REV B hub layout + swept-path checks |
# | Config | `config/baseline.toml` | every parameter, unit-suffixed (sheet baseline) |
# | Runs | `results/<date>_<name>/` | `config.toml`, `manifest.json`, `timeline.parquet` + `sites.json`, `layout.json`, `trips.json` |
# | Front end | `app/` | FastAPI + Sim Workbench: map (Leaflet), hub plan, 3D hub (three.js) |
# | Documents | `docs/` | `THEORY.md`, Typst `report.typ` / `slides.typ` |
#
# ## How to run
#
# ```
# uv run ember-hub-simulator run              # simulate config/baseline.toml -> results/
# uv run ember-hub-simulator app              # web workbench on http://127.0.0.1:8000
# uv run ember-hub-simulator figures          # docs/figures/*.svg + .png from the latest run
# uv run ember-hub-simulator report           # docs/report.pdf and docs/slides.pdf
# uv run pytest -q                           # tests, including these notebooks
# ```

# %%
import ember_hub_simulator
from ember_hub_simulator import Config, ProjectPaths

paths = ProjectPaths.discover()
print("Ember Hub Simulator: version", ember_hub_simulator.__version__)
print("project root:", paths.root)

# %% [markdown]
# ## The baseline configuration
#
# Units are in the key names (`_km`, `_min`, `_kW`); `Params.from_config` converts to SI once.

# %%
cfg = Config.from_toml(paths.baseline)
cfg
