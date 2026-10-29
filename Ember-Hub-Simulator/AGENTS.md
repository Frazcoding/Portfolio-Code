# Ember Hub Simulator: agent instructions

Ember Bristol-London coach charging hub: operations, cost and site layout simulator (Sim Workbench project). Generated from `Frazcoding/sim-template`. Fraser's global conventions apply; the ones that matter here:

## Purpose and layout

```
config/baseline.toml     every model parameter (unit-suffixed keys): the Ember sheet baseline, S1 selected
data/                    sites_bristol.json (sheet S1-S3), bristol_gis.json (QGIS layers), temple_works_design.json
                         (final hub design + ORS dead run); written by tools/export_*.py from Ember-Site-Selection
src/ember_hub_simulator/
  config.py              Config dataclasses (TOML -> validated), ParamSpec table, ProjectPaths
  model.py               Params (SI), HubModel (sheet port), DaySimulation (operating day), Simulation -> SimOutput
  design.py              HubDesign: the imported EMB-HUB-003 / -005 design, variant per fleet size
  geo.py                 Nominatim, OSRM (routes, dead-run tables), Overpass site screening (QGIS criteria)
  runner.py              Runner (simcore Run folders), SiteCatalogue, Payloads (JSON shapes of the web API)
  webapi.py              WebApi: the JSON API shared by app/server.py and the browser build (Pyodide)
  figures.py / report.py matplotlib (fraser style) and Typst builders; cli.py: `ember-hub-simulator` console script
app/server.py            FastAPI over WebApi; app/static/ = Sim Workbench shell (tokens.css, bundle.css, bundle.js verbatim)
                         + app.js (map, plan, 3D, inputs) + backend.js (browser backend for the static build) + ember.css
tools/                   export_gis.py, export_design.py (data imports), build_static.py (dist/ + zip for sharing)
notebooks/               Jupytext percent scripts (00_overview, 01_model); executed by the tests
docs/                    THEORY.md (model + sheet cell map), report.typ, slides.typ, style/fraser.typ, figures/
results/<date>_<name>/   config.toml, manifest.json, timeline.parquet, sites.json, layout.json, trips.json
tests/                   pytest; test_sheet_parity.py pins the sheet; notebooks are marked `notebook`
```

**This is an operations and cost model, not physics:** it uses simcore only for unit conversion and run folders, and
its relations are the Ember sheet's formulas (rule 1 below does not apply to them). When the sheet changes, update
`model.py`, `config/baseline.toml`, `data/sites_bristol.json` and `tests/test_sheet_parity.py` together. The hub design
is not generated here: change it in Ember-Site-Selection and re-run `tools/export_design.py`.

## Commands

```
uv sync                           # install (add --extra tracking for MLflow)
uv run pytest -q                  # all tests incl. notebooks; -m "not notebook" for the quick set
uv run ember-hub-simulator run [config.toml]   # simulate -> results/<date>_<name>/
uv run ember-hub-simulator app --port 8000     # Sim Workbench
uv run ember-hub-simulator figures | report | mlflow-index
uv run python tools/build_static.py      # server-free build for sharing (SHARING.md)
```

## Rules

1. **Physics lives in simcore.** Compose `simcore` equations; never re-derive or re-type one in this project. A missing
   equation goes into simcore (with docstring, source, validity range and a reference test) first. Project-level relations
   that are not yet there are marked `TODO(simcore)` in `model.py`; do not add more without telling Fraser.
2. **Object-oriented.** Models, components and equations are classes (dataclasses for parameters and state, equations as
   methods). No loose module-level functions except thin entry points.
3. **SI internally** (K, Pa, W, J, kg, s); the unit goes in the name (`T_K`, `p_Pa`, `_C`, `_kW` at the edges). Convert with
   `simcore.core.Units`. State units in docstrings, labels and plots.
4. **Config:** all parameters in `config/baseline.toml` and `Config`; new parameter = new field + `ParamSpec` (range) + TOML key.
5. **Runs:** every run writes `results/<YYYY-MM-DD>_<name>/` (config.toml, manifest.json, Parquet). MLflow is optional and only
   an index over the run folders (store kept outside kDrive).
6. **THEORY.md:** `docs/THEORY.md` documents the physics. Change the physics, change THEORY.md in the same commit. Cite sources
   (author year / standard clause); write `TODO(verify)` rather than inventing a citation.
7. **Notebooks:** thin; import the package and simcore, never define physics. Every equation gets its own markdown cell
   (`EquationDisplay.show` for simcore equations; LaTeX with source for project-level ones) then one code cell evaluating it.
8. **Plots:** `PlotStyle.apply()` (= `plt.style.use("fraser")`); axis labels `Quantity symbol (unit)`, dimensionless `(–)`; direct
   series labels; panels titled `(a) ...`; validation plots with 1:1 dashed line, ±10 % band, RMSE and n. Export SVG + 300 dpi PNG.
9. **Front end:** keep `app/static/{tokens.css,bundle.css,bundle.js}` verbatim from the Sim Workbench design system; app logic goes in `app.js`.
   The plan and 3D views draw the imported design features (palette of Ember-Site-Selection/scripts/12_blender_design.py).
10. **Documents:** Typst with `docs/style/fraser.typ`; numbers come from `docs/kpis.json` (written by `report`), never typed by hand.
11. **Git:** commit and push in logical chunks with clear messages. Never force-push.
12. British English, direct and concise.
