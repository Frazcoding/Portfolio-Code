# UK-grown vs imported avocado — BOM, LCA and LCC study: scope

Status: **draft for review** (2026-10-01). Nothing is modelled yet. This fixes what will be built and how it will be judged.

## 1. Question

Can a heated, lit, CO₂-enriched UK greenhouse supply avocados with lower carbon and competitive cost per kg compared
with imported fruit? If not, which conditions would make it competitive: grid decarbonisation, on-site renewables,
rooftop integration, scale, setpoints or yield?

**Design targets (user, 2026-10-02).** The two pass/fail criteria for every design option:
1. **Carbon:** kg CO₂e per kg delivered to the RDC **below imports**, i.e. below the 2025 volume-weighted import
   average of **1.15 kg CO₂e/kg** (range 0.79–1.47), and ideally below the lowest-carbon origin (Israel, 0.86).
2. **Cost:** levelised £/kg **below the landed import price**: CIF at the UK border of **£2.07/kg** (2023–25, all
   origins), with Colombia (£1.82) and Peru (£1.86) the cheapest. CIF excludes UK handling, ripening and margin, so
   it is a strict target.

Numbers come from `imports.py` (§3.9).

## 2. Goal and scope (ISO 14040/14044)

| Item | Choice |
| --- | --- |
| Functional unit | **1 kg of ripe, saleable avocado delivered to a UK regional distribution centre (RDC)** |
| Secondary units | per m² growing area per year; per MWh of heat (heating-system comparison only) |
| Study period | 30 years; components replaced at end of service life (B4); residual value at year 30 |
| Boundary | Cradle to RDC, plus end of life of the greenhouse and its plant. UK and import chains share the same boundary: orchard/greenhouse → packing → transport → ripening → RDC. Retail and consumer stages are excluded because they are identical for both. |
| Life-cycle stages | EN 15978 modules A1–A5, B2–B4, B6 (energy), B7 (water), C1–C4; module D (recycling credit) reported separately, never netted |
| Impact categories | GWP100 (IPCC AR6), primary; water scarcity (AWARE, m³ world-eq), secondary; land occupation (m²·yr), indicative |
| Costing | ISO 15686-5 LCC; real discount rate 3.5 % (HM Treasury Green Book); 2026 £; **indicative rates only**, each with a cited source |
| Guidance | PAS 2050-1 (horticultural products), RICS WLCA 2nd ed. (2023), CIBSE TM65 (building services embodied carbon) |
| Crop | Avocado (*Persea americana*), high-density dwarf trees in in-ground beds (see §4) |

## 3. Scenarios

All scenarios run from **one site configuration** (`lca/config.py`), so size, location and form are inputs rather
than code edits.

### 3.1 Site configuration (adjustable)

| Parameter | Range | Notes |
| --- | --- | --- |
| Growing area | 100 m² – 4 ha (continuous) | Thesis = 400 m²; commercial references 1 ha and 4 ha |
| Form | `ground` Venlo / `rooftop` | Rooftop changes floor boundary (heated building below), wind exposure, structure and access costs |
| Location | any lat/lon (Open-Meteo archive via `simcore.weather`) | Chelmsford default; London, Manchester, Glasgow city cases |
| Gutter height, bay width, aspect ratio | 4–7 m, 4–8 m, 1–4 | Dwarf trees need ≥ 5 m gutter |
| Cover | single glass / twin-wall PC / diffuse glass | U-value, light transmission and BOM change together |
| Screens | none / energy / energy + blackout | |
| Supplementary lighting | 0 – 250 µmol m⁻² s⁻¹ LED | Controlled to a daily light integral (DLI) target |
| Climate strategy | thesis (18 °C continuous) / crop-led (sourced day/night/flowering setpoints) | §4.3 |

**Rooftop specifics:** floor coupled to the building's heated ceiling, the roof's imposed-load limit as a constraint
(BS EN 1991-1-1), wind at roof height, crane and access premium, and an optional integrated-RTG case. In that case
building exhaust air supplies heat and CO₂ (Nadal et al. 2017; Sanyé-Mengual et al. 2015).

### 3.2 Heating and CO₂ supply

| ID | Heat | CO₂ enrichment |
| --- | --- | --- |
| HP-A / HP-G / HP-W | R717 two-stage heat pump: air / ground / river (existing model) | none, or purchased liquid CO₂ |
| GB | Gas condensing boiler | none, flue-gas CO₂, or purchased |
| CHP | Gas CHP + condensing boiler top-up + heat buffer | flue-gas CO₂ (cleaned); electricity used on site, surplus exported with credit |
| SM | **Rooftop on a supermarket: heat recovered from its refrigeration plant** (R744 transcritical booster gas cooler, or condenser heat via a heat-pump lift), heat-pump/boiler top-up | none, or purchased |

**Supermarket case (SM):** refrigeration heat rejection runs almost continuously and is largest in summer, while greenhouse
demand peaks in winter. The model will take an hourly refrigeration load profile (store size, cabinet/cold-room
duty, ambient-dependent COP), work out how much heat is recoverable at a usable temperature, and allocate it: greenhouse first, then store
space heating (as stores already do), with the rest rejected. Only the extra plant (heat exchangers, pipework, controls,
any lift heat pump) and any refrigeration COP penalty from raised discharge pressure are charged to the greenhouse.
The heated store below also warms the greenhouse floor through the roof deck (`Q_below` in the model).

### 3.3 Electricity supply

| ID | Supply |
| --- | --- |
| GRID | UK grid, hourly carbon intensity, decarbonising to the NESO Future Energy Scenarios pathway |
| HYBRID | Grid + on-site wind (+ PV); self-consumption and export |
| OFFGRID | On-site wind + PV + battery + large thermal store; no grid. Sized by least-cost LP (PyPSA + HiGHS) to a chosen reliability, e.g. ≤ 1 % unmet heat. Reports curtailment and oversizing. |

Wind uses the hydrogen project's sheared ERA5 wind and power-curve code. PV uses the Plantpost PV model.

### 3.4 Imported fruit

Origins: **Peru, Israel, Chile, Colombia, South Africa, Morocco, Spain, Kenya, Mexico** (94 % of 2025 UK
imports; Morocco added, Mexico now < 1 %). Each runs as
orchard → packhouse → reefer road → port → **reefer sea freight** (real sea-route distance via `searoute`) → UK port →
road → UK ripening room → RDC. **Air-freight** variant for the long-haul origins.

### 3.5 Headline set vs sweeps

Running every combination is not useful. The study reports:
- **Headline:** 1 ha ground Venlo at Chelmsford, crop-led climate, lights on, CO₂ on, for HP-A, HP-G, HP-W, GB and CHP
  × GRID, plus HP-G × HYBRID and × OFFGRID, against all import origins (sea), plus the air-freight variant.
- **Sweeps:** area (100 m² → 4 ha), form (ground vs rooftop), city, lighting intensity, setpoint strategy, grid year
  (2026 → 2050), CO₂ on/off.
- **Break-even plots:** grid carbon intensity and yield at which each UK option equals sea-freighted imports.

### 3.6 Step 2 status (2026-10-01)

Done: `config.py`, `climate.py`, `greenhouse.py`. `tests/test_reproduce.py` reproduces the original sim for all three
sources (31/31 annual sums, bit-identical). Changes beyond the original apply to new cases only:
- plant scales per m², and the heat pump is sized to design heat loss (as multiples of the thesis R717 unit);
- the heating setpoint ramps at 2 K/h by default, to avoid sudden morning setpoint jumps;
- floor-to-soil coupling follows ISO 13370 (the thesis preset keeps 1.2 W/m²K; ISO gives 0.47 at 400 m² and 0.14 at 1 ha);
- auxiliary vent power: the original expression `(900.0 * vent > 0.02)` adds 1 W, not 900 W, while venting. New
  cases use 900 W per 400 m²; the thesis preset keeps the original for the reproduction test.

