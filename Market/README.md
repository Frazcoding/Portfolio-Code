# Commercialisation, Market Research & Feasibility Audit Dossier

**Project:** Decarbonised Controlled Environment Agriculture (CEA) Glasshouse & Industrial Ammonia ($\text{R717}$) Heat Pump  
**Target Geography:** Scotland (Central Belt, Tayside / Carse of Gowrie, Perthshire & Angus soft fruit corridor, Speyside)  
**Location:** `BEng-CEA-Heatpump/Market/`

---

## Directory Overview & File Index

This folder compiles the complete market landscape, go-to-market strategy, feasibility audit, and executable financial models for commercialising the greenhouse simulation and heat pump project in Scotland.

```
BEng-CEA-Heatpump/Market/
│
├── 01_CLAUDE_MARKET_SCAN.md              # Detailed UK & Scottish market research (incumbents, CEA, competitors)
├── market_scan.html                     # Interactive HTML dashboard visualizing the market scan data
├── 02_SCOTLAND_GO_TO_MARKET_STRATEGY.md # Comprehensive commercialisation roadmap across 5 core pillars
├── 03_FEASIBILITY_AUDIT_AND_TARGET_KPIS.md # Complete feasibility audit and numerical target specifications
├── audit_financials.py                  # Executable 20-year cash flow, LCOH & financial model runner
├── audit_feasibility.py                 # Executable crop-by-crop Scottish breakeven audit script
└── README.md                            # This directory index and executive guide
```

---

## Document Summaries

### 1. `01_CLAUDE_MARKET_SCAN.md` & `market_scan.html`
* **Author/Origin:** Market research performed by Claude (October 2026).
* **Key Findings:**
  * **The Scottish Landscape:** Scotland is currently nearly devoid of large commercial heated glass (only Standhill Farm in Hawick, Borders, operating 1.6 ha on biomass; vertical farms like Jones Food Company entered administration due to high electricity costs).
  * **UK Incumbents & Benchmarks:** UK glasshouses are old (>70% over 40 years old) and facing massive electricity network standing charge hikes (+94% TNUoS in 2026). The benchmark projects for heat pumps are AGR Fenland (33 MW NH₃ heat pumps + CHP) and Low Carbon Farming (29 ha on Anglian Water sewage heat).
  * **Software Competitors:** Analysis of Dutch simulation/digital twin tools (Hortinergy, Priva ECO, Source.ag, KASPRO). Demonstrates the unique market gap filled by this project (refrigerant cycle modeling + UK tariffs + site-specific wind/grid + import trade LCA).

### 2. `02_SCOTLAND_GO_TO_MARKET_STRATEGY.md`
* **Author/Origin:** Strategic commercialisation roadmap developed in this session.
* **Core Pillars Covered:**
  * **Private Energy Deals:** Behind-the-meter private wire wind PPAs (bypassing DUoS/TNUoS network charges for 8–10p/kWh power), local curtailment / spill-wind contracts, and flexibility market dispatch (SPEN/SSEN CMZ tenders).
  * **Industrial Waste Heat Symbiosis:** Co-location with Scotch whisky distilleries (taking $70\text{--}80^\circ\text{C}$ pot ale and condenser water; biogenic fermentation $\text{CO}_2$ capture) and Scottish Water Horizons (sewer heat recovery via water-source heat pumps at $\text{SCOP} \ge 4.5$).
  * **Supermarket & Offtake Deals:** Retail Scope 3 emissions drivers (M&S, Sainsbury's, Tesco), partnering with Scottish Producer Organisations (Angus Soft Fruits, East of Scotland Growers) to secure 5- to 10-year floor-and-ceiling supply contracts, and the Good Food Nation public procurement route.
  * **Scottish Government Support & Grants:** SMART:SCOTLAND feasibility grants, Scottish Enterprise Green Heat Innovation Support Programme (GHISP, 30–50% capital match), Agricultural Reform Programme (Tier 3/4), and SEPA CAR water licensing.
  * **Investment & Financial Engineering:** OpCo/PropCo asset separation, Heat-as-a-Service (HaaS) models, Scottish National Investment Bank (SNIB) patient debt, and a 4-phase rollout roadmap.

### 3. `03_FEASIBILITY_AUDIT_AND_TARGET_KPIS.md`
* **Author/Origin:** Quantitative audit and target KPI specification developed in this session.
* **Core Deliverables:**
  * **The Master Feasibility Matrix:** Exact threshold targets across Thermodynamics ($\text{SCOP} \ge 3.50$ air / $\ge 4.50$ effluent), Electricity Tariffs ($\le 10.7\text{p}$ vs CIF, $\le 19.6\text{p}$ for cucumber, $\le 27.9\text{p}$ vs wholesale), CAPEX ($\le £200\text{/m}^2$ glasshouse, $\le £700\text{/kW}$ heat pump skid), and Agronomic Yields ($39.4\text{ kg/m}^2$ for tomato, $+9.6\%$ gap closed via biogenic $\text{CO}_2$).
  * **The Off-Grid Reality Check:** Explains why 100% off-grid islanded wind causes economic failure (38–44% wind curtailment driving electricity to 38–49p/kWh), and why grid-tethering + PPA unlocks commercial success.
  * **1-Hectare Commercial Financial Model:** Comparative 20-year cash flow model showing Model A (Off-grid, negative EBITDA) vs Model B3 (Air HP + PPA @ £2.10/kg: 12.6% IRR, 7.2 yr payback) vs Model C (Distillery Waste Heat: 20.6% IRR, 4.7 yr payback, £499k/yr EBITDA).

---

## Executable Analysis Scripts

### Running the Financial Model:
```powershell
python BEng-CEA-Heatpump/Market/audit_financials.py
```
*Outputs 20-year CAPEX, OPEX, EBITDA, Simple Payback, 20-year Project IRR, and NPV@8% across 7 glasshouse supply architectures.*

### Running the Scottish Crop Breakeven Audit:
```powershell
python BEng-CEA-Heatpump/Market/audit_feasibility.py
```
*Evaluates the Carse of Gowrie, Perthshire simulation dataset to calculate specific electricity consumption ($kWh_e/kg$), non-electric cost baselines, breakeven electricity prices ($p_e^*$), and required yield thresholds ($Y^*$) across 10 crops.*

---

## Data Provenance, Sourcing & Verification Standard

All documents, numbers, and models in this folder follow strict provenance standards:
- **Tier 1 (Official & Statutory Data):** DESNZ 2025 Greenhouse Gas Conversion Factors, DESNZ Quarterly Energy Prices (Q3 2025 + CCL 2026), UN Comtrade 2023–2025 trade database, DEFRA official wholesale market series 2024–2026, ECMWF ERA5 2023 climate reanalysis, SAC/SRUC Table 11 & Table 17 benchmarks, Good Food Nation (Scotland) Act 2022, SEPA CAR regulations.
- **Tier 2 (Derived Simulation Models):** Dynamic greenhouse multi-node heat balance (`greenhouse_fast.py`), CoolProp R717 two-stage thermodynamic cycle map, hourly PyPSA capacity expansion models.
- **Tier 3 (Estimated & Sensitivity-Tested Rates):** Industrial heat pump skid installation costs cross-referenced against Danish Energy Agency technology catalogues; borehole drilling quotes (£40–150/m); standard horticultural labour at National Living Wage + 23% on-costs.
- Full bibliographic citations and verification registers are published in Section 8 of both `02_SCOTLAND_GO_TO_MARKET_STRATEGY.md` and `03_FEASIBILITY_AUDIT_AND_TARGET_KPIS.md`.

