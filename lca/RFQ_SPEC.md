# RFQ specification: glasshouse + R717 heat plant (Gate B → C)

Status: draft for issue, 2026-10-03. Prepared from the Gate B design (see `HANDOFF.md` §3c and
`results/site_opt/refined_cucumber.json`). Quantities come from `python rfq_quantities.py cucumber`
and are indicative (concept design). The quotes replace the placeholder rates in `data/rates.csv`, which
currently make up about half the structure capex.

## 1. Purpose and what we need back

We are pricing a heated glasshouse for high-wire cucumber (tomato as the alternative) on a Scottish
industrial waste-heat site. Each supplier is asked for:

1. A budget price (±15 %) for the package as specified, **ex works and installed** separately, in GBP,
   valid 90 days, with the price basis date.
2. Unit rates for the quantity-variable lines (per m², per m, per kW) so we can re-price other sizes
   between 5 and 30 ha.
3. Lead time, installation duration and crew size (we will cost UK labour separately if needed).
4. Product datasheets: U-value, light transmission (hemispherical / diffuse), weight, design life,
   warranty, and an **EPD or kg CO₂e per unit** where one exists. Embodied carbon is part of the study's
   pass/fail test.
5. Any design changes the supplier recommends for cost, with their price effect.

Please price exactly what is specified, then offer alternatives separately.

## 2. Project basis (all packages)

| Item | Basis |
| --- | --- |
| Location | Central Belt / Ayrshire / Fife, Scotland (finalist sites in §6). Exposed coastal sites possible |
| Standard | EN 13031-1:2019, Type A (glass), class **A15**, consequence class **CC0**; ULS and SLS checks. BS EN 1991 UK NA for snow and wind (site zone and v_b to be confirmed with the site) |
| Size | 2–6 ha per phase in the central case; unit rates needed for 5 / 10 / 20 / 30 ha |
| Form | Wide-span single-ridge pitched roof, span 16–24 m, roof pitch 10–16°, gutter 4.5–5.8 m, ridges N–S |
| Cover | Double-glazed AR sealed units on roof and walls (low-e is priced as an option only) |
| Crop | High-wire cucumber / tomato, hung crop load per EN 13031-1 (supplier to state the value used) |
| Heating | Low-temperature hot water, 51 mm pipe-rail + growing pipe, supply ≤ 55 °C from the heat pump, up to 80 °C from waste heat |
| Organic | Soil-grown beds (organic certification target): no concrete floor under the beds; concrete paths only |

## 3. Packages and placeholder lines to be quoted

Every line here is a placeholder in `data/rates.csv` or the site model. The model rate is shown so the
supplier can see what the study assumes; it is **not** a target price.

### 3.1 Glazing and glazing system (structure supplier or glazing specialist)

| Line | Specification | Model rate | Placeholder range |
| --- | --- | ---: | --- |
| `glass_dbl_ar_m2` | Double sealed unit, 2 × 4 mm toughened, AR coating on all four faces; state Ug and τ hemispherical | £65/m² | £45–100 |
| `glass_dbl_lowe_m2` (option) | As above plus low-e; state Ug, τ and the low-e emissivity | £75/m² | £50–120 |
| `glass_single_m2` (reference) | 4 mm toughened 2×AR horticultural single glass, Venlo pane | £25/m² | £15–40 |
| `aluminium` | Glazing bars, ridge and gutter extrusions for double units; kg per m² of roof | £6/kg | £4–9/kg |

### 3.2 Climate equipment (greenhouse installer)

| Line | Specification | Model rate | Placeholder range |
| --- | --- | ---: | --- |
| `heating_pipe_m` | 51 × 2.0 mm galvanised pipe-rail incl. bends, supports, connection to header | £8/m | £5–12 |
| `energy_screen_m2` | Single energy screen (state energy saving %, light loss), incl. drive and wires | £6/m² | £4–9 |
| Screen saving | State the tested energy saving of the offered screen cloth (needed for the model: register item `screen_u_factor`) | — | — |

### 3.3 R717 (ammonia) heat pump (industrial refrigeration contractor)

