import json
import numpy as np

# Let's write a comprehensive audit of the numbers:
# 1. Levelised Cost of Heat (LCOH)
# 2. Crop Cost & Carbon Thresholds
# 3. Offtake & Revenue Scenarios (CIF vs Wholesale vs Retail Contract)
# 4. CAPEX & OPEX Ceilings
# 5. Financial Project Metrics (1 ha Scottish Glasshouse Model)

def lcoh_calc(heat_demand_kwh_m2, scop, elec_price, hp_capex_kw, design_kw_m2, life=20, rate=0.035, om=0.02):
    ann = rate / (1 - (1 + rate)**-life)
    cap = design_kw_m2 * hp_capex_kw * 1.18 # incl install
    ann_cap = cap * ann
    ann_om = cap * om
    elec_kwh = heat_demand_kwh_m2 / scop
    ann_elec = elec_kwh * elec_price
    tot_cost = ann_cap + ann_om + ann_elec # GBP/m2/yr
    lcoh_gbp_mwh = (tot_cost / (heat_demand_kwh_m2 / 1000)) # GBP/MWh_th
    lcoh_p_kwh = lcoh_gbp_mwh / 10 # p/kWh_th
    return lcoh_gbp_mwh, lcoh_p_kwh, ann_cap, ann_elec

print("=== 1. LEVELISED COST OF HEAT (LCOH) AUDIT IN PERTHSHIRE ===")
# Tomato heat demand in Perthshire = 169 kWh/m2
# Peak heat loss = 0.12 kW/m2 (or 120 W/m2)
print("Scenario | SCOP | Elec Price (p/kWh) | HP Skid (£/kW) | LCOH (£/MWh_th) | LCOH (p/kWh_th)")
scenarios = [
    ("Air-Source (Baseline Offgrid)", 3.27, 49.0, 990, 0.12),
    ("Air-Source (Grid 17.3p)", 3.27, 17.3, 990, 0.12),
    ("Air-Source (Utility PPA 10p)", 3.27, 10.0, 990, 0.12),
    ("Air-Source (Optimised Skid £600)", 3.50, 10.0, 600, 0.12),
    ("Water/WWTP Source (SCOP 4.5)", 4.50, 10.0, 850, 0.10),
    ("Distillery Direct Waste Heat", 99.0, 2.0, 150, 0.10), # just plate HX + pump
]

for name, scop, ep, hp_c, d_kw in scenarios:
    gbp_mwh, p_kwh, c_cap, c_el = lcoh_calc(169.0, scop, ep/100, hp_c, d_kw)
    print(f"{name:<30} | {scop:4.2f} | {ep:5.1f} | £{hp_c:4.0f} | £{gbp_mwh:5.1f}/MWh | {p_kwh:4.2f} p/kWh")

print("\nConventional Scottish Heating Benchmarks:")
print("  Natural Gas Boiler (Grid):      £45 - £60 / MWh_th (4.5 - 6.0 p/kWh)")
print("  Biomass Boiler (Woodchip/Pellet): £65 - £85 / MWh_th (6.5 - 8.5 p/kWh)")
print("  LPG / Kerosene (Rural off-grid): £90 - £125 / MWh_th (9.0 - 12.5 p/kWh)")
print("  Direct Electric Resistance:     £180 - £220 / MWh_th (18 - 22 p/kWh)")

print("\n=== 2. FINANCIAL MODEL: 1 HECTARE SCOTTISH GLASSHOUSE (TOMATO & CUCUMBER) ===")
# 1 ha = 10,000 m2
# Compare 3 power/heat supply models:
# Model A: Air HP + Dedicated Off-grid Wind (Current model in SCOPE.md)
# Model B: Air HP + Grid-Backed Wind / PPA (10p/kWh)
# Model C: Industrial Waste Heat (Distillery / WWTP) + PPA

