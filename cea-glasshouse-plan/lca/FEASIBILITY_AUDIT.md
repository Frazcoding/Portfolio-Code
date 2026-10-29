# Feasibility Audit & Target KPI Specification: Scottish Greenhouse Decarbonisation

**Project Scope:** Controlled Environment Agriculture (CEA) Glasshouse & Industrial Heat Pump System  
**Baseline Reference Site:** Carse of Gowrie, Perthshire ($56.42^\circ\text{N}, 3.20^\circ\text{W}$)  
**Anchor Engineering:** Dynamic Venlo/PC Glasshouse, Two-Stage Ammonia ($\text{R717}$) Heat Pump / Water-Source Heat Pump, Stratified Buffer Thermal Storage, Grid/Wind/Waste Heat Integration  
**Date of Audit:** October 2026

---

## Executive Summary: The Feasibility Scorecard

The current engineering simulation establishes that a high-efficiency Scottish glasshouse powered by a two-stage heat pump **decisively wins on carbon** against imported fresh produce landed at Central Scotland Regional Distribution Centres (RDCs), slashing cradle-to-gate emissions by **60% to 75%** for major vine crops. 

However, the **fully off-grid dedicated wind baseline fails on delivered cost** because sizing islanded wind turbines, battery storage, and seasonal thermal buffers to guarantee 99.5%+ autonomy incurs severe turbine curtailment ($38\%\text{--}44\%$) and high levelised electricity costs ($38.4\text{p to } 49.0\text{p / kWh}$).

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               THE MASTER TARGET MATRIX                                 │
├────────────────────────────┬─────────────────────────────┬─────────────────────────────┤
│ Metric Category            │ Current Simulation Baseline │ Target Threshold for Market │
├────────────────────────────┼─────────────────────────────┼─────────────────────────────┤
│ Electricity Supply Price   │ 38.4p – 49.0p/kWh (Offgrid) │ ≤ 10.7p/kWh (vs Import CIF) │
│                            │                             │ ≤ 19.6p/kWh (vs UK Whlesale)│
│ Heat Pump Seasonal COP     │ 3.15 – 3.27 (Air Source)    │ ≥ 3.50 (Optimised Air/Recov)│
│                            │ 3.53 – 3.80 (Ground Source) │ ≥ 4.50 (Effluent / Water)   │
│ Levelised Cost of Heat     │ £224.8 / MWh_th (Offgrid)   │ ≤ £65 – £75 / MWh_th (Air)  │
│ (LCOH)                     │ £127.9 / MWh_th (17.3p Grid)│ ≤ £10 – £25 / MWh_th (Waste)│
│ Glasshouse Structure CAPEX │ £200 / m² (£2.0M / ha)      │ ≤ £180 – £200 / m²          │
│ Heat Pump Skid CAPEX       │ £990 / kW (Skid + Evap)     │ ≤ £600 – £750 / kW          │
│ Tomato Yield (Perthshire)  │ 35.9 kg/m² (Light-penalised)│ ≥ 39.5 – 42.0 kg/m²         │
│ Cucumber Yield (Perthshire)│ 48.6 kg/m²                  │ ≥ 46.0 – 50.0 kg/m²         │
│ Offtake Realised Price     │ £1.60/kg (Tomato Import CIF)│ ≥ £1.85/kg (Wholesale floor)│
│                            │ £1.40/kg (Cuc. Import CIF)  │ ≥ £2.10/kg (Retail Contract)│
│ 20-Year Project IRR        │ -99% (Negative EBITDA)      │ ≥ 12.0% (Unlevered)         │
│ Simple Capital Payback     │ Infinite (Cash negative)    │ ≤ 7.0 – 7.5 Years           │
└────────────────────────────┴─────────────────────────────┴─────────────────────────────┘
```

---

## 1. Energy & Tariff Thresholds: What Electricity & Heat Prices Make It Work?

```
Delivered Tomato Production Cost (£/kg) vs. Electricity Price (p/kWh)
 4.00 ┼
      │                                                ● Off-grid Base (49p, £2.16)
 3.00 ┼                                      ● Off-grid Ridge (38.4p, £2.01)
      │
 2.10 ┼────────────────────────────────────── Supermarket Contract Threshold (£2.10)
      │                            ● Grid (17.3p, £1.69) 
 1.85 ┼─────────────────────────── UK Wholesale Average (£1.85)
 1.60 ┼──────────────● Import CIF (£1.60) [Breakeven: 10.7p/kWh]
      │   ● Utility PPA (10p, £1.59)
 1.00 ┼
      │
 0.00 ┼───────┬───────┬───────┬───────┬───────┬───────┬───────┬───────┬
      0       10      20      30      40      50      60      70      80
                           Delivered Electricity Price (p/kWh)
