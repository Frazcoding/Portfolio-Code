"""Orchestration shared by the CLI and the web app: config -> Simulation -> simcore ``Run`` folder -> API payloads."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .config import Config, ProjectPaths
from .design import HubDesign
from .model import SimOutput, Simulation, SiteCase


@dataclass
class RunResult:
    """A finished run: its folder, manifest and (in memory) output."""

    run_dir: Path
    manifest: dict
    output: SimOutput


class SiteCatalogue:
    """Candidate hub sites for the comparison: the listed sites (sheet values) and the screened OSM plots.

    Screened plots have no agent's figures, so they take the ``default_*`` lease and spare grid capacity (placeholders,
    shown as such in the front end).
    """

    DEFAULT_LEASE_GBP_M2_YR = 20.0
    DEFAULT_SPARE_GRID_KVA = 1000.0

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)

    def listed(self) -> list[dict]:
        path = self.data_dir / "sites_bristol.json"
        return json.loads(path.read_text(encoding="utf-8"))["sites"] if path.exists() else []

    def gis(self) -> dict:
        path = self.data_dir / "bristol_gis.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def screened(self, top: int = 10) -> list[dict]:
        out = []
        for p in self.gis().get("candidate_plots", [])[:top]:
            lon, lat = p["centroid"]
            name = p["name"] or f"{p['landuse'].title()} plot"
            out.append({"id": p["plot_id"], "name": f"{p['plot_id']} {name}", "lon": lon, "lat": lat,
                        "deadrun_km": p["deadrun_km"], "deadrun_min": p["deadrun_min"], "area_m2": p["area_m2"],
                        "lease_gbp_per_m2_yr": self.DEFAULT_LEASE_GBP_M2_YR, "grid_distance_m": p["primary_dist_m"],
                        "spare_grid_kVA": self.DEFAULT_SPARE_GRID_KVA, "kind": "screened", "landuse": p["landuse"],
                        "score": p["score"], "screen_rank": p["rank"], "primary_sub": p["primary_sub"],
                        "geometry": p["geometry"], "placeholder": ["lease_gbp_per_m2_yr", "spare_grid_kVA"]})
        return out

    def all(self) -> list[dict]:
        return self.listed() + self.screened()


class Runner:
    """Runs simulations; :meth:`run` records them as ``results/<date>_<name>/`` run folders, :meth:`evaluate` does not."""

    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root is not None else ProjectPaths.discover().root
        self.results = self.root / "results"
        self.catalogue = SiteCatalogue(ProjectPaths.discover().data)   # site and design data ship with the code
        self._design: HubDesign | None = None

    # ------------------------------------------------------------------ running
    @staticmethod
    def alternatives(sites: list[dict] | None) -> list[SiteCase]:
        return [SiteCase.from_dict(s) for s in (sites or [])]

    @property
    def design(self) -> HubDesign:
        """The imported Temple Works design (from the catalogue's data folder, which ships with the code)."""
        if self._design is None:
            self._design = HubDesign.load(self.catalogue.data_dir)
        return self._design

    def evaluate(self, config: Config, sites: list[dict] | None = None) -> SimOutput:
        """Run the model without recording (the live front end calls this on every input change)."""
        return Simulation.from_config(config, self.alternatives(sites), self.design).run()

    def run(self, config: Config, name: str = "baseline", inputs: list[str | Path] | None = None,
            track: bool = False, sites: list[dict] | None = None) -> RunResult:
        """Simulate ``config`` and write the run folder. ``inputs`` (files) are hashed into the manifest."""
        cfg_dict: dict[str, Any] = config.to_dict()
        if inputs:
            cfg_dict["inputs"] = [str(p) for p in inputs]
        from simcore.results import Run   # run folders need pyarrow; the browser build only evaluates

        if sites is None:
            sites = self.catalogue.listed()
        with Run(self.root, name, cfg_dict) as run:
            out = self.evaluate(config, sites)
            for key, obj in (("sites", out.sites), ("layout", out.layout), ("trips", out.trips)):
                (run.dir / f"{key}.json").write_text(json.dumps(obj, default=float), encoding="utf-8")
                run.artifacts.append(f"{key}.json")
            manifest = run.finish(out.kpis, {"timeline": out.frame.reset_index()})
            if track:
                run.log_to_mlflow()
        return RunResult(run.dir, manifest, out)

    # ------------------------------------------------------------------ run folders
    def run_dirs(self) -> list[Path]:
        """Run folders that contain a finished manifest, oldest first (by creation time in the manifest)."""
        found = []
        for mf in self.results.glob("*/manifest.json"):
            try:
                m = json.loads(mf.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if m.get("status") == "finished" and (mf.parent / "timeline.parquet").exists():
                found.append((m.get("created_utc", ""), mf.parent.name, mf.parent))
        return [p for _, _, p in sorted(found)]

    def latest(self) -> Path:
        dirs = self.run_dirs()
        if not dirs:
            raise FileNotFoundError(f"no finished runs in {self.results}; run `uv run ember-hub-simulator run` first")
        return dirs[-1]

    def resolve(self, name: str) -> Path:
        """Run folder by name; rejects anything that is not a direct child of ``results/``."""
        if not name or name != Path(name).name or name in (".", ".."):
            raise FileNotFoundError(name)
        path = self.results / name
        if not (path / "manifest.json").exists():
            raise FileNotFoundError(name)
        return path

    def load(self, run_dir: Path) -> tuple[dict, pd.DataFrame]:
        """Manifest and timeline frame (indexed by time) of a run folder."""
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        frame = pd.read_parquet(run_dir / "timeline.parquet").set_index("time")
        return manifest, frame

    def load_extras(self, run_dir: Path) -> dict:
        out = {}
        for key in ("sites", "layout", "trips"):
            path = run_dir / f"{key}.json"
            out[key] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
        return out

    def load_config(self, run_dir: Path) -> Config:
        """The configuration a run was made with (``config.toml`` in the run folder)."""
        return Config.from_toml(run_dir / "config.toml")

    def summaries(self) -> list[dict]:
        out = []
        for d in reversed(self.run_dirs()):
            m = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
            out.append({"name": d.name, "status": m["status"], "created_utc": m["created_utc"],
                        "runtime_s": m["runtime_s"], "kpis": m["metrics"]})
        return out


class Payloads:
    """JSON shapes of the web API (``SimRun`` of the Sim Workbench design system, ``index.d.ts``, plus Ember extras)."""

    DEC = 4

    @classmethod
    def kpi_info(cls) -> list[dict]:
        return [{"key": k.key, "label": k.label, "unit": k.unit, "dec": k.dec} for k in SimOutput.KPI_INFO]

    @classmethod
    def schema(cls, base: Config, project: str, catalogue: SiteCatalogue) -> dict:
        params = [{"key": s.key, "label": s.label, "unit": s.unit, "value": base.get(s.key), "min": s.lo, "max": s.hi,
                   "step": s.step, "group": s.group} for s in Config.editable_specs()]
        text = {k: base.get(k) for k in sorted(Config.TEXT_KEYS)}
        return {"project": project, "params": params, "text": text, "kpis": cls.kpi_info(),
                "variables": [{"key": v.key, "label": v.label, "unit": v.unit} for v in SimOutput.VARIABLES],
                "sites": catalogue.listed(), "screened": catalogue.screened()}

    @classmethod
    def simrun(cls, name: str, out: SimOutput) -> dict:
        return cls.from_frame(name, out.frame, out.kpis, {"sites": out.sites, "layout": out.layout, "trips": out.trips,
                                                         "selected": out.selected})

    @classmethod
    def from_frame(cls, name: str, frame: pd.DataFrame, kpis: dict, extras: dict) -> dict:
        """``{name, n, vars, data, kpis, ...}``: ``data[key]`` is one number per time step; ``t`` is elapsed hours."""
        n = len(frame)
        dt_s = float((frame.index[1] - frame.index[0]).total_seconds()) if n > 1 else 60.0
        vars_ = [{"key": "t", "label": "Time", "unit": "h"}]
        data: dict[str, list[float]] = {"t": np.round(frame["t_h"].to_numpy(dtype=float), 4).tolist()}
        labels = {v.column: v for v in SimOutput.VARIABLES}
        for col in frame.columns:
            if col == "t_h":
                continue
            v = labels.get(col)
            key = v.key if v else col
            if v:
                vars_.append({"key": key, "label": v.label, "unit": v.unit})
            else:
                j, what = col[1:].split("_", 1)
                lab = {"mode": ("state", "code"), "prog": ("leg progress", "–"), "soc": ("SOC", "%"), "chg": ("charger", "index")}[what]
                vars_.append({"key": key, "label": f"Coach {j} {lab[0]}", "unit": lab[1]})
            data[key] = np.round(frame[col].to_numpy(dtype=float), cls.DEC).tolist()
        clean = {k: (float(x) if x is not None and np.isfinite(float(x)) else 0.0) for k, x in kpis.items()}
        return {"name": name, "n": n, "vars": vars_, "data": data, "kpis": clean,
                "t0": frame.index[0].isoformat(), "dt_s": dt_s, **extras}
