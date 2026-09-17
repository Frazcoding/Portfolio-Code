# GEMINI.md — Plantpost: Urban Vertical Green Infrastructure & Resource Modelling

---

## 1. Executive Project Overview & Engineering Scope

- **Repository**: `Plantpost-Urban-Infrastructure-Modelling`
- **Lead Engineer**: Fraser James Mclellan
- **Role**: Co-Founder & Head of Environmental Modelling (Technical Lead)
- **Domain**: Controlled Environment Agriculture (CEA), Urban Green Infrastructure, Off-Grid Solar & Battery Microgrids, Hydro-meteorology & Evapotranspiration, Urban Microclimate & Ecosystem Services
- **Startup Provenance & IP Award**:
  - Originated at the **University of Bologna (UNIBO Incubator)** within the *Design Methods for Industrial Engineering* program.
  - Winner of the prestigious **Bugnion Intellectual Property Award (€2,500 patenting services)** at **UNIBO Startup Day** for its proprietary localized microclimate, rainwater recapture, and thermal/hydraulic balancing system.
  - Pitched directly to venture capital juries, corporate sustainability leaders, and institutional investors (including PwC).
- **Core Mission**:
  - Transform the startup's original feasibility spreadsheet (`Plantpost reqs.xlsx`) into a production-grade, open-source, dynamic simulation suite in Python.
  - Resolve the central engineering bottleneck of off-grid urban green infrastructure:
    > *Can a self-contained, multifunctional urban street pole achieve 100% off-grid electrical reliability for public lighting and 100% rainwater self-sufficiency for vertical foliage irrigation across extreme seasonal European weather fluctuations without municipal grid or water connections?*
- **Primary Archetype**:
  - A $4.5\text{ m}$ multifunctional urban street post integrating:
    1. A $3.14\text{ m}^2$ circular rainwater catchment and solar photovoltaic canopy ($r = 1.0\text{ m}$).
    2. A 4-tier vertical living column with modular green foliage planters at heights $z \in \{1.0, 2.0, 3.0, 4.0\}\text{ m}$.
    3. An off-grid electrical powertrain: Monocrystalline PV canopy, maximum power point tracking (MPPT) charge controller, a $12\text{V}$ LiFePO4 battery bank, and a $47.1\text{ W}$ high-efficiency LED public street luminaire.
    4. A closed-loop hydraulic irrigation network: Internal base reservoir ($A_{\text{tank}} = 0.15\text{ m}^2$), submersible $12\text{V}$ DC micro-pump ($\eta = 70\%$), multi-tier manifold, and pressure-compensating drip emitters.
- **Geographic & Climatic Anchors**:
  - **Primary Baseline**: Bologna, Italy (Mediterranean continental, Cfa climate, UNIBO incubator location) using hourly Typical Meteorological Year (TMY) and PVGIS solar/meteorological datasets.
  - **Multi-City Portability Comparison**: Benchmark performance against Northern European maritime climates (Edinburgh and London, UK) to assess geographic boundary limits and storage requirements.
- **Strategic Purpose**: Demonstrates advanced competencies in environmental system modelling, dynamic mass and energy balances, off-grid storage sizing, crop hydrology (FAO-56 Penman-Monteith), and urban ecosystem impact quantification for cleantech startups, sustainability consultancies, and green infrastructure authorities.

---

## 2. System Boundary & Physical Architecture