Results are in `results/step2_summary.json` (run `run_step2.py`). To check in step 3: heat demand per m² against
commercial glasshouse benchmarks, heating for humidity control (not modelled yet), and summer overheating (> 30 °C for
about 320 h at commercial scale), which needs shading/fogging or accounting for crop stress.

### 3.7 Step 3 status (2026-10-01) — awaiting review of yield and setpoints

Done: `crop.py` (Farquhar leaf, 10-layer canopy, hourly greenhouse CO₂ balance with dosing, floral induction,
calibrated carbon partition, age ramp), `calibrate_crop.py` → `data/crop_calibration.json`, LED lighting in
`greenhouse.py`, `run_step3.py` → `results/step3_summary.json`.

Leaf model checks against measurements not used in the fit: light saturation 1053 vs 1110 µmol/m²/s, CO₂
saturation 1274 vs 1350–1470 ppm, temperature optimum 24.5 vs 20–31 °C, compensation point 10 (fitted via Rd).
Calibration: 20 t/ha/yr at the Mbombela reference climate gives a fruit partition of 0.14 after 25 % wood/root maintenance.

1 ha, Chelmsford, ground-source heat pump, in-ground beds:

| Case | t/ha/yr | Heat kWh/m² | Elec kWh/m² | Grid kg CO₂/kg (2023) | Dosed CO₂ kg/kg |
| --- | --- | --- | --- | --- | --- |
| thesis 18 °C | 6.2 | 144 | 57 | 14.6 | 0 |
| crop-led | 4.6 | 83 | 37 | 13.8 | 0 |
| crop-led + CO₂ | 7.5 | 83 | 37 | 8.4 | 33.5 |
| crop-led + CO₂ + LED 150 | 12.8 | 34 | 147 | 18.7 | 27.0 |
| same, containers | 2.8 | 34 | 147 | 84 | 103 |
| rooftop 2000 m² London + CO₂ + LED | 12.7 | 40 | 153 | 19.7 | 25.8 |

Changes to the plan: **in-ground beds replace containers** as the default, because root restriction cut orchard-level
photosynthesis from 23 to ~7 µmol/m²/s in potted trees (Schaffer & Whiley 2003); the container factor of 0.5 is an assumption.
Open points for review: crop-led summer venting at 28 °C costs yield (> 30 °C for ~330 h); induction never limits
flowering at these setpoints (the annual sum is a loose test); dosed CO₂ mostly escapes through the vents, so how it is
accounted for (fossil vs by-product, step 7) decides whether enrichment helps or hurts on carbon; canopy assimilation
is on the high side (all leaves at sunlit capacity), which the calibration absorbs.

### 3.8 Step 3 review decisions and follow-up (2026-10-01)

User decisions: **containers** stay the planting system (root factor 0.5 remains an assumption, sensitivity later);
dosed CO₂ reported **both** as an emission and with by-product allocation; LED daily light target 18 mol/m²/d kept as an
estimate; summer venting studied together with heat recovery.

Added: **semi-closed cooling** (`config.Cooling`): fan-coils cool and dehumidify with water from the borehole field (or
river), putting the heat into the ground instead of venting it. 1 ha, containers, CO₂ + LED 150 (`run_step3b.py`):

| Summer vent setpoint | Yield t/ha | + semi-closed | Heat recovered kWh/m² | Hours > 30 °C (off → on) |
| --- | --- | --- | --- | --- |
| 24 °C | 3.70 | 4.63 | 127 | 136 → 56 |
| 26 °C | 3.31 | 4.55 | 158 | 139 → 60 |
| 28 °C | 2.85 | 4.36 | 170 | 333 → 150 |

Venting at 24 °C costs no extra energy and raises yield by 30 %, so it is now the crop-led default. Semi-closed cooling
adds a further 25 % and recovers 127–170 kWh/m² of summer heat, which is 3–5 times the winter heating demand with LEDs
(~35 kWh/m²). The current lumped borehole model leaks that heat to the far field within weeks (ground only reaches
12.7 °C, heat-pump SCOP barely moves), so recovering it for winter needs a **seasonal store** (borehole or aquifer
thermal energy storage, sized for storage rather than extraction). That store is added in step 4 alongside the
supermarket waste-heat case, which has the same summer-surplus/winter-demand mismatch.

### 3.9 Import benchmark (step 6 brought forward, 2026-10-02)

Done: `fetch_imports_data.py` → `data/imports_trade.csv` (UN Comtrade HS 080440, UK imports by origin 2023–25, CIF;
ECB USD→GBP annual means), `data/imports_farm_ghg.csv`, `data/imports_routes.csv`, `data/freight_factors.csv` (DESNZ
2025), `data/chain_stages.csv` (Blaauw et al. 2024), and `imports.py` → `results/imports_summary.json`.

| Origin | 2025 share | Farm | Total kg CO₂e/kg (range) | CIF £/kg 2025 | Farm data |
| --- | --- | --- | --- | --- | --- |
| Peru | 40 % | 0.96 | 1.36 (0.88–1.49) | 1.86 | measured |
| Israel | 14 % | 0.58 | 0.86 (0.56–1.39) | 2.29 | proxy |
| Chile | 13 % | 0.58 | 0.99 (0.69–1.51) | 2.25 | proxy |
| Colombia | 9 % | 0.59 | 0.98 (0.67–1.49) | 1.82 | weak (creole variety) |
| South Africa | 8 % | 0.58 | 1.15 (1.11–1.24) | 2.14 | measured |
| Morocco (road) | 5 % | 0.58 | 1.06 (0.76–1.58) | 2.37 | proxy |
| Spain (road) | 3 % | 0.58 | 1.01 (0.71–1.54) | 2.88 | proxy |
| **Weighted average** | 94 % covered | | **1.15 (0.79–1.47)** | **2.07** (all origins) | |
| Air freight (any long-haul) | ~0 % | | 4.9 (Israel) – 14 (Chile) | | |

Notes:
- **The farm stage dominates** (50–70 %). Only Peru, South Africa and Mexico have measured export-orchard LCAs. Chile,
  Israel, Kenya, Morocco and Spain use the literature median (0.58) with the literature range: the main data gap.
- Peru carries 40 % of the weight, so the choice between Esteve-Llorens et al. 2022 (0.96, large coastal export farms, used) and
  Elorrieta-Mendoza et al. 2025 (0.60, small producers) moves the average by about 0.15.
- Gross figures throughout. Blaauw nets off 0.52 kg/kg orchard sequestration (compost, savannah) to report 0.38; that credit is
  reported separately and not netted, consistent with how UK fruit is treated. Land-use change is not quantified for any origin.
- **Check against Blaauw (South Africa, gross to Rotterdam ≈ 0.90):** this model gives 1.15. The difference is transport. DESNZ
  average-laden reefer HGV with WTT gives 0.21 for the 1,810 km road leg (Blaauw 0.07), and the 8000+ TEU container ship gives 0.18 for
  the sea leg (Blaauw 0.095; Pedreschi et al. 2022 0.17–0.20). Using DESNZ factors keeps the transport method consistent across all origins.
- No reefer-container uplift on the ship factor and no port reefer plug-in time: both would raise the import figures slightly.

### 3.10 Break-even screen (2026-10-02) — awaiting decision on cost target

