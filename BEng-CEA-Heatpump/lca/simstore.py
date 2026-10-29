"""Permanent store for expensive pure calculations (greenhouse + crop evaluation, hourly heat profiles, LP results).

A result is keyed on its inputs (site, design, crop, options, any arrays) and on a hash of the model code and data it
depends on, so editing the model or a rate file makes old entries unreachable instead of silently stale. Entries are
pickles under results/store/<kind>/; writes are atomic so parallel workers can share it. Delete the folder to reset.
Set CEA_NO_STORE=1 to bypass."""
import dataclasses
import hashlib
import os
import pickle
import tempfile
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE / "results" / "store"
SIMCORE = HERE.parent / "simcore" if (HERE.parent / "simcore").is_dir() else HERE.parent.parent / "simcore"
SIM = HERE.parent / "sim"
SEARCH = (HERE, SIM, SIMCORE.parent)               # the Code root only for the simcore package (see _resolve)
DATA = [p for d in (HERE / "data", HERE / "data" / "siting") for p in sorted(d.glob("*")) if p.suffix in (".csv", ".json", ".xlsx")]
DATA += [HERE / "results" / "compare.json"]       # optimise._state reads D (CO2 price, rates) from it; a stale entry kept the 0.20 CO2 price (2026-10-07)
DOC_ONLY = ("input_register.csv",)                    # documentation tables: never read by a model
# Each kind depends only on the code it runs (static import graph from its entry modules) and the data files those
# modules name. 'lp' is keyed on its own solver code plus the values it reads (profiles, prices, plant constants), passed
# in its args by finalist_lp.run, so cost, finance and documentation edits leave cached LPs valid (2026-10-05).
ENTRIES = {"evaluate": ("site_opt",), "profiles": ("site_opt",), "lp": ("finalist_lp",)}
LP_ONLY = ("finalist_lp", "coldyear", "offgrid", "energy_grid")
_CODE = {}


def _digest(parts):
    h = hashlib.sha256()
    for p in parts:
        h.update(p)
    return h.hexdigest()


def _resolve(name, pkg_dir=None):
    for base in ((pkg_dir,) if pkg_dir else ()) + SEARCH:
        if base == SIMCORE.parent and not name.startswith("simcore"):
            continue
        parts = name.split(".")
        f = base.joinpath(*parts).with_suffix(".py")
        if f.exists():
            return f
        init = base.joinpath(*parts, "__init__.py")
        if init.exists():
            return init
    return None


def module_graph(entries):
    """Source files reachable by import (module- or function-level) from the entry modules, within lca/, simcore/, sim/."""
    import ast
    todo = [f for f in (_resolve(e) for e in entries) if f]
    seen = set()
    while todo:
        f = todo.pop()
        if f in seen:
            continue
        seen.add(f)
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    base = f.parent
                    for _ in range(node.level - 1):
                        base = base.parent
                    mods = [node.module] if node.module else []
                    names = [(m, base) for m in mods] + [((node.module + "." if node.module else "") + a.name, base)
                                                         for a in node.names]
                else:
                    names = [node.module] + [f"{node.module}.{a.name}" for a in node.names]
            for n in names:
                r = _resolve(*n) if isinstance(n, tuple) else _resolve(n)
                if r and r.name != "simstore.py":
                    todo.append(r)
                    if r.name != "__init__.py" and (r.parent / "__init__.py").exists():
                        todo.append(r.parent / "__init__.py")
    return sorted(seen)


def data_refs(files):
    """Data files whose name appears in a string constant of the given modules."""
    import ast
    consts = set()
    for f in files:
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                consts.add(node.value)
    blob = " | ".join(consts)
    return [p for p in DATA if p.name not in DOC_ONLY and (p.name in blob or (p.parent.name == "siting" and "siting" in blob))]


def deps(kind):
    files = module_graph(ENTRIES[kind]) if kind != "lp" else [f for f in (_resolve(m) for m in LP_ONLY) if f]
    return files, data_refs(files)


def code_hash(kind):
    """Hash of the source and data this kind of result depends on (see ENTRIES)."""
    if kind not in _CODE:
        if kind in ENTRIES:
            files, data = deps(kind)
        else:
            files = sorted(p for p in HERE.glob("*.py") if p.name != "simstore.py") + sorted(SIMCORE.glob("*.py"))
            data = [p for p in DATA if p.name not in DOC_ONLY]
        _CODE[kind] = _digest(kind.encode() + p.name.encode() + p.read_bytes() for p in list(files) + list(data))
    return _CODE[kind]


def _feed(h, v):
    if isinstance(v, np.ndarray):
        h.update(str(v.shape).encode() + np.ascontiguousarray(v).tobytes())
    elif isinstance(v, dict):
        for k in sorted(v, key=str):
            h.update(str(k).encode())
            _feed(h, v[k])
    elif isinstance(v, (list, tuple)):
        for i in v:
            _feed(h, i)
    elif dataclasses.is_dataclass(v) and not isinstance(v, type):
        h.update(type(v).__name__.encode())
        for f in dataclasses.fields(v):
            h.update(f.name.encode())
            _feed(h, getattr(v, f.name))
    elif isinstance(v, (int, float, str, bool, type(None), np.generic)):
        h.update(repr(v).encode())
    else:
        h.update(repr(v).encode())


def key(kind, *args):
    h = hashlib.sha256(code_hash(kind).encode())
    for a in args:
        _feed(h, a)
    return h.hexdigest()


def get_or_compute(kind, args, fn):
    if os.environ.get("CEA_NO_STORE"):
        return fn()
    path = ROOT / kind / f"{key(kind, *args)}.pkl"
    if path.exists():
        try:
            return pickle.loads(path.read_bytes())
        except Exception:
            pass
    out = fn()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "wb") as f:
        pickle.dump(out, f, protocol=pickle.HIGHEST_PROTOCOL)
    for attempt in range(5):
        try:
            os.replace(tmp, path)
            break
        except PermissionError:                      # another worker (or the sync client) holds the target: same key, same content
            if path.exists():
                os.unlink(tmp)
                break
            time.sleep(0.2 * (attempt + 1))
    else:
        os.unlink(tmp)
    return out