The physical system boundary encompasses the stand-alone off-grid pole, its surrounding atmospheric control volume, and the immediate urban street canyon:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                        PLANTPOST PHYSICAL SYSTEM & ENERGY-WATER BOUNDARY                        │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                  │
│   [ATMOSPHERIC INPUTS]        [SOLAR PV & LIGHTING SUBSYSTEM]       [RAINWATER & IRRIGATION]     │
│                                                                                                  │
│    Solar GHI / DNI (t) ───►  ┌─────────────────────────────┐       ┌────────────────────────┐    │
│    Rainfall Rate P(t)  ───►  │ Circular PV Canopy (3.14 m²)│       │ Catchment Dish (3.14m²)│    │
│    Ambient Temp Tamb(t)───►  │   Monocrystalline Solar     │       │ Filter & Diverter (90%)│    │
│    Relative Humidity RH───►  └──────────────┬──────────────┘       └───────────┬────────────┘    │
│    Wind Speed U2 (t)   ───►                 │ P_pv(t)                          │ Q_rain(t)       │
│                                             ▼                                  ▼                 │
│                              ┌─────────────────────────────┐       ┌────────────────────────┐    │
│                              │ MPPT Charge Controller      │       │ Base Reservoir Buffer  │    │
│                              │   & 12V LiFePO4 Battery     │       │   Atank = 0.15 m²      │    │
│                              │   State of Charge: SoC(t)   │       │   Height: h_water(t)   │    │
│                              └──────────────┬──────────────┘       └───────────┬────────────┘    │
│                                             │                                  │                 │
│                         ┌───────────────────┴───────────────────┐              │                 │
│                         │ P_light(t)                            │ P_pump(t)    │ Q_irr(t)        │
│                         ▼                                       ▼              ▼                 │
│             ┌────────────────────────┐              ┌───────────────────────────────────────┐    │
│             │ Public LED Luminaire   │              │ 12V DC Micro-Pump & Vertical Manifold │    │
│             │ 47.1 W (Dusk-to-Dawn)  │              │ Dynamic Head: H_dyn = z_i - h_w + h_f │    │
│             └────────────────────────┘              └──────────────────┬────────────────────┘    │
│                                                                        │ Drip Emitters           │
│                                                                        ▼                         │
│                                                     ┌───────────────────────────────────────┐    │
│                                                     │ 4-Tier Living Foliage Column          │    │
│                                                     │   Tier 4: z = 4.0 m  (0.27 L/day)     │    │
│                                                     │   Tier 3: z = 3.0 m  (0.27 L/day)     │    │
│                                                     │   Tier 2: z = 2.0 m  (0.27 L/day)     │    │
│                                                     │   Tier 1: z = 1.0 m  (0.27 L/day)     │    │
│                                                     └──────────────────┬────────────────────┘    │
│                                                                        │ Transpiration           │
│                                                                        ▼                         │
│                                                     ┌───────────────────────────────────────┐    │
│                                                     │ Urban Microclimate & Ecosystem Co-ben │    │
│                                                     │ - Evaporative Cooling: Q_evap (kWth)  │    │
│                                                     │ - Stormwater Attenuation (L diverted) │    │
│                                                     │ - PM2.5 / NOx Deposition Bio-filter   │    │
│                                                     │ - Avoided Grid CO2e Emissions         │    │
│                                                     └───────────────────────────────────────┘    │
│                                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Mathematical & Physical Formulation

### 3.1. Astronomical Solar Geometry & Lighting Load Schedule
The public lighting system operates strictly from dusk to dawn based on instantaneous solar elevation:

$$\alpha_{\text{sun}}(t) = \arcsin\left( \sin\phi \sin\delta + \cos\phi \cos\delta \cos\omega(t) \right)$$

Where $\phi$ is site latitude, $\delta$ is solar declination, and $\omega(t)$ is the hour angle. The luminaire switches on when $\alpha_{\text{sun}}(t) \le -6^\circ$ (civil twilight):

$$P_{\text{light}}(t) = \begin{cases} 47.1\text{ W} & \text{if } \alpha_{\text{sun}}(t) \le -6^\circ \\ 0 & \text{otherwise} \end{cases}$$

Monthly daily operating hours vary from $8.5\text{ h/day}$ (June) to $15.0\text{ h/day}$ (December), yielding an annual lighting electricity demand of $\approx 200.8\text{ kWh/yr}$.

---

