# Liquid CO2 Market Pricing & Procurement Analysis: Scotland & CEA Glasshouse Context

**Author**: Fraser James Mclellan  
**Project**: BEng CEA Greenhouse Two-Stage Ammonia Heat Pump Simulation & Commercial Model  
**Date**: October 2026  
**Audited Parameter**: `co2_price` in `lca/breakeven.py` and `Inputs` in `Glasshouse_Capex_Opex_Model.xlsx` (Placeholder: **£0.20 / kg** / **£200 / tonne**)

---

## 1. Executive Summary & Scottish Price Tiers

Unlike retail fuels or grid electricity, liquid carbon dioxide ($\text{LCO}_2$) is not traded on an open commodity exchange. Prices in the UK are governed by bilateral, long-term industrial supply contracts, heavily index-linked to energy surcharges, delivery volume, and regional logistics.

For commercial greenhouse crop enrichment (typically targeting $800\text{--}1,000\text{ ppm}$ during daylight hours, consuming $25\text{--}50\text{ g CO}_2/\text{m}^2/\text{h}$ or $250\text{--}400\text{ t CO}_2/\text{ha/year}$), the Scottish pricing landscape breaks down into three distinct tiers:

| Supply Mode | Scale / Batch Size | Delivered Price [£/tonne] | Unit Price [£/kg] | Primary Use Case in Scotland |
|---|:---:|:---:|:---:|---|
| **Bulk Road Tanker (VIE)** | **10 – 20 tonne drops** | **£220 – £320 / t** | **£0.22 – £0.32 / kg** | **Commercial Glasshouse (0.5 – 5+ ha)** |
| **Microbulk (CryoEase / Mini-tank)** | 1 – 3 tonne drops | **£380 – £550 / t** | **£0.38 – £0.55 / kg** | Pilot vertical farms, R&D facilities |
| **High-Pressure Cylinders / Bundles** | 34 kg liquid dip-tubes / 16-packs | **£1,200 – £2,200 / t** | **£1.20 – £2.20 / kg** | Craft breweries, small research labs |
| **Biogenic Distillery Co-location** | Direct pipeline / scrubber | **£0 – £60 / t** | **£0.00 – £0.06 / kg** | **Strategic Scottish Symbiosis (Lever)** |

### Validation of Model Placeholder (£0.20 / kg = £200 / tonne)
* **Finding**: The model’s current placeholder of **£0.20 / kg (£200 / tonne)** sits at the **lowest bound** of competitive commercial bulk road tanker supply.
* **Assessment**: While achievable on multi-year, high-volume contracts ($>300\text{ tonnes/year}$) near the Central Belt distribution spine, a realistic Scottish baseline for an unintegrated standalone facility is **£0.25 / kg (£250 / tonne)**, with a sensitivity range of **£0.20 to £0.35 / kg**.

---

## 2. Market Structure & Regional Supply in Scotland

### 2.1 Regional Supply Hubs & Active Suppliers
Scotland relies on a mix of local storage terminals and cross-border road haulage from northern English production plants:

1. **Lothian Supply Company (LSC) / Clean Carbon (Livingston, West Lothian)**:
   * **Infrastructure**: Operates Central Scotland's primary liquid $\text{CO}_2$ storage hub with over **110 tonnes** of on-site cryogenic capacity.
   * **Fleet & Coverage**: Dedicated road-tanker fleet covering Glasgow, Edinburgh, Fife, Falkirk, Lanarkshire, and Perthshire.
   * **Advantage**: Independent terminal buffered against short-term national supply crunches; offers contract terms without traditional cylinder rental penalties.
2. **BOC (Linde plc) (Cambuslang / Grangemouth / Aberdeen)**:
   * National market leader in industrial cryogenic gas distribution. Operates bulk cryogenic road tankers supplying bulk Vacuum Insulated Evaporator (VIE) systems across Scotland.
3. **Albion Gases (Dumbarton / Glasgow)**:
   * Major regional supplier of food-grade liquid $\text{CO}_2$ across Central and Western Scotland.
4. **Air Liquide UK (via regional distributor partners such as Russell Gas)**:
   * Supplies industrial and beverage-grade cryogenic $\text{CO}_2$ from Central Belt depots.
5. **Nippon Gases UK**:
   * Operates bulk tanker delivery routes serving Scottish industrial and food processing accounts from Northern English terminals.

