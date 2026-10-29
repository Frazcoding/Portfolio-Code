"""Typst reports and slides: write ``docs/kpis.json`` from the latest run, then compile with the ``typst`` package."""
from __future__ import annotations

import json
import os
from pathlib import Path

import typst
from simcore import __version__ as simcore_version

from .config import ProjectPaths
from .figures import FigureBuilder
from .model import SimOutput
from .runner import Runner


class ReportBuilder:
    """Compiles ``docs/report.typ`` and ``docs/slides.typ`` to PDF using the numbers of the latest run."""

    DOCUMENTS = ("report", "slides")
    WINDOWS_FONTS = Path(r"C:\Windows\Fonts")

    def __init__(self, root: Path | None = None, project_name: str | None = None):
        self.paths = ProjectPaths(Path(root)) if root is not None else ProjectPaths.discover()
        self.runner = Runner(self.paths.root)
        self.project_name = project_name or self.paths.root.name

    def font_paths(self) -> list[str]:
        paths = [str(self.WINDOWS_FONTS)] if self.WINDOWS_FONTS.is_dir() else []
        extra = os.environ.get("TYPST_FONT_PATHS")
        return paths + (extra.split(os.pathsep) if extra else [])

    def write_kpis(self, run_dir: Path | None = None) -> Path:
        """``docs/kpis.json``: run identity, raw KPIs and display strings (read by Typst with ``json(...)``)."""
        run_dir = run_dir or self.runner.latest()
        manifest, _ = self.runner.load(run_dir)
        cfg = self.runner.load_config(run_dir)
        kpis = manifest["metrics"]
        shown = {k.key: f"{kpis[k.key]:,.{k.dec}f}" for k in SimOutput.KPI_INFO if k.key in kpis}
        git = manifest.get("git") or {}
        doc = {
            "project": self.project_name,
            "run": run_dir.name,
            "commit": (git.get("commit") or "no git")[:7] + (" (dirty)" if git.get("dirty") else ""),
            "simcore": simcore_version,
            "origin": cfg.route.origin_name,
            "dest": cfg.route.dest_name,
            "site": cfg.site.name,
            "distance_km": cfg.route.distance_km,
            "drive_time_min": cfg.route.drive_time_min,
            "headway_min": cfg.timetable.headway_min,
            "charge_power_kW": cfg.hub.charge_power_kW,
            "battery_kWh": cfg.bus.battery_kWh,
            "horizon_h": cfg.sim.horizon_h,
            "kpis": kpis,
            "fmt": shown,
            "units": {k.key: k.unit for k in SimOutput.KPI_INFO},
            "labels": {k.key: k.label for k in SimOutput.KPI_INFO},
        }
        path = self.paths.docs / "kpis.json"
        path.write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
        return path

    def build(self, run_dir: Path | None = None) -> list[Path]:
        """Refresh figures and KPIs from the run, compile both documents; returns the PDFs."""
        run_dir = run_dir or self.runner.latest()
        FigureBuilder(self.paths.root).build(run_dir)
        self.write_kpis(run_dir)
        pdfs = []
        for name in self.DOCUMENTS:
            src, out = self.paths.docs / f"{name}.typ", self.paths.docs / f"{name}.pdf"
            typst.compile(str(src), output=str(out), font_paths=self.font_paths())
            pdfs.append(out)
        return pdfs
