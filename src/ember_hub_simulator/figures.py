"""Report / slide figures from a run folder (fraser style, SVG + PNG into ``docs/figures``)."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .config import ProjectPaths
from .model import HubModel, Mode
from .plotting import PlotStyle
from .runner import Runner


class FigureBuilder:
    """Builds the standard figures from the latest (or a named) run.

    ``day``    full width: (a) site grid load, (b) coach state of charge over the simulated period
    ``blocks`` full width: coach state against time (a Gantt chart of the operating days)
    ``sites``  full width: annual cost per return trip by site, split by cost item, infeasible sites marked
    """

    NAMES = ("day", "blocks", "sites")
    COST_LABELS = {"land_lease": "Land lease", "site_works": "Site works", "chargers": "Chargers",
                   "grid_connection": "Grid connection", "fleet": "Fleet lease", "driver_wages": "Driver wages",
                   "electricity": "Electricity"}

    def __init__(self, root: Path | None = None):
        self.paths = ProjectPaths(Path(root)) if root is not None else ProjectPaths.discover()
        self.runner = Runner(self.paths.root)

    def build(self, run_dir: Path | None = None) -> list[Path]:
        plt.switch_backend("Agg")
        PlotStyle.apply()
        run_dir = run_dir or self.runner.latest()
        manifest, frame = self.runner.load(run_dir)
        extras = self.runner.load_extras(run_dir)
        saved: list[Path] = []
        for name in self.NAMES:
            fig = getattr(self, f"_{name}")(frame, manifest["metrics"], extras)
            saved += PlotStyle.save(fig, self.paths.figures / name)
        return saved

    @staticmethod
    def coaches(frame: pd.DataFrame) -> int:
        return sum(1 for c in frame.columns if c.endswith("_mode"))

    # ------------------------------------------------------------------ figures
    def _day(self, f: pd.DataFrame, k: dict, extras: dict):
        t = f["t_h"].to_numpy()
        fig, (a, b) = plt.subplots(2, 1, figsize=(PlotStyle.FULL_W, 9 * PlotStyle.CM), sharex=True)
        a.fill_between(t, 0, f["grid_kVA"], step="post", color=PlotStyle.OKABE_ITO[0], alpha=0.35, lw=0)
        a.step(t, f["grid_kVA"], where="post", color=PlotStyle.OKABE_ITO[0], lw=1.0)
        a.axhline(k["peak_kVA"], color=PlotStyle.OKABE_ITO[1], ls="--", lw=0.9)
        a.annotate("Sheet peak load (all chargers)", (t[-1], k["peak_kVA"]), xytext=(-4, 4), textcoords="offset points",
                   ha="right", fontsize=7.5, color=PlotStyle.OKABE_ITO[1])
        a.set_ylabel("Grid load $S$ (kVA)")
        a.set_title("(a) Site grid load", loc="left", fontweight="bold")
        a.set_ylim(0, k["peak_kVA"] * 1.15)
        for j in range(1, self.coaches(f) + 1):
            b.plot(t, f[f"c{j}_soc"], lw=0.8, alpha=0.8)
        b.set_ylabel("State of charge (%)")
        b.set_ylim(0, 105)
        b.set_title("(b) Coach state of charge", loc="left", fontweight="bold")
        b.set_xlabel("Time (h)")
        b.set_xlim(0, t[-1])
        b.set_xticks(np.arange(0, t[-1] + 1, 6))
        return fig

    def _blocks(self, f: pd.DataFrame, k: dict, extras: dict):
        t = f["t_h"].to_numpy()
        n = self.coaches(f)
        colors = {Mode.PARKED: "#BBBBBB", Mode.DEADRUN_OUT: "#E69F00", Mode.OUTBOUND: "#0072B2", Mode.TURNAROUND: "#56B4E9",
                  Mode.INBOUND: "#0072B2", Mode.DEADRUN_IN: "#E69F00", Mode.QUEUED: "#D55E00", Mode.CHARGING: "#009E73"}
        fig, ax = plt.subplots(figsize=(PlotStyle.FULL_W, (2.2 + 0.45 * n) * PlotStyle.CM))
        dt = t[1] - t[0]
        for j in range(1, n + 1):
            m = f[f"c{j}_mode"].to_numpy().astype(int)
            edges = np.flatnonzero(np.diff(m)) + 1
            for s, e in zip(np.r_[0, edges], np.r_[edges, len(m)]):
                ax.broken_barh([(t[s], (e - s) * dt)], (j - 0.4, 0.8), color=colors[m[s]], lw=0)
        ax.set_yticks(range(1, n + 1), [f"Coach {j}" for j in range(1, n + 1)])
        ax.invert_yaxis()
        ax.set_xlim(0, t[-1])
        ax.set_xticks(np.arange(0, t[-1] + 1, 6))
        ax.set_xlabel("Time (h)")
        shown = (Mode.OUTBOUND, Mode.TURNAROUND, Mode.DEADRUN_OUT, Mode.CHARGING, Mode.QUEUED, Mode.PARKED)
        handles = [plt.Rectangle((0, 0), 1, 1, color=colors[m]) for m in shown]
        ax.legend(handles, ["On route", "Turnaround", "Dead run", "Charging", "Queued", "Parked"], ncols=6,
                  loc="upper center", bbox_to_anchor=(0.5, 1.18), handlelength=1, fontsize=7.5)
        ax.grid(False, axis="y")
        return fig

    def _sites(self, f: pd.DataFrame, k: dict, extras: dict):
        rows = sorted(extras.get("sites") or [], key=lambda r: r["gbp_per_trip"])
        fig, ax = plt.subplots(figsize=(PlotStyle.FULL_W, (2.5 + 0.7 * max(len(rows), 1)) * PlotStyle.CM))
        y = np.arange(len(rows))
        left = np.zeros(len(rows))
        trips = np.array([r["total_gbp_yr"] / r["gbp_per_trip"] for r in rows])
        for i, item in enumerate(HubModel.COST_ITEMS):
            v = np.array([r["costs_gbp_yr"][item] for r in rows]) / trips
            ax.barh(y, v, left=left, color=PlotStyle.OKABE_ITO[i % 7], label=self.COST_LABELS[item], height=0.6)
            left += v
        for yi, r in zip(y, rows):
            mark = f"rank {r['rank']}" if r["rank"] else "not feasible"
            ax.annotate(f"£{r['gbp_per_trip']:,.0f} ({mark})", (left[yi], yi), xytext=(4, 0), textcoords="offset points",
                        va="center", fontsize=7.5)
        ax.set_yticks(y, [r["site_name"][:40] for r in rows])
        ax.invert_yaxis()
        ax.set_xlabel("Annual cost per return trip (£)")
        ax.set_xlim(0, left.max() * 1.3 if len(rows) else 1)
        ax.legend(ncols=4, loc="upper center", bbox_to_anchor=(0.5, -0.3), fontsize=7.5, handlelength=1)
        ax.grid(False, axis="y")
        return fig
