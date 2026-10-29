# Simulation viewers: data, models and rebuild

Run `run_suite.cmd` (or `python serve_viewers.py`) to open the hub. Viewers load their results and 3D models from local
files, so they must be served; opening `viewer.html` directly from disk will not load data.

Rebuild:

```
python assets/fetch_assets.py      # once: CC0 textures, HDRI sky, decals (cached in assets/)
python build_all.py                # regenerate viewers + hub from existing results
python build_all.py --force        # re-run all eight annual simulations (minutes)
python build_all.py --models       # also rebuild every Blender model (Blender 5.x)
```

## What each viewer shows

Every project runs a full year (8,760 hours) on real 2023 data: ERA5 hourly weather (Open-Meteo archive, cached in
`simcore/cache`), GB grid carbon intensity (NESO) and Octopus Agile prices (region C). Control and dynamics run at
sub-hourly steps (10 min for buildings and heat pumps, 15 min industrial, 30 s greenhouse climate, 1 s UniBoat sessions);
outputs are hourly means or sums. UniBoat also has a 1-second race scenario, and the whole-life carbon project a
60-year lifecycle scenario.

| Panel | Content |
| --- | --- |
| 3D scene | Blender model with scanned PBR materials, HDRI sky lighting, ambient occlusion and day/night lighting driven by simulated irradiance. Parts are bound to channels (colour by temperature, fan/rotor spin, vent rotation, tank levels, screen opacity, luminaire glow and light pools, visibility of scenario-specific equipment). Particles flow along pipe centrelines at a speed set by mass flow and coloured by state temperature. Click equipment for its specification and live values. |
| State points | Every refrigerant / water / air / hydrogen node: T, P, h, s, quality, mass flow (and specific exergy in the channel list). Numbered markers sit on the model. |
| Diagrams | Live log P–h and T–s cycle on the fluid's saturation dome (24-hour trail), store and riser profiles, exergy destruction and power-balance bars. |
| Variables | Every channel (70–210 per scenario), searchable, with min/mean/max, annual integral and monthly statistics; tick a channel to plot it. |
| Annual KPIs | Seasonal performance, energy, cost, carbon, comfort, operation and exergy summaries. |
| Timeline | Year / month / week / day zoom with min-max envelopes, overview strip, scroll-to-zoom, keyboard stepping (←/→, Shift for 24 samples). |

Results are written per scenario to `<project>/viewer_data/<scenario>.json` (manifest) + `.bin` (Float32, channel-major)
and `<project>/results/<scenario>_hourly.csv.gz` + `_kpis.json` for engineering use.

## Code layout

| Path | Purpose |
| --- | --- |
| `simcore/` | Shared engine: weather and grid loaders, CoolProp property wrapper, compressor maps, single-stage and two-stage (flash/open-intercooler, air or liquid source) cycle solvers, gridded performance maps, ε-NTU and psychrometric helpers, stratified storage, ISO 13790 5R1C zone, solar/PV, results writer |
| `<project>/annual_sim.py` (`sim/annual_sim.py` for BEng-CEA) | The project's annual model and export |
| `make_*.py` | Runs a project's scenarios, sets viewer bindings, writes `viewer.html` |
| `blendlib/` | Procedural Blender library: PBR materials on scanned textures, decals, routed pipework, compressors (scroll, screw, reciprocating), heat exchangers, vessels, pumps, valves, fans, packaged units, containers, wind turbines, ship hulls |
| `<project>/create_*_asset.py` | Builds the project's `.blend`, `.glb`, `_meta.json` (anchors + flow paths) and preview render |
| `<project>/export_*_asset.py` | Re-exports the `.glb` after hand-editing the `.blend` (keeps `_meta.json`) |
| `viewer_core/` | Shared viewer (Three.js r160 modules) |
| `assets/` | CC0 textures (Poly Haven, ambientCG), HDRI sky, generated signs/labels/foliage |
| `_archive/pre_upgrade_2026-10-01.zip` | Snapshot of the previous scripts, models and viewers |

## Limits

These are engineering simulations built on documented assumptions (listed in each `annual_sim.py` docstring and in
`MODEL_AUDIT.md`), not validated design calculations. Equipment geometry is sized to the simulated duty from typical
manufacturer envelopes; it is not a procurement selection.
