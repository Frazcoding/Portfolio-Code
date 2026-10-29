# GEMINI.md — Whole-Life Carbon & Life Cycle Costing Assessment (EN 15978 / RICS)

---

## 1. Executive Project Overview & Engineering Scope

- **Repository**: `Whole-Carbon-Lifecycle-Assessment`
- **Lead Engineer**: Fraser James Mclellan
- **Domain**: Whole-Life Carbon (WLC), Life Cycle Costing (LCC), Decarbonisation & Sustainability Advisory, Building Services Engineering
- **Core Mission**: Build a production-grade, open-source techno-economic and carbon accounting engine implementing **EN 15978** and the **RICS Whole Life Carbon Assessment for the Built Environment (2nd Edition, 2023)** to resolve the central dilemma of modern sustainable engineering:
  > *Under a rapidly decarbonising electrical grid, does an ultra-efficient, low-carbon new build ever overcome the upfront demolition and construction carbon deficit compared to a retained-structure deep retrofit?*
- **Primary Archetype**: A 5-storey UK commercial office building with a Gross Internal Area ($\text{GIA}$) of **$7,500\text{ m}^2$** ($1,500\text{ m}^2$ floorplate, $3.8\text{ m}$ floor-to-floor height, $45\%$ window-to-wall ratio [WWR], reinforced concrete frame with ribbed slab, Edinburgh/UK climatic and grid context).
- **Dual-Currency Methodology**: Evaluates interventions across both **Carbon Currency** ($\text{kg CO}_2\text{e}/\text{m}^2\text{ GIA}$ across Modules A1–C4 + D over a 60-year Reference Study Period) and **Financial Capital Currency** ($\text{\pounds}/\text{m}^2\text{ GIA}$, Capex, 60-year Opex, and Net Present Value via **BS ISO 15686-5** Life Cycle Costing).
- **Strategic Purpose**: Serves as Fraser's flagship public portfolio project for leading sustainability and engineering consultancies (e.g. Arup, Buro Happold, Cundall, Atelier Ten, Max Fordham, Hilson Moran, Foster + Partners), demonstrating mastery of whole-life carbon accounting, CIBSE TM65 MEP embodied carbon, EU/UK F-Gas refrigerant dynamics, and UK Net Zero Carbon Buildings Standard (NZCBS) / LETI / RIBA 2030 targets.

---

## 2. System Boundary & Life Cycle Architecture

The simulation covers the full **60-year Reference Study Period (RSP)** in accordance with **EN 15978:2011**, **BS EN 15686-5:2017**, and the **RICS Professional Standard: Whole life carbon assessment for the built environment (2nd Edition, 2023)**.

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 EN 15978 / RICS 2ND EDITION LIFE CYCLE BOUNDARY                 │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                  │
│   [UPFRONT EMBODIED]       [IN-USE EMBODIED & OPERATIONAL]       [END OF LIFE]    [BEYOND LIFE]  │
│       (A1 – A5)                       (B1 – B7)                    (C1 – C4)       (MODULE D)    │
│                                                                                                  │
│   ┌─────────────────┐      ┌─────────────────────────────┐      ┌───────────────┐ ┌────────────┐ │
│   │ A1: Extraction  │      │ B1: In-Use Fugitive Refriger│      │ C1: De-con /  │ │ D: Reuse,  │ │
│   │ A2: Transport   │      │     (EU F-Gas Leakage)      │      │     Demolition│ │    Recovery, │ │
│   │ A3: Manufacture │───►  │ B2: Maintenance             │───►  │ C2: Transport │ │    Recycle   │ │
│   │ A4: Site Transp │      │ B3: Repair                  │      │ C3: Waste Proc│ │    Credits   │ │
│   │ A5: Construction│      │ B4: Replacement (MEP 15yr)  │      │ C4: Disposal  │ │ (Reported  │ │
│   │     & Waste     │      │ B5: Refurbishment           │      └───────────────┘ │  Separately│ │
│   └─────────────────┘      │ B6: Operational Energy (kWh)│                        │  per RICS) │ │
│                            │ B7: Operational Water       │                        └────────────┘ │
│                            └─────────────────────────────┘                                       │
│                                           │                                                      │
│                                           ▼                                                      │
│                        [ DYNAMIC UK GRID DECARBONISATION ]                                       │
│                        (National Grid ESO FES / DESNZ 2026–2086)                                 │
│                                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### The 4 Evaluated Intervention Scenarios

