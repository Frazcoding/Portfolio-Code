# Engineering Simulation & Whole-Life Carbon Portfolio

Consolidated monorepo for Fraser McLellan's thermodynamic, energy systems, whole-life carbon (WLC/LCA), and urban infrastructure digital-twin simulations.

## Portfolio Projects

| Project | Domain | Summary |
| :--- | :--- | :--- |
| [`BEng-CEA-Heatpump/`](BEng-CEA-Heatpump/) | Controlled-Environment Agriculture & LCA | Dynamic 20 × 20 m Venlo glasshouse + two-stage ammonia ($R717$) heat pump (air, borehole, river sources), plus UK commercial glasshouse vs imports LCA/LCC (`lca/`). |
| [`cea-glasshouse-plan/`](cea-glasshouse-plan/) | Commercial Glasshouse Feasibility & Funder Stack | 8 ha lit glasshouse business plan, energy options (PPA wind, biomethane CHP, sea-water/waste-heat HPs), and lender/funder stack modelling (`funders-feasibility`). |
| [`Whole-Carbon-Lifecycle-Assessment/`](Whole-Carbon-Lifecycle-Assessment/) | Whole-Life Carbon (RIBA / EN 15978) | 7,500 m² commercial office across 4 scenarios (Baseline Gas, Deep Retrofit, Standard New Build, Timber New Build): 8,760 h operational simulation + 60-year A1–C4 WLC. |
| [`Building-Heatpump-Retrofit/`](Building-Heatpump-Retrofit/) | Building Services & Grid-Capped Dispatch | 6,000 m² Edinburgh office retrofit under a 60 kWe grid cap using 4 × 40 kW R290 modules and 2 × 100 m³ stratified thermal stores. |
| [`Heat-Pump-Simulation/`](Heat-Pump-Simulation/) | Thermodynamics & Control | Two-stage R290 air-source heat pump with flash economiser, frost/defrost physics, stratified buffer/DHW tanks, and Octopus Agile tariff control. |
| [`High-Temp-Waste-Heat-Recovery/`](High-Temp-Waste-Heat-Recovery/) | Industrial Decarbonisation | High-temperature screw heat pumps ($R600$, $R1234ze(Z)$, $R1233zd(E)$) with economiser + IHX upgrading dairy effluent and spray-dryer exhaust to 95 °C water / 2.7 bar steam. |
| [`Plantpost-Urban-Infrastructure-Modelling/`](Plantpost-Urban-Infrastructure-Modelling/) | Autonomous Urban Infrastructure | Off-grid PV canopy, $\text{LiFePO}_4$ microgrid with adaptive dimming, rainwater drip irrigation, and urban particulate capture across London, Edinburgh, and Bologna. |
| [`PyPsa-Green-Hydrogen-Microgrid/`](PyPsa-Green-Hydrogen-Microgrid/) | Renewable Energy & Hydrogen Systems | Island wind–hydrogen microgrid on Lewis: 3 × 6.2 MW turbines, PEM electrolyser stack physics, 350 bar real-gas storage, and Ro-Pax ferry bunkering. |
| [`UniBoat-Powertrain-Cooling/`](UniBoat-Powertrain-Cooling/) | Electric Marine Thermal Management | Monaco Energy Class hydrofoiling catamaran: foil hydrodynamics, battery/inverter loss modelling, and pumped two-phase $R1233zd(E)$ cooling loop. |
| [`Ember-Hub-Simulator/`](Ember-Hub-Simulator/) | EV Fleet & Charging Hub Operations | Interactive Sim Workbench simulator for the Ember Bristol–London electric coach charging hub (operations, cost parity, swept-path layout, and GIS site screening). |
| [`HP-Hosting-Capacity-GNN/`](HP-Hosting-Capacity-GNN/) | Power Networks & Graph ML | Graph Neural Network (Physics-Guided GNN + `pandapower`) for LV distribution network heat-pump hosting capacity. |

## Shared Digital-Twin Viewer Infrastructure

- [`index.html`](index.html) — Portfolio master hub displaying live simulation KPIs and linking to all 8 interactive 3D Three.js digital-twin viewers.
- [`viewer_core/`](viewer_core/) — Shared WebGL/Three.js scene renderer, PBR material pipeline, animated fluid-flow particles, and timeline scrubber (`viewer.js`, `viewer.css`).
- [`assets/`](assets/) — Shared CC0 PBR textures, decals, and HDRIs (`python assets/fetch_assets.py`).
- [`build_all.py`](build_all.py) — Regenerates all viewers and the master hub (`python build_all.py [--force] [--models]`).
- [`serve_viewers.py`](serve_viewers.py) / [`run_suite.cmd`](run_suite.cmd) — Local HTTP server for the 3D portfolio hub.
- [`_legacy/`](_legacy/) — Frozen `simcore v0.1.0` functional solver package used by the 8 annual simulation scripts.