`breakeven.py` → `results/breakeven_summary.json`, `figures/breakeven.png`. Per m² per year:
carbon/kg = (E·CI + dosed CO₂·f + S)/Y + 0.16 and cost/kg = (capex annuity + O&M + labour + E·price + CO₂)/Y + £0.25.
Structure carbon S, capex, labour and packing cost are **placeholder estimates** until the BOM (step 5); electricity
price (DESNZ QEP, 17.3 p/kWh incl. CCL) and grid factor (DESNZ 2025, 0.245 kg/kWh incl. T&D and WTT) are sourced.

**Carbon (target 1.15):**
- Structure embodied carbon alone sets a yield floor: S = 1, 2, 3 kg CO₂e/m²/yr needs ≥ 10, 20, 31 t/ha **before any energy**.
  A new glasshouse is around 2–3, so a new build needs open-field-level yield and nearly zero energy carbon.
- With S = 0 (structure already exists) at 15 t/ha, the electricity allowance is 4 kWh/kg on the 2025 grid, 20 on a 50 g/kWh
  grid and 89 on on-site wind. Simulated cases use 49 (no LED), 115 (beds + LED) and 333–517 kWh/kg (containers + LED).
- Dosed CO₂ counted as an emission adds 20–80 kg/kg; only by-product accounting is compatible with the target.
- **Passes only for:** existing structure + waste heat + on-site wind + no LED → 0.22–0.31 kg/kg at 7.5–20 t/ha.

**Cost (target £2.07):**
- Labour alone (0.15 h/m², £15/h) needs ≥ 12 t/ha to stay under the target.
- New glasshouse (£200/m²) + heat pump with zero energy cost needs ≥ 167 t/ha; with a free structure but a paid heat pump, ≥ 85 t/ha.
- Best conceivable (existing structure, free waste heat, wind, no LED): **£12.2 / £6.2 / £4.7 per kg** at 7.5 / 15 / 20 t/ha,
  i.e. 2–6 × the import price. Best simulated case: £53/kg (beds + LED); current default (containers): £148/kg.
- **No combination within scope meets the cost target at import prices.** The cost goal needs a reframing (price premium,
  co-products, or a different crop); decision pending with the user.

### 3.11 Switch to in-ground beds (user decision 2026-10-02)

`config.Crop.planting` now defaults to `"bed"` (reverses the §3.8 container decision). Container results are kept in
`results/step3b_summary_containers.json`. Steps 3 and 3b re-run (step 3 now also uses 24 °C venting), and `run_step3c.py`
adds LED 0/75/150 × semi-closed. 1 ha Chelmsford, CO₂ on, venting at 24 °C:

| Case | t/ha | Elec kWh/kg | New glasshouse, grid kg/kg | Same, wind | Cost £/kg | Integrated rooftop kg/kg | Integrated £/kg |
| --- | --- | --- | --- | --- | --- | --- | --- |
| containers + LED150 (old default) | 3.7 | 401 | 107 | 12.7 | 183 | 4.32 | 103 |
| beds, no LED | 8.8 | 42 | 13.9 | 4.04 | 48 | 0.35 | 11.6 |
| beds, no LED + semi-closed | 10.5 | 41 | 13.0 | 3.47 | 41 | **0.37** | **10.8** |
| beds, LED75 + semi-closed | 13.3 | 73 | 20.3 | 3.22 | 43 | 0.85 | 19.6 |
| beds, LED150 + semi-closed | 15.9 | 97 | 25.9 | 3.12 | 44 | 1.17 | 25.4 |

"Integrated rooftop" = existing structure, waste heat (no heat-pump capex or compressor electricity), on-site wind, dosed
CO₂ as by-product; LED capex and fan-coil power kept. Semi-closed fan-coil capex is not yet costed.
- Beds raise yield 3.8× at the same energy (3.7 → 14.2 t/ha with LED150) and bring the semi-closed case to 15.9 t/ha, at
  the top of the open-field range.
- LEDs now add yield (8.8 → 14.2 t/ha) but still cost more than they return: in the integrated case LED150 takes carbon from
  0.37 to 1.17 (just above the import target) and cost from £10.8 to £25.4/kg.
- **Best design: beds, no LED, semi-closed, integrated rooftop: 0.37 kg CO₂e/kg (3× below imports), £10.8/kg (5× above).**
  The carbon goal is met; the cost goal is still not met.

### 3.12 Multi-crop comparison (2026-10-02)

The same system is screened for nine more crops, viewed in `../crop_compare.html` (linked from the hub). Files:
`crops.py` (crop library, setpoints, sources), `run_crops.py` → `results/crops_sim.json` (1 ha, ground-source heat pump,
unlit, crop setpoints), `data/country_routes.csv`, `fetch_imports_data.py` (now all crops), `compare.py` →
`results/compare.json` + page (built from `crop_compare_template.html`). The page recomputes carbon and cost live
from per-m² inputs for the chosen structure, heat, electricity, CO₂ accounting, yield case and assumptions.

Sources and their quality:
- UK yield: CBS NL glasshouse averages 2022–24 for tomato, cucumber, pepper, aubergine and strawberry. Lettuce,
  raspberry, blueberry and grape are estimates.
- Labour, consumables, CO₂ dose and packing cost are estimates.
- Imports, farm stage: Poore & Nemecek (2018) category means for unheated or field origins. Heated NL/BE uses
  WUR Energiemonitor 2024 (37 kg CO₂/m²) / CBS yield + non-energy inputs.
- Imports, prices: Comtrade CIF 2023–25.
- Imports, transport: DESNZ 2025 factors on estimated routes.

| Crop | Imports kg/kg | Imports £/kg | New + HP, grid: kg / £ | New + HP, wind | Existing + waste heat + wind |
| --- | --- | --- | --- | --- | --- |
| Tomato | 1.24 | 1.60 | 0.54 / 1.30 | 0.30 / 1.30 | 0.23 / 0.60 |
| Cucumber | 0.75 | 1.40 | 0.49 / 1.02 | 0.21 / 1.02 | 0.16 / 0.42 |
| Sweet pepper | 1.15 | 2.04 | 0.89 / 2.25 | 0.35 / 2.25 | 0.22 / 0.89 |
| Aubergine | 1.05 | 1.55 | 0.52 / 1.32 | 0.24 / 1.32 | 0.17 / 0.59 |
| Lettuce | 0.56 | 1.45 | 0.63 / 2.09 | 0.33 / 2.09 | 0.17 / 0.60 |
| Strawberry | 1.19 | 4.61 | 1.21 / 4.64 | 0.74 / 4.64 | 0.46 / 2.01 |
| Raspberry | 1.82 | 7.54 | 3.70 / 16.1 | 2.13 / 16.1 | 1.12 / 6.59 |
| Blueberry | 1.24 | 5.63 | 4.06 / 16.6 | 2.30 / 16.6 | 1.10 / 5.33 |
| Table grape | 1.20 | 2.16 | 3.22 / 15.1 | 1.54 / 15.1 | 0.33 / 3.74 |
| Avocado | 1.15 | 2.07 | 13.0 / 41.3 | 3.47 / 41.3 | 0.37 / 10.8 |

- Tomato, cucumber and aubergine beat imports on both goals even as a new glasshouse with a grid-powered heat pump.
  Pepper passes on carbon, and on cost only with an existing structure. Strawberry sits at break-even.
- Lettuce passes once on wind or waste heat.
- Raspberry, blueberry and grape pass only as the integrated rooftop. Avocado never passes on cost.
- **Caveat: simulated heat is low** (tomato 117 kWh/m² against ~275 kWh/m² total energy for the Dutch sector average)
  because heating for humidity control is not modelled. With heat × 2.4 on grid power, tomato and aubergine
  still pass both goals. Cucumber tips just over on carbon (0.79 against 0.75), and pepper fails both.
- Annual per-kg results hide seasonality: unlit UK crops do not supply in winter, when the import figures apply most.