```

### 1.1 Breakeven Electricity Price ($p_e^*$) by Crop
Delivered cost per kg is formulated as:
$$\text{Cost} = \text{Non-Electric OPEX \& CAPEX} + (\text{Specific Electricity Consumption} \times p_e)$$

Auditing the Perthshire Carse of Gowrie run yields the exact breakeven electricity price required to beat both foreign import CIF (border price) and domestic UK DEFRA wholesale prices:

| Crop | Specific Elec ($kWh_e/kg$) | Non-Electric Cost (£/kg) | Import CIF (£/kg) | Breakeven $p_e^*$ vs CIF | DEFRA Wholesale (£/kg) | Breakeven $p_e^*$ vs Wholesale |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Cucumber** | **1.80** | **£1.05** | £1.40 | **19.6 p/kWh** | £1.65 | **33.3 p/kWh** |
| **Tomato** | **1.47** | **£1.44** | £1.60 | **10.7 p/kWh** | £1.85 | **27.9 p/kWh** |
| **Aubergine**| **1.77** | **£1.44** | £1.55 | **6.5 p/kWh** | £1.75 | **17.5 p/kWh** |
| **Sweet Pepper**| **3.35** | **£2.42** | £2.04 | *Negative* | £2.80 | **11.3 p/kWh** |
| **Strawberry**| **2.67** | **£5.55** | £4.61 | *Negative* | £6.00 | **16.8 p/kWh** |
| **Lettuce** | **1.90** | **£2.45** | £1.45 | *Negative* | £2.50 | **2.6 p/kWh** |

> [!IMPORTANT]
> **Key Finding on Electricity:**
> - **Cucumber** is viable in Scotland today on standard industrial grid tariffs ($17.3\text{p/kWh}$), beating import CIF by £0.04/kg.
> - **Tomato** beats import CIF at $\le 10.7\text{p/kWh}$ (utility wind PPA or private wire) and beats UK wholesale at any price below $27.9\text{p/kWh}$.
> - Sizing an islanded off-grid power system creates artificial economic failure; **grid-tethering + behind-the-meter PPA is an absolute feasibility prerequisite.**

### 1.2 Waste Heat Tariff Thresholds ($p_{\text{heat}}^*$)
When co-locating with a Scotch whisky distillery (e.g., spent wash / pot ale cooling at $70\text{--}80^\circ\text{C}$) or wastewater treatment plant ($12^\circ\text{C}$ effluent via WSHP):
- **Direct Distillery Waste Heat:** Avoids the heat pump entirely. Heat exchanger + circulation pump costs $\approx £0.97\text{ / MWh}_{\text{th}}$ ($0.1\text{ p/kWh}$). Maximum commercial purchase price to maintain a 50% discount to biomass: **$\le £25.00\text{ / MWh}_{\text{th}}$** ($2.5\text{ p/kWh}_{\text{th}}$).
- **Wastewater Effluent Heat (Scottish Water Horizons):** Elevates heat pump $\text{SCOP}$ from $3.27 \to 4.50$. Electricity demand drops from $52.4 \to 37.5\text{ kWh/m}^2$. Maximum concession fee to Scottish Water: **$\le £5.00\text{ / MWh}_{\text{th}}$ abstracted**.

---

## 2. Thermodynamic & Plant Engineering Thresholds

```
                      HEAT SOURCE & CYCLE SELECTION MATRIX
       SCOP
        6.0 ┼──────────────────────────────────────────────────────────
            │                                     ● Distillery Effluent /
        5.0 ┼───────────────────                  Wastewater WSHP (4.5–5.2)
            │                   ● Closed GSHP
        4.0 ┼                   Boreholes (3.8)
            │  ● Ambient Air
        3.0 ┼  (3.1–3.3)
            │
        0.0 ┼───────────────────┬─────────────────┬────────────────────
               Air Source          Borehole Field    Industrial Effluent