1. **Scenario 1 — Baseline / Counterfactual (Do-Minimum Gas Replacement)**:
   - *Structure & Envelope*: Existing 1980s concrete framed building retained as-is; uninsulated cavity facade, single/standard double glazing ($U_{\text{wall}} = 1.6\text{ W/m}^2\text{K}$, $U_{\text{win}} = 2.8\text{ W/m}^2\text{K}$), leaky envelope ($q_{50} = 10\text{ m}^3/(\text{h}\cdot\text{m}^2)$).
   - *MEP Services*: Like-for-like end-of-life replacement with modern condensing gas boilers ($\eta = 92\%$), standard air-cooled chillers ($EER = 2.8$, R410A refrigerant), constant air volume (CAV) ventilation without heat recovery.
   - *Energy Intensity*: Total Energy Use Intensity ($\text{EUI}$) = **$140\text{ kWh/m}^2/\text{yr}$** ($90\text{ kWh/m}^2$ gas heating + $50\text{ kWh/m}^2$ electricity).
   - *Upfront Capital*: Minimal (£420/m²).

2. **Scenario 2 — Deep Retrofit (Retained Structure + Fabric-First + Electrification)**:
   - *Structure*: **100% substructure and superstructure retained** (zero demolition of existing concrete columns, slabs, or shear walls; avoiding all A1–A3 structural embodied carbon).
   - *Envelope*: High-performance curtain walling / triple glazing ($U_{\text{win}} = 0.85\text{ W/m}^2\text{K}$, $g = 0.35$), internal/external mineral wool and bio-insulation ($U_{\text{wall}} = 0.18\text{ W/m}^2\text{K}$, $U_{\text{roof}} = 0.12\text{ W/m}^2\text{K}$), airtightness membrane retrofit ($q_{50} = 2.0\text{ m}^3/(\text{h}\cdot\text{m}^2)$).
   - *MEP Services*: Central 4-pipe reversible Air-Source Heat Pumps (ASHP) with ultra-low GWP refrigerant (**R290 propane**, $\text{GWP} = 3$, seasonal $\text{SCOP} = 3.6$, $\text{SEER} = 4.2$), Variable Air Volume (VAV) with Mechanical Ventilation Heat Recovery ($\text{MVHR}$, $\eta_{\text{hr}} = 82\%$), demand-controlled ventilation (DCV), high-efficiency LED lighting ($6\text{ W/m}^2$), and a $120\text{ kWp}$ rooftop solar PV array generating $\approx 14\text{ kWh/m}^2/\text{yr}$.
   - *Energy Intensity*: Net operational $\text{EUI}$ = **$55\text{ kWh/m}^2/\text{yr}$** (all-electric, fully aligned with LETI Commercial Office target).

3. **Scenario 3 — Standard New Build (Demolition + Conventional Steel & Concrete)**:
   - *Demolition*: Full deconstruction of existing $7,500\text{ m}^2$ building (Module C1 deconstruction energy, C2 transport, C3/C4 waste processing).
   - *Structure*: Standard UK construction practice: Reinforced concrete substructure (CEM I Portland cement, $380\text{ kg CO}_2\text{e/m}^3$), structural steel framed superstructure with composite metal deck and reinforced concrete slabs ($60\text{ kg steel/m}^2$).
   - *Envelope & MEP*: Compliant modern curtain walling ($U_{\text{win}} = 1.2\text{ W/m}^2\text{K}$, $U_{\text{wall}} = 0.22\text{ W/m}^2\text{K}$), centralized ASHP with **R32 refrigerant** ($\text{GWP} = 675$, $\text{SCOP} = 3.4$), MVHR ($\eta_{\text{hr}} = 75\%$), LED lighting, rooftop PV.
   - *Energy Intensity*: Net operational $\text{EUI}$ = **$55\text{ kWh/m}^2/\text{yr}$** (all-electric).
   - *Embodied Carbon*: High upfront footprint ($>850\text{ kg CO}_2\text{e/m}^2$).

4. **Scenario 4 — Exemplar Low-Carbon New Build (Mass Timber + High-GGBS Concrete)**:
   - *Demolition*: Full deconstruction of existing building with high material diversion to recycling/crushing (Module D circular credits).
   - *Structure*: 70% Ground Granulated Blast-Furnace Slag (GGBS) cement replacement in substructure/foundations; Cross-Laminated Timber (CLT) floor slabs and Glulam timber beam/column superstructure, sequestering biogenic carbon.
   - *Envelope & MEP*: Passivhaus-standard envelope ($U_{\text{win}} = 0.75\text{ W/m}^2\text{K}$, $U_{\text{wall}} = 0.14\text{ W/m}^2\text{K}$, $q_{50} = 0.8\text{ m}^3/(\text{h}\cdot\text{m}^2)$), wood-fibre insulation, ultra-high-efficiency central water-to-water heat recovery chillers and R290 ASHP ($\text{SCOP} = 4.1$, $\text{SEER} = 4.8$), displacement ventilation with run-around coil heat recovery, maximized rooftop and facade BIPV generating $\approx 22\text{ kWh/m}^2/\text{yr}$.
   - *Energy Intensity*: Net operational $\text{EUI}$ = **$45\text{ kWh/m}^2/\text{yr}$** (all-electric, achieving LETI Exemplar Net Zero rating).

---

## 3. Mathematical & Carbon Accounting Formulation