### 3.13 System optimisation and electricity supply (step 4, 2026-10-02)

New options, all off for the thesis preset (`tests/test_reproduce.py` still bit-identical):
- `config.Hydronics`: buffer floor, flow margin, weather-compensated supply curve, variable-speed pump and
  price-led buffer charging.
- `config.HeatSupply`: `cycle` (two-stage / single-stage), `hx_scale` (evaporator and condenser UA) and the
  ground-field parameters.
- `config.cover()`: glass or PC.
- `config.optimised()`: the full bundle.
- `simcore/single_stage_liquid.py`: new cycle solver.
- `run_step4a.py`: step-by-step study.
- `run_crops.py`: 6 variants × 10 crops, with hourly profiles.
- `energy_systems.py`: PyPSA least-cost wind + battery + grid.

**Tomato, 1 ha, PC, ground source — step by step:**

| Step | Elec kWh/m² | SCOP | Note |
| --- | --- | --- | --- |
| Thesis control | 50.4 | 3.72 | buffer ≥ 35 °C, 3 W/m² fixed-speed pump |
| + low-temperature supply | 49.3 | 3.84 | limited by emitter: pipe rail needs ~45–50 °C at peak |
| + variable-speed pump (1 W/m²) | 43.0 | 3.84 | pump 15 → ~1 kWh/m² |
| + seasonal borehole store, semi-closed | 45.3 | 4.01 | source 6.6 → 8.6 °C; cooling adds 3.6 kWh; h > 30 °C 126 → 44 |
| + grow pipes (4.5 m/m²) | 42.9 | 4.44 | supply 25 °C |
| + 2× evaporator/condenser | 40.8 | 4.83 | full optimisation |
| price-led buffer charging | 43.3 | 4.40 | rejected: cheaper kWh but more of them |
| single-stage NH3 instead | 41.1 | 4.76 | no gain; single-stage NH3 hits discharge limit above ~35 °C flow, R290 3–10 % worse |
| glass cover (optimised) | 64.9 | 4.61 | heat 117 → 223 kWh/m² |

**Cost-effectiveness:**
- Only low-temperature control and the variable-speed pump pay back at the estimated capex.
- Grow pipes (£35/m²), 2× HX (+10 % HP) and the extra borehole field (£400/kW) cut carbon, but cost more per kg
  than they save.
- The page therefore offers three systems: thesis control, **controls + pump** (default) and full optimisation.

**Cover choice:**
- Glass gives ~10 % more yield (light 0.80 vs 0.70; 0.8 % yield per % light, Marcelis et al. 2006).
- But it doubles heat demand and heat-pump size, so with heat pumps PC is cheaper and lower carbon for every
  heated crop.
- Glass runs also show more unmet hours (heat pump sized at −4 °C design; sizing to be reviewed).

**Electricity supply** (Chelmsford 2023 wind at 50 m, capacity factor 23.8 %):
- **On-site medium turbine (£3,200/kW, Renewables First):** least cost chooses almost no wind (≤ 2 % of demand).
  At ~£0.15/kWh before storage, turbine power is barely cheaper than grid at £0.18–0.20, and the surplus sells
  for only 5 p.
- **Forcing ≥ 80 % wind:** £0.34–0.62/kWh, 0.07–0.08 kg/kWh.
- **Utility-scale turbine cost (£1,400/kW, Arup 2024 for DESNZ):** least cost meets ~50 % of demand from wind at
  £0.12–0.17/kWh and 0.12–0.17 kg/kWh.
- **Wind carbon is always lower.** Wind is cheaper only at utility scale; the earlier "on-site wind" option was a
  carbon factor only and has been removed.

| Crop (controls + pump, PC) | Imports kg / £ | Grid kg / £ | Utility-wind kg / £ | Existing roof + waste heat + utility wind |
| --- | --- | --- | --- | --- |
| Tomato | 1.24 / 1.60 | 0.57 / 1.43 | 0.46 / 1.40 | 0.27 / 0.63 |
| Cucumber | 0.75 / 1.40 | 0.50 / 1.11 | 0.36 / 1.06 | 0.18 / 0.42 |
| Sweet pepper | 1.15 / 2.04 | 0.92 / 2.49 | 0.67 / 2.40 | 0.30 / 0.93 |
| Aubergine | 1.05 / 1.55 | 0.54 / 1.46 | 0.41 / 1.41 | 0.21 / 0.62 |
| Lettuce | 0.56 / 1.45 | 0.69 / 2.32 | 0.54 / 2.27 | 0.30 / 0.64 |
| Strawberry | 1.19 / 4.61 | 1.31 / 5.13 | 1.07 / 5.04 | 0.70 / 2.15 |
| Raspberry | 1.82 / 7.54 | 4.09 / 17.9 | 3.24 / 17.6 | 2.00 / 7.06 |
| Blueberry | 1.24 / 5.63 | 4.46 / 18.5 | 3.39 / 18.1 | 2.02 / 5.56 |
| Table grape | 1.20 / 2.16 | 3.53 / 16.9 | 2.62 / 16.5 | 1.18 / 3.92 |
| Avocado | 1.15 / 2.07 | 13.1 / 42.1 | 9.10 / 40.8 | 2.88 / 10.6 |

(PC yields are glass literature yields × 0.90.)

### 3.14 Borehole costing and air source (2026-10-02)

The heat-plant capex was a single guessed £1,200/kW. It is now explicit, using the project's own capex model
(`../CALCULATIONS_WHITE_PAPER.md` §6.1):
- R717 skid £850/kW;
- air-source coil and supports +£140/kW;
- drilling £75/m (UK quotes £40–150/m);
- installation +18 %.

The field is the thesis field (16 × 120 m per R717 unit, UA 7 kW/K), scaled with heat-pump size and doubled for the
seasonal store. For 1 ha of tomato that is 282 boreholes, 34 km of drilling, ~£300/m². Embodied carbon is
15 kg CO₂e/m of borehole over 50 years.

Results:
- **Boreholes add £0.24–0.30/kg** to tomato, cucumber and aubergine, and £1–6/kg to the low-yield crops, whose heat
  pumps are oversized for frost protection.
- The new **air-source variant** (`ctrlair_*`) uses ~13 % more electricity (SCOP 3.2–3.3 against 3.8) but no field,
  so it is cheaper for every crop.
- Controls + pump, PC, grid, new glasshouse:

| Crop | Ground source | Air source | Imports |
| --- | --- | --- | --- |
| Tomato | £1.68 | £1.45 | £1.60 |
| Cucumber | £1.30 | £1.13 | £1.40 |
| Aubergine | £1.71 | £1.48 | £1.55 |

Air source is now the page default. The thesis field is ~1.8× a VDI 4640 sizing (50 W/m), so a leaner field would
narrow the gap, at a lower source temperature.

### 3.15 Perthshire, off-grid dedicated wind (2026-10-02)

Site: Carse of Gowrie (56.42 N, 3.20 W), 2023 ERA5. It was chosen from five Perthshire candidates as the mildest
(9.0 °C mean), sunniest (3,495 MJ/m², 79 % of Westland) and equal-windiest (5.5 m/s at 45 m). ERA5 smooths terrain,
so a +15 % "ridge" wind case is shown.

Files:
- `run_perthshire.py`: sims, controls + pump, PC, air and ground source.
- `offgrid.py`: PyPSA least cost. Wind at £2,500/kW (SAC/SRUC guide: 250 kW £550–700k), battery store and inverter
  sized separately, hot-water heat store, heat pump as a link with hourly COP. No grid, unserved energy penalised.
- `perthshire_results.py` → `results/perthshire/results.json`, `../figures/perthshire_offgrid.png`.