```

### 2.1 Seasonal Performance Factor Targets
- **Air-Source Baseline:** Current simulated SCOP is **3.27** (Tomato) and **3.15** (Cucumber).
  - *Target Threshold:* **$\text{SCOP} \ge 3.50$**.
  - *Engineering Levers:* Low-temperature weather-compensated heating curves ($40\text{--}45^\circ\text{C}$ max flow), subcooling loop utilization for root-zone bench warming, and two-stage flash economiser optimization.
- **Water/Effluent Source:**
  - *Target Threshold:* **$\text{SCOP} \ge 4.50$**. Eliminates winter air-cooler reverse-cycle defrost parasitic loads.
- **Auxiliary Fan Power Ceiling:**
  - Current auxiliary fan consumption is $11.1\text{ kWh/m}^2/\text{yr}$ (larger than the compressor power for frost-protected crops).
  - *Target Threshold:* **$\le 4.0\text{ kWh/m}^2/\text{yr}$** using variable-speed EC fans interlocked with solar gain and humidity deficit thresholds.

### 2.2 Heat Pump Skid Sizing vs. Thermal Storage Peak-Shaving
- **Current Approach:** Sized for 100% of peak heat loss at $-4^\circ\text{C}$ ($120\text{ W/m}^2$, or $1,200\text{ kW/ha}$).
- **Target Commercial Approach:** 
  - Size heat pump skid at **$65\%\text{--}75\%$ of design peak** ($80\text{ W/m}^2$, or $800\text{ kW/ha}$).
  - Utilize the stratified hot water buffer ($40\text{--}60\text{ m}^3/\text{ha}$) to shave the top 25% peak load during extreme cold snaps.
  - *CAPEX Impact:* Cuts heat pump skid capital cost from **£1.40M/ha down to £0.94M/ha** (saving £460,000/ha).

### 2.3 Glazing & Thermal Envelope
- **Twin-wall Polycarbonate (PC):**
  - Thermal loss: $U \approx 2.8\text{--}3.1\text{ W/m}^2\text{K}$. Light transmission: $\tau \approx 72\%$.
  - Saves 45% annual heat demand compared to single glass, but incurs a 10% yield reduction.
- **Diffuse Double Glass with Anti-Reflective (AR) Coating (The Optimal Target):**
  - Thermal loss: $U \approx 1.8\text{--}2.0\text{ W/m}^2\text{K}$. Light transmission: $\tau \ge 81\%$.
  - *Target Threshold:* Provides the low heat loss of PC while recovering the 10% light penalty, lifting Perthshire tomato yield from $35.9 \to 41.5\text{ kg/m}^2$.

---

## 3. Capital Expenditure (CAPEX) & Asset Ceilings

To deliver an institutional Project IRR $\ge 12.0\%$, upfront capital cannot exceed strict benchmarks:

```
                            CAPEX BUDGET BREAKDOWN (1 HECTARE)
                 ┌────────────────────────────────────────────────────────┐
                 │ Total Turnkey Capital Ceiling: £2.80M – £3.10M / ha    │
                 └───────────────────────────┬────────────────────────────┘
                                             │
      ┌──────────────────────────────┬───────┴──────────────────────┬────────────────────────────┐
      ▼                              ▼                              ▼                            ▼