### 3.2. Solar PV Generation & Off-Grid Battery Microgrid Dynamics
The circular canopy captures global tilted solar irradiance $G_{\text{tilt}}(t)$ ($\text{W/m}^2$):

$$P_{\text{pv}}(t) = A_{\text{pv}} \cdot \eta_{\text{pv}} \cdot G_{\text{tilt}}(t) \cdot \left[ 1 - \gamma_{\text{temp}} (T_{\text{cell}}(t) - 25^\circ\text{C}) \right] \cdot \eta_{\text{MPPT}} \cdot \eta_{\text{dirt}}$$

Where:
- $A_{\text{pv}} = 3.14\text{ m}^2$ (effective canopy area with diameter $D = 2.0\text{ m}$).
- $\eta_{\text{pv}} = 0.215$ (high-efficiency monocrystalline silicon cells).
- $\gamma_{\text{temp}} = 0.0038\text{ K}^{-1}$ (PV temperature derating coefficient).
- $\eta_{\text{MPPT}} = 0.98$ and $\eta_{\text{dirt}} = 0.95$ (soiling and wiring balance of system factor).

The battery state of charge ($\text{SoC}(t) \in [\text{SoC}_{\min}, 1.0]$) evolves over discrete time steps $\Delta t = 1\text{ h}$:

$$\Delta E_{\text{bat}}(t) = \begin{cases} (P_{\text{pv}}(t) - P_{\text{load}}(t)) \cdot \eta_{\text{chg}} \cdot \Delta t & \text{if } P_{\text{pv}} \ge P_{\text{load}} \\ \frac{P_{\text{pv}}(t) - P_{\text{load}}(t)}{\eta_{\text{dis}}} \cdot \Delta t & \text{if } P_{\text{pv}} < P_{\text{load}} \end{cases}$$

$$\text{SoC}(t + \Delta t) = \text{SoC}(t) + \frac{\Delta E_{\text{bat}}(t)}{C_{\text{bat, nom}}}$$

Where $P_{\text{load}}(t) = P_{\text{light}}(t) + P_{\text{pump}}(t) + P_{\text{aux}}$.
- **Reliability Metric**: The Loss of Load Probability ($\text{LOLP}$) over the annual simulation:
  $$\text{LOLP} = \frac{\sum_{t=1}^{8760} \mathbb{I}(\text{SoC}(t) \le \text{SoC}_{\min} \land P_{\text{load}}(t) > 0)}{T_{\text{lit}}}$$
- **Autonomy Goal**: Sizing $C_{\text{bat, nom}}$ (LiFePO4, $\text{DoD}_{\max} = 80\%$) such that $\text{LOLP} \le 0.01$ ($99\%$ lighting availability through December solstice).

---

### 3.3. Hydrology, Rainwater Harvesting & FAO-56 Evapotranspiration
The rainwater volume harvested per time step $\Delta t$ into the base reservoir is:

$$V_{\text{harvest}}(t) = P_{\text{rain}}(t) \cdot A_{\text{catch}} \cdot C_{\text{runoff}} \cdot \eta_{\text{filter}}$$

Where $A_{\text{catch}} = 3.14\text{ m}^2$, $C_{\text{runoff}} = 0.90$ (smooth sealed composite canopy), and $\eta_{\text{filter}} = 0.95$ (first-flush mesh diverter).

Plant water demand is driven by atmospheric evaporative demand using the **FAO-56 Penman-Monteith** formulation for reference evapotranspiration ($ET_0$, $\text{mm/day}$):

$$ET_0 = \frac{0.408 \Delta (R_n - G) + \gamma \frac{900}{T_{\text{mean}} + 273} u_2 (e_s - e_a)}{\Delta + \gamma (1 + 0.34 u_2)}$$

Daily crop water demand across the 4 tiers of vertical foliage is governed by species crop coefficients ($K_c$) and effective canopy cover ($A_{\text{canopy}}$):