### 2.2 Feedstock Origin & Geographic Freight Differential
* **Upstream Sources**: Over 60–70% of UK merchant $\text{CO}_2$ historically originated as a byproduct of synthetic ammonia manufacturing (CF Fertilisers at Billingham, Teesside) and bioethanol refining (Ensus at Wilton, Teesside; Vivergo Fuels at Saltend, Hull). 
* **The "Scottish Freight Premium"**:
  * **Central Belt (Glasgow, Edinburgh, Falkirk, Livingston)**: Benefits from direct motorway links (M8/M74/M9) and proximity to the Livingston and Cambuslang depots. Bulk delivery charges are standard mainland rates (£100–£180 per drop).
  * **Perthshire / Angus / Tayside**: Approximately 50–90 miles north of the Central Belt. Adds a modest haulage differential of **£20 – £35 / tonne** to delivered product.
  * **Aberdeenshire & Scottish Highlands**: Distance from primary production facilities in Teesside/Hull adds **£50 – £90+ / tonne** in road-tanker deadhead freight.

---

## 3. On-Site Storage Infrastructure Costs (Cryogenic VIE Tank)

A commercial glasshouse consuming pure liquid $\text{CO}_2$ requires an on-site cryogenic bulk storage and gasification system:

```
┌────────────────────────────────┐         ┌────────────────────────┐         ┌────────────────────────┐
│     Cryogenic Road Tanker      │         │ Cryogenic Tank (VIE)   │         │ Atmospheric / Hydronic │
│    (15–20 t bulk delivery)     │────────►│ (-20 °C, 18–22 bar)    │────────►│ Vaporiser (45 °C loop) │
└────────────────────────────────┘         │ 10–30 t liquid buffer  │         └───────────┬────────────┘
                                           └────────────────────────┘                     │
                                                                                          ▼
                                                                              ┌────────────────────────┐
                                                                              │ Glasshouse Dosing Net  │
                                                                              │ (800–1,000 ppm PAR)    │
                                                                              └────────────────────────┘
```

### 3.1 Capital & Lease Expenditure Breakdown
1. **Vacuum Insulated Evaporator (VIE) Tank**:
   * **Size**: Typically a 10-tonne ($12\,\text{m}^3$) to 25-tonne ($30\,\text{m}^3$) vertical vacuum-insulated pressure vessel (stainless steel inner vessel, carbon steel outer shell, perlite vacuum insulation).
   * **Contract Model**: Industrial gas majors (BOC, Air Liquide) rarely require growers to purchase the vessel outright. It is provided on a long-term **Facility Charge / Tank Rental Agreement**.
   * **Monthly Rental**: **£450 – £750 / month** (£5,400 – £9,000 / year) depending on vessel capacity and telemetry setup.
   * **Outright Purchase (Alternative)**: £45,000 – £75,000 installed.
2. **Vaporisation System**:
   * Because $\text{CO}_2$ is stored as a liquid at $-20^\circ\text{C}$ and $\sim 20\,\text{bar}$, it requires latent heat of vaporisation ($345\,\text{kJ/kg}$) before injection into the greenhouse air.
   * **Integration**: While ambient aluminium finned vaporisers can ice up in Scottish winters, a CEA glasshouse paired with a two-stage heat pump can route low-grade hydronic return water ($35\text{--}45^\circ\text{C}$) through a shell-and-tube or water-bath vaporiser, achieving virtually free vaporisation.
3. **Statutory Compliance & Telemetry**:
   * Remote telemetry monitoring (automatic low-level reorder): £25 – £50 / month.
   * Written Scheme of Examination & maintenance under the UK **Pressure Systems Safety Regulations 2000 (PSSR)**: £600 – £1,200 / year.

---

## 4. Historical Volatility & The Fragility of Fossil Byproduct $\text{CO}_2$

The UK commercial $\text{CO}_2$ market has experienced unprecedented shocks that highlight the operational risk of relying on merchant liquid $\text{CO}_2$:

* **Pre-2021 Baseline**: Food-grade liquid $\text{CO}_2$ traded at **£80 – £120 / tonne** delivered.
* **The 2021–2022 Crisis**: Natural gas spikes forced CF Fertilisers to idle its ammonia operations at Ince (permanently closed) and Billingham. Spot prices for liquid $\text{CO}_2$ rocketed from £100/t to **£1,000 – £3,000 / tonne**, creating an acute supply famine across food processing, brewing, and protected horticulture.
* **Post-2023 Restructuring**: The market stabilized via imports from Norway and mainland Europe, alongside the restart of bioethanol capture (Ensus/Vivergo). However, structural pricing settled permanently higher, establishing a new floor at **£200 – £300 / tonne**.

---

## 5. The Strategic Scottish Advantage: Biogenic $\text{CO}_2$ Symbiosis

As identified in the project's Scotland commercialisation strategy (`Market/02_SCOTLAND_GO_TO_MARKET_STRATEGY.md`), Scotland holds an unmatched natural hedge against merchant $\text{CO}_2$ pricing.