┌──────────────┐              ┌──────────────┐              ┌──────────────┐              ┌──────────────┐
│ Glasshouse   │              │ Energy Plant │              │ Thermal Store│              │ Civil/Elec   │
│ Structure    │              │ (R717 Skid)  │              │ (Stratified) │              │ Connection   │
├──────────────┤              ├──────────────┤              ├──────────────┤              ├──────────────┤
│ £180–£200/m² │              │ £650–£800/kW │              │ £80–£120/m³  │              │ £150k–£250k  │
│ (£1.8–£2.0M) │              │ (£650k–£800k)│              │ (£100k–£150k)│              │ Private Wire │
└──────────────┘              └──────────────┘              └──────────────┘              └──────────────┘
```

### 3.1 Itemised Cost Benchmarks
1. **Glasshouse Structure & Internal Fit-out:**
   - *Anchor:* SAC/SRUC Table 11 commercial Venlo glasshouse = **£200.00 / m²** (£2.0M / ha).
   - *Target Ceiling:* **$\le £190.00 / \text{m}^2$** for a 2-hectare+ block (scale economies reduce perimeter foundation and gable wall costs by 12%).
2. **Industrial Heat Pump Skid:**
   - *Current Baseline:* £850/kW skid + £140/kW air coil = **£990 / kW**.
   - *Target Ceiling:* **$\le £700 / \text{kW}$** fully installed. Achievable via packaged commercial ammonia chillers/heat pumps (e.g., Sabroe/Johnson Controls or GEA standard modular skids rather than bespoke field engineering).
3. **Borehole Drilling (The Fatal Flaw of GSHP):**
   - Deep boreholes at £75/m require 34 km of drilling per hectare = **£300 / m²** (£3.0M/ha).
   - *Hurdle Verdict:* **Closed-loop borehole GSHP is disqualified from commercial feasibility.** Capital recovery adds £0.24–£0.30/kg to crop costs. Water-source or air-source must be used.

---

## 4. Agronomic Yield Thresholds at Scottish Latitudes

Scottish solar radiation at the Carse of Gowrie is $79.4\%$ of Westland (Netherlands), resulting in an unlit yield discount of $16.9\%$ (yield light factor $0.831$).

### 4.1 Minimum Break-even Yields ($Y^*$)
The table below specifies the yield required per hectare to cover capital amortization and fixed operational expenses (labour, maintenance, packaging, seeds/fertilisers):

```
                       CROP YIELD GAP: CURRENT VS. BREAKEVEN
       kg/m²
        60 ┼                                      Current Simulation Yield
           │                                 ░░░░ Breakeven Yield @ 10p PPA
        50 ┼                   50.9
           │              48.6 ░░░░
        40 ┼         42.0
           │    35.9 ░░░░
        30 ┼
           │
        20 ┼                             31.3
           │                        19.8 ░░░░
        10 ┼
           │
         0 ┼─────────┬────────────────────┬────────────────────┬────────
                  Tomato               Cucumber             Sweet Pepper
```

| Crop | Perthshire Unlit Yield ($kg/m^2$) | Break-even Yield @ 17.3p Grid ($kg/m^2$) | Break-even Yield @ 10p PPA ($kg/m^2$) | Yield Delta Needed |
| :--- | :---: | :---: | :---: | :---: |
| **Cucumber** | **48.6** | 50.9 | **45.9** | **SURPLUS (+5.6%)** |
| **Tomato** | **35.9** | 42.0 | **39.4** | **-9.6%** |
| **Aubergine**| **36.6** | 45.5 | **42.1** | **-15.1%** |
| **Sweet Pepper**| **19.8** | 31.3 | **28.8** | **-45.7%** |
| **Strawberry**| **8.3** | 12.2 | **11.8** | **-41.5%** |
| **Lettuce** | **15.0** | 30.9 | **29.4** | **-96.2%** |

> [!TIP]
> **Agronomic Viability Verdict:**
> - **Tomato ($35.9 \to 39.4\text{ kg/m}^2$):** Bridging this 9.6% gap is readily achievable without artificial lighting by injecting biogenic $\text{CO}_2$ ($800\text{--}1,000\text{ ppm}$) from local distillery fermentation and utilizing high-haze diffuse double glass.
> - **Strawberry ($8.3 \to 11.8\text{ kg/m}^2$):** Unheated soil beds yield 8.3 kg/m². Commercial Scottish strawberry growers (e.g., Angus Soft Fruits) utilizing tabletop raised gutters, everbearing varieties, and heat-pump frost protection routinely achieve **$12.0\text{--}15.0\text{ kg/m}^2$**, transforming strawberries into an exceptionally profitable Scottish crop.
> - **Berries / Orchards (Raspberry, Blueberry, Grape, Avocado):** Permanently fail broad-acre heated glasshouse economics. Their low yields ($0.8\text{--}2.2\text{ kg/m}^2$) cannot absorb £2.0M/ha civil capital costs.

---

## 5. Commercial Offtake & Pricing Realities

Evaluating a domestic production facility against **Import CIF** (border cargo value) is an artificially harsh benchmark. Import CIF excludes UK port inspection fees, inland refrigerated transport from Dover/Hull to Central Scotland (+£0.06/kg), importer overhead, and supermarket packhouse margins.

```
                           PRICE CASCADE: TOMATO (PER KG)
 £7.00 ┼
       │                                                      ● Supermarket Retail
 £5.00 ┼                                                        Shelf (£5.00–£7.00)
       │
 £3.00 ┼
       │                              ● Supermarket 10-Yr Supply
 £2.00 ┼           ● DEFRA Wholesale    Contract (£2.10)
       │  ● Import   Average (£1.85)
 £1.00 ┼    CIF (£1.60)
       │
 £0.00 ┼───────┬──────────────┬──────────────────┬───────────────────────┬
           Border         Wholesale          Contract                 Retail
