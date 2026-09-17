import argparse
from pathlib import Path
import shutil
import sys
import pandas as pd

from src.config import BuildingArchetype, EconomicParameters, SCENARIO_CONFIGS
from src.emission_factors import EmissionFactorDatabase
from src.grid_decarbonisation import GridDecarbonisationModel
from src.inventory import BuildingInventory
from src.carbon_calculator import WholeLifeCarbonEngine
from src.lcc_calculator import LifeCycleCostingEngine
from src.benchmarking import SustainabilityBenchmarkScorer
from src.plotting import WLCPlotter


def run_pipeline(
    export_figures: bool = True,
    sweep_grid: bool = False,
    sweep_refrigerants: bool = False,
    sync_collateral: bool = False,
) -> None:
    print("\n" + "=" * 80)
    print("WHOLE-LIFE CARBON & LIFE CYCLE COSTING SIMULATION ENGINE")
    print("EN 15978:2011 / BS ISO 15686-5:2017 / RICS 2nd Edition (2023)")
    print("Archetype: 5-Storey UK Commercial Office (7,500 m² GIA)")
    print("=" * 80 + "\n")

    # 1. Initialize Engines
    archetype = BuildingArchetype()
    econ = EconomicParameters()
    db = EmissionFactorDatabase()
    grid = GridDecarbonisationModel()
    inventory = BuildingInventory(archetype=archetype)

    carbon_engine = WholeLifeCarbonEngine(db=db, grid=grid, inventory=inventory, archetype=archetype)
    lcc_engine = LifeCycleCostingEngine(econ_params=econ, archetype=archetype, grid_model=grid)
    scorer = SustainabilityBenchmarkScorer()

    # 2. Run Calculations
    print("[1/4] Computing Whole-Life Carbon accounting (Modules A1-C4 + Module D)...")
    carbon_results = carbon_engine.calculate_all()

    print("[2/4] Computing BS ISO 15686-5 Life Cycle Costing & HM Treasury NPV...")
    lcc_results = lcc_engine.calculate_all(carbon_results)

    print("[3/4] Scoring against LETI, RIBA 2030, and UK NZCBS benchmarks...")
    benchmark_results = scorer.score_all(carbon_results)

    # 3. Print Executive Summary Table
    print("\n" + "-" * 80)
    print("EXECUTIVE ASSESSMENT SUMMARY TABLE (DESNZ Green Book Central Grid, 60-Yr RSP)")
    print("-" * 80)

    summary_rows = []
    for sc_id in ["scenario_1", "scenario_2", "scenario_3", "scenario_4"]:
        c = carbon_results[sc_id]
        l = lcc_results[sc_id]
        b = benchmark_results[sc_id]
        name = SCENARIO_CONFIGS[sc_id].short_name

        summary_rows.append(
            {
                "Scenario": name,
                "A1-A5 Upfront [kg/m²]": round(c.upfront_per_m2(), 1),
                "B1-B5 In-Use [kg/m²]": round(c.b1_b5_inuse_embodied / c.gia, 1),
                "B6 Oper 60-Yr [kg/m²]": round(c.operational_per_m2("desnz_central"), 1),
                "C1-C4 EOL [kg/m²]": round(c.c1_c4_end_of_life / c.gia, 1),
                "Net WLC [kg/m²]": round(c.total_wlc_per_m2("desnz_central"), 1),
                "Module D [kg/m²]": round(c.module_d_credits / c.gia, 1),
                "Upfront Capex [£/m²]": round(l.upfront_capex_per_m2(), 0),
                "60-Yr NPV [£/m²]": round(l.financial_npv_per_m2(), 0),
                "MAC [£/t]": round(l.marginal_abatement_cost_gbp_per_tonne, 1) if sc_id != "scenario_1" else "-",
                "LETI Band": b.leti_embodied_band,
                "RIBA 2030": "PASS" if b.riba_2030_pass else "FAIL",
                "NZCBS": "PASS" if (b.nzcbs_upfront_pass and b.nzcbs_operational_pass) else "FAIL",
            }
        )

    summary_df = pd.DataFrame(summary_rows)
    print(summary_df.to_string(index=False))
    print("-" * 80)

    # Dynamic Carbon Payback Calculation
    base_res = carbon_results["scenario_1"]
    retrofit_res = carbon_results["scenario_2"]
    newbuild_res = carbon_results["scenario_3"]

    payback_retrofit = carbon_engine.calculate_payback_years(base_res, retrofit_res, "desnz_central")
    payback_newbuild = carbon_engine.calculate_payback_years(retrofit_res, newbuild_res, "desnz_central")
    payback_fes = carbon_engine.calculate_payback_years(retrofit_res, newbuild_res, "fes_leading_way")

    print(f"\n[KEY ENGINEERING FINDINGS]")
    print(f"• Deep Retrofit carbon payback vs Baseline Counterfactual: Year {payback_retrofit} (DESNZ Central)")
    if payback_newbuild is None:
        print("• Standard New Build vs Deep Retrofit: Never breaks even (irrecoverable carbon deficit)")
    else:
        print(f"• Standard New Build vs Deep Retrofit breakeven: Year {payback_newbuild}")
    if payback_fes is None:
        print("• Under ESO 'Leading the Way' grid decarb: New Build NEVER catches up to Deep Retrofit.")

    # 4. Generate Figures
    if export_figures:
        print("\n[4/4] Generating Extended 6-Figure Publication Suite...")
        plotter = WLCPlotter()
        generated = plotter.generate_all_figures(carbon_results, lcc_results, benchmark_results)
        for fig_name, fig_path in generated.items():
            print(f"  ✓ Saved {fig_name}: {fig_path.name}")

    # 5. Grid Trajectory Sensitivity Sweep
    if sweep_grid:
        print("\n" + "-" * 80)
        print("GRID DECARBONISATION SENSITIVITY SWEEP (60-Year Whole Life Carbon [kg CO₂e/m² GIA])")
        print("-" * 80)
        grid_rows = []
        for sc_id, sc_cfg in SCENARIO_CONFIGS.items():
            c = carbon_results[sc_id]
            grid_rows.append(
                {
                    "Scenario": sc_cfg.short_name,
                    "DESNZ Central [kg/m²]": round(c.total_wlc_per_m2("desnz_central"), 1),
                    "ESO Leading the Way [kg/m²]": round(c.total_wlc_per_m2("fes_leading_way"), 1),
                    "Static SAP 10.2 [kg/m²]": round(c.total_wlc_per_m2("sap10_static"), 1),
                }
            )
        print(pd.DataFrame(grid_rows).to_string(index=False))
        print("-" * 80)

    # 6. Refrigerant Sensitivity Sweep
    if sweep_refrigerants:
        print("\n" + "-" * 80)
        print("CIBSE TM65 REFRIGERANT LIFE CYCLE EMISSIONS (60-Year Fugitive & Venting [kg CO₂e/m² GIA])")
        print("-" * 80)
        ref_rows = []
        for sc_id, sc_cfg in SCENARIO_CONFIGS.items():
            c = carbon_results[sc_id]
            ref_leakage_m2 = c.b1_refrigerant_leakage / c.gia
            ref_venting_m2 = (c.c4_disposal_and_venting - 1.5 * c.gia) / c.gia
            ref_rows.append(
                {
                    "Scenario": sc_cfg.short_name,
                    "Refrigerant": sc_cfg.refrigerant_type,
                    "GWP (100-Yr)": db.get_refrigerant_gwp(sc_cfg.refrigerant_type),
                    "B1 In-Use Leakage [kg/m²]": round(ref_leakage_m2, 1),
                    "C4 EOL Venting [kg/m²]": round(ref_venting_m2, 1),
                    "Total Refrigerant [kg/m²]": round(ref_leakage_m2 + ref_venting_m2, 1),
                }
            )
        print(pd.DataFrame(ref_rows).to_string(index=False))
        print("-" * 80)

    # 7. Portfolio Collateral Synchronization
    if sync_collateral:
        portfolio_dir = Path("/home/fraser/Life/Career/Job-Applications/Portfolio/figures")
        portfolio_dir.mkdir(parents=True, exist_ok=True)
        fig1_src = Path(__file__).parent / "figures" / "fig1_wlc_stage_breakdown.png"
        fig2_src = Path(__file__).parent / "figures" / "fig2_cumulative_carbon_payback.png"

        if fig1_src.exists() and fig2_src.exists():
            shutil.copy2(fig1_src, portfolio_dir / "fig1_wlc_stage_breakdown.png")
            shutil.copy2(fig2_src, portfolio_dir / "fig2_cumulative_carbon_payback.png")
            print(f"\n✓ Portfolio Hero Figures synchronized to: {portfolio_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Whole Life Carbon and Life Cycle Costing Engine.")
    parser.add_argument("--run-all", action="store_true", default=True, help="Run complete assessment pipeline.")
    parser.add_argument("--export-figures", action="store_true", default=True, help="Export all 6 publication figures.")
    parser.add_argument("--sweep-grid", action="store_true", help="Perform sensitivity sweep across grid trajectories.")
    parser.add_argument("--sweep-refrigerants", action="store_true", help="Perform CIBSE TM65 refrigerant sweep.")
    parser.add_argument("--sync-collateral", action="store_true", help="Sync hero figures to portfolio directory.")

    args = parser.parse_args()

    run_pipeline(
        export_figures=args.export_figures,
        sweep_grid=args.sweep_grid,
        sweep_refrigerants=args.sweep_refrigerants,
        sync_collateral=args.sync_collateral,
    )


if __name__ == "__main__":
    main()