cases = [
    {"name": "Model A: Air HP + Offgrid Wind (Current)", "elec_p": 0.49, "scop": 3.27, "hp_capex": 990, "crop": "tomato", "yield": 35.9, "price_sale": 1.60},
    {"name": "Model B1: Air HP + PPA @ Import CIF", "elec_p": 0.10, "scop": 3.40, "hp_capex": 800, "crop": "tomato", "yield": 38.0, "price_sale": 1.60},
    {"name": "Model B2: Air HP + PPA @ Wholesale", "elec_p": 0.10, "scop": 3.40, "hp_capex": 800, "crop": "tomato", "yield": 38.0, "price_sale": 1.85},
    {"name": "Model B3: Air HP + PPA @ Supermarket Contract", "elec_p": 0.10, "scop": 3.40, "hp_capex": 800, "crop": "tomato", "yield": 40.0, "price_sale": 2.10},
    {"name": "Model C: Distillery Waste Heat + PPA", "elec_p": 0.10, "scop": 15.0, "hp_capex": 250, "crop": "tomato", "yield": 42.0, "price_sale": 2.10},
    {"name": "Model B-Cuc: Air HP + PPA @ Import CIF", "elec_p": 0.10, "scop": 3.20, "hp_capex": 800, "crop": "cucumber", "yield": 50.0, "price_sale": 1.40},
    {"name": "Model B-Cuc: Air HP + PPA @ Wholesale", "elec_p": 0.10, "scop": 3.20, "hp_capex": 800, "crop": "cucumber", "yield": 50.0, "price_sale": 1.65},
]

# Glasshouse structure CAPEX: £200/m2 = £2,000,000 / ha
# HP capex: design_kw * hp_capex
# Working capital / other: £200k

for c in cases:
    area = 10000.0 # m2
    y = c["yield"] # kg/m2
    tot_yield_kg = y * area
    p_sale = c["price_sale"]
    revenue = tot_yield_kg * p_sale
    
    # Capex
    d_kw = 1200.0 # 120 W/m2 for 1 ha
    hp_cap = d_kw * c["hp_capex"] * 1.18
    struct_cap = 200.0 * area
    tot_capex = struct_cap + hp_cap
    
    # Opex
    # Non-energy, non-capital opex per kg from our audit:
    # Tomato: labour=£0.38, O&M=£0.19, CO2=£0.14, Pack=£0.15 => £0.86/kg
    # Cucumber: labour=£0.25, O&M=£0.15, CO2=£0.10, Pack=£0.10 => £0.60/kg
    base_opex_kg = 0.86 if c["crop"] == "tomato" else 0.60
    fixed_opex = base_opex_kg * tot_yield_kg
    
    # Energy opex
    heat_kwh = (169.0 if c["crop"] == "tomato" else 270.0) * area
    comp_elec = heat_kwh / c["scop"]
    aux_elec = 11.0 * area
    tot_elec = comp_elec + aux_elec
    energy_opex = tot_elec * c["elec_p"]
    
    tot_opex = fixed_opex + energy_opex
    ebitda = revenue - tot_opex
    
    # Depreciation over 25 yrs
    depr = tot_capex / 25.0
    ebit = ebitda - depr
    
    # Simple Payback
    payback = tot_capex / ebitda if ebitda > 0 else float("inf")
    
    # Simple 20-yr Project IRR approx
    # NPV at r=0.08:
    r = 0.08
    ann_factor = (1 - (1+r)**-20) / r
    npv = -tot_capex + ebitda * ann_factor
    # IRR
    irr_range = np.linspace(-0.1, 0.4, 501)
    npvs = [-tot_capex + sum(ebitda / (1+ir)**t for t in range(1, 21)) for ir in irr_range]
    try:
        idx = np.where(np.diff(np.sign(npvs)))[0][0]
        irr = irr_range[idx] * 100
    except:
        irr = -99.0
        
    print(f"\n{c['name']}:")
    print(f"  CAPEX: £{tot_capex/1e6:.2f}M | Revenue: £{revenue/1e3:.0f}k/yr (@ £{p_sale:.2f}/kg)")
    print(f"  OPEX: £{tot_opex/1e3:.0f}k/yr (Fixed £{fixed_opex/1e3:.0f}k, Energy £{energy_opex/1e3:.0f}k)")
    print(f"  EBITDA: £{ebitda/1e3:.0f}k/yr (Margin: {ebitda/revenue*100:.1f}%)")
    print(f"  Simple Payback: {payback:.1f} yrs | 20-yr IRR: {irr:.1f}% | NPV(8%): £{npv/1e3:.0f}k")