$$V_{\text{irr, req}}(t) = ET_0(t) \cdot K_c(t) \cdot A_{\text{foliage}} \cdot \frac{1}{\eta_{\text{drip}}}$$

Where baseline annual water requirement averages $1.09\text{ L/day}$ ($0.2725\text{ L/day}$ per tier) in mild conditions, rising dynamically to $>2.8\text{ L/day}$ during midsummer heatwaves.

The reservoir water storage volume ($V_{\text{tank}}(t) \in [0, V_{\text{tank, max}}]$) obeys continuous mass balance:

$$V_{\text{tank}}(t + \Delta t) = \min\left( V_{\text{tank, max}}, \; \max\left(0, \; V_{\text{tank}}(t) + V_{\text{harvest}}(t) - V_{\text{irr, actual}}(t) - V_{\text{evap, tank}}(t)\right) \right)$$

If $V_{\text{tank}}(t) = 0$, plants enter **Drought Stress Index (DSI)**, tracking cumulative deficit days.

---

### 3.4. Dynamic Multi-Tier Hydraulic Head & Micro-Pump Power
The water level in the cylindrical base reservoir ($A_{\text{tank}} = 0.15\text{ m}^2$) is:

$$h_{\text{water}}(t) = \frac{V_{\text{tank}}(t) \cdot 10^{-3}}{A_{\text{tank}}} \quad [\text{m}]$$

For each vertical living tier $i \in \{1, 2, 3, 4\}$ located at elevation $z_i \in \{1.0, 2.0, 3.0, 4.0\}\text{ m}$:
1. **Static Geodetic Head**:
   $$H_{\text{static}, i}(t) = z_i - h_{\text{water}}(t) \quad [\text{m}]$$
2. **Dynamic Friction Head Loss** via Darcy-Weisbach:
   $$h_{f, i} = f \cdot \frac{L_i}{d_h} \cdot \frac{v^2}{2g} + \sum K_{\text{minor}} \frac{v^2}{2g} \quad [\text{m}]$$
3. **Total Dynamic Pumping Head**:
   $$H_{\text{total}, i}(t) = H_{\text{static}, i}(t) + h_{f, i} + H_{\text{emitter, req}} \quad [\text{m}]$$
4. **Electrical Micro-Pump Power Consumption**:
   $$P_{\text{pump}, i}(t) = \frac{\rho_{\text{water}} \cdot g \cdot H_{\text{total}, i}(t) \cdot Q_{\text{flow}, i}}{\eta_{\text{pump}}} \quad [\text{W}]$$

Where:
- $\rho = 1000\text{ kg/m}^3$, $g = 9.81\text{ m/s}^2$.
- $\eta_{\text{pump}} = 0.70$ (efficient $12\text{V}$ brushless DC micro-submersible pump).
- $Q_{\text{flow}} = 0.0009\text{ m}^3/\text{s}$ ($0.9\text{ L/s}$ pulsed manifold delivery over scheduled daily irrigation intervals).
- Pumping electrical energy totals $\approx 38.0\text{ kWh/yr}$ in the baseline operational profile.

---

### 3.5. Urban Ecosystem Services & Microclimate Co-benefits

1. **Localized Evaporative Cooling (Urban Heat Island Mitigation)**:
   Transpiration converts sensible urban heat into latent heat, providing passive environmental cooling:
   $$\dot{Q}_{\text{cool}}(t) = \dot{m}_{\text{transp}}(t) \cdot h_{fg}(T) \quad [\text{kW}_{\text{th}}]$$
   Where $h_{fg} \approx 2.45\times 10^6\text{ J/kg}$. At peak summer transpiration ($2.5\text{ L/day}$), each post delivers $\approx 1.7\text{ kWh}_{\text{th}}/\text{day}$ of localized cooling.

