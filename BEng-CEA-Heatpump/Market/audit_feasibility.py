"""audit_feasibility.py - Sourced Crop Breakeven & Yield Hurdle Audit for Scottish CEA

Sources:
- Simulation Dataset: BEng-CEA-Heatpump/lca/results/perthshire/results.json and sim.json
  (Hourly Carse of Gowrie ERA5 2023 climate, Numba-compiled dynamic thermal model, CoolProp R717 map)
- Import Trade Benchmarks: UN Comtrade 2023-2025 volume-weighted CIF border prices
- Transport Factors: DESNZ 2025 freight conversion factors with +460-500 km Scottish RDC haulage uplift
- Baseline Rates: SAC/SRUC Table 11 (£200/m2 glasshouse), Table 17 (£2,500/kW wind), DESNZ 17.3 p/kWh electricity
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent / "lca"

with open(REPO / "results" / "perthshire" / "sim.json") as f:
    ps = json.load(f)

print("--- PERTHSHIRE SIMULATION OUTPUTS (Carse of Gowrie) ---")
for p in ps:
    case = p["case"]
    heat = p["heat_kWh_m2"]
    elec = p["electricity_kWh_m2"]
    comp = p["comp_kWh_m2"]
    aux = p["aux_kWh_m2"]
    scop = p["scop_unit"]
    yield_val = p.get("crop_yield_t_ha", float("nan"))
    print(f"{case:<25}: Heat={heat:6.1f} kWh/m2 | Elec={elec:5.1f} kWh/m2 (Comp={comp:4.1f}, Aux={aux:4.1f}) | SCOP={scop:4.2f} | Yield={yield_val:5.1f} t/ha")

with open(REPO / "results" / "perthshire" / "results.json") as f:
    res = json.load(f)

print("\n--- PERTHSHIRE DETAILED COST & CARBON BREAKDOWN (AIR SOURCE, BASE WIND) ---")
for row in res["rows"]:
    c = row["crop"]
    name = row["name"]
    ab = row["air_base"]
    y = ab["yield"] # kg/m2
    c_tot = ab["gbp"] # GBP/kg
    kg_co2 = ab["kg"] # kg CO2e/kg
    imp_p = row["imports_gbp"]
    imp_c = row["imports_kg"]
    cost_brk = ab["cost"]
    
    print(f"\nCrop: {name} (Yield = {y:.2f} kg/m2)")
    print(f"  Import CIF: £{imp_p:.2f}/kg | Carbon: {imp_c:.2f} kg CO2e/kg")
    print(f"  Scottish Air+Wind: £{c_tot:.2f}/kg | Carbon: {kg_co2:.2f} kg CO2e/kg")
    print(f"  Cost breakdown (£/kg): Cap=£{cost_brk['capital']:.2f}, O&M=£{cost_brk['o_and_m']:.2f}, Lab=£{cost_brk['labour']:.2f}, Elec=£{cost_brk['electricity']:.2f}, CO2=£{cost_brk['co2']:.2f}, Pack=£{cost_brk['packing']:.2f}")
    
    # Specific electric kWh per kg
    e_price = ab["offgrid"]["price"]
    kwh_kg = cost_brk["electricity"] / e_price if e_price > 0 else 0
    non_elec = c_tot - cost_brk["electricity"]
    
    # Thresholds:
    # 1. Breakeven electricity price to beat Import CIF
    be_pe_cif = (imp_p - non_elec) / kwh_kg if kwh_kg > 0 else None
    
    # 2. Breakeven electricity price to beat DEFRA Wholesale (if available)
    # 3. Breakeven yield to beat Import CIF at grid electricity (17.3 p/kWh)
    # Total annual cost per m2 excl electricity = non_elec * y
    ann_non_elec_m2 = non_elec * y
    elec_kwh_m2 = kwh_kg * y
    # At grid price 0.173:
    ann_cost_grid_m2 = ann_non_elec_m2 + elec_kwh_m2 * 0.173
    req_yield_grid_cif = ann_cost_grid_m2 / (imp_p - cost_brk["packing"]) # packing is per kg
    
    # At wind PPA price 0.10:
    ann_cost_ppa_m2 = ann_non_elec_m2 + elec_kwh_m2 * 0.10
    req_yield_ppa_cif = ann_cost_ppa_m2 / (imp_p - cost_brk["packing"])
    
    print(f"  Energy intensity: {kwh_kg:.2f} kWh_e/kg | Delivered Elec Price: {e_price*100:.1f} p/kWh")
    if be_pe_cif is not None:
        print(f"  -> Breakeven Elec Price vs CIF (£{imp_p:.2f}/kg): {be_pe_cif*100:.1f} p/kWh")
    print(f"  -> Required Yield @ 17.3p Grid: {req_yield_grid_cif:.1f} kg/m2 (Current = {y:.1f} kg/m2, +{(req_yield_grid_cif/y - 1)*100:.1f}%)")
    print(f"  -> Required Yield @ 10.0p PPA:  {req_yield_ppa_cif:.1f} kg/m2 (Current = {y:.1f} kg/m2, +{(req_yield_ppa_cif/y - 1)*100:.1f}%)")