| Line | Specification |
| --- | --- |
| Duty | Heat output = design heat loss of the chosen design at −3.1 °C outdoor / crop night setpoint indoor (§6 table), delivered at 45–55 °C to a buffer, return ~30 °C |
| Source | Air (R717 direct-expansion or glycol air coolers; state defrost method). Option: low-grade water source (WWTP effluent 8–16 °C) |
| Role | Full standby for the waste-heat supply (runs during source outages, ~5–8 weeks/yr) and the main heat source above the waste-heat capacity |
| Turndown | Variable-speed compressors; state minimum stable load |
| Scope | Packaged plant room or container, air coolers, controls, electrical connection to site LV board, commissioning, F-gas-free documentation, ammonia safety (EN 378, detection, ventilation) |
| Price | Installed £/kW at the duty above, plus unit rate for ±50 % duty. The study now uses the Danish Energy Agency 2026 data sheet (1–10 MW air source 1.02–1.15 MEUR/MW); quotes replace or confirm it |
| Performance | COP at 7/45, 2/45, −3/50 °C; part-load COP at 50 % |
| O&M | Annual service cost and refrigerant top-up assumptions |

### 3.4 Heat connection to the source (district-heating pipe contractor)

| Line | Specification | Model value |
| --- | --- | --- |
| Pre-insulated pipe | Twin or single pair, DN to suit the waste-heat duty (§6), 80/40 °C, buried, incl. trenching, crossings, heat exchanger skid at the source and metering | 500 m × £1,000/m (placeholder) |

Price per metre for DN 100 / 150 / 200, plus the source-side heat-exchanger skid as a separate line.

### 3.5 Heat store (tank supplier)

Insulated steel hot-water buffer, 30–80 °C, volume from the LP (§6). The study uses the DEA (2019) storage
catalogue formula (7,450 V^-0.47 EUR2015/m³) inflated to 2025; quotes for 500 / 1,000 / 2,000 m³ confirm it.

### 3.6 Lower-priority lines

| Line | Specification | Model rate |
| --- | --- | ---: |
| `xps_m2` | 100 mm XPS edge insulation, 1 m deep perimeter | £25/m² |
| `pc_twin_m2` | Twin-wall polycarbonate (alternative cover) | £20/m² |
| `etfe3_m2` | 3-layer ETFE cushion (alternative cover) | £975/m² (architectural price) |
| Battery | Containerised Li-ion, 2 h, size from §6; state £/kWh, round-trip efficiency, warranty cycles | £400/kWh + £150/kW |
| Advisers | Design fees for the heat plant (DEA capex excludes them) | not priced |

### 3.7 Residual systems (BP19b): the part of the SAC/SRUC £200/m² anchor not priced bottom-up

The cost model sets the reference house to £2M/ha (SAC/SRUC 2026 Table 11) and treats what the bottom-up list does not
price as a £94/m² residual. It is split below (`data/residual_items.csv`, `python bplan_residual.py`); the split is a
**placeholder** except the climate-computer line. Quote each line separately as installed, with the fixed part (per site)
apart from the per-m² part, so the Scale sheet can use real fixed shares.

| Line | Specification | Model £/m² | Fixed per site (model) |
| --- | --- | ---: | ---: |
| Erection labour | Frame, glazing, pipe-rail and screens, per m² of floor; crew, weeks per ha | 30.0 | none |
| Climate computer | Controller, sensors, wiring, outside weather station; state software licence per year | 14.0 | £27k |
| Vents | Roof vent racks, motors, actuators, insect screens; vent area 11.7 % of floor | 12.0 | none |
| Irrigation | Fertigation unit (EC/pH, 2+ channels), water treatment, tanks, drain recirculation | 14.0 | £60k |
| Crop wires and rails | Hanging wires, rails, trolleys, gutters or bed edging, per m² grown | 8.0 | none |
| Electrics | Distribution, lighting, plant-room wiring, earthing | 6.0 | £20k |
| Design and project management | Design, permits (planning, building warrant), PM | 10.4 | £60k |

Also ask: each line's life, and which of these are normally excluded from a glasshouse quote (so none is counted twice).

### 3.8 Second-hand glasshouse (BP19c; dismantler or glasshouse specialist)

Ask for: purchase price per m² of an available Venlo-type used structure; dismantle, haulage to the site and re-erection
(£/m²); foundations; glass and seal replacement allowance; condition survey; the design wind and snow rating the
structure can carry (EN 13031-1, site zone) and whether the original design documents exist. Model placeholders:
purchase £60/m² (SAC/SRUC, sourced), re-erection £25-50/m², glass replacement 5-30 % of glazed area (`bplan_secondhand.py`).

## 4. Embodied carbon data requested

EPD (EN 15804) or supplier kg CO₂e per unit for: double-glazed units, aluminium extrusions (primary/recycled
share), energy screen, polycarbonate, ETFE, XPS, pre-insulated pipe, the heat-pump package and the battery.
Items with no factor are currently listed as missing in the model (`costing.evaluate()['missing_co2']`).

