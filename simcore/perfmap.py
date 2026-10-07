"""Gridded steady-state performance maps with multilinear interpolation.

A cycle solver is evaluated once over a rectilinear grid of boundary conditions
(e.g. air temperature, water temperature, compressor speed). The time-domain
simulation then interpolates every output quantity at once, which makes
sub-hourly control over a full year affordable while keeping each map point a
full thermodynamic solution.
"""
import hashlib
import itertools
import json
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from . import CACHE


def _solve_line(args):
    fn_path, fn_name, params, axes, outer_idx, out_keys = args
    import importlib
    import importlib.util
    import sys
    from pathlib import Path
    fp = Path(fn_path)
    if fp.parent.name == "simcore":
        sys.path.insert(0, str(fp.parent.parent))
        mod = importlib.import_module(f"simcore.{fp.stem}")
    else:
        spec = importlib.util.spec_from_file_location("_pm_mod", fn_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    fn = getattr(mod, fn_name)
    names = list(axes)
    inner = [axes[n] for n in names[1:]]
    res = np.full([len(a) for a in inner] + [len(out_keys)], np.nan)
    guess = None
    for idx in itertools.product(*[range(len(a)) for a in inner]):
        point = {names[0]: axes[names[0]][outer_idx]}
        point.update({n: inner[i][j] for i, (n, j) in enumerate(zip(names[1:], idx))})
        try:
            out, guess = fn(params, point, guess)
            res[idx] = [out[k] for k in out_keys]
        except Exception:
            guess = None
    return outer_idx, res


class PerfMap:
    def __init__(self, name, fn_path, fn_name, params, axes, out_keys, workers=None, deps=()):
        self.axes = {k: np.asarray(v, dtype=float) for k, v in axes.items()}
        self.names = list(axes)
        self.out_keys = list(out_keys)
        self.kidx = {k: i for i, k in enumerate(self.out_keys)}
        tag = hashlib.sha1(json.dumps([params, {k: list(v) for k, v in axes.items()}, out_keys,
                                       open(fn_path, "rb").read().hex()]
                                      + [open(d, "rb").read().hex() for d in deps], sort_keys=True, default=str)
                           .encode()).hexdigest()[:12]
        path = CACHE / f"perfmap_{name}_{tag}.npy"
        if path.exists():
            self.data = np.load(path)
        else:
            outer = self.axes[self.names[0]]
            shape = [len(a) for a in self.axes.values()] + [len(out_keys)]
            data = np.full(shape, np.nan)
            jobs = [(str(fn_path), fn_name, params, {k: list(v) for k, v in self.axes.items()}, i, self.out_keys)
                    for i in range(len(outer))]
            with ProcessPoolExecutor(max_workers=workers or max(1, (os.cpu_count() or 2) - 1)) as ex:
                for i, res in ex.map(_solve_line, jobs):
                    data[i] = res
            self.data = data
            np.save(path, data)
        self.valid = np.isfinite(self.data[..., 0])
        self._fill()

    def _fill(self):
        """Replace failed points by nearest valid neighbour along the last axes (keeps interpolation finite)."""
        d = self.data
        bad = ~np.isfinite(d)
        if not bad.any():
            return
        for ax in reversed(range(d.ndim - 1)):
            for direction in (1, -1):
                for _ in range(d.shape[ax]):
                    shifted = np.roll(d, direction, axis=ax)
                    take = ~np.isfinite(d) & np.isfinite(shifted)
                    d[take] = shifted[take]
        self.data = d

    def coverage(self):
        return float(self.valid.mean())

    def __call__(self, **pt):
        """Interpolate all outputs at one point; returns (vector, validity weight)."""
        idx, w = [], []
        for n in self.names:
            a = self.axes[n]
            v = min(max(pt[n], a[0]), a[-1])
            i = int(np.clip(np.searchsorted(a, v) - 1, 0, len(a) - 2))
            f = (v - a[i]) / (a[i + 1] - a[i])
            idx.append(i)
            w.append(f)
        out = np.zeros(len(self.out_keys))
        ok = 0.0
        for corner in itertools.product((0, 1), repeat=len(self.names)):
            wt = 1.0
            sl = []
            for c, i, f in zip(corner, idx, w):
                wt *= f if c else (1 - f)
                sl.append(i + c)
            if wt == 0:
                continue
            sl = tuple(sl)
            out += wt * self.data[sl]
            ok += wt * self.valid[sl]
        return out, ok

    def get(self, vec, key):
        return vec[self.kidx[key]]