2. **Stormwater Retention & Peak Attenuation**:
   Fraction of precipitation captured and retained from urban runoff surfaces:
   $$\Phi_{\text{storm}} = \frac{\sum V_{\text{harvest}}}{\sum P_{\text{rain}} \cdot A_{\text{catch}}} \times 100\%$$

3. **Particulate Air Filtration ($PM_{2.5}$ and $PM_{10}$ Bio-deposition)**:
   Dry deposition flux to foliage surface area $A_{\text{leaf}} = \text{LAI} \cdot A_{\text{plan}}$:
   $$F_{PM}(t) = v_d \cdot C_{PM}(t) \cdot A_{\text{leaf}} \quad [\mu\text{g/h}]$$
   Where $v_d \approx 0.005\text{ m/s}$ is the deposition velocity for urban foliage.

4. **Avoided Operational Grid Carbon**:
   Displacing municipal high-pressure sodium ($150\text{ W}$) or standard grid-powered LED ($50\text{ W}$) fixtures:
   $$E_{\text{avoided}} = \sum_{t=1}^{8760} \left( P_{\text{baseline}}(t) \cdot \text{EF}_{\text{grid}}(t) \right) \quad [\text{kg CO}_2\text{e/yr}]$$

---

## 4. Techno-Economic & Physical Design Parameters

All parameters represent the validated engineering baseline established during the UNIBO incubator development:

### 4.1. Geometric & Structural Parameters
| Component / Parameter | Symbol | Nominal Value | Units | Description / Reference |
|---|---|---|---|---|
| **Total Post Height** | $H_{\text{post}}$ | 4.50 | $\text{m}$ | Vertical clearance for street/pathway lighting |
| **Canopy Outer Diameter** | $D_{\text{canopy}}$ | 2.00 | $\text{m}$ | Circular catchment canopy |
| **Catchment Plan Area** | $A_{\text{catch}}$ | 3.14 | $\text{m}^2$ | $\pi (D/2)^2$ projected catchment area |
| **Planter Column Tiers** | $N_{\text{tiers}}$ | 4 | — | Modular vertical growing levels |
| **Tier Heights** | $z_1, z_2, z_3, z_4$ | 1.0, 2.0, 3.0, 4.0 | $\text{m}$ | Vertical elevation above grade |
| **Reservoir Base Area** | $A_{\text{tank}}$ | 0.15 | $\text{m}^2$ | Cylindrical internal water column footprint |
| **Reservoir Total Capacity**| $V_{\text{tank, max}}$ | 150.0 | $\text{L}$ | Base water storage tank ($h_{\max} = 1.0\text{ m}$) |

### 4.2. Electrical & Photovoltaic Parameters
| Parameter | Symbol | Nominal Value | Units | Description / Standard |
|---|---|---|---|---|
| **PV Rated Efficiency** | $\eta_{\text{pv}}$ | 21.5 | $\%$ | High-efficiency monocrystalline solar cells |
| **PV Temperature Coeff** | $\gamma_{\text{temp}}$ | -0.38 | $\%/\text{K}$ | Power degradation above $25^\circ\text{C}$ cell temp |
| **MPPT & BOS Efficiency** | $\eta_{\text{BOS}}$ | 93.1 | $\%$ | Combined MPPT (98%) and cabling/soiling |
| **LED Luminaire Power** | $P_{\text{light}}$ | 47.1 | $\text{W}$ | High-CRI public luminaire (as per Excel BOM) |
| **Lighting Switch Threshold**| $\alpha_{\text{dusk}}$| -6.0 | $\text{deg}$ | Solar elevation civil twilight trigger |
| **Battery Chemistry** | — | LiFePO4 | — | Lithium Iron Phosphate ($>3,500$ cycle life) |
| **Nominal System Voltage**| $V_{\text{sys}}$ | 12.8 | $\text{V}$ | 4S LiFePO4 configuration |
| **Nominal Battery Capacity**| $C_{\text{bat}}$ | 1.28 | $\text{kWh}$ | $100\text{ Ah} @ 12.8\text{ V}$ baseline sizing |
| **Max Depth of Discharge** | $\text{DoD}_{\max}$ | 80.0 | $\%$ | $\text{SoC}_{\min} = 0.20$ reserve floor |
| **Round-Trip Efficiency** | $\eta_{\text{rt}}$ | 92.0 | $\%$ | Battery charge/discharge coulombic efficiency|