## 5. Evaluation

Quotes are compared on installed £ per m² of floor (structure + glazing + climate), £/kW (heat pump), £/m
(pipe) and kg CO₂e. They go into `data/rates.csv` (`cost_tier = quote`, with supplier and date), the site
optimisation is rerun, and the Gate C design is frozen on the quoted rates.

## 6. Design quantities by finalist site

Generated by `python rfq_quantities.py cucumber` (2026-10-03, cucumber Gate B designs). Model rates are the
current placeholders, shown for context only. Plant: heat pump at the full design load (standby rule); the LP
option (heat pump at 43–46 % plus a 13–61 MWh store) is shown in SCOPE.md §3.17 — please also quote the heat pump
at 45 % of the duty and the store at 500 / 1,500 / 2,000 m³ so both options can be priced.

### Girvan + Ailsa Bay distilleries — 4.7 ha, 4 spans x 21.2 m, 555 m long, gutter 4.5 m, pitch 10 deg, dbl_ar
| Item | Unit | Quantity | Model rate (GBP) | Model cost (GBP k) | Status |
|---|---|---:|---:|---:|---|
| steel | t | 287 | 4,890 | 1,403 | industry cost model |
| aluminium | kg | 68,135 | 6 | 409 | PLACEHOLDER |
| glass_dbl_ar_m2 | m2 | 53,231 | 65 | 3,460 | PLACEHOLDER |
| concrete | m3 | 1,163 | 102 | 119 | trade price |
| pir_panel_m2 | m2 | 409 | 52 | 21 | retail |
| heating_pipe_m | m | 105,981 | 8 | 848 | PLACEHOLDER |
| energy_screen_m2 | m2 | 47,103 | 6 | 283 | PLACEHOLDER |
Plant: {'hp_kW_design': 5501, 'wind_kW': 203, 'batt_kWh': 0, 'lp_store_kWh': 764, 'lp_hp_kW_th': 5501, 'lp_wind_kW': 139, 'lp_batt_kWh': 0}

### Caledonian Paper Mill, Shewalton, Irvine — 7.5 ha, 9 spans x 16.3 m, 509 m long, gutter 4.5 m, pitch 10 deg, dbl_ar
| Item | Unit | Quantity | Model rate (GBP) | Model cost (GBP k) | Status |
|---|---|---:|---:|---:|---|
| steel | t | 327 | 4,890 | 1,600 | industry cost model |
| aluminium | kg | 104,663 | 6 | 628 | PLACEHOLDER |
| glass_dbl_ar_m2 | m2 | 81,768 | 65 | 5,315 | PLACEHOLDER |
| concrete | m3 | 1,568 | 102 | 160 | trade price |
| pir_panel_m2 | m2 | 0 | 52 | 0 | retail |
| heating_pipe_m | m | 167,649 | 8 | 1,341 | PLACEHOLDER |
| energy_screen_m2 | m2 | 74,510 | 6 | 447 | PLACEHOLDER |
Plant: {'hp_kW_design': 8758, 'wind_kW': 0, 'batt_kWh': 0, 'lp_store_kWh': 1, 'lp_hp_kW_th': 8758, 'lp_wind_kW': 196, 'lp_batt_kWh': 0}

### Cameronbridge distillery — 4.6 ha, 28 spans x 15.4 m, 108 m long, gutter 4.5 m, pitch 12 deg, dbl_ar
| Item | Unit | Quantity | Model rate (GBP) | Model cost (GBP k) | Status |
|---|---|---:|---:|---:|---|
| steel | t | 209 | 4,890 | 1,021 | industry cost model |
| aluminium | kg | 67,796 | 6 | 407 | PLACEHOLDER |
| glass_dbl_ar_m2 | m2 | 52,965 | 65 | 3,443 | PLACEHOLDER |
| concrete | m3 | 1,037 | 102 | 106 | trade price |
| pir_panel_m2 | m2 | 0 | 52 | 0 | retail |
| heating_pipe_m | m | 104,607 | 8 | 837 | PLACEHOLDER |
| energy_screen_m2 | m2 | 46,492 | 6 | 279 | PLACEHOLDER |
Plant: {'hp_kW_design': 5618, 'wind_kW': 0, 'batt_kWh': 0, 'lp_store_kWh': 0, 'lp_hp_kW_th': 5618, 'lp_wind_kW': 68, 'lp_batt_kWh': 0}