### 3.1. Upfront Embodied Carbon (Modules A1–A5)
The upfront embodied carbon capital of material elements is determined using the **ICE Database v3.0** cradle-to-gate factors supplemented by verified Environmental Product Declarations (EPDs):

$$E_{\text{upfront}} = \sum_{i \in \mathcal{M}} m_i \cdot \text{ECF}_{i} \cdot (1 + w_i) + E_{A4} + E_{A5} \quad [\text{kg CO}_2\text{e}]$$

Where:
- $m_i$: Net installed mass of material $i$ [$\text{kg}$ or $\text{m}^3$ or $\text{m}^2$].
- $\text{ECF}_i$: Cradle-to-gate (A1–A3) Embodied Carbon Factor from ICE v3.0 [$\text{kg CO}_2\text{e/unit}$].
- $w_i$: On-site construction wastage rate per RICS 2nd Edition (e.g. $5\%$ for structural concrete, $1\%$ for off-site precast/steel, $10\%$ for plasterboard/insulation).
- $E_{A4} = \sum_i m_i \cdot d_i \cdot \text{EF}_{\text{freight}}$: Transport to site, where $d_i$ is road/sea freight distance and $\text{EF}_{\text{freight}} = 0.1069\text{ kg CO}_2\text{e}/(\text{t}\cdot\text{km})$ for HGV.
- $E_{A5}$: On-site installation energy, site compound emissions, and disposal of construction waste per RICS defaults (£/turnover factor or $14\text{ kg CO}_2\text{e/m}^2\text{ GIA}$).

### 3.2. In-Use Embodied Carbon & MEP Replacement Cycles (Modules B1–B5)
For building fabric and building services (MEP), replacements occur when component service life $L_k$ is shorter than the 60-year Reference Study Period ($T_{\text{RSP}} = 60$):

$$E_{\text{replacement}} = \sum_{k \in \mathcal{K}} \left\lfloor \frac{T_{\text{RSP}} - 1}{L_k} \right\rfloor \cdot E_{\text{MEP}, k} \cdot (1 + \Delta_{\text{decarb}, k}) \quad [\text{kg CO}_2\text{e}]$$

Where:
- $L_k$: Component service life per CIBSE Guide M and RICS defaults (e.g. ASHP chillers $L = 15\text{ years}$, AHU fans $L = 20\text{ years}$, distribution pipework/ducts $L = 30\text{ years}$, LED fittings $L = 15\text{ years}$, curtain wall seals/double glazing units $L = 30\text{ years}$).
- $E_{\text{MEP}, k}$: CIBSE TM65 basic/mid-level embodied carbon of plant item $k$:
  $$E_{\text{MEP}, k} = M_k \cdot \text{ECF}_{\text{materials}} + E_{\text{refrigerant, init}}$$
- $\Delta_{\text{decarb}, k}$: Manufacturing decarbonisation coefficient reducing future replacement embodied carbon by $1.0\%$ compound annually.

### 3.3. Refrigerant Fugitive Emissions (Module B1 & End of Life C4)
Refrigerant leakage constitutes a massive hidden emission source in heat pump retrofits under **CIBSE TM65 §4.2** and **EU/UK F-Gas Regulations (Regulation (EU) 2024/573)**:

$$E_{\text{refrig}} = M_{\text{ref}} \cdot \text{GWP} \cdot \left[ \sum_{t=1}^{60} \alpha_{\text{leak}, t} + (1 - \eta_{\text{recov}}) \cdot \left( 1 + \left\lfloor \frac{T_{\text{RSP}} - 1}{L_{\text{HP}}} \right\rfloor \right) \right] \quad [\text{kg CO}_2\text{e}]$$

Where:
- $M_{\text{ref}}$: Initial refrigerant system charge [$\text{kg}$] (typically $0.35\text{--}0.50\text{ kg/kW}_{\text{th}}$ for direct expansion/VRF, $0.15\text{--}0.25\text{ kg/kW}_{\text{th}}$ for packaged modular chillers).
- $\text{GWP}$: 100-year Global Warming Potential per IPCC AR6 (R410A: $2,088$; R32: $675$; R1234ze: $<1$; R290 propane: $3$).
- $\alpha_{\text{leak}, t}$: Annual operational leakage rate ($3.5\%/\text{yr}$ for centralized chillers, $6.0\%/\text{yr}$ for split/VRF systems per BESA/CIBSE).
- $\eta_{\text{recov}}$: End-of-life and replacement recovery efficiency ($95\%$ under certified F-Gas technician handling; remaining $5\%$ vented to atmosphere in Module C4).

### 3.4. Dynamic Operational Carbon Across Grid Trajectories (Module B6)
Operational emissions are evaluated dynamically year-by-year ($t = 1 \dots 60$, from 2026 to 2086):