### 4.3. Hydrological & Hydraulic Parameters
| Parameter | Symbol | Nominal Value | Units | Description / Reference |
|---|---|---|---|---|
| **Canopy Runoff Coeff** | $C_{\text{runoff}}$ | 0.90 | — | Smooth composite drainage surface |
| **First-Flush Filter Eff** | $\eta_{\text{filter}}$ | 95.0 | $\%$ | Self-cleaning vortex mesh filter |
| **Baseline Water Demand** | $V_{\text{irr, base}}$| 1.09 | $\text{L/day}$ | Total post baseline ($0.2725\text{ L/tier/day}$) |
| **Summer Peak Demand** | $V_{\text{irr, peak}}$| 2.85 | $\text{L/day}$ | High vapor pressure deficit midsummer demand |
| **Irrigation Efficiency** | $\eta_{\text{drip}}$ | 90.0 | $\%$ | Pressure-compensating sub-surface drip |
| **DC Micro-Pump Type** | — | Brushless DC | — | Submersible $12\text{V}$ centrifugal micro-pump |
| **Pump Combined Eff** | $\eta_{\text{pump}}$ | 70.0 | $\%$ | Motor + impeller efficiency (as per Excel) |
| **Manifold Tubing ID** | $d_h$ | 8.0 | $\text{mm}$ | Food-grade PE internal distribution pipe |
| **Nominal Flow Rate** | $Q_{\text{pump}}$ | 0.90 | $\text{L/min}$ | Pulsed batch delivery ($0.000015\text{ m}^3/\text{s}$) |

---

## 5. Standard Repository Architecture

```
Plantpost-Urban-Infrastructure-Modelling/
├── GEMINI.md                                  ← This governance & technical specification file
├── README.md                                  ← 5-Stage Executive Showcase README
├── requirements.txt                           ← Minimal, pinned dependencies
├── .gitignore                                 ← Standard Python / Jupyter ignore rules
├── Plantpost reqs.xlsx                        ← Historical startup baseline spreadsheet
│
├── src/                                       ← Production Python calculation modules
│   ├── __init__.py
│   ├── config.py                              ← Post dimensions, electrical BOM, hydraulic & crop constants
│   ├── weather.py                             ← PVGIS/TMY hourly data ingestion & solar astronomy engine
│   ├── energy.py                              ← PV generation, LED load schedule & LiFePO4 battery SoC simulation
│   ├── hydrology.py                           ← FAO-56 Penman-Monteith, rainwater catchment mass balance & tank sizing
│   ├── hydraulics.py                          ← Multi-tier static head, pipe friction & DC micro-pump power engine
│   ├── ecosystem.py                           ← Evaporative cooling, stormwater attenuation, PM deposition & carbon
│   └── plotting.py                            ← Publication-grade visual generator (Extended 6-Figure Suite)
│
├── notebooks/                                 ← Interactive, documented showcase notebooks
│   ├── 01_weather_and_resource_ingestion.ipynb       ← Weather data pipeline, irradiance & astronomical twilight
│   ├── 02_solar_photovoltaics_and_battery_storage.ipynb ← PV output, LED schedules & battery autonomy optimization
│   ├── 03_hydrology_evapotranspiration_and_pumping.ipynb← Rainwater balance, FAO-56 ET & multi-tier hydraulic head
│   └── 04_integrated_ecosystem_services_and_multi_city.ipynb ← Full-year co-benefits & Bologna vs Edinburgh benchmark
│
├── data/                                      ← Transparent tabular input datasets
│   ├── weather_bologna_hourly.csv             ← Hourly TMY weather data (irradiance, temp, RH, rain)
│   ├── weather_edinburgh_hourly.csv           ← Northern maritime comparison weather dataset
│   ├── crop_coefficients_vertical_foliage.csv ← Monthly Kc and stomatal resistance for urban ivy/ferns
│   └── plantpost_reqs_baseline.csv            ← Clean CSV export of original Excel feasibility matrix
│
├── figures/                                   ← High-resolution exported figures (PNG & SVG)
│   ├── fig1_annual_resource_balance_water_energy.png (and .svg)
│   ├── fig2_dynamic_battery_soc_winter_stress.png   (and .svg)
│   ├── fig3_rainwater_tank_storage_drought_resilience.png (and .svg)
│   ├── fig4_hydraulic_vertical_head_pumping_dynamics.png (and .svg)
│   ├── fig5_urban_ecosystem_services_dashboard.png   (and .svg)
│   └── fig6_multi_city_climate_feasibility_frontier.png (and .svg)
│
└── main.py                                    ← CLI entry point to run full simulation & export figures
```

