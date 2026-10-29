from pathlib import Path
from typing import Dict, List, Optional
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.config import SCENARIO_CONFIGS
from src.carbon_calculator import LifeCycleCarbonResult
from src.lcc_calculator import LifeCycleCostResult
from src.benchmarking import BenchmarkComplianceResult


class WLCPlotter:
    """Master publication-grade visual generator adhering strictly to GEMINI.md visual rules."""

    COLORS = {
        "upfront": "#1f77b4",  # Dark Blue
        "inuse": "#ff7f0e",    # Orange
        "oper": "#d62728",     # Red / Crimson
        "eol": "#7f7f7f",      # Grey
        "mod_d": "#2ca02c",    # Green
        "scenario_1": "#d62728",
        "scenario_2": "#2ca02c",
        "scenario_3": "#1f77b4",
        "scenario_4": "#9467bd",
    }

    def __init__(self, output_dir: Optional[Path] = None):
        if output_dir is None:
            output_dir = Path(__file__).resolve().parent.parent / "figures"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._setup_matplotlib()

    def _setup_matplotlib(self) -> None:
        """Enforce strict pure black fonts and publication layout."""
        plt.style.use("seaborn-v0_8-whitegrid")
        mpl.rcParams.update(
            {
                "font.family": "sans-serif",
                "text.color": "#000000",
                "axes.labelcolor": "#000000",
                "axes.edgecolor": "#000000",
                "xtick.color": "#000000",
                "ytick.color": "#000000",
                "grid.color": "#e0e0e0",
                "grid.linestyle": "--",
                "grid.alpha": 0.7,
                "figure.autolayout": False,
                "legend.frameon": True,
                "legend.edgecolor": "#000000",
                "legend.facecolor": "#ffffff",
            }
        )

    def plot_fig1_wlc_stage_breakdown(
        self, carbon_results: Dict[str, LifeCycleCarbonResult]
    ) -> Path:
        """Figure 1: WLC Life Cycle Module Breakdown Stack (EN 15978 / RICS 2nd Edition)."""
        scenarios = list(carbon_results.keys())
        labels = [SCENARIO_CONFIGS[s].short_name for s in scenarios]
        gia = carbon_results[scenarios[0]].gia

        upfront = [carbon_results[s].a1_a5_upfront / gia for s in scenarios]
        inuse = [carbon_results[s].b1_b5_inuse_embodied / gia for s in scenarios]
        oper = [carbon_results[s].b6_operational_by_trajectory["desnz_central"] / gia for s in scenarios]
        eol = [carbon_results[s].c1_c4_end_of_life / gia for s in scenarios]
        mod_d = [carbon_results[s].module_d_credits / gia for s in scenarios]

        x = np.arange(len(scenarios))
        width = 0.52

        fig, ax = plt.subplots(figsize=(10, 6.5))

        p1 = ax.bar(x, upfront, width, label="Upfront Embodied (A1-A5)", color=self.COLORS["upfront"])
        p2 = ax.bar(x, inuse, width, bottom=upfront, label="In-Use Embodied & Replacements (B1-B5)", color=self.COLORS["inuse"])
        bot_oper = [u + i for u, i in zip(upfront, inuse)]
        p3 = ax.bar(x, oper, width, bottom=bot_oper, label="Operational Energy (B6, 60-Yr DESNZ Central)", color=self.COLORS["oper"])
        bot_eol = [b + o for b, o in zip(bot_oper, oper)]
        p4 = ax.bar(x, eol, width, bottom=bot_eol, label="End of Life (C1-C4)", color=self.COLORS["eol"])
        p5 = ax.bar(x, mod_d, width, label="Module D Circular Credits & Biogenic Carbon", color=self.COLORS["mod_d"], hatch="//", alpha=0.85)

        # Baseline reference line
        ax.axhline(0, color="#000000", linewidth=1.0)
        ax.axhline(1000, color="#d62728", linestyle=":", linewidth=1.2, label="LETI Band C Current Baseline (600 kg/m² Upfront)")

        ax.set_ylabel("Whole Life Carbon Intensity [kg CO₂e/m² GIA]", color="#000000", fontsize=11, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, color="#000000", fontsize=10, fontweight="bold")
        ax.set_title("Whole Life Carbon Breakdown Across 60-Year Study Period (EN 15978 / RICS)", color="#000000", fontsize=12, fontweight="bold", pad=15)

        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, fontsize=9)
        plt.subplots_adjust(bottom=0.22, top=0.92, left=0.10, right=0.95)

        png_path = self.output_dir / "fig1_wlc_stage_breakdown.png"
        svg_path = self.output_dir / "fig1_wlc_stage_breakdown.svg"
        fig.savefig(png_path, dpi=300)
        fig.savefig(svg_path)
        plt.close(fig)
        return png_path

    def plot_fig2_cumulative_carbon_payback(
        self, carbon_results: Dict[str, LifeCycleCarbonResult]
    ) -> Path:
        """Figure 2: 60-Year Dynamic Cumulative Carbon Payback across grid trajectories."""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 10), sharex=True)
        years = np.arange(1, 61)

        # Panel 1: DESNZ Central Grid
        for sc_id in ["scenario_1", "scenario_2", "scenario_3", "scenario_4"]:
            res = carbon_results[sc_id]
            cum_tonnes = np.array(res.annual_cumulative_carbon["desnz_central"]) / 1000.0
            ax1.plot(
                years,
                cum_tonnes,
                label=SCENARIO_CONFIGS[sc_id].name,
                color=self.COLORS[sc_id],
                linewidth=2.2,
            )

        ax1.set_ylabel("Cumulative Emissions [t CO₂e]", color="#000000", fontsize=10, fontweight="bold")
        ax1.set_title("60-Year Cumulative Carbon: DESNZ Green Book Central Grid Projection", color="#000000", fontsize=11, fontweight="bold")
        ax1.legend(loc="upper center", bbox_to_anchor=(0.5, -0.10), ncol=2, fontsize=8.5)

        # Panel 2: ESO Leading the Way vs Static SAP 10.2
        for sc_id in ["scenario_2", "scenario_3", "scenario_4"]:
            res = carbon_results[sc_id]
            cum_fes = np.array(res.annual_cumulative_carbon["fes_leading_way"]) / 1000.0
            cum_sap = np.array(res.annual_cumulative_carbon["sap10_static"]) / 1000.0
            short_name = SCENARIO_CONFIGS[sc_id].short_name

            ax2.plot(years, cum_fes, label=f"{short_name} (ESO Rapid Decarb)", color=self.COLORS[sc_id], linewidth=2.0)
            ax2.plot(years, cum_sap, label=f"{short_name} (Static SAP 10.2 Grid)", color=self.COLORS[sc_id], linestyle="--", linewidth=1.5)

        ax2.set_xlabel("Time [Years]", color="#000000", fontsize=10, fontweight="bold")
        ax2.set_ylabel("Cumulative Emissions [t CO₂e]", color="#000000", fontsize=10, fontweight="bold")
        ax2.set_title("Grid Sensitivity: National Grid ESO 'Leading the Way' vs Static SAP 10.2", color="#000000", fontsize=11, fontweight="bold")
        ax2.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=2, fontsize=8)

        plt.subplots_adjust(bottom=0.18, top=0.94, hspace=0.35, left=0.10, right=0.95)

        png_path = self.output_dir / "fig2_cumulative_carbon_payback.png"
        svg_path = self.output_dir / "fig2_cumulative_carbon_payback.svg"
        fig.savefig(png_path, dpi=300)
        fig.savefig(svg_path)
        plt.close(fig)
        return png_path

    def plot_fig3_spatial_elemental_breakdown(
        self, carbon_results: Dict[str, LifeCycleCarbonResult]
    ) -> Path:
        """Figure 3: Spatial & Elemental Carbon Intensity (Upfront Modules A1-A5)."""
        scenarios = ["scenario_1", "scenario_2", "scenario_3", "scenario_4"]
        labels = [SCENARIO_CONFIGS[s].short_name for s in scenarios]
        elements = [
            "1.0 Substructure",
            "2.0 Superstructure",
            "3.0 Facade & Envelope",
            "4.0 Internal Finishes",
            "5.0 MEP Services",
        ]
        gia = carbon_results[scenarios[0]].gia

        fig, ax = plt.subplots(figsize=(10, 6.5))
        y = np.arange(len(scenarios))
        height = 0.65

        left = np.zeros(len(scenarios))
        palette = ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f"]

        for idx, elem in enumerate(elements):
            vals = [carbon_results[s].elemental_a1_a5.get(elem, 0.0) / gia for s in scenarios]
            clean_name = elem.split(" ", 1)[1] if " " in elem else elem
            ax.barh(y, vals, height, left=left, label=clean_name, color=palette[idx % len(palette)])
            left += np.array(vals)

        ax.set_yticks(y)
        ax.set_yticklabels(labels, color="#000000", fontsize=10, fontweight="bold")
        ax.set_xlabel("Upfront Embodied Carbon Intensity [kg CO₂e/m² GIA]", color="#000000", fontsize=11, fontweight="bold")
        ax.set_title("Elemental Breakdown of Upfront Embodied Carbon (Modules A1-A5)", color="#000000", fontsize=12, fontweight="bold", pad=15)

        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, fontsize=9)
        plt.subplots_adjust(bottom=0.20, top=0.92, left=0.18, right=0.95)

        png_path = self.output_dir / "fig3_spatial_elemental_breakdown.png"
        svg_path = self.output_dir / "fig3_spatial_elemental_breakdown.svg"
        fig.savefig(png_path, dpi=300)
        fig.savefig(svg_path)
        plt.close(fig)
        return png_path

    def plot_fig4_mep_refrigerant_fgas_tradeoff(
        self, carbon_results: Dict[str, LifeCycleCarbonResult]
    ) -> Path:
        """Figure 4: MEP & Refrigerant Fugitive Emissions Trade-off (CIBSE TM65)."""
        scenarios = ["scenario_1", "scenario_2", "scenario_3", "scenario_4"]
        labels = [SCENARIO_CONFIGS[s].short_name for s in scenarios]
        gia = carbon_results[scenarios[0]].gia

        b1_leakage = [carbon_results[s].b1_refrigerant_leakage / gia for s in scenarios]
        b4_replacement = [carbon_results[s].b4_replacement / gia for s in scenarios]
        mep_a1_a5 = [carbon_results[s].elemental_a1_a5.get("5.0 MEP Services", 0.0) / gia for s in scenarios]
        c4_venting = [(carbon_results[s].c4_disposal_and_venting - 1.5 * gia) / gia for s in scenarios]

        x = np.arange(len(scenarios))
        width = 0.55

        fig, ax = plt.subplots(figsize=(10, 6.5))

        ax.bar(x, mep_a1_a5, width, label="Initial MEP Machinery Embodied (A1-A3)", color="#4e79a7")
        bot_b4 = mep_a1_a5
        ax.bar(x, b4_replacement, width, bottom=bot_b4, label="Periodic Plant Replacements (B4)", color="#f28e2b")
        bot_b1 = [m + r for m, r in zip(bot_b4, b4_replacement)]
        ax.bar(x, b1_leakage, width, bottom=bot_b1, label="In-Use Fugitive Refrigerant Leakage (B1)", color="#e15759")
        bot_c4 = [b + l for b, l in zip(bot_b1, b1_leakage)]
        ax.bar(x, c4_venting, width, bottom=bot_c4, label="End-of-Life Refrigerant Venting (C4)", color="#76b7b2")

        ax.set_ylabel("Lifecycle MEP Carbon Intensity [kg CO₂e/m² GIA]", color="#000000", fontsize=11, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, color="#000000", fontsize=10, fontweight="bold")
        ax.set_title("CIBSE TM65 MEP Lifecycle Carbon and Refrigerant Global Warming Impact", color="#000000", fontsize=12, fontweight="bold", pad=15)

        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, fontsize=9)
        plt.subplots_adjust(bottom=0.22, top=0.92, left=0.10, right=0.95)

        png_path = self.output_dir / "fig4_mep_refrigerant_fgas_tradeoff.png"
        svg_path = self.output_dir / "fig4_mep_refrigerant_fgas_tradeoff.svg"
        fig.savefig(png_path, dpi=300)
        fig.savefig(svg_path)
        plt.close(fig)
        return png_path

    def plot_fig5_techno_economic_carbon_cost_frontier(
        self,
        carbon_results: Dict[str, LifeCycleCarbonResult],
        lcc_results: Dict[str, LifeCycleCostResult],
    ) -> Path:
        """Figure 5: Techno-Economic Pareto Frontier & Marginal Abatement Cost."""
        scenarios = ["scenario_1", "scenario_2", "scenario_3", "scenario_4"]
        fig, ax = plt.subplots(figsize=(10, 6.5))

        for s in scenarios:
            c_res = carbon_results[s]
            l_res = lcc_results[s]
            wlc_m2 = c_res.total_wlc_per_m2("desnz_central")
            npv_m2 = l_res.financial_npv_per_m2()

            mac_val = l_res.marginal_abatement_cost_gbp_per_tonne
            mac_str = f"MAC: £{mac_val:.1f}/t" if s != "scenario_1" else "Baseline"

            ax.scatter(
                wlc_m2,
                npv_m2,
                s=200,
                color=self.COLORS[s],
                label=f"{SCENARIO_CONFIGS[s].short_name} ({mac_str})",
                edgecolor="#000000",
                linewidth=1.5,
                zorder=5,
            )

        # Draw Pareto connector line between Retrofit and Timber New Build
        wlc_line = [carbon_results[s].total_wlc_per_m2("desnz_central") for s in ["scenario_4", "scenario_2"]]
        npv_line = [lcc_results[s].financial_npv_per_m2() for s in ["scenario_4", "scenario_2"]]
        ax.plot(wlc_line, npv_line, linestyle="--", color="#7f7f7f", linewidth=1.5, label="Optimal Decarbonisation Frontier")

        ax.set_xlabel("60-Year Whole Life Carbon [kg CO₂e/m² GIA]", color="#000000", fontsize=11, fontweight="bold")
        ax.set_ylabel("60-Year Life Cycle Cost Net Present Value [£/m² GIA]", color="#000000", fontsize=11, fontweight="bold")
        ax.set_title("Techno-Economic Pareto Frontier: 60-Year Carbon vs Life Cycle Cost (BS ISO 15686-5)", color="#000000", fontsize=12, fontweight="bold", pad=15)

        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, fontsize=9)
        plt.subplots_adjust(bottom=0.22, top=0.92, left=0.12, right=0.95)

        png_path = self.output_dir / "fig5_techno_economic_carbon_cost_frontier.png"
        svg_path = self.output_dir / "fig5_techno_economic_carbon_cost_frontier.svg"
        fig.savefig(png_path, dpi=300)
        fig.savefig(svg_path)
        plt.close(fig)
        return png_path

    def plot_fig6_leti_riba_benchmark_compliance(
        self,
        carbon_results: Dict[str, LifeCycleCarbonResult],
        benchmarks: Dict[str, BenchmarkComplianceResult],
    ) -> Path:
        """Figure 6: LETI and RIBA 2030 Benchmark Compliance Matrix."""
        scenarios = ["scenario_1", "scenario_2", "scenario_3", "scenario_4"]
        labels = [SCENARIO_CONFIGS[s].short_name for s in scenarios]

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 6.8))
        x = np.arange(len(scenarios))
        width = 0.52

        # Panel A: Upfront Embodied Carbon (A1-A5)
        upfront_vals = [carbon_results[s].upfront_per_m2() for s in scenarios]
        bars1 = ax1.bar(x, upfront_vals, width, color="#1f77b4", edgecolor="#000000", label="Upfront Embodied (A1-A5)")
        ax1.axhline(300.0, color="#2ca02c", linestyle="--", linewidth=1.5, label="LETI 2030 Band A Limit (300 kg/m²)")
        ax1.axhline(500.0, color="#ff7f0e", linestyle="--", linewidth=1.5, label="RIBA 2030 Office Target (500 kg/m²)")
        ax1.axhline(600.0, color="#d62728", linestyle="--", linewidth=1.5, label="LETI Band C Baseline (600 kg/m²)")

        ax1.set_ylabel("Upfront Embodied Carbon [kg CO₂e/m² GIA]", color="#000000", fontsize=10, fontweight="bold")
        ax1.set_xticks(x)
        ax1.set_xticklabels(labels, color="#000000", fontsize=9, fontweight="bold", rotation=15)
        ax1.set_title("Panel A: Upfront Embodied Carbon (A1-A5)", color="#000000", fontsize=11, fontweight="bold")
        ax1.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=1, fontsize=8.5)

        # Panel B: Operational Energy Use Intensity (EUI)
        eui_vals = [SCENARIO_CONFIGS[s].net_operational_eui for s in scenarios]
        bars2 = ax2.bar(x, eui_vals, width, color="#ff7f0e", edgecolor="#000000", label="Net Operational EUI")
        ax2.axhline(55.0, color="#2ca02c", linestyle="--", linewidth=1.5, label="LETI / UK NZCBS 2030 Limit (55 kWh/m²/yr)")
        ax2.axhline(70.0, color="#ff7f0e", linestyle="--", linewidth=1.5, label="RIBA 2025 Office Limit (70 kWh/m²/yr)")

        ax2.set_ylabel("Energy Use Intensity [kWh/m²/yr]", color="#000000", fontsize=10, fontweight="bold")
        ax2.set_xticks(x)
        ax2.set_xticklabels(labels, color="#000000", fontsize=9, fontweight="bold", rotation=15)
        ax2.set_title("Panel B: Operational Energy Intensity (B6)", color="#000000", fontsize=11, fontweight="bold")
        ax2.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=1, fontsize=8.5)

        plt.subplots_adjust(bottom=0.32, top=0.92, wspace=0.30, left=0.08, right=0.95)

        png_path = self.output_dir / "fig6_leti_riba_benchmark_compliance.png"
        svg_path = self.output_dir / "fig6_leti_riba_benchmark_compliance.svg"
        fig.savefig(png_path, dpi=300)
        fig.savefig(svg_path)
        plt.close(fig)
        return png_path

    def generate_all_figures(
        self,
        carbon_results: Dict[str, LifeCycleCarbonResult],
        lcc_results: Dict[str, LifeCycleCostResult],
        benchmarks: Dict[str, BenchmarkComplianceResult],
    ) -> Dict[str, Path]:
        return {
            "fig1": self.plot_fig1_wlc_stage_breakdown(carbon_results),
            "fig2": self.plot_fig2_cumulative_carbon_payback(carbon_results),
            "fig3": self.plot_fig3_spatial_elemental_breakdown(carbon_results),
            "fig4": self.plot_fig4_mep_refrigerant_fgas_tradeoff(carbon_results),
            "fig5": self.plot_fig5_techno_economic_carbon_cost_frontier(carbon_results, lcc_results),
            "fig6": self.plot_fig6_leti_riba_benchmark_compliance(carbon_results, benchmarks),
        }