### 5.1 Scotch Whisky Distilleries
* **The Chemistry**: During wash fermentation, yeast converts sugars into ethanol and carbon dioxide:
  $$\text{C}_6\text{H}_{12}\text{O}_6 \longrightarrow 2\,\text{C}_2\text{H}_5\text{OH} + 2\,\text{CO}_2 \uparrow$$
* **Purity**: Fermentation off-gas is naturally **$>99.5\%$ pure $\text{CO}_2$** saturated with water vapor and trace congeners/alcohols. It does **not** contain toxic combustion contaminants found in natural gas boilers or CHP engines (such as sulfur dioxide $\text{SO}_2$, nitrogen oxides $\text{NO}_x$, carbon monoxide $\text{CO}$, or ethylene $\text{C}_2\text{H}_4$).
* **Economics**:
  * Scotland’s 140+ distilleries vent hundreds of thousands of tonnes of biogenic $\text{CO}_2$ annually.
  * Capturing this gas requires a simple foam trap, water scrubber, condenser, and low-pressure blower.
  * Direct over-the-fence piping to an adjacent glasshouse eliminates road haulage, cryogenic liquefaction, and cryogenic storage.
  * **Delivered Cost**: **£0 – £40 / tonne** (essentially the power cost of running the scrubber and blower), representing a **75% to 100% reduction** in crop enrichment operational expenditure.

### 5.2 Scottish Biomethane / Anaerobic Digestion (AD) Plants
* Scotland has a dense network of agricultural and municipal AD plants (e.g. across Perthshire, Angus, and Aberdeenshire) upgrading raw biogas ($60\%\,\text{CH}_4, 40\%\,\text{CO}_2$) to grid-spec biomethane.
* The membrane separation or amine scrubbers vent biogenic $\text{CO}_2$.
* Upgrading facilities (such as those developed by Pentair, Bright Renewables, or Greenlane) can liquefy this gas into food-grade biogenic $\text{LCO}_2$, selling locally at **£120 – £180 / tonne**, significantly undercutting imported fossil $\text{CO}_2$.

---

## 6. Recommendations for the Financial Model (`Glasshouse_Capex_Opex_Model.xlsx`)

To ensure robust sensitivity testing across standalone and integrated Scottish scenarios, apply the following parameter schedule:

```python
# ==============================================================================
# AUDITED LIQUID CO2 PRICING PARAMETERS (SCOTLAND - OCTOBER 2026)
# ==============================================================================

# STANDALONE COMMERCIAL GLASSHOUSE (MERCHANT BULK LCO2)
CO2_PRICE_BASELINE_GBP_KG     = 0.25    # £250/t: Central Scotland 15-20 t road tanker delivered
CO2_PRICE_CONSERVATIVE_GBP_KG = 0.32    # £320/t: Rural Scotland / smaller contracts
CO2_PRICE_OPTIMISTIC_GBP_KG   = 0.20    # £200/t: Current model placeholder (large volume tier)

# INFRASTRUCTURE (VIE TANK & EVAPORATOR)
CO2_VIE_TANK_RENTAL_GBP_YEAR  = 7200.0  # ~£600/month for 15-tonne cryogenic tank + telemetry
CO2_PSSR_INSPECTION_GBP_YEAR  = 800.0   # Statutory safety inspection & compliance

# INTEGRATED / COLLOCATED LEVERS (SCOTTISH DISTILLERY / AD SYMBIOSIS)
CO2_DISTILLERY_BIOGENIC_GBP_KG = 0.03   # £30/t: Scrubbing & blowers (over-the-fence pipeline)
CO2_DISTILLERY_FREE_LEVER_KG   = 0.00   # £0/t: Net-zero distillery partner absorbs scrubbing capex
```

### OPEX Impact Summary for a 1-Hectare Glasshouse
* **Typical Annual Consumption**: $300\text{ tonnes CO}_2/\text{year}$ ($30\,\text{kg/m}^2/\text{year}$ across $10,000\,\text{m}^2$).
* **Standalone Merchant Supply (@ £0.25/kg + tank hire)**:
  $$\text{OPEX} = (300,000\,\text{kg} \times £0.25) + £8,000 = \mathbf{£83,000 / \text{year}}$$
* **Integrated Distillery Pipeline (@ £0.03/kg, no cryogenic tank)**:
  $$\text{OPEX} = 300,000\,\text{kg} \times £0.03 = \mathbf{£9,000 / \text{year}}$$
* **Net Annual Saving from Scottish Co-location**: **£74,000 / year / hectare**.