$$E_{\text{oper}} = \sum_{t=1}^{60} \left[ D_{\text{elec}, t} \cdot \text{EF}_{\text{grid}}(t) + D_{\text{gas}, t} \cdot \text{EF}_{\text{gas}} \right] \quad [\text{kg CO}_2\text{e}]$$

Where:
- $D_{\text{elec}, t}$: Annual net operational electricity demand [$\text{kWh/yr}$] accounting for solar PV self-consumption.
- $D_{\text{gas}, t}$: Annual natural gas demand [$\text{kWh/yr}$] (zero for all-electric retrofits and new builds).
- $\text{EF}_{\text{gas}} = 0.20288\text{ kg CO}_2\text{e/kWh}$ (DESNZ 2024 emissions factor).
- $\text{EF}_{\text{grid}}(t)$: Time-dependent grid carbon factor [$\text{kg CO}_2\text{e/kWh}$] evaluated across **3 distinct scenarios**:
  1. **National Grid ESO FES 'Leading the Way'**: Rapid power sector decarbonisation, falling from $0.120\text{ kg/kWh}$ (2026) to $0.012\text{ kg/kWh}$ by 2035, and $<0.005\text{ kg/kWh}$ by 2045.
  2. **DESNZ Green Book Central Projection**: Official UK Treasury appraisal trajectory, falling to $0.038\text{ kg/kWh}$ by 2035 and $0.010\text{ kg/kWh}$ by 2050.
  3. **Static Counterfactual (SAP 10.2 Baseline)**: Constant grid intensity ($0.136\text{ kg CO}_2\text{e/kWh}$ for electricity) demonstrating the historical analytical error of assuming static grid carbon.

### 3.5. Carbon Payback Horizon & Tipping-Point Dynamics
The carbon payback period ($t_{\text{payback}}$) of Intervention $A$ (e.g. Deep Retrofit) relative to Baseline Counterfactual $B$ is the earliest year $T^*$ satisfying:

$$\Delta E_{\text{upfront}} + \sum_{t=1}^{T^*} \Delta E_{\text{in-use embodied}, t} \le \sum_{t=1}^{T^*} \left( E_{\text{oper}, B}(t) - E_{\text{oper}, A}(t) \right)$$

Similarly, for New Build $N$ versus Deep Retrofit $R$:

$$t_{\text{breakeven}}(N \text{ vs } R) = \min \left\{ T^* \;\middle|\; \sum_{t=0}^{T^*} \left( E_{\text{WLC}, N}(t) - E_{\text{WLC}, R}(t) \right) \le 0 \right\}$$

If no such $T^* \le 60$ exists, the New Build creates an **irrecoverable whole-life carbon deficit**, proving that retention and retrofit is the superior net-zero strategy.

### 3.6. Life Cycle Costing (BS ISO 15686-5) & Marginal Abatement Cost
The financial model computes the **Net Present Value (NPV)** in real 2026 GBP (£) over 60 years using **HM Treasury Green Book** social time preference discount rates ($r_t = 3.5\%$ for years $1\text{--}30$; $r_t = 3.0\%$ for years $31\text{--}60$):

$$\text{NPV}_{\text{LCC}} = \text{CAPEX} + \sum_{t=1}^{60} \frac{C_{\text{energy}, t} + C_{\text{maint}, t} + C_{\text{replacement}, t}}{(1 + r_t)^t} \quad [\text{\pounds}]$$

Where:
- $\text{CAPEX}$: Upfront construction/retrofit capital expenditure benchmarked to **BCIS / Spon's 2026** commercial office data [$\text{\pounds/m}^2\text{ GIA}$].
- $C_{\text{energy}, t} = D_{\text{elec}, t} \cdot p_{\text{elec}}(t) + D_{\text{gas}, t} \cdot p_{\text{gas}}(t)$, with energy prices escalated per DESNZ retail projections.
- $C_{\text{replacement}, t}$: Financial cost of periodic MEP and envelope replacements.

The **Marginal Abatement Cost (MAC)** of transitioning from Baseline to Retrofit or New Build is:

$$\text{MAC} = \frac{\text{NPV}_{\text{LCC, scenario}} - \text{NPV}_{\text{LCC, baseline}}}{\text{WLC}_{\text{baseline}} - \text{WLC}_{\text{scenario}}} \quad [\text{\pounds/t CO}_2\text{e abated}]$$

A negative MAC indicates a "win-win" investment where operational energy bill savings exceed the upfront retrofit capital over the building lifecycle.

---

## 4. Techno-Economic & Emission Factor Reference Parameters

All embodied carbon factors are anchored to the **University of Bath ICE Database v3.0**, **CIBSE TM65**, and official UK government publications:

### 4.1. Material Embodied Carbon Factors (ICE Database v3.0 & EPDs)