---

## 6. The Extended 6-Figure Publication Suite

Every generated plot must adhere to master publication standards: clean minimalist aesthetic (`seaborn-v0_8-whitegrid`), explicit physical units enclosed in brackets on all axes (e.g. `Solar Generation [kWh/month]`, `Battery State of Charge [%]`, `Tank Storage [L]`, `Head [m]`), high-contrast palettes, and exported at $300\text{ DPI}$ PNG and vector SVG.

1. **Figure 1 — Annual Dual-Resource Balance: Energy & Water (`fig1_annual_resource_balance_water_energy`)**:
   - 2-panel linked monthly overview directly validating and extending the Excel model:
     - Panel A (Energy): Monthly Solar PV Generation ($\text{kWh}$) vs. Total Demand (Lighting $200.8\text{ kWh/yr}$ + Pumping $38.0\text{ kWh/yr}$), highlighting winter deficit months (-$12.6\text{ kWh}$ in Dec) and summer surplus months (+$12.3\text{ kWh}$ in July).
     - Panel B (Water): Monthly Rainwater Inflow ($\text{L}$) vs. Dynamic Crop Irrigation Demand ($\text{L}$), identifying seasonal water surplus and summer drawdown periods.
2. **Figure 2 — Hourly Battery State of Charge & Winter Solstice Stress Test (`fig2_dynamic_battery_soc_winter_stress`)**:
   - Detailed time-series across the critical December/January period:
     - Top track: Hourly solar irradiance $G_{\text{tilt}}$ and load pulse ($47.1\text{ W}$ LED).
     - Bottom track: Dynamic Battery $\text{SoC}(t)$ for three capacity sizings ($0.8\text{ kWh}$, $1.28\text{ kWh}$, $2.0\text{ kWh}$), demonstrating the exact threshold where $\text{LOLP} \le 1\%$ is achieved without blackouts.
3. **Figure 3 — Rainwater Reservoir Storage & Drought Resilience (`fig3_rainwater_tank_storage_drought_resilience`)**:
   - Full 8760-hour continuous reservoir storage curve:
     - Water volume ($V_{\text{tank}}$ in Liters) tracked against precipitation storm pulses and FAO-56 crop evapotranspiration withdrawals.
     - Highlights tank overflow losses during heavy autumn downpours and proves zero-drought-stress survival through a 28-day Mediterranean summer drought.
4. **Figure 4 — Multi-Tier Hydraulic Head & Micro-Pump Power Dynamics (`fig4_hydraulic_vertical_head_pumping_dynamics`)**:
   - Technical hydraulic performance chart:
     - Left axis: Total dynamic head ($H_{\text{total}}$ in meters) to Tiers 1 through 4 as base reservoir water level fluctuates between empty ($0\text{ m}$) and full ($1.0\text{ m}$).
     - Right axis: Instantaneous pump electrical power ($P_{\text{pump}}$ in Watts) and daily energy consumption ($\text{Wh/day}$) across irrigation schedules.