Yields are glass yields × 0.90 (PC) × 0.83 (light, 0.79^0.8). Imports are delivered to central Scotland: +460 km
from the port, +500 km by road.

**Energy:**
- Heat demand is ~45 % above Chelmsford (tomato 169 against 116 kWh/m²); hours above 30 °C fall from ~126 to ~10.
- Turbine capacity factor is only 15.9 % (22.8 % ridge).
- Off-grid supply needs ~600–840 kW of wind, 1–1.5 MWh of battery and a 160–320 MWh hot-water store per heated
  hectare.
- 23–40 % of wind output is curtailed and 0.2–0.5 % of demand goes unserved.
- Delivered electricity costs £0.38–0.51/kWh for heated crops and £0.79–1.00 for barely heated ones (steady fan
  load through lulls).

| Crop | UK yield kg/m² | Imports kg / £ | Off-grid kg / £ | Ridge £ | Grid-connected ref kg / £ | Break-even off-grid £/kWh |
| --- | --- | --- | --- | --- | --- | --- |
| Cucumber | 48.6 | 0.81 / 1.40 | **0.26** / 1.73 | 1.59 | 0.75 / 1.43 | 0.20 |
| Tomato | 35.9 | 1.30 / 1.60 | **0.37** / 2.16 | 2.01 | 0.81 / 1.80 | 0.11 |
| Aubergine | 36.6 | 1.11 / 1.55 | **0.31** / 2.24 | 2.06 | 0.81 / 1.86 | 0.07 |
| Sweet pepper | 19.8 | 1.22 / 2.04 | **0.48** / 3.95 | 3.61 | 1.43 / 3.21 | none |
| Lettuce | 15.0 | 0.62 / 1.45 | **0.50** / 3.96 | 3.73 | 0.98 / 2.87 | none |
| Strawberry | 8.3 | 1.25 / 4.61 | **1.09** / 7.86 | 7.49 | 1.66 / 6.11 | none |
| Raspberry, blueberry, grape | 1.9–2.3 | 1.3–1.9 / 2.2–7.5 | 2.6–3.7 / 27–29 | | | none |
| Avocado | 0.80 | 1.20 / 2.07 | 5.6 / 72 | | | none |

**Conclusion:**
- Off-grid wind makes six crops beat imports on carbon by 2–5× (cucumber, tomato, aubergine, pepper) or narrowly
  (lettuce, strawberry).
- No crop beats imports on cost. Cucumber is closest (+24 %; +14 % at a ridge site) and needs electricity at
  ≤ £0.20/kWh, half the off-grid cost.
- Even grid-connected, Perthshire tomato (£1.80) misses on cost: less light and more heat than Chelmsford.
- Low-yield crops fail both goals because the fixed structure, plant and wind costs fall on few kg.

Remaining levers not yet modelled:
- heat-pump size for barely-heated crops (berries, grapes): currently sized for 18 °C at −4 °C;
- vent and circulation fans (~9 kWh/m², now the largest auxiliary load);
- heat-pump sizing below design load (buffer peak shaving);
- sourced capex for the heat pump, field and grow pipes;
- humidity-control heating.

### 3.16 Design, costing and siting toolchain (2026-10-02/03)

Standards alignment (data/input_register.csv): ASABE EP406.4 cover U and infiltration (new glass 0.5-1.0 ACH; 0.75
used), heating design -3.1 C (99 % of 1995-2024 ERA5 at the site) at the crop night setpoint, ISO 6946 inner cover
surface, ISO 13370 floor and edge insulation, EU Ecodesign 1253/2014 and EN 16798-3 for heat recovery, HM Treasury
Green Book 3.5 %.

Model additions (all default off, thesis reproduction unchanged; `greenhouse_fast.py` is the Numba copy, checked
month by month by `tests/test_fast.py`):
- opaque insulated north wall, separate wall U, ISO 13370 edge insulation;
- heat-recovery dehumidification; Dutch-style humidity control (gap + minimum pipe); cover temperature from U;
- free-form light input (`i_floor`), glazed/opaque areas and volume from `design.py`;
- waste heat: direct medium-grade into the buffer with priority over the heat pump (`waste_kw`), or low-grade as the
  water-source heat pump's source (`t_source`); transcritical CO2 cycle (`simcore/co2_transcritical.py`, built and
  tested, not used: SCOP 2.2-2.4 vs R717 3.1-3.2; R717 kept, AGR Fenland precedent).

Design and cost (`design.py`, `sizing.py`, `costing.py`, `data/rates.csv`): free-form cross-section profile x spans
x orientation; per-facet Hay-Davies light with Fresnel angular transmission calibrated to product THem and frame
shading from the design's members; preliminary EN 1991 snow (incl. multi-span and curved-roof drift) and wind member
sizing (not the structural design); quantities x rates, cost anchored to SAC/SRUC GBP 2M/ha for a single-glass Venlo
(residual GBP 94/m2), embodied carbon bottom-up (IStructE 2020 / ICE v3 / European Aluminium 2024). Findings: double
glazing is the largest lever (~GBP 0.30/kg); ETFE fails on cost at architectural prices (GBP 850-1,100/m2) and its
light advantage disappears with consistent angular treatment; gutter ~5 m beats 7 m by ~GBP 0.08-0.11/kg in this
model (no value for climate stability); half of the double-glass capex rests on placeholder prices (RFQ needed).

Siting (`siting.py`, `site_opt.py`, `site_rank.py`, `refine.py`, `energy_grid.py`): 120 Scottish waste-heat sites
(Wikipedia distillery capacities + supplement, EEA UWWTD via EMODnet, SEPA SPRI 2023) with BRE (2020) sector
methods; GWA 3 wind; OSRM road distance to the 7 Central Belt RDCs with TAG v2.03 haulage costs and DESNZ 2025
reefer factors; imports carry the same port-to-RDC haul. Grid-backed wind by dispatch sweep; NESO 2026/27 TNUoS
residual increase by band; DEA Aug 2026 heat-pump capex; seasonal import benchmark from monthly Comtrade.
Results: results/site_opt/ (ranking_*.json, refined_*.json).

### 3.17 Gate B step 5: bias fixes, size, LP, EN 13031-1 (2026-10-03)

User decisions (2026-10-03): the R717 (ammonia) heat pump is always installed and costed at the full design heat
load, as standby for waste-heat outages; wind may export only what is left after the greenhouse's own loads, and is
sized for own use (a small battery is allowed where storing our own wind beats exporting at SEG and buying back);
GreenLight validation waits for the other computer.

Changes (Gate A results archived in results/site_opt/gateA_archive/):
- `site_opt.py`: heat pump at the design load everywhere (DEA ch. 40 is for ammonia units, p. 287-288; scope
  includes HP, air coolers, grid/DH connection, building, excludes advisers); waste heat follows
  `availability()`: planned shutdown (distillery 28 d from mid-July, Whisky Advocate 2022 3-4 weeks; paper mill
  10 d, Process Barron 5-10 d; food/AD 14 d placeholder; WWTP none) + one unplanned week in the coldest week
  (placeholder stress case; Cameronbridge strikes 28 Sep-15 Oct 2026 show such stoppages happen).
- `energy_grid.py`: wind -> load -> battery (own wind only) -> export; turbine and battery chosen on capex + imports
  with export revenue left out, export credited afterwards; wind life-cycle carbon on wind used on site only.
  Battery: DESNZ GBP 400/kWh, NREL ATB 2024 (85 % RTE, 15 yr, 2.5 % O&M), IVL C444 75 kg CO2e/kWh.
- `greenhouse_fast.py`: design-independent inputs cached per process (map, prices, weather, solar); 0.6 -> 0.18 s
  per design, results identical; tests/test_fast.py PASS.