| Building Element / Material | Specification / Standard | Cradle-to-Gate (A1–A3) Factor | Waste Rate ($w_i$) | Density / Unit | Source / Audit Ref |
|---|---|---|---|---|---|
| **Substructure Concrete (CEM I)** | Standard C30/37, 100% Portland | $0.158\text{ kg CO}_2\text{e/kg}$ ($380\text{ kg/m}^3$) | 5.0 % | $2,400\text{ kg/m}^3$ | ICE v3.0 Concrete |
| **Substructure Concrete (70% GGBS)**| Low-carbon C30/37, 70% blast slag | $0.052\text{ kg CO}_2\text{e/kg}$ ($125\text{ kg/m}^3$) | 5.0 % | $2,400\text{ kg/m}^3$ | ICE v3.0 Concrete / EPD |
| **Superstructure Structural Steel** | S355 UK section (60% scrap EAF/BF) | $1.550\text{ kg CO}_2\text{e/kg}$ | 1.0 % | $7,850\text{ kg/m}^3$ | ICE v3.0 Steel |
| **Reinforcing Steel (Rebar)** | High scrap content EAF ($>95\%$ scrap) | $0.760\text{ kg CO}_2\text{e/kg}$ | 5.0 % | $7,850\text{ kg/m}^3$ | ICE v3.0 Bar & Rod |
| **Cross-Laminated Timber (CLT)** | PEFC certified Spruce/Pine (Fossil A1-A3)| $0.280\text{ kg CO}_2\text{e/kg}$ ($126\text{ kg/m}^3$) | 1.5 % | $450\text{ kg/m}^3$ | EPD Stora Enso / ICE |
| **CLT Biogenic Sequestration** | Stored atmospheric carbon (RICS Module D)| $-1.640\text{ kg CO}_2\text{e/kg}$ ($-738\text{ kg/m}^3$)| — | $450\text{ kg/m}^3$ | EN 16449 / RICS rules |
| **Standard Double Glazing Unit** | 6mm toughened / 16mm argon / 6mm Low-E | $52.0\text{ kg CO}_2\text{e/m}^2\text{ pane}$ | 2.0 % | Per $\text{m}^2$ pane | ICE v3.0 Glass |
| **High-Performance Triple Glazing** | 6mm Low-E / 16mm Kr / 4mm / 16mm Kr / 6mm | $88.0\text{ kg CO}_2\text{e/m}^2\text{ pane}$ | 2.0 % | Per $\text{m}^2$ pane | Verified Saint-Gobain EPD |
| **Curtain Wall Aluminium Framing**| Thermally broken, 50% recycled billet | $6.800\text{ kg CO}_2\text{e/kg}$ | 3.0 % | $2,700\text{ kg/m}^3$ | ICE v3.0 Aluminium |
| **Mineral Wool Cavity Insulation** | Stone wool slab ($\lambda = 0.034\text{ W/mK}$) | $1.280\text{ kg CO}_2\text{e/kg}$ ($38.4\text{ kg/m}^3$)| 8.0 % | $30\text{ kg/m}^3$ | ICE v3.0 Insulation |
| **Wood-Fibre Bio-Insulation** | Flexible wood fibre batts | $0.310\text{ kg CO}_2\text{e/kg}$ ($15.5\text{ kg/m}^3$)| 5.0 % | $50\text{ kg/m}^3$ | Steico EPD |
| **Plasterboard Internal Lining** | 12.5mm standard gypsum board | $0.390\text{ kg CO}_2\text{e/kg}$ ($3.9\text{ kg/m}^2$) | 10.0 % | $10\text{ kg/m}^2$ | ICE v3.0 Plasterboard |

### 4.2. MEP Equipment & Refrigerant Parameters (CIBSE TM65 & F-Gas)

| Equipment / Carrier | TM65 Material Carbon | Service Life ($L_k$) | Refrigerant Type | Initial Charge ($M_{\text{ref}}$) | Annual Leakage ($\alpha_{\text{leak}}$) | End-of-Life Venting ($1-\eta_{\text{rec}}$) |
|---|---|---|---|---|---|---|
| **Commercial ASHP (Scenario 2)** | $16.5\text{ kg CO}_2\text{e/kW}_{\text{th}}$ | 15 years | **R290 (Propane)** ($\text{GWP} = 3$) | $0.18\text{ kg/kW}_{\text{th}}$ | 2.5 % / yr | 5.0 % |
| **Standard ASHP (Scenario 3)** | $18.2\text{ kg CO}_2\text{e/kW}_{\text{th}}$ | 15 years | **R32** ($\text{GWP} = 675$) | $0.32\text{ kg/kW}_{\text{th}}$ | 3.5 % / yr | 5.0 % |
| **Baseline Chiller (Scenario 1)** | $22.0\text{ kg CO}_2\text{e/kW}_{\text{th}}$ | 15 years | **R410A** ($\text{GWP} = 2,088$) | $0.45\text{ kg/kW}_{\text{th}}$ | 5.0 % / yr | 10.0 % |
| **Air Handling Units (MVHR)** | $12.0\text{ kg CO}_2\text{e}/(\text{m}^3/\text{h})$| 20 years | None (hydronic coils) | — | — | — |
| **Distribution Pipework & Ducts**| $28.0\text{ kg CO}_2\text{e/m}^2\text{ GIA}$ | 30 years | Water / Air | — | — | — |
| **Rooftop Solar PV Array** | $620\text{ kg CO}_2\text{e/kWp}$ | 25 years | Monocrystalline Si | — | — | — |

