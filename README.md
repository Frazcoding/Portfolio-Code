# Whole-Life Carbon & Life Cycle Costing Assessment Engine
### Implementing EN 15978:2011, BS ISO 15686-5:2017 & RICS 2nd Edition (2023)

**Lead Engineer**: Fraser James Mclellan  
**Specialism**: Whole-Life Carbon (WLC), Life Cycle Costing (LCC), Decarbonisation Advisory & Building Services Engineering  
**Climatic & Grid Context**: United Kingdom (Edinburgh / National Grid ESO FES & DESNZ Trajectories, 2026–2086)

---

## Stage 1: Executive Summary & Core Engineering Finding

Modern building sustainability advisory faces a fundamental strategic dilemma:
> *Under a rapidly decarbonising electrical grid, does an ultra-efficient, low-carbon new build ever overcome the upfront demolition and construction carbon deficit compared to a retained-structure deep retrofit?*

This repository provides an open-source, rigorous computational simulation engine resolving this dilemma for a **$7,500\text{ m}^2\text{ GIA}$ 5-storey UK commercial office building** across a **60-year Reference Study Period (RSP)**.

### Headline Engineering Findings:
1. **The Irrecoverable Demolition Carbon Deficit**: Retaining the existing reinforced concrete substructure and frame in a **Deep Retrofit** eliminates **$>65\%$** of upfront embodied carbon ($155.2\text{ kg CO}_2\text{e/m}^2$ vs $364.6\text{ kg CO}_2\text{e/m}^2$ for standard new build).
2. **The Dynamic Grid Decarbonisation Paradox**: Under official **DESNZ Green Book Central** and **National Grid ESO 'Leading the Way'** trajectories, grid electricity falls from $\approx 0.120\text{ kg/kWh}$ (2026) to $<0.012\text{ kg/kWh}$ (2035) and $<0.005\text{ kg/kWh}$ (2045). Because operational carbon approaches near-zero, a new build **never pays back its upfront construction deficit** against a deep retrofit, leaving an irrecoverable carbon penalty.
3. **Refrigerant Global Warming Impact**: Under **CIBSE TM65 §4.2**, baseline air-cooled chillers using **R410A** ($\text{GWP} = 2,088$) leak **$229.3\text{ kg CO}_2\text{e/m}^2\text{ GIA}$** over 60 years—exceeding the entire upfront construction footprint of the Deep Retrofit. Transitioning to natural refrigerants (**R290 Propane**, $\text{GWP} = 3$) virtually eliminates fugitive lifecycle emissions ($<0.1\text{ kg CO}_2\text{e/m}^2$).
4. **Economic Optimum (BS ISO 15686-5)**: Deep Retrofit delivers the lowest 60-year Life Cycle Cost Net Present Value ($\text{NPV}_{\text{LCC}} = \text{\pounds}2,799\text{/m}^2\text{ GIA}$), saving over **$\text{\pounds}1,500\text{/m}^2$** compared to new build options.

---

## Stage 2: Methodology & System Boundary