- `sizing.py` takes partial factors and reference-period factors; `en13031.py` checks the designs.

Results (cucumber / tomato, GBP 10/MWh heat; imports at the Scottish RDCs GBP 1.57 / 1.77 per kg, 0.81 / 1.30 kg
CO2e/kg):

| Site | Cucumber GBP/kg, kg/kg | Tomato GBP/kg, kg/kg | Gate A cucumber | Design (cucumber) |
| --- | --- | --- | --- | --- |
| Girvan + Ailsa Bay | 1.00, 0.26 | 1.34, 0.37 | 0.80 | 3-ridge pitched, 15.3 m span, 12 deg, 4.5 m gutter, 4.7 ha, 0.2 MW wind |
| Caledonian Paper, Irvine | 1.01, 0.29 | 1.36, 0.38 | 0.84 | single ridge, 16.3 m, 10 deg, 4.5 m, 7.5 ha |
| Cameronbridge | 1.03, 0.30 | 1.38, 0.41 | 0.86 | single ridge, 15.4 m, 12 deg, 4.5 m, 4.6 ha |
| The Creamery, Stranraer | 1.06, 0.35 | 1.39, 0.47 | - | 42 % waste heat |
| North British | 1.07, 0.30 | 1.44, 0.41 | 0.86 | 1.7 ha (urban) |

- All six leading sites per crop pass both goals centrally and under every sensitivity. The cost rise from Gate A
  (+GBP 0.17-0.20/kg) is the standby heat pump (GBP 104-110/m2 of floor, about half the structure capex).
- Girvan now leads honestly: its 0.2 MW turbine pays on own use alone; sizing for export would cut another
  GBP 0.08/kg there (the Gate A artefact), and that case is excluded.
- Outages: the planned summer shutdown costs ~nothing (low heat demand); the unplanned coldest week costs
  GBP 0.04-0.05/kg. Battery: chosen in ~60 % of sweep designs but zero at the refined optima (no value there).
- Size (fixed 5/10/20/30 ha, re-optimised): cost rises GBP 0.04-0.10/kg from 5 to 30 ha; without the wall-light
  credit it is nearly flat (Girvan cucumber 1.05 -> 1.07). The small optimum is the wall-light credit plus a flat
  waste-heat rate covering a small house fully (waste share 94 % at 5 ha, 32-49 % at 30 ha). Every size passes.
- EN 13031-1 (Type A, A15, CC0; K_FI 0.8; snow x0.874, wind pressure x0.862 for 15 yr): all designs pass; A15
  would save 0.5-0.9 kg/m2 steel (GBP 2.6-4.8/m2). Costing stays on the conservative CC2 50-yr basis until Gate C.
  Steel of 4-7 kg/m2 looks light for these spans: the concept member model has no connections or bracing design.

Electricity price fix (2026-10-03): the hourly price used to scale the whole DESNZ non-domestic mean to the Agile
shape, so the cheapest 1 % of hours cost ~0 p/kWh. Now only the wholesale share follows the shape (0.32, UtilityBidder
16 Apr 2026 citing Drax spring 2026: wholesale ~31-32 % of a business bill, the rest network/policy/levies); 0.5 is a
sensitivity (large HV sites). Cheapest hours now ~11.8 p/kWh. Effect on the sweep and refinement: none at the penny
level (heat is mostly waste heat). Flat-price LP results archived in results/site_opt/lp_flatprice_archive/.

Heat store + plant LP (`finalist_lp.py`, item 4; PyPSA + HiGHS, hourly, availability profile in place, store cost
DEA 2019 large hot-water tanks 7,450 V^-0.47 EUR2015/m3 x 1.2876 HICP, 25 K swing):

| Site | Cucumber standby / LP-sized HP (GBP/kg) | LP HP vs design | LP store | Tomato standby / LP |
| --- | --- | --- | --- | --- |
| Girvan | 1.00 / 0.92 | 46 % | 13 MWh (~450 m3) | 1.35 / 1.22 |
| Caledonian | 1.01 / 0.94 | 43 % | 61 MWh (~2,100 m3) | 1.36 / 1.26 |
| Cameronbridge | 1.02 / 0.93 | 44 % | 46 MWh (~1,600 m3) | 1.37 / 1.26 |

- With the full-standby rule the LP lands within 1 p/kg of the sweep's dispatch (cross-check passed), builds almost
  no store and only 0.07-0.2 MW of wind; battery ~0.
- If the heat pump is sized by the LP instead (40-46 % of the design load) a 13-61 MWh hot-water store carries the
  coldest-week outage, saving GBP 0.07-0.09/kg (cucumber) and 0.10-0.12/kg (tomato). The saving is capital (half a
  heat pump vs a tank), not price arbitrage: it survived the price fix unchanged. It holds only while an outage
  in cold weather lasts no longer than the modelled week; Cameronbridge's 2026 strikes ran ~3 weeks (in autumn).
  Kept as an option for the user; the central case stays full standby (user rule 2026-10-03).
- Runtime: 12 LPs took 36 min one at a time (simplex) and 50 min with 3 workers + interior point on this 4-core
  laptop; the solver is back on the default.

GreenLight cross-check (R5, 2026-10-03; `gl_validate.py`, `gl_run.py`, `gl_chunks.py`; results/greenlight/):
Caledonian Paper, tomato (GreenLight's crop model is tomato only), refined Gate B design, 2023 site weather, matched
geometry, cover U and light, setpoints, screen rule, infiltration; no lamps. Run as four parallel quarter-year
chunks (quarters 2-4 start from a mature crop, 6-day spin-up); GreenLight's BDF solver needed max_step 300 s, an
auto-restart, and a day screen threshold of -15 C (a -100 C threshold overflowed its smooth controller and blew the
model up silently from day 90; caught and fixed, results discarded).

| Month | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | Year |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GreenLight kWh/m2 | 35.1 | 29.2 | 29.9 | 20.0 | 9.4 | 3.5 | 5.3 | 5.2 | 11.8 | 28.2 | 38.8 | 13.5 | 229.8 |
| Ours kWh/m2 | 32.4 | 21.7 | 13.1 | 3.1 | 0.2 | 0.0 | 0.0 | 0.0 | 1.2 | 9.5 | 25.2 | 14.3 | 120.6 |

- **Fails the +-15 % heat test: ours is 48 % below GreenLight.** Monthly shape agrees (r 0.87) and midwinter
  agrees (Jan, Dec within 8 %); the gap is spring/summer/autumn, where ours heats almost nothing.
- GreenLight's off-season heat comes at dawn (June peak 05:00, 38 W/m2: the step from the night to the day
  setpoint at sunrise) and on humid nights (RH ~90 %, screen part-closed). Our model ramps the setpoint and lets
  the morning sun do it, and its humidity control adds little heat. Dutch practice heats for humidity
  ("minimumbuis"), so GreenLight is probably nearer reality here; our model likely underestimates annual heat.
- Peak (design) heat is unaffected (winter agrees), so heat-pump size and capex stand.
- Cost effect at the waste-heat sites is small: +109 kWh/m2 x GBP 10/MWh = GBP 1.1/m2/yr, ~GBP 0.03/kg tomato; the
  heat source still covers it (8.5 ha x 230 kWh/m2 = 20 GWh of 83). Where the heat pump supplies the heat (WWTP
  sites, outages, large houses) the extra electricity is ~31 kWh/m2, ~GBP 0.15/kg: material there.
- Yield not checked: quarters 2-4 start from an assumed crop; needs the continuous year (on the 32 GB machine).


### 3.18 Model verification against GreenLight and the yield model (R6-R8, 2026-10-03)