### 4.3. Financial Cost & Energy Tariff Benchmarks (BCIS / Spon's 2026)

| Parameter | Baseline (Scenario 1) | Deep Retrofit (Scenario 2) | Standard New Build (Scenario 3) | Timber New Build (Scenario 4) |
|---|---|---|---|---|
| **Upfront CAPEX (£/m² GIA)** | £420 / m² | £1,450 / m² | £2,450 / m² | £2,850 / m² |
| **Demolition & Site Clearance** | £0 / m² | £35 / m² (strip-out) | £165 / m² (full deconstruction) | £185 / m² (selective deconstruction) |
| **MEP Replacement Capex (% initial)**| 100 % every 15 yr | 80 % every 15 yr | 85 % every 15 yr | 80 % every 15 yr |
| **Annual Routine Maintenance** | £14.50 / m² / yr | £18.20 / m² / yr | £19.50 / m² / yr | £21.00 / m² / yr |
| **Electricity Tariff (2026 Baseline)**| £0.240 / kWh (real) | £0.240 / kWh (real) | £0.240 / kWh (real) | £0.240 / kWh (real) |
| **Natural Gas Tariff (2026 Baseline)**| £0.075 / kWh (real) | N/A (all-electric) | N/A (all-electric) | N/A (all-electric) |
| **HM Treasury Discount Rate** | 3.5% (Yr 1–30) / 3.0% (Yr 31–60) | Same | Same | Same |
| **DESNZ Shadow Carbon Value (2026)**| £268 / t CO₂e (real 2026 £) rising to £378 / t by 2050 and £450 / t by 2086 |

---

## 5. Standard Repository Architecture

```
Whole-Carbon-Lifecycle-Assessment/
├── GEMINI.md                                  ← This governance & technical specification file
├── README.md                                  ← 5-Stage Executive Showcase README
├── requirements.txt                           ← Pinned dependencies (pandas, openpyxl, matplotlib, seaborn, scipy)
├── .gitignore                                 ← Standard Python / data gitignore
│
├── src/                                       ← Production Python calculation modules
│   ├── __init__.py
│   ├── config.py                              ← Building geometry, financial params, discount rates, EUI baselines
│   ├── inventory.py                           ← Bill of Quantities (BoQ) engine for all 4 intervention scenarios
│   ├── emission_factors.py                    ← ICE Database v3.0, CIBSE TM65 MEP factors, EPD lookups, F-Gas GWPs
│   ├── grid_decarbonisation.py                ← 2026–2086 dynamic grid models (FES Leading the Way, DESNZ Central, SAP 10.2)
│   ├── carbon_calculator.py                   ← EN 15978 / RICS engine: Modules A1–A5, B1–B5, B6, C1–C4, and Module D
│   ├── lcc_calculator.py                      ← BS ISO 15686-5 Capex, 60-year replacement Opex, energy bills, NPV & MAC
│   ├── benchmarking.py                        ← LETI Climate Emergency, RIBA 2030, and UK NZCBS scoring engine
│   └── plotting.py                            ← Publication-grade visual generator (Extended 6-Figure Suite)
│
├── notebooks/                                 ← Interactive showcase notebooks
│   └── whole_life_carbon_exploration.ipynb    ← Interactive scenario analysis, sensitivity sweeps & visualizations
│
├── data/                                      ← Transparent tabular input datasets
│   ├── bill_of_quantities.csv                 ← Elemental material quantities (substructure, frame, envelope, finishes, MEP)
│   ├── ice_database_v3_factors.csv            ← Cleaned University of Bath ICE v3.0 carbon intensity factors
│   ├── grid_emission_trajectories_2026_2086.csv ← Official DESNZ and National Grid ESO annual kg CO₂e/kWh projections
│   └── cost_benchmarks_rics_bcis.csv          ← BCIS capital cost and maintenance benchmarks (£/m² GIA)
│
├── figures/                                   ← High-resolution exported figures (PNG & SVG)
│   ├── fig1_wlc_stage_breakdown.png           (and .svg)
│   ├── fig2_cumulative_carbon_payback.png     (and .svg)
│   ├── fig3_spatial_elemental_breakdown.png   (and .svg)
│   ├── fig4_mep_refrigerant_fgas_tradeoff.png (and .svg)
│   ├── fig5_techno_economic_carbon_cost_frontier.png (and .svg)
│   └── fig6_leti_riba_benchmark_compliance.png (and .svg)
│
└── main.py                                    ← CLI entry point to run full assessment and export deliverables
```