5. **Figure 5 — Urban Ecosystem Services & Microclimate Co-Benefits Dashboard (`fig5_urban_ecosystem_services_dashboard`)**:
   - 4-quadrant executive scorecard visualising quantified urban environmental impact:
     - Quadrant A: Daily sensible evaporative cooling power ($\text{kW}_{\text{th}}$) mitigating the Urban Heat Island.
     - Quadrant B: Stormwater runoff volume attenuated and diverted from municipal storm drains ($\text{L/yr}$ and $\%$).
     - Quadrant C: Annual particulate matter bio-filtration ($g\text{ PM}_{2.5}$ and $g\text{ PM}_{10}$ intercepted).
     - Quadrant D: Net avoided grid operational carbon ($\text{kg CO}_2\text{e/yr}$) relative to conventional street lights.
6. **Figure 6 — Multi-City Climate Feasibility & Storage Frontier (`fig6_multi_city_climate_feasibility_frontier`)**:
   - Comparative engineering feasibility plot contrasting **Bologna (Mediterranean)** vs. **Edinburgh (Northern Maritime)** vs. **London (Temperate)**:
     - Compares annual solar yield, required battery capacity for $99\%$ winter autonomy, annual rainfall harvested, and irrigation deficit risk.
     - Identifies the geographical boundary envelope for off-grid infrastructure commercialisation.

> **Portfolio Bridge Rule**: The two top hero figures (`fig1_annual_resource_balance_water_energy.png` and `fig2_dynamic_battery_soc_winter_stress.png`) must be synced to `/home/fraser/Life/Career/Job-Applications/Portfolio/figures/` upon execution.

---

## 7. Developer & Agent Operational Instructions

### 7.1. Python Environment & Dependencies
- Maintain an isolated virtual environment with pinned numerical and scientific dependencies:
  ```bash
  cd /home/fraser/Code/Portfolio/Plantpost-Urban-Infrastructure-Modelling
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  ```
- Core libraries: `pandas >= 2.0.0`, `numpy >= 1.24.0`, `scipy >= 1.10.0`, `matplotlib >= 3.7.0`, `seaborn >= 0.12.0`, `openpyxl >= 3.1.0`.

### 7.2. CLI Execution Commands
- Execute the complete baseline environmental simulation and export all publication figures:
  ```bash
  python main.py --run-all --export-figures
  ```
- Run the battery storage and tank capacity parametric optimization sweeps:
  ```bash
  python main.py --optimize-storage --evaluate-drought
  ```
- Execute the multi-city climate comparison (Bologna vs. Edinburgh vs. London):
  ```bash
  python main.py --multi-city-benchmark
  ```
- Synchronize hero figures to Fraser's master job application collateral:
  ```bash
  python main.py --sync-collateral
  ```

### 7.3. Standards Compliance & Verification Rules
- **Physical Consistency with Spreadsheet**:
  - The monthly aggregated results of the dynamic hourly model must match the original spreadsheet totals within $\pm 5\%$ under equivalent boundary conditions ($258\text{ kWh/yr}$ PV, $200.8\text{ kWh/yr}$ lighting, $38.0\text{ kWh/yr}$ pumping, $2,612\text{ L/yr}$ rainfall collected).
- **Truth-in-Advertising & Attribution**:
  - Maintain absolute alignment with `/home/fraser/Life/Career/Job-Applications/Portfolio/SOURCES.md`:
    - Credit Fraser as Co-Founder and Head of Environmental Modelling.
    - Accurately cite the **UNIBO $\times$ Bugnion Intellectual Property Prize** (€2,500 patenting services awarded at UNIBO Startup Day).
    - Transparently distinguish between the initial feasibility spreadsheet calculations and the high-fidelity dynamic hourly model.