```

### 5.1 Real Market Realization Thresholds
1. **Import CIF (Base Floor):** £1.60/kg (Tomato), £1.40/kg (Cucumber).
2. **DEFRA UK Wholesale Average (2024–2026):**
   - Round Tomatoes: £1.55/kg; Vine/Truss Tomatoes: **£1.73 – £2.08/kg**; Cherry Tomatoes: **£2.12 – £2.56/kg**.
   - Cucumbers: **£1.05 – £1.28/kg**.
   - Strawberries: **£4.10 – £6.00/kg**.
3. **Supermarket 10-Year Supply Agreement (The Bankable Target):**
   - Sainsbury’s 10-year agreements (Thanet Earth / Evesham Vale Growers precedent) index price to input costs.
   - Adding a **15% Scottish Provenance / Scope 3 Decarbonisation Premium** sets bankable offtake contracts at:
     - **Truss Tomatoes: £2.10 / kg**
     - **Cucumbers: £1.65 / kg**
     - **Tabletop Strawberries: £6.50 / kg**

---

## 6. Financial Architecture & Hurdle Rates (1-Hectare Commercial Model)

The table below contrasts 5 commercial architectures for a 1-hectare glasshouse in Perthshire:

| Financial Metric | Model A: Air HP + Offgrid Wind (Current) | Model B1: Air HP + PPA @ Import CIF | Model B2: Air HP + PPA @ Wholesale | Model B3: Air HP + PPA @ Retail Contract | Model C: Distillery Waste Heat + PPA |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Electricity Price** | 49.0 p/kWh | 10.0 p/kWh | 10.0 p/kWh | 10.0 p/kWh | 10.0 p/kWh |
| **Offtake Price Realised** | £1.60 / kg | £1.60 / kg | £1.85 / kg | **£2.10 / kg** | **£2.10 / kg** |
| **Total CAPEX** | **£3.40 M** | **£3.13 M** | **£3.13 M** | **£3.13 M** | **£2.35 M** |
| Annual Revenue | £574 k | £608 k | £703 k | £840 k | £882 k |
| Annual Energy OPEX | £307 k | £61 k | £61 k | £61 k | £22 k |
| Fixed OPEX (Labour/O&M/Pack) | £309 k | £327 k | £327 k | £344 k | £361 k |
| **Annual EBITDA** | **-£41 k** | **+£220 k** | **+£315 k** | **+£435 k** | **+£499 k** |
| **EBITDA Margin** | *-7.2%* | *36.3%* | *44.9%* | **51.8%** | **56.5%** |
| **Simple Capital Payback** | **Infinite** | **14.2 Years** | **9.9 Years** | **7.2 Years** | **4.7 Years** |
| **20-Year Project IRR** | **Negative** | **3.5%** | **7.8%** | **12.6%** | **20.6%** |
| **Net Present Value (NPV @ 8%)**| **-£3.81 M** | **-£0.97 M** | **-£0.04 M** | **+£1.14 M** | **+£2.54 M** |
| **Institutional Bankability** | **FAIL** | **Sub-commercial** | **Patient/SNIB** | **BANKABLE (Green Debt)**| **PREMIUM (Top Decile)** |

```
                       CUMULATIVE CASH FLOW OVER 20 YEARS
       £M
       +8 ┼                                                     ● Model C (Distillery)
          │                                              ● Model B3 (PPA Contract)
       +4 ┼
          │                                  ● Model B2 (Wholesale)
        0 ┼───────────────────────────────────────────────────────────
          │                 ● Model B1 (CIF)
       -4 ┼
          │  ● Model A (Off-grid)
       -8 ┼───┬───────┬───────┬───────┬───────┬───────┬───────┬───────┬
          0   2       4       6       8      10      12      14      20
                                      Years