---

## 6. The Extended 6-Figure Publication Suite

Every generated figure must adhere to master publication standards: clean minimalist whitegrid styling (`seaborn-v0_8-whitegrid`), simple captions and axis labels with explicit physical units enclosed in brackets (e.g. `Embodied Carbon [kg CO₂e/m² GIA]`, `Net Present Value [£/m² GIA]`, `Time [Years]`), pure black fonts exclusively (`#000000` / `'black'`), legend positioned below the graph, zero in-plot annotations (strictly legend only), mandatory true visual inspection of exported image files to ensure complete clarity, and exported at 300 DPI PNG and vector SVG.

1. **Figure 1 — WLC Life Cycle Module Breakdown Stack (`fig1_wlc_stage_breakdown`)**:
   - Stacked bar chart comparing the 4 scenarios across EN 15978 life cycle modules:
     - Upfront Embodied (A1–A5) [Dark Blue]
     - In-Use Embodied & Replacements (B1–B5) [Orange]
     - Operational Energy (B6) over 60 years [Red/Crimson]
     - End of Life (C1–C4) [Grey]
     - Module D Circular Credits (hatched green bar extending below the axis).
   - Shows total Whole-Life Carbon intensity ($\text{kg CO}_2\text{e/m}^2\text{ GIA}$) with direct comparison against LETI and RIBA 2030 limits.

2. **Figure 2 — 60-Year Dynamic Cumulative Carbon Payback (`fig2_cumulative_carbon_payback`)**:
   - 2-panel comparative chart:
     - Top Panel: Cumulative $\text{t CO}_2\text{e}$ trajectories from Year 0 to Year 60 under **DESNZ Green Book Central Grid**, highlighting the upfront carbon spike at Year 0 for demolition/new build and the carbon payback intersection point between Deep Retrofit and New Build.
     - Bottom Panel: Sensitivity comparison showing cumulative carbon trajectories under **FES 'Leading the Way'** (where new build *never* catches up to retrofit) versus **Static SAP 10.2** (illustrating the historical distortion where operational energy appeared to justify demolition).

3. **Figure 3 — Spatial & Elemental Carbon Intensity (`fig3_spatial_elemental_breakdown`)**:
   - Horizontal grouped bar chart breaking down upfront embodied carbon (A1–A5) by functional building element across the 4 scenarios:
     - Substructure & Foundations
     - Superstructure Frame & Upper Floors
     - Facade & External Envelope
     - Internal Finishes & Partitions
     - Building Services (MEP Plant & Distribution).
   - Visualizes how structural retention eliminates $>65\%$ of upfront embodied carbon in Deep Retrofit.

4. **Figure 4 — MEP & Refrigerant Fugitive Emissions Trade-off (`fig4_mep_refrigerant_fgas_tradeoff`)**:
   - Sankey / Grouped component waterfall isolating HVAC/MEP lifecycle carbon under CIBSE TM65:
     - Initial Plant Embodied (heat pump casing, compressors, copper heat exchangers)
     - Distribution infrastructure (ductwork, hydronic piping)
     - Periodic B4 Plant Replacements (Year 15, 30, 45)
     - B1 Operational Refrigerant Leakage comparing **R410A** vs. **R32** vs. **R290 (propane)**
     - C4 End-of-Life Venting losses.
   - Highlights that high-GWP refrigerant leakage can exceed the entire physical embodied carbon of the heat pump machinery itself.

5. **Figure 5 — Techno-Economic Pareto Frontier & Marginal Abatement Cost (`fig5_techno_economic_carbon_cost_frontier`)**:
   - Dual-currency engineering Pareto plot:
     - X-axis: 60-Year Whole Life Carbon [$\text{t CO}_2\text{e}$ or $\text{kg CO}_2\text{e/m}^2$].
     - Y-axis: 60-Year Life Cycle Cost Net Present Value ($\text{NPV}_{\text{LCC}}$ [$\text{\pounds/m}^2\text{ GIA}$]).
     - Annotations: Marginal Abatement Cost ($\text{MAC}$ in $\text{\pounds/t CO}_2\text{e}$ abated) between Baseline $\to$ Deep Retrofit, and Deep Retrofit $\to$ Low-Carbon New Build.
     - Identifies the economically optimal, carbon-minimal design frontier.

6. **Figure 6 — LETI & RIBA 2030 Benchmark Compliance Matrix (`fig6_leti_riba_benchmark_compliance`)**:
   - Executive scorecard matrix and gauge visual:
     - Panel A: Upfront Embodied Carbon (A1–A5) benchmarked against LETI Band A ($<300$), Band B ($<450$), Band C ($<600$), and RIBA 2030 Office Target ($<500\text{ kg CO}_2\text{e/m}^2$).
     - Panel B: Operational Energy Intensity ($\text{kWh/m}^2/\text{yr}$) against LETI Target ($55\text{ kWh/m}^2/\text{yr}$) and UK NZCBS limits.
     - Displays letter grades (A++ to G) for all 4 scenarios.

