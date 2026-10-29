# Handover — simulation portfolio upgrade (state at 2026-10-01)

Start here in the next session. Background reading: `VIEWER_DATA.md` (architecture, rebuild) and `MODEL_AUDIT.md`
(per-project assumptions, results, findings). Pre-upgrade snapshot: `_archive/pre_upgrade_2026-10-01.zip`.
This folder is **not a git repository**; history relies on kDrive sync and the archive zip.

## Current state

All eight projects have a full-year 2023 simulation (8,760 h; UniBoat also a 1 s race; WLC also a 60-year lifecycle),
a procedurally generated photoreal Blender model, and a viewer on the shared `viewer_core`. All eight viewers were
verified loading model + data. `python build_all.py` regenerates everything from cached results.

| Project | Scenarios | Model script | Sim |
| --- | --- | --- | --- |
| Heat-Pump-Simulation | london, london_agile, glasgow | `create_heatpump_asset.py` | `annual_sim.py` (+ `model/`) |
| High-Temp-Waste-Heat-Recovery | dairy_butane, dairy_r1234zez, steam_r1233 | `create_industrial_asset.py` | `annual_sim.py` (+ `model/`) |
| Building-Heatpump-Retrofit | tes_smart, tes_basic, direct | `create_retrofit_asset.py` | `annual_sim.py` (+ `model/`) |
| BEng-CEA-Heatpump | air, ground, water, thesis | `create_greenhouse_asset.py` | `sim/annual_sim.py` |
| Plantpost | london, edinburgh, bologna, edinburgh_200ah | `create_plantpost_asset.py` | `annual_sim.py` (uses `src/config.py`) |
| PyPsa-Green-Hydrogen-Microgrid | base, weak_grid, half_pem | `create_hydrogen_asset.py` | `annual_sim.py` |
| UniBoat-Powertrain-Cooling | season, race | `create_uniboat_asset.py` | `annual_sim.py` |
| Whole-Carbon-Lifecycle-Assessment | scenario_1..4_year, lifecycle | `create_wlc_asset.py` | `annual_sim.py` (+ `src/` engine) |

## Open engineering issues (decide / fix)

1. **UniBoat cooling sizing** — physics gives ~2.9 kW peak heat at 36 kt vs the documented 11.6 kW design; the loop is
   oversized. Either resize the loop/plates or revisit the hydrodynamic and loss assumptions (catamaran resistance,
   foil L/D, motor map). Hull and foil geometry are still estimates.
2. **WLC performance gap** — simulated net EUI for low-carbon scenarios 63–73 kWh/m² vs engine config 45–55. Decide
   whether to calibrate unregulated loads (small power 10 W/m², base 2.5 + 1.5 W/m²) or keep the gap as a finding.
3. **Hydrogen dispatch is rule-based**, not a PyPSA optimisation despite the project name. Option: run a PyPSA LP
   (pypsa 1.3 + HiGHS are installed) for capacity/dispatch and feed it into the physics model.
4. **Agile load-shifting gains are small** (Heat-Pump-Simulation ~1–4 %). Possible next step: a predictive controller
   using the day-ahead price curve.
5. **HTHP/steam economics** depend on fixed 2023 tariffs (£/kWh in `High-Temp-Waste-Heat-Recovery/annual_sim.py`);
   add tariff scenarios (e.g. 2025 prices, CfD, UK IETF grant) if economics matter.
6. **Hydrogen compressor state points** show design-state temperatures even when flow is zero — mask with NaN when
   `h2_rate == 0`.
7. **Greenhouse auxiliary power bug** — `BEng-CEA-Heatpump/sim/annual_sim.py` has `(900.0 * vent > 0.02)` in `W_aux`,
   which adds 1 W instead of 900 W while venting (about 5 % of annual electricity). It is left as-is so the published viewer
   numbers do not move; the new `lca/` model fixes it for new cases.
8. **UK glasshouse vs imports study in progress** (started as avocado LCA/LCC) — start from
   `BEng-CEA-Heatpump/lca/HANDOFF.md` (state at 2026-10-02, next steps); full record in `BEng-CEA-Heatpump/lca/SCOPE.md`.
   Python environment: `C:\Users\frase\.venvs\portfolio` (outside kDrive).

## Polish backlog

- Grass texture tiling visible at long range (ground disc in `viewer_core/viewer.js` and site grass boxes); add a
  macro-variation layer or larger tile.
- GLB sizes 3–34 MB (greenhouse, WLC largest). Options: 512 px textures for small parts, KTX2/WebP textures, instance
  repeated geometry (crop, PV panels). Draco was disabled because the decoder stalls; meshopt is an alternative.
- Some default cameras could be tightened (UniBoat race, WLC lifecycle). Set in each `make_*.py` → `scene_cfg()`.
- Old `*_scene.js` files in each project are unused leftovers (originals are also in the archive zip).
- `CALCULATIONS_WHITE_PAPER.md` / project READMEs still describe the earlier models in places.

## Calibration choices worth knowing

- Frost/defrost: coil surface at refrigerant + 35 % of the air–refrigerant difference; defrost at 7 kg (heat pump),
  5 kg per module (retrofit), 14 kg (greenhouse air cooler).
- Plantpost PV uses `CAD_CAL = 0.557` so London matches the UNIBO CAD yield of 258.1 kWh/yr.
- UniBoat training sessions are paced at 18 kt so they fit the 10 kWh class cap; limp-home below 5 % SOC.
- R717 two-stage uses an open intercooler (`intercooler="open"` in `simcore/two_stage.py`) to keep HP discharge < 150 °C.
- HTHP condenser is two-zone (desuperheat + condense); sink UA scales with (Q/Q_design)^0.6.

## Working notes

- Run Blender: `"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup -P <create script>`
  from the project folder; check `<stem>_preview.png` after every change.
- Texture/HDRI/decal assets: `python assets/fetch_assets.py` (cached; CC0).
- Performance maps cache in `simcore/cache/perfmap_*.npy`; the cache key includes the solver, `hx.py` and `thermo.py`
  source, so physics edits rebuild maps automatically.
- Projects share module names (`annual_sim`, `model`, `src`, `params`); `make_*.py` load them via
  `generate_frontends.load_project_module` — keep that when adding projects.
- Quick browser QA without a server: headless Edge with `--allow-file-access-from-files --use-angle=swiftshader
  --virtual-time-budget=45000 --screenshot=...` on the `file:///.../viewer.html` URL (`?scenario=`, `?t=`, `?tab=`
  select scenario, hour index and panel). Use a fresh `--user-data-dir` each time to avoid cached JS.
- Write patch scripts with `encoding="utf-8"` (Windows default cp1252 corrupts files).
