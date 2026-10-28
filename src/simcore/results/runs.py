"""Reproducible run folders: ``results/<YYYY-MM-DD>_<name>/`` with ``config.toml``, Parquet outputs and ``manifest.json``.

The run folder is the source of truth. MLflow (optional extra ``simcore[tracking]``) is only a comparison UI over a
local SQLite store in ``Paths.cache()/mlflow/mlflow.db`` that can be rebuilt from the manifests at any time.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import math
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd

from .. import __version__
from ..core import Paths


class Run:
    """One simulation run.

    Usage::

        with Run(project_root, "baseline", config) as run:
            ...
            run.finish(kpis, {"hourly": df})

    ``config`` may contain ``seed`` and ``inputs`` (list of file paths, or dict name -> path, relative to
    ``project_root`` or absolute) whose SHA-256 hashes are recorded. ``None`` values are not representable in
    TOML and are omitted from ``config.toml``.
    """

    def __init__(self, project_root, name: str, config: dict | None = None):
        self.project_root = Path(project_root)
        self.name = name
        self.config = dict(config or {})
        self.status = "running"
        self._t0 = time.perf_counter()
        self.created_utc = self._now()
        self.kpis: dict = {}
        self.artifacts: list[str] = []
        self.dir = self._make_dir()
        (self.dir / "config.toml").write_text(self.to_toml(self.config), encoding="utf-8")
        self.artifacts.append("config.toml")
        self._write_manifest()

    # ------------------------------------------------------------------ folder
    def _make_dir(self) -> Path:
        base = self.project_root / "results"
        base.mkdir(parents=True, exist_ok=True)
        stem = f"{_dt.date.today():%Y-%m-%d}_{self.name}"
        n = 1
        while True:
            path = base / (stem if n == 1 else f"{stem}_{n}")
            try:
                path.mkdir()
                return path
            except FileExistsError:
                n += 1

    @staticmethod
    def _now() -> str:
        return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")

    # ------------------------------------------------------------------ life cycle
    def finish(self, kpis: dict, outputs: dict[str, pd.DataFrame]) -> dict:
        """Write Parquet outputs (``<key>.parquet``) and the final manifest; returns the manifest dict."""
        for key, df in (outputs or {}).items():
            fname = f"{key}.parquet"
            df.to_parquet(self.dir / fname)
            self.artifacts.append(fname)
        self.kpis = dict(kpis or {})
        self.status = "finished"
        return self._write_manifest()

    def __enter__(self) -> "Run":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is not None:
            self.status = "failed"
            self._write_manifest(error=f"{exc_type.__name__}: {exc}")
        elif self.status == "running":
            self.finish({}, {})
        return False  # never swallow exceptions

    # ------------------------------------------------------------------ manifest
    def manifest(self, error: str | None = None) -> dict:
        finished = self.status in ("finished", "failed")
        m = {
            "name": self.name,
            "status": self.status,
            "created_utc": self.created_utc,
            "finished_utc": self._now() if finished else None,
            "runtime_s": round(time.perf_counter() - self._t0, 3),
            "git": self._git(self.project_root),
            "simcore_version": __version__,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "seed": self.config.get("seed"),
            "input_hashes": self._input_hashes(),
            "params": self.flatten(self.config),
            "metrics": self.kpis,
            "artifacts": [a for a in self.artifacts if a != "manifest.json"],
        }
        if error:
            m["error"] = error
        return m

    def _write_manifest(self, error: str | None = None) -> dict:
        m = self.manifest(error)
        (self.dir / "manifest.json").write_text(json.dumps(m, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
        return m

    @staticmethod
    def flatten(d: dict, prefix: str = "") -> dict:
        """Flatten nested dicts to dotted keys; lists and scalars are kept as values."""
        out = {}
        for k, v in d.items():
            key = f"{prefix}{k}"
            if isinstance(v, dict):
                out.update(Run.flatten(v, key + "."))
            else:
                out[key] = v
        return out

    def _input_hashes(self) -> dict:
        inputs = self.config.get("inputs")
        if not inputs:
            return {}
        items = inputs.items() if isinstance(inputs, dict) else ((str(p), p) for p in inputs)
        out = {}
        for label, p in items:
            path = Path(p)
            if not path.is_absolute():
                path = self.project_root / path
            if path.is_file():
                h = hashlib.sha256()
                with open(path, "rb") as fh:
                    for chunk in iter(lambda: fh.read(1 << 20), b""):
                        h.update(chunk)
                out[str(label)] = h.hexdigest()
            else:
                out[str(label)] = None  # missing input is recorded, not fatal
        return out

    @staticmethod
    def _git(root: Path) -> dict | None:
        """``{"commit", "dirty"}`` for the repo containing ``root``, or None if it is not a git repo.

        The ``results/`` folder is excluded from the dirty check so that run output does not mark its own run dirty.
        """
        try:
            head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=30)
            if head.returncode != 0:
                return None
            st = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--", ".", ":(exclude)results"],
                                capture_output=True, text=True, timeout=30)
            return {"commit": head.stdout.strip(), "dirty": bool(st.stdout.strip())}
        except (OSError, subprocess.SubprocessError):
            return None

    # ------------------------------------------------------------------ TOML writer
    @classmethod
    def to_toml(cls, data: dict) -> str:
        """Minimal TOML serialiser for nested dict / str / int / float / bool / date / list (``None`` omitted)."""
        lines: list[str] = []
        cls._emit_table(data, [], lines)
        return "\n".join(lines).strip() + "\n"

    @classmethod
    def _emit_table(cls, table: dict, path: list[str], lines: list[str]) -> None:
        scalars = {k: v for k, v in table.items() if v is not None and not isinstance(v, dict)}
        subs = {k: v for k, v in table.items() if isinstance(v, dict)}
        if path and (scalars or not subs):
            lines += ["", "[" + ".".join(cls._key(p) for p in path) + "]"]
        for k, v in scalars.items():
            lines.append(f"{cls._key(k)} = {cls._value(v)}")
        for k, v in subs.items():
            cls._emit_table(v, path + [k], lines)

    @staticmethod
    def _key(k) -> str:
        k = str(k)
        return k if k and all(c.isalnum() and c.isascii() or c in "_-" for c in k) else json.dumps(k, ensure_ascii=False)

    @classmethod
    def _value(cls, v: Any) -> str:
        if hasattr(v, "item") and not isinstance(v, (list, tuple, dict)):  # numpy scalar
            v = v.item()
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, int):
            return str(v)
        if isinstance(v, float):
            if math.isnan(v):
                return "nan"
            if math.isinf(v):
                return "inf" if v > 0 else "-inf"
            return repr(v)
        if isinstance(v, (_dt.datetime, _dt.date)):
            return v.isoformat()
        if isinstance(v, (list, tuple)):
            return "[" + ", ".join(cls._value(x) for x in v if x is not None) + "]"
        if isinstance(v, dict):  # inline table (dict inside a list)
            return "{" + ", ".join(f"{cls._key(k)} = {cls._value(x)}" for k, x in v.items() if x is not None) + "}"
        return json.dumps(str(v), ensure_ascii=False)  # str, Path, ...: JSON escapes are valid TOML basic-string escapes

    # ------------------------------------------------------------------ MLflow (optional)
    @staticmethod
    def _import_mlflow():
        try:
            import mlflow
        except ImportError as e:
            raise ImportError("MLflow is not installed; install the tracking extra with `uv add simcore[tracking]`"
                              " (or `uv sync --extra tracking`).") from e
        return mlflow

    @staticmethod
    def default_tracking_uri() -> str:
        store = Paths.cache() / "mlflow"
        store.mkdir(parents=True, exist_ok=True)
        return "sqlite:///" + (store / "mlflow.db").as_posix()

    @staticmethod
    def _log_manifest(mlflow, manifest: dict, run_dir: Path, project_root: Path, tracking_uri: str | None) -> None:
        mlflow.set_tracking_uri(tracking_uri or Run.default_tracking_uri())
        mlflow.set_experiment(Path(project_root).resolve().name)
        with mlflow.start_run(run_name=run_dir.name):
            params = {k: (v if isinstance(v, (int, float, str)) else json.dumps(v, default=str))
                      for k, v in (manifest.get("params") or {}).items()}
            mlflow.log_params({k: str(v)[:500] for k, v in params.items()})
            metrics = {k: float(v) for k, v in (manifest.get("metrics") or {}).items()
                       if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)}
            if metrics:
                mlflow.log_metrics(metrics)
            git = manifest.get("git") or {}
            mlflow.set_tags({
                "simcore.run_dir": str(run_dir),
                "simcore.status": str(manifest.get("status")),
                "simcore.version": str(manifest.get("simcore_version")),
                "git.commit": str(git.get("commit")),
                "git.dirty": str(git.get("dirty")),
                "simcore.artifacts": ";".join(manifest.get("artifacts", []))[:5000],
            })

    def log_to_mlflow(self, tracking_uri: str | None = None) -> None:
        """Log this run's params, metrics and artifact paths to MLflow (default: local SQLite under ``Paths.cache()``).

        The experiment is the project folder name. Raises ImportError (with the install hint) if MLflow is missing.
        """
        mlflow = self._import_mlflow()
        self._log_manifest(mlflow, self.manifest(), self.dir, self.project_root, tracking_uri)

    @classmethod
    def rebuild_mlflow_index(cls, project_root, tracking_uri: str | None = None) -> int:
        """Log every ``results/*/manifest.json`` of the project to MLflow; returns the number of runs logged."""
        mlflow = cls._import_mlflow()
        root = Path(project_root)
        n = 0
        for mf in sorted((root / "results").glob("*/manifest.json")):
            cls._log_manifest(mlflow, json.loads(mf.read_text(encoding="utf-8")), mf.parent, root, tracking_uri)
            n += 1
        return n