> **Portfolio Bridge Rule**: The two top hero figures (`fig1_wlc_stage_breakdown.png` and `fig2_cumulative_carbon_payback.png`) must be synced to `/home/fraser/Life/Career/Job-Applications/Portfolio/figures/` upon execution.

---

## 7. Developer & Agent Operational Instructions

### 7.1. Python Environment & Dependencies
- Use an isolated virtual environment containing pinned data science and carbon accounting dependencies:
  ```bash
  cd /home/fraser/Code/Portfolio/Whole-Carbon-Lifecycle-Assessment
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  ```
- Core libraries: `pandas >= 2.0.0`, `numpy >= 1.24.0`, `openpyxl >= 3.1.0`, `matplotlib >= 3.7.0`, `seaborn >= 0.12.0`, `scipy >= 1.10.0`.

### 7.2. CLI Execution Commands
- Execute the complete baseline whole-life carbon and life cycle costing calculation:
  ```bash
  python main.py --run-all --export-figures
  ```
- Run sensitivity sweeps across grid decarbonisation trajectories:
  ```bash
  python main.py --sweep-grid --sweep-refrigerants
  ```
- Generate and sync hero figures to portfolio collateral:
  ```bash
  python main.py --sync-collateral
  ```

### 7.3. Standards Compliance & Verification Rules
- **RICS 2nd Edition Mandatory Rules**:
  - Biogenic carbon sequestered in timber must be reported separately and cannot be subtracted from upfront A1–A5 fossil emissions.
  - Module D benefits (reuse, recycling, energy recovery) must be reported as a separate information module and never aggregated into net A1–C4 whole-life carbon totals.
- **Source Traceability**:
  - All material carbon intensities must explicitly reference a specific table row in `ice_database_v3_factors.csv` or verified manufacturer EPD number.
  - All MEP calculations must cite CIBSE TM65 equation numbers.
- **Truth in Advertising**:
  - Clearly identify the building as an archetype model representing typical 1980s/90s UK commercial office stock rather than an as-built single structure.
  - Maintain absolute consistency with `/home/fraser/Life/Career/Job-Applications/Portfolio/SOURCES.md`.

### 7.4. Strict Code & Visual Standards: OOP, Minimal Comments & `/grill-me`
All code, carbon accounting calculators, LCC engines, and plotting modules in this repository must strictly adhere to the following standards:

1. **Strict Object-Oriented Architecture**:
   - All modules (`BuildingInventory`, `EmissionFactorDatabase`, `GridDecarbonisationModel`, `WholeLifeCarbonEngine`, `LifeCycleCostingEngine`, `SustainabilityBenchmarkScorer`, `WLCPlotter`) must be written as class- and object-oriented Python modules.
   - Sprawling procedural scripts or flat function files are prohibited. Encapsulate material quantities, life cycle stages, discount factors, and compliance metrics into cohesive domain classes.

2. **Minimal, High-Signal Comments**:
   - Code must be clear, concise, and self-documenting through expressive variable and method naming.
   - Zero redundant comments: Never write comments explaining obvious syntax or routine steps.
   - Keep comments strictly minimal, reserved only for EN 15978 / RICS / CIBSE TM65 standard formulas, Treasury Green Book discounting equations, or critical baseline assumptions.

3. **Clear and Concise Implementation**:
   - Maintain lean classes and methods with a high signal-to-noise ratio. Eliminate boilerplate, dead code, and speculative abstractions.

4. **Strict Publication-Grade Visual Standards**:
   - **No In-Plot Annotations (Legend Only)**: Strictly legend only. No floating text annotations, callout arrows, or text labels inside the axes (`ax.annotate`, `ax.text`).
   - **Legend Below Graph**: The legend must strictly be positioned below the graph (outside the plot area, horizontal orientation/columns) to ensure zero obstruction of data.
   - **Captions & Axis Labels**: Wording for captions and axis labels must be simple, direct, and concise, with explicit physical units enclosed in brackets on all axes (e.g. `Embodied Carbon [kg CO₂e/m²]`, `Net Present Value [£/m²]`, `Time [Years]`).
   - **Pure Black Fonts**: All typography across every figure (titles, axis labels, tick numbers, legend text) must strictly be pure black (`#000000` / `'black'`). No grey, light-toned, or faded text.
   - **Mandatory True Visual Inspection**: Every generated figure must undergo a true visual inspection (inspecting the rendered image file) to ensure all stacked bars, trajectory lines, Pareto frontiers, and legends are completely visible, crisp, legible, and unclipped.

5. **Interactive Alignment via `/grill-me`**:
   - For ANY ambiguities, uncertainties, or design choices regarding how codes, simulations, or graphs should be generated, agents MUST trigger `/grill-me` (or interview the user via structured interactive questions) before making assumptions or writing speculative code.