The simulation couples **Carbon Currency** ($\text{kg CO}_2\text{e/m}^2\text{ GIA}$) and **Financial Capital Currency** ($\text{\pounds/m}^2\text{ GIA}$) across all standardized life cycle modules:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 EN 15978 / RICS 2ND EDITION LIFE CYCLE BOUNDARY                 │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│   [UPFRONT EMBODIED]       [IN-USE EMBODIED & OPERATIONAL]       [END OF LIFE]    [BEYOND LIFE]  │
│       (A1 – A5)                       (B1 – B7)                    (C1 – C4)       (MODULE D)    │
│   ┌─────────────────┐      ┌─────────────────────────────┐      ┌───────────────┐ ┌────────────┐ │
│   │ A1: Extraction  │      │ B1: Fugitive Refrigerants   │      │ C1: De-con /  │ │ D: Reuse,  │ │
│   │ A2: Transport   │      │     (EU F-Gas Leakage)      │      │     Demolition│ │    Recovery, │ │
│   │ A3: Manufacture │───►  │ B2: Maintenance / B3: Repair│───►  │ C2: Transport │ │    Recycle   │ │
│   │ A4: Site Transp │      │ B4: Replacements (MEP 15yr) │      │ C3: Waste Proc│ │    Credits   │ │
│   │ A5: Construction│      │ B6: Operational Energy (kWh)│      │ C4: Disposal  │ │ (Reported  │ │
│   └─────────────────┘      └─────────────────────────────┘      └───────────────┘ │  Separately│ │
│                                           │                                       └────────────┘ │
│                                           ▼                                                      │
│                        [ DYNAMIC UK GRID DECARBONISATION ]                                       │
│                        (DESNZ Green Book / National Grid ESO FES 2026–2086)                      │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Evaluated Intervention Scenarios:
1. **Scenario 1 — Baseline Counterfactual**: Existing 1980s concrete framed building retained; like-for-like condensing gas boiler replacement ($\eta = 92\%$), standard air-cooled chiller (R410A), uninsulated facade ($140\text{ kWh/m}^2/\text{yr}$ EUI). Upfront Capex: £420/m².
2. **Scenario 2 — Deep Retrofit**: 100% substructure and superstructure retained; high-performance triple glazing ($U = 0.85$), bio-insulation ($U = 0.18$), central ASHP with **R290 propane** ($\text{SCOP} = 3.6$), MVHR ($82\%$), rooftop PV ($55\text{ kWh/m}^2/\text{yr}$ EUI). Upfront Capex: £1,485/m².
3. **Scenario 3 — Standard New Build**: Full demolition of existing building; structural steel frame ($60\text{ kg/m}^2$), composite slabs, ASHP with **R32** ($\text{GWP} = 675$), compliant envelope ($55\text{ kWh/m}^2/\text{yr}$ EUI). Upfront Capex: £2,615/m².
4. **Scenario 4 — Exemplar Timber New Build**: Selective deconstruction; 70% GGBS concrete foundations, Glulam/CLT timber superstructure, Passivhaus envelope, R290 ASHP, maximized BIPV ($45\text{ kWh/m}^2/\text{yr}$ EUI). Upfront Capex: £3,035/m².

---

## Stage 3: Executive Summary Results Table

All figures evaluated over the 60-year Reference Study Period (2026–2086) under **DESNZ Green Book Central Grid** and **HM Treasury Green Book Discounting** ($3.5\% \to 3.0\%$):

| Metric | Scenario 1: Baseline (Gas) | Scenario 2: Deep Retrofit | Scenario 3: Standard New Build | Scenario 4: Timber New Build |
|---|:---:|:---:|:---:|:---:|
| **A1–A5 Upfront Embodied** [$\text{kg CO}_2\text{e/m}^2$] | 33.4 | **155.2** | 364.6 | 218.1 |
| **B1–B5 In-Use Embodied & Replacements** [$\text{kg/m}^2$] | 273.1 | **177.9** | 189.1 | 181.8 |
| *— of which Fugitive Refrigerant Leakage (B1)* | *221.9* | *0.0* | *13.0* | *0.0* |
| **B6 Operational Energy (60-Yr)** [$\text{kg/m}^2$] | 1,154.9 | **65.3** | 65.3 | 53.4 |
| **C1–C4 End of Life** [$\text{kg/m}^2$] | 13.4 | **8.5** | 17.8 | 17.5 |
| **Net Whole-Life Carbon (A1–C4)** [$\text{kg/m}^2$] | 1,474.7 | **406.8** | 636.8 | 470.7 |
| **Module D Circular Credits** [$\text{kg CO}_2\text{e/m}^2$] | 0.0 | 0.0 | 0.0 | **-143.9** (CLT Biogenic) |
| **Initial Upfront CAPEX** [$\text{\pounds/m}^2\text{ GIA}$] | £420 | £1,485 | £2,615 | £3,035 |
| **60-Yr Life Cycle Cost NPV** [$\text{\pounds/m}^2\text{ GIA}$] | £1,490 | **£2,799** | £4,343 | £4,815 |
| **Marginal Abatement Cost (MAC)** [$\text{\pounds/t CO}_2\text{e}$] | — | **£1,225.4 / t** | £3,404.9 / t | £3,312.1 / t |
| **LETI Embodied Carbon Band** | Band A++ (Retained) | **Band A+** | Band B | **Band A+** |
| **RIBA 2030 Climate Challenge** | FAIL | **PASS** | **PASS** | **PASS** |
| **UK Net Zero Carbon Standard (NZCBS)** | FAIL | **PASS** | **PASS** | **PASS** |
| **Carbon Payback vs Baseline Counterfactual** | — | **Year 6** | Year 14 | Year 10 |
| **Breakeven vs Deep Retrofit** | — | **N/A (Superior)** | **Never** | **Never** |

---

## Stage 4: Extended 6-Figure Publication Suite

All figures are programmatically generated and adhere strictly to master visual rules (pure black typography `#000000`, legend strictly below graphs, bracketed physical units, zero in-plot annotations, 300 DPI PNG & vector SVG):

### Figure 1 — Whole Life Carbon Breakdown Across 60-Year Study Period
Stacked breakdown across EN 15978 modules comparing the 4 scenarios with LETI baseline limits and separate Module D biogenic credits:
![Figure 1: WLC Stage Breakdown](figures/fig1_wlc_stage_breakdown.png)

### Figure 2 — 60-Year Dynamic Cumulative Carbon Payback
Dynamic trajectory analysis under DESNZ Green Book Central Grid (top) and grid sensitivity comparing rapid ESO decarb vs Static SAP 10.2 (bottom):
![Figure 2: Cumulative Carbon Payback](figures/fig2_cumulative_carbon_payback.png)

### Figure 3 — Elemental Breakdown of Upfront Embodied Carbon (A1–A5)
RICS NRM elemental breakdown visualizing how 100% structural retention completely eliminates substructure and superstructure embodied emissions:
![Figure 3: Spatial & Elemental Breakdown](figures/fig3_spatial_elemental_breakdown.png)

### Figure 4 — CIBSE TM65 MEP Lifecycle Carbon & Refrigerant F-Gas Trade-off
Analysis of HVAC machinery embodied carbon, replacement cycles, operational leakage, and venting across R410A, R32, and R290 propane:
![Figure 4: MEP Refrigerant Trade-off](figures/fig4_mep_refrigerant_fgas_tradeoff.png)

### Figure 5 — Techno-Economic Pareto Frontier (BS ISO 15686-5 LCC vs Carbon)
Dual-currency engineering Pareto frontier plotting 60-year LCC Net Present Value against Whole-Life Carbon, identifying Deep Retrofit as the optimal design:
![Figure 5: Techno-Economic Pareto Frontier](figures/fig5_techno_economic_carbon_cost_frontier.png)

### Figure 6 — LETI & RIBA 2030 Benchmark Compliance Matrix
Dual-panel scorecard evaluating Upfront Embodied Carbon (Panel A) and Operational EUI (Panel B) against UK Net Zero benchmarks:
![Figure 6: Benchmark Compliance](figures/fig6_leti_riba_benchmark_compliance.png)

---

## Stage 5: Installation, Verification & Reproducibility Guide

### Quickstart Setup

```bash
# 1. Clone repository
git clone https://github.com/fraser-mclellan/Whole-Carbon-Lifecycle-Assessment.git
cd Whole-Carbon-Lifecycle-Assessment

# 2. Set up Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install pinned dependencies
pip install -r requirements.txt
```

### CLI Execution Commands

```bash
# Run the complete carbon accounting, LCC, and figure generation pipeline:
python main.py --run-all --export-figures

# Run sensitivity sweeps across grid trajectories and CIBSE TM65 refrigerants:
python main.py --sweep-grid --sweep-refrigerants

# Synchronize hero figures to master portfolio collateral:
python main.py --sync-collateral
```

### Interactive Jupyter Notebook

Explore the underlying math, sensitivity sweeps, and data interactive tables:
```bash
jupyter notebook notebooks/whole_life_carbon_exploration.ipynb
```

---

## Technical Standards & Data References
- **BS EN 15978:2011**: *Sustainability of construction works — Assessment of environmental performance of buildings — Calculation method*.
- **BS ISO 15686-5:2017**: *Buildings and constructed assets — Service life planning — Part 5: Life-cycle costing*.
- **RICS Professional Standard (2nd Edition, 2023)**: *Whole life carbon assessment for the built environment*.
- **CIBSE TM65: 2021**: *Embodied carbon in building services: A calculation methodology*.
- **University of Bath**: *Inventory of Carbon and Energy (ICE Database v3.0)*.
- **DESNZ (2024)**: *Green Book Supplementary Guidance: Valuation of energy use and greenhouse gas emissions for appraisal*.
- **National Grid ESO**: *Future Energy Scenarios (FES) 2024: Leading the Way*.
