"""Results container and viewer export.

Each scenario is written to ``<project>/viewer_data/`` as
  ``<key>.json``  manifest (channels, KPIs, state points, diagrams, viewer config)
  ``<key>.bin``   Float32 little-endian, channel-major (n samples per channel)
and to ``<project>/results/<key>_hourly.csv.gz`` for engineering use.

Units: this is an *edge* module; channels are stored in the engineering units named in each channel's ``unit``
(deg C, bar, kJ/kg, kW ...), exactly as the legacy v0.1.0 exporter did.
"""
from __future__ import annotations

import gzip
import json
import math

import numpy as np


class Results:
    """Time-series channels + KPIs for one scenario, exportable to the viewer format."""

    STATE_FIELDS = [
        ("T", "Temperature", "°C", 1),
        ("P", "Pressure", "bar", 3),
        ("h", "Specific enthalpy", "kJ/kg", 1),
        ("s", "Specific entropy", "kJ/(kg·K)", 4),
        ("x", "Vapour quality", "–", 3),
        ("m", "Mass flow", "kg/s", 4),
        ("ex", "Specific flow exergy", "kJ/kg", 1),
    ]

    def __init__(self, key, name, n, t0="2023-01-01T00:00:00Z", dt=3600.0, time_unit="s"):
        self.key = key
        self.name = name
        self.n = n
        self.t0 = t0
        self.dt = dt
        self.time_unit = time_unit
        self.channels = {}
        self.meta = {}
        self.kpis = []
        self.state_points = []
        self.diagrams = []
        self.config = {}
        self.start = 0          # default cursor sample in the viewer

    # -- channels -----------------------------------------------------------
    def ch(self, key, values, unit, label, group, dec=2):
        arr = np.asarray(values, dtype=np.float64)
        if arr.shape != (self.n,):
            raise ValueError(f"{self.key}/{key}: expected {self.n} samples, got {arr.shape}")
        self.channels[key] = arr
        self.meta[key] = {"key": key, "label": label, "unit": unit, "group": group, "dec": dec}
        return arr

    def state_point(self, sid, name, loop, fluid, rec, x_valid=True):
        """rec: dict of arrays with keys T,P,h,s,x,m,ex (engineering units)."""
        self.state_points.append({"id": sid, "name": name, "loop": loop, "fluid": fluid})
        for f, flabel, unit, dec in self.STATE_FIELDS:
            if f in rec and (f != "x" or x_valid):
                self.ch(f"{sid}_{f}", rec[f], unit, f"{sid} {name} · {flabel}", f"State · {loop}", dec)

    def kpi(self, label, value, unit, group="Annual", dec=1, note=""):
        v = float(value)
        self.kpis.append({"label": label, "value": v if math.isfinite(v) else None, "unit": unit,
                          "group": group, "dec": dec, "note": note})

    # -- writers --------------------------------------------------------------
    def write(self, project_dir, scenario_cfg):
        out = project_dir / "viewer_data"
        out.mkdir(exist_ok=True)
        keys = list(self.channels)
        block = np.stack([self.channels[k] for k in keys]).astype("<f4")
        (out / f"{self.key}.bin").write_bytes(block.tobytes())
        stats = []
        for k in keys:
            a = self.channels[k]
            f = a[np.isfinite(a)]
            stats.append((float(f.min()), float(f.max())) if f.size else (0.0, 0.0))
        manifest = {
            "key": self.key, "name": self.name, "n": self.n, "t0": self.t0, "dt": self.dt,
            "timeUnit": self.time_unit, "start": int(self.start),
            "channels": [dict(self.meta[k], min=self._r(s[0]), max=self._r(s[1])) for k, s in zip(keys, stats)],
            "kpis": self.kpis, "statePoints": self.state_points, "diagrams": self.diagrams,
            **scenario_cfg,
        }
        missing = self._missing_refs(manifest, set(keys))
        if missing:
            raise ValueError(f"{self.key}: viewer config references unknown channels {sorted(missing)}")
        (out / f"{self.key}.json").write_text(json.dumps(manifest, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        res = project_dir / "results"
        res.mkdir(exist_ok=True)
        with gzip.open(res / f"{self.key}_hourly.csv.gz", "wt", encoding="utf-8", newline="") as fh:
            fh.write("t_s," + ",".join(f"{k} [{self.meta[k]['unit']}]" for k in keys) + "\n")
            t = np.arange(self.n) * self.dt
            data = np.column_stack([t] + [self.channels[k] for k in keys])
            np.savetxt(fh, data, delimiter=",", fmt="%.6g")
        (res / f"{self.key}_kpis.json").write_text(json.dumps(self.kpis, indent=1, ensure_ascii=False), encoding="utf-8")
        return {"key": self.key, "name": self.name, "badge": scenario_cfg.get("badge", self.key),
                "channels": len(keys), "bytes": block.nbytes}

    @staticmethod
    def _r(v):
        return float(f"{v:.6g}")

    @staticmethod
    def _missing_refs(manifest, keys):
        refs = set()
        for sec in ("chartDefault", "sensors", "ledger", "cmds"):
            for item in manifest.get(sec, []):
                k = item if isinstance(item, str) else item.get("key")
                refs.add(k)
                if isinstance(item, dict) and item.get("refKey"):
                    refs.add(item["refKey"])
        for b in manifest.get("bindings", []):
            for f in ("key", "colorKey", "speedKey"):
                if b.get(f):
                    refs.add(b[f])
        for tag in manifest.get("tags", []):
            refs.update(tag.get("keys", []))
        return {r for r in refs if r and r not in keys}

    @staticmethod
    def monthly_sum(values, times, scale=1.0):
        months = times.dt.month.to_numpy()
        return [float(np.sum(values[months == m]) * scale) for m in range(1, 13)]