Validation case: Caledonian Paper, tomato (GreenLight is tomato-only), refined Gate B design, 2023 site weather.
- **Start (R5):** our annual heat was 48 % below GreenLight's (121 vs 230 kWh/m2). Hour-by-hour comparison ruled out the setpoint
  ramp and humidity control. GreenLight's 1-D soil drained 49 kWh/m2/yr and chunks 2-4 started on 10 C soil; with an ISO 13370
  equivalent deep soil and a mature soil seed (`gl_variant.py`) GreenLight gives 208.5 kWh/m2, so ours was still 42 % low.
- **Controlled constant-weather runs (`gl_ctrl.py`, mature crop, GreenLight LAI matched):** night envelope loss, screen and
  infiltration agree within ~5 %. The gap was transpiration: thesis law LE = 0.21 I + 14 VPD gave 398 kg/m2/yr vs GreenLight 645.
  (A first version of these runs used GreenLight's young crop, LAI 0.1-0.3, and our synthetic weather lacked the outdoor humidity
  ratio; both were fixed before drawing conclusions.)
- **Fixes (all options default to thesis behaviour; `test_reproduce`, `test_fast`, `test_costing`, `tests/test_r6_options.py` pass):**
  crop transpiration lambda E = A0 (1 - exp(-k LAI)) G + B0 LAI VPD (Baille et al. 1994; Stanghellini 1987) with a seasonal LAI
  schedule (`transp.py`); Vanthoor (2011) roof-vent law with vent area 11.7 % of floor; GreenLight floor + 5 soil layers over the ISO
  deep conductance; floor light share from canopy optics (PAR k 0.7, floor reflectance 0.65; NIR k 0.27, 0.5).
- **Result vs GreenLight (annual):** heat 197.8 vs 208.5 kWh/m2 (0.95, passes +-15 %), monthly r 0.98, RMSE 3.0 kWh/m2/month,
  transpiration 640 vs 645 kg/m2, 23 h above 30 C vs 7. Remaining: Mar-Apr and Oct under by 4-6 kWh/m2/month, dull days ~40 % low
  on heat (low-light transpiration), GreenLight exceeds our design heat load 183 h/yr (4.7 kWh/m2).
- **Cucumber:** GreenLight cannot run it. Constants A0 0.24, B0 30 W/m2/kPa per LAI, k 0.7 from Medrano et al. (2005) (A 0.24,
  B 22-37.6), tested against the measured lysimeter transpiration of Nikolaou et al. (2017): predicted within -7 % (autumn-winter)
  and -10 % (spring), at LAI 1-1.9; the design LAI of 3.0 is an extrapolation (`python transp.py`).
- **Yield (R8, `crop_gh.py`):** photosynthesis and carbon balance on the hourly climate with CO2 enrichment; fruit partition
  calibrated to the CBS yield on the Westland reference house (tomato 0.70, cucumber 0.77); maintenance Rm25 0.015 g CH2O/g/d,
  CH2O to DM 0.7, tomato fruit-set loss above 25 C daily mean. Checks: light elasticity 0.88 (tomato), 1.00 (cucumber); GreenLight
  tomato yield (`gl_year.py`) see below. Replaces CBS x light^0.8 and the 25 kg/m2 CO2 placeholder (model dose ~40 kg/m2).
- **Effect on the Gate B finalists before re-optimisation:** yield 0.86-1.00 of the old formula; cucumber GBP/kg at GBP 10/MWh heat
  1.00-1.03 -> 1.16-1.23 (import 1.57), tomato 1.34-1.38 -> 1.45-1.55 (import 1.77); heat 190-225 -> 315-345 (cucumber) and
  117-141 -> 195-220 kWh/m2 (tomato).

## 4. Crop and growth model

### 4.1 System

High-density 'Hass' (pruned) on clonal rootstock, about 800–1,600 trees/ha equivalent, in in-ground beds (user decision
§3.11, 2026-10-02; containers as a sensitivity, see §3.7). A naturally
compact cultivar ('Wurtz'/'Little Cado') is a sensitivity case. Planting density, canopy height and container volume are
config inputs.

### 4.2 Model (hourly, coupled to the greenhouse sim)

- **Light:** sun + LED PAR, cover transmission, Beer–Lambert canopy interception, with sunlit and shaded leaves treated separately (de Pury & Farquhar 1997).
- **Photosynthesis:** Farquhar–von Caemmerer–Berry, with leaf parameters for avocado from the literature. This makes the
  CO₂, temperature and light responses physical instead of fitted multipliers.
- **CO₂ balance:** greenhouse air ppm from canopy uptake, dosing, ventilation loss (existing vent/ACH model) and
  soil/substrate respiration. Dosing control: setpoint (e.g. 800 ppm) when vents are near-closed, ambient-tracking when open.
- **Carbon balance:** growth and maintenance respiration (Q10), allocation to leaf/wood/root/fruit, with a fruit-sink priority
  during fruit growth.
- **Phenology:** floral induction from accumulated cool temperatures (Buttrose & Alexander 1978; Salazar-García et
  al. 1998), flowering and fruit set (temperature-limited), fruit growth to maturity (months), physiological drop.
  Alternate bearing is a carry-over of the previous year's crop load.
- **Tree age:** non-bearing years 1–2, rising yield to maturity by about year 5. All 30 years are simulated, so the per-kg
  denominator includes the unproductive establishment years.
- **Water and nutrients:** transpiration (existing Penman–Monteith-style term) → irrigation volume → fertiliser N, P and K
  from crop removal, with production emissions for each.
- **Calibration targets:** published high-density orchard yields and avocado leaf gas-exchange data; the model is accepted
  only when it reproduces open-field reference yields under reference climates before it is used in the greenhouse.

### 4.3 Climate strategy (setpoints may change if sourced)

Crop-led strategy: day/night temperature setpoints, a cool-night flowering-induction window, humidity/VPD limits and
DLI targets, each referenced to avocado physiology literature. The thesis strategy (18 °C continuous) stays as a scenario
so the effect of the change is visible.

## 5. Bill of materials (parametric, complete)

`lca/bom.py` builds quantities from the site configuration and the sized plant. Each line records: element, material,
quantity, unit, mass, ICE v3 (or EPD/TM65) factor ID, service life, replacement count, indicative £ rate, **source**,
**confidence** (sized / scaled / estimated).

| Group | Contents |
| --- | --- |
| Substructure | Site strip, excavation, pad footings (concrete + rebar), ground beams/kerb |
| Floor | Concrete slab or central paths, gravel bed, ground cover fabric, drainage channels, sumps |
| Superstructure | Steel columns, trusses, gutters, purlins (galvanised), bracing |
| Envelope | Aluminium glazing bars, glass or twin-wall PC, side walls, doors, seals |
| Climate | Roof vents + rack drives, energy/blackout screens + motors, circulation fans, fogging/humidification |
| Heating distribution | Pipe rail, grow pipes, manifolds, mixing groups, buffer tank, insulation |
| Lighting | LED fixtures (by PPFD and photosynthetic photon efficacy), cabling, drivers |
| Growing system | Containers, substrate, trellis/support, fertigation unit, dosing pumps, water tanks, rainwater collection |
| CO₂ | Liquid CO₂ tank + vaporiser, or flue-gas cleaner + distribution tubing |
| Heat supply | Per scenario: R717 heat pump (compressors, HX from UA, intercooler, NH₃ charge, valves, frame), air cooler and fans / boreholes (HDPE, grout, glycol, drilling) / river intake; gas boiler + flue; CHP engine + generator + HX + catalyst |
| Electrical and controls | Switchgear, cabling, climate computer, sensors; grid connection |
| On-site energy | Wind turbine (tower, nacelle, blades, foundation), PV (modules, mounting, inverters), battery, thermal store |
| Packhouse | Grading, packing, cold store (scaled per t/yr) |
| Rooftop only | Structural strengthening allowance, edge protection, crane/lift |