```

---

## 7. The Five Non-Negotiable Strategic Pivots

To transition this project from an academic simulation into an investable commercial reality in Scotland, execute these five strategic pivots:

1. **Abandon the Islanded Off-Grid Model:**
   - Eliminate dedicated micro-wind turbines and massive battery banks. Sizing generation for 100% winter autonomy destroys economics via 40% curtailment.
   - **Pivot to:** A grid-connected behind-the-meter PPA (8.0–10.5 p/kWh) or dynamic tariff import with local constraint spill-wind contracts.
2. **Anchor Adjacent to a Waste Heat Source (Distillery or WWTP):**
   - Co-locating next to a Scotch whisky distillery cuts capital expenditure by £780,000/ha, reduces energy operating expenses by 65%, and boosts Project IRR to **20.6%**.
   - Solves the biogenic $\text{CO}_2$ dosing challenge without fossil fuel combustion.
3. **Adopt Bivalent Heat Pump & Thermal Buffer Sizing:**
   - Downsize the heat pump from 120 W/m² (100% design) to 80 W/m² (70% bivalent). Use the stratified buffer tank to shave the peak cold snaps, saving ~£300,000/ha in skid costs.
4. **Target High-Margin Crops with Tabletop Gutters:**
   - Focus exclusively on **Cucumbers, Vine/Truss Tomatoes, and Tabletop Everbearing Strawberries**.
   - Discontinue modelling tree crops (Avocado) or field berries in soil beds under glass.
5. **Contract with Supermarket Producer Organisations (POs):**
   - Structure 5- to 10-year floor-and-ceiling supply contracts with Angus Soft Fruits or East of Scotland Growers (ESG) at £1.85–£2.10/kg rather than selling into spot wholesale or matching bare CIF import prices.

---

## 8. Sourced and Verified Evidence Register (Data Provenance & Traceability)

Every numerical parameter, cost rate, environmental factor, and policy citation across this audit is catalogued below with its primary source, confidence level, and verification method.

### 8.1 Primary Datasets & Official Publications
| Parameter / Domain | Value / Formulation | Confidence | Primary Source & Citation | Verification Method in Repo |
| :--- | :--- | :---: | :--- | :--- |
| **Grid Electricity Carbon Intensity** | 0.2454 kg $\text{CO}_2\text{e/kWh}$ (incl. generation, T&D, WTT) | **[Sourced]** | DESNZ (2025) *Greenhouse gas reporting: conversion factors 2025* (UK electricity generation 0.17700 + T&D 0.01853 + WTT generation 0.04590 + WTT T&D 0.00397). | Verified in `breakeven.py` lines 24–26; matches official DESNZ spreadsheet. |
| **Onshore Wind Lifecycle Carbon** | 0.0110 kg $\text{CO}_2\text{e/kWh}$ (11 g/kWh) | **[Sourced]** | IPCC AR5 WGIII Annex III (2014) Table A.III.2 (Lifecycle GHG emissions of renewable energy technologies, median). | Verified in `breakeven.py` line 28; `energy_grid.py` line 26. |
| **Industrial Electricity Price Baseline** | 17.30 p/kWh (16.5p + 0.801p CCL) | **[Sourced]** | DESNZ *Quarterly Energy Prices* (Dec 2025), Table 3.4.1 (Manufacturing industry average Q3 2025) + HMRC Climate Change Levy main rate for electricity (from 1 April 2026: 0.801 p/kWh). | Verified in `breakeven.py` lines 34–36; `config.py`. |
| **Export Tariff (Smart Export Guarantee)** | 5.50 p/kWh | **[Sourced]** | SAC/SRUC (Jan 2026) *Developing SME-scale Controlled Environment Agriculture in the Highlands & Islands*, Table 17. | Verified in `energy_grid.py` line 25. |
| **Commercial Glasshouse Turnkey CAPEX** | £200.00 / m² (£2.0M / ha) | **[Sourced]** | SAC/SRUC (Jan 2026) *Developing SME-scale CEA*, Table 11 ("Commercial Venlo glasshouse, fully equipped with screens, irrigation, climate control"). | Verified in `costing.py` line 21 (`SAC_COMMERCIAL_GBP_M2 = 200.0`); `data/rates.csv`. |
| **Medium Wind Turbine CAPEX (250 kW)** | £2,500 / kW (£550k–£700k installed) | **[Sourced]** | SAC/SRUC (Jan 2026) Table 17 (250 kW wind turbine on 40–45 m tower, turnkey installation). | Verified in `energy_grid.py` line 24; `offgrid.py` line 21. |
| **Utility-Scale Wind Turbine CAPEX** | £1,400 / kW | **[Sourced]** | Arup (2024) for DESNZ *Electricity Generation Costs 2024*, Onshore Wind Reference Case. | Verified in `SCOPE.md` §3.13; `energy_systems.py`. |
| **Battery Energy Storage CAPEX** | £400 / kWh | **[Sourced]** | DESNZ (2024) *Energy Storage Cost Benchmarks* (2-hour lithium-ion utility battery). | Verified in `offgrid.py` line 22; `SCOPE.md` §2. |
| **Import Trade Volumes & CIF Prices** | HS 070200 (Tomato: £1.60/kg), HS 070700 (Cucumber: £1.40/kg) | **[Sourced]** | UN Comtrade Database (UK imports by origin, 2023–2025 volume-weighted CIF average; ECB annual USD/EUR to GBP FX rates). | Verified in `data/imports_trade.csv`; script `fetch_imports_data.py`. |
| **UK Domestic Wholesale Prices** | Tomatoes: £1.55–£2.12/kg, Cucumbers: £1.05–£1.28/kg, Berries: £4.10–£9.12/kg | **[Sourced]** | DEFRA *Wholesale Fruit and Vegetable Prices in England and Wales* (Official weekly series, 2024–2026). | Verified in `data/defra_wholesale_prices.csv` (17,704 weekly price observations). |
| **Dutch Benchmark Yields** | Tomato: 48 kg/m², Cucumber: 65 kg/m², Pepper: 28 kg/m² | **[Sourced]** | CBS Netherlands (Centraal Bureau voor de Statistiek), StatLine Table 37738 *Groenteteelt; oogst en teeltoppervlakte per groentesoort*, 2022–2024 sector mean. | Verified in `crops.py` line 23; `data/crops.csv`. |
| **Light–Yield Elasticity** | 0.80 % yield per 1.0 % PAR light | **[Sourced]** | Marcelis, L.F.M., et al. (2006), *Quantification of the effect of light quantity on crop yield in greenhouse horticulture*, Acta Horticulturae 711: 351–360. | Verified in `perthshire_results.py` line 6; `SCOPE.md` §3.15. |
| **Scottish Solar Radiation & Climate** | 3,495 MJ/m²/yr GHI at Carse of Gowrie ($79.4\%$ of Westland 4,402 MJ/m²) | **[Sourced]** | ECMWF ERA5 Reanalysis (2023 hourly surface radiation, ambient temperature, humidity at $56.42^\circ\text{N}, 3.20^\circ\text{W}$). | Verified via `simcore/weather.py` cache; Open-Meteo ERA5 API. |
| **Scottish Waste Heat Resource** | Distilleries ($70\text{--}80^\circ\text{C}$), WWTPs ($12.3^\circ\text{C}$ effluent, 0.66 kWh/m³) | **[Sourced]** | BRE (2020) for ClimateXChange, *Potential sources of waste heat for heat networks in Scotland*, University of Edinburgh, doi:10.7488/era/730. | Verified in `siting.py` lines 4–15; `data/siting/distilleries_wikipedia.json`. |
| **Refrigerated Transport Freight Carbon** | Reefer HGV: 0.169 kg $\text{CO}_2\text{e/t-km}$; Ship: 0.016 kg/t-km (incl WTT) | **[Sourced]** | DESNZ (2025) *Conversion Factors: Freight Transport*, refrigerated articulated HGV >33t, average laden. | Verified in `data/freight_factors.csv`; `imports.py`. |
| **Central Scotland Haulage Uplift** | Port leg: +460 km; Road leg from Channel: +500 km | **[Sourced]** | Road distance measured from Port of Dover / London Gateway to Central Belt RDC hub (Eurocentral, ML1 4YF) via Highways England / Transport Scotland network. | Verified in `perthshire_results.py` line 28 (`EXTRA_KM`). |
| **Financial Discount Rate** | 3.50 % real (Social/Green Book), 8.0 % commercial | **[Sourced]** | HM Treasury *Green Book* (2022) standard real discount rate (3.5%); commercial infrastructure equity hurdle (8.0%). | Verified in `breakeven.py` line 21; `audit_financials.py`. |

---

### 8.2 Engineering Performance & Simulation Parameters
| Parameter | Value | Confidence | Origin & Engineering Derivation |
| :--- | :---: | :---: | :--- |
| **Two-Stage R717 Heat Pump COP** | 3.27 air source, 3.80 ground source | **[Derived]** | Thermodynamic simulation in `greenhouse.py` coupled to CoolProp R717 cycle model (open intercooler, reciprocating compressor map, variable frequency drive, weather-compensated supply curve). |
| **Annual Heat Demand (Perthshire)** | 169.0 kWh/m² (Tomato, PC cover) | **[Derived]** | Dynamic multi-node greenhouse thermal model in `greenhouse_fast.py` (Numba-compiled hourly balance of solar gain, cover conduction, ventilation, crop transpiration, energy screen, and floor storage). |
| **Unmet Indoor Setpoint Hours** | 0 – 14 hours / year | **[Derived]** | Verified across all simulated 8,760 hours; indoor air held within $\pm 0.5^\circ\text{C}$ of setpoint calendar. |
| **Heat Pump Skid Turnkey Cost** | £990 / kW design heat loss | **[Estimated]** | £850/kW open-flash R717 skid + £140/kW outdoor air coil + 18% installation factor (`CALCULATIONS_WHITE_PAPER.md` §6.1). Cross-checked with Danish Energy Agency (DEA) Technology Catalogue 2024 for industrial ammonia heat pumps (€600–900/kW). |
| **Borehole Field Cost (GSHP)** | £75 / m drilling + piping | **[Estimated]** | UK non-domestic GSHP industry range (£40–150/m). At 34 km drilling per hectare, adds £300/m² (£3.0M/ha), proving closed-loop boreholes are economically unfeasible. |
| **Atmospheric Water Thermal Store** | £100 / m³ (£85–120/m³) | **[Estimated]** | Standard insulated industrial atmospheric buffer tank quotes; £100k for 1,000 m³ stratified store. |
| **Labour Intensity** | 0.90 h/m²/yr (Tomato), 0.70 h/m² (Cucumber) | **[Estimated]** | Agricultural horticultural standard labour requirements for trellised glasshouse crops at National Living Wage (£12.21/h + 23% on-costs = £15.00/h). |

---

### 8.3 Scottish Commercial, Corporate & Statutory Verification
* **Standhill Farm (Hawick, Scottish Borders):** Verified as Scotland's sole existing commercial tomato glasshouse (1.6 ha Venlo, 2 × 1 MW biomass boilers + anaerobic digestate power/$\text{CO}_2$, trading under Scotty Brand). Proves consumer pull for Scottish-grown glasshouse produce.
* **AGR Fenland Glasshouse (Wimblington, Cambridgeshire):** 21.7 ha glasshouse heated by **4 × 8.25 MW (33 MW total) industrial ammonia ($\text{R717}$) heat pumps** coupled to open-water reservoir abstraction. Directly validates the two-stage ammonia heat pump engineering model deployed in this study.
* **Low Carbon Farming / Greencoat Capital (Ingham & Crown Point):** 29 ha of commercial glasshouses heated via large-scale industrial heat pumps extracting thermal energy from **Anglian Water wastewater treatment effluent**. Directly validates the Scottish Water Horizons co-location business model.
* **Sainsbury's 10-Year Glasshouse Supply Agreements:** Announced in 2025/2026 with Thanet Earth (Kent) and Evesham Vale Growers (Worcestershire) for long-term domestic tomato, pepper, and cucumber supply, establishing bankable commercial contract precedents.
* **Good Food Nation (Scotland) Act 2022 (asp 5):** Scottish statutory instrument requiring health boards (NHS Scotland) and local authorities to establish Good Food Nation plans prioritising locally produced, low-carbon food procurement.
* **SEPA CAR Authorisation:** *Water Environment (Controlled Activities) (Scotland) Regulations 2011* (CAR), regulating abstraction and thermal discharge thresholds to Scottish rivers and transitional waters.