Packaging, ripening and logistics are modelled in the supply-chain step, so UK and imported fruit are treated alike.

## 6. LCA method

- **A1–A3:** BOM mass × ICE v3 factors (TM65 mid-level method for building-services equipment where no EPD exists).
- **A4:** transport distances by material class (UK default HGV factor). **A5:** site energy, waste factors, borehole
  drilling diesel.
- **B6 energy:** hourly electricity and gas from the coupled sim × hourly grid intensity, scaled along the FES pathway
  for each year of the 30. Gas at DESNZ factors including upstream. CHP export credited at the displaced marginal
  grid intensity (reported separately as well as net).
- **Refrigerant:** annual leak rate and end-of-life loss × GWP. R717 is GWP 0, so this term matters only for the
  boiler/CHP chillers and imported reefer containers.
- **Purchased CO₂:** production and transport factor. Flue CO₂ is free; dosed CO₂ mostly ends up vented.
- **B7 water:** irrigation volume × AWARE characterisation factor for site and origin.
- **C1–C4:** dismantling, transport, recycling, landfill. **D:** steel, aluminium, glass recycling credit.
- **Imports:** orchard stage per origin from published avocado LCAs (including land-use change where the source
  reports it), reefer road and sea freight from DEFRA/GLEC factors with the reefer energy uplift, ripening-room energy,
  loss rates per stage. Origin data with weak sources are flagged as such.

## 7. LCC method

- CAPEX from indicative £ rates in the BOM (SPON's Architects' & Builders' and Mechanical & Electrical price books,
  published £/kW for heat pumps, boilers, CHP and wind, £/m drilling).
- OPEX: electricity and gas tariffs with scenarios (current, high, low; CHP export price), CO₂ purchase, water,
  labour (h per m² per year), maintenance as % CAPEX per year, insurance.
- Replacement costs at service-life intervals; residual value at year 30.
- Outputs: NPV, **levelised cost £/kg**, comparison with the **landed import price** (UK wholesale avocado price), cost of
  carbon abated (£/t CO₂e) relative to sea-freighted imports.

## 8. Uncertainty

Each uncertain input has a distribution (BOM masses by confidence class, emission factors, prices, service lives,
yield model parameters, origin data). Monte Carlo (≥ 1,000 draws) on the headline set; tornado charts for one-at-a-time
sensitivity; results reported as median and 90 % interval.

## 9. Code layout

```
BEng-CEA-Heatpump/lca/
  SCOPE.md            this file
  config.py           one SiteConfig dataclass: geometry, form, location, crop, lighting, energy, economics
  greenhouse.py       parametric version of sim/annual_sim.py (geometry from config; thesis case reproduced exactly)
  crop.py             avocado growth, phenology and CO2 balance
  energy_systems.py   gas boiler, CHP, wind, PV, battery, thermal store, off-grid sizing (PyPSA)
  bom.py              parametric BOM
  imports.py          import supply chains and sea routes
  lca.py, lcc.py      assessment; reuses Whole-Carbon-Lifecycle-Assessment/src engines where they fit
  uncertainty.py      Monte Carlo + tornado
  run_study.py        headline set, sweeps, break-even → results/*.json + viewer data
  data/               factors, rates, origin data (CSV, every row with a source column)
```

`sim/annual_sim.py` and the thesis notebooks stay untouched. The new parametric model must reproduce the existing
400 m² results before anything else is built on it.

## 10. Work plan and review gates

1. **Scope** (this document) → *review*
2. **Parametric greenhouse + crop-led climate**: generalise geometry and location, verify against current 400 m² results
3. **Growth model + CO₂ balance**: calibrate against open-field references → *review yield and setpoints*
4. **Heating and electricity systems**: boiler, CHP, wind/PV/battery, off-grid sizing
5. **BOM**: generate and review line by line → *review BOM before any carbon or cost numbers*
6. **Imports model**
7. **LCA + LCC + uncertainty**, break-even analysis
8. **Viewer tab + write-up**

## 11. Known risks and assumptions to watch

- **Avocado under glass is rare** and has little published data for this setting. Expect wide yield uncertainty; the break-even yield plot is the robust result.
- **Run time:** the current sim takes 10-minute steps with 30 s climate sub-steps. Hundreds of sweep cases will need a
  coarser step for sweeps (validated against the full step) or parallel runs.
- **Scale effects:** heat demand per m² falls with area (lower envelope-to-floor ratio), which strongly favours larger
  sites. Rooftop cases also gain heat from the building below.
- **Early expectation:** at today's grid intensity a heated, lit UK greenhouse will probably exceed sea-freighted imports
  in kg CO₂e/kg. The value of the study is in quantifying the conditions under which that reverses.

## 12. References (to cite; ✓ = confirmed, ? = to be checked before use)

- ✓ ISO 14040/14044; EN 15978; EN 15804+A2; ISO 15686-5; PAS 2050-1:2012
- ✓ RICS (2023) Whole life carbon assessment for the built environment, 2nd ed.; CIBSE TM65 (2021)
- ✓ Jones & Hammond, ICE Database v3 (University of Bath / Circular Ecology)
- ✓ DESNZ/DEFRA GHG conversion factors (current year); NESO Future Energy Scenarios; GLEC Framework v3
- ✓ HM Treasury Green Book; SPON's price books (current editions)
- ✓ Boulay et al. (2018) AWARE water scarcity method, Int J LCA 23
- ✓ Farquhar, von Caemmerer & Berry (1980) Planta 149; de Pury & Farquhar (1997) Plant Cell Environ 20
- ✓ Vanthoor et al. (2011) greenhouse climate model, Biosystems Engineering 110
- ✓ Schaffer, Wolstenholme & Whiley (eds) (2013) *The Avocado: Botany, Production and Uses*, 2nd ed., CABI
- ✓ Buttrose & Alexander (1978) floral initiation in 'Fuerte' avocado, Scientia Horticulturae 8
- ? Salazar-García et al. (1998) 'Hass' floral development, J Amer Soc Hort Sci
- ✓ Sanyé-Mengual et al. (2015) rooftop greenhouse LCA/LCC Barcelona, Int J LCA 20
- ? Nadal et al. (2017) integrated rooftop greenhouse energy, Applied Energy
- ✓ Blaauw et al., *Life Cycle Assessment of an Avocado: Grown in South Africa – Enjoyed in Europe*, SSRN (cited in thesis)
- ✓ Blaauw et al. (2024) Environmental Management, peer-reviewed version (PMC11438827): gross 904.85, net 382.97 kg CO₂e/t
- ✓ Elorrieta-Mendoza et al. (2025) Avocado production in different biomes throughout Peru, Int J LCA, doi:10.1007/s11367-025-02561-5
- ✓ Esteve-Llorens et al. (2022) Peruvian hyper-arid coast, green asparagus and avocado (via Elorrieta-Mendoza Table 6)
- ✓ Pedreschi et al. (2022) Short vs long-distance avocado supply chains, Foods 11:1807
- ✓ Hernández Lagana (2026) Measuring carbon and water footprints in avocado value chains, FAO, ISBN 978-92-5-140751-6
- ✓ Solarte-Toro et al. (2023) Environ Sci Pollut Res 30:8790–8808 (Colombia, creole avocado)
- ? Astier et al. (2014) Mexico, and Bartl et al. (2012) Peru: values taken second-hand from the tables above
- ✓ DESNZ (2025) GHG conversion factors (flat file); UN Comtrade (HS 080440)
- ✗ No orchard LCA found for Chile, Israel, Kenya, Morocco or Spain (proxies used)
