"""Build the static, server-free version of the app into ``dist/`` and ``ember-hub-simulator-web.zip`` (for sharing as
a link from any static host: Netlify Drop, GitHub Pages, Cloudflare Pages; see SHARING.md).

The page runs the same Python package in the browser with Pyodide (``app/static/backend.js``); route, place search and
site screening call OSRM, Nominatim and Overpass directly from the browser. Saving run folders needs the server version.

    uv run python tools/build_static.py         # -> dist/index.html, dist/static/*
    python -m http.server -d dist 8800          # local check: http://localhost:8800
"""
from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIMCORE = ROOT.parent / "simcore" / "src" / "simcore"
DIST = ROOT / "dist"

# modules the web API needs (cli / figures / report / plotting need matplotlib or typst and stay server-side)
PACKAGE = ["__init__.py", "config.py", "design.py", "model.py", "runner.py", "geo.py", "webapi.py"]
DATA = ["bristol_gis.json", "sites_bristol.json", "temple_works_design.json"]
STATIC = ["app.js", "backend.js", "bundle.js", "bundle.css", "tokens.css", "ember.css"]

SIMCORE_INIT = '''"""Subset of simcore for the browser build: unit conversion only (copied verbatim from simcore/core)."""
'''
SIMCORE_CORE_INIT = '''"""Subset of simcore.core for the browser build (Units, Constants), copied verbatim from simcore."""
from .constants import Constants
from .units import Units

__all__ = ["Constants", "Units"]
'''


class StaticBuild:
    def bundle(self, prev: dict[str, str] | None = None) -> dict[str, str]:
        """Python sources and data, keyed by their path under the virtual project root (/app in Pyodide)."""
        prev = prev or {}
        files = {f"src/ember_hub_simulator/{m}": (ROOT / "src" / "ember_hub_simulator" / m).read_text(encoding="utf-8")
                 for m in PACKAGE}
        files["src/simcore/__init__.py"] = SIMCORE_INIT
        files["src/simcore/core/__init__.py"] = SIMCORE_CORE_INIT
        for m in ("units.py", "constants.py"):
            src = SIMCORE / "core" / m
            files[f"src/simcore/core/{m}"] = src.read_text(encoding="utf-8") if src.exists() else prev[f"src/simcore/core/{m}"]
        files["config/baseline.toml"] = (ROOT / "config" / "baseline.toml").read_text(encoding="utf-8")
        for d in DATA:
            files[f"data/{d}"] = (ROOT / "data" / d).read_text(encoding="utf-8")
        return files

    def index(self) -> str:
        html = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
        html = html.replace('href="/static/', 'href="static/').replace('src="/static/', 'src="static/')
        return html.replace("<head>", "<head>\n<script>window.EMBER_STATIC = true;</script>", 1)

    def build(self) -> Path:
        prev_bundle = DIST / "static" / "py_bundle.json"
        prev = json.loads(prev_bundle.read_text(encoding="utf-8")) if prev_bundle.exists() else {}
        if DIST.exists():
            shutil.rmtree(DIST)
        (DIST / "static").mkdir(parents=True)
        for f in STATIC:
            shutil.copy2(ROOT / "app" / "static" / f, DIST / "static" / f)
        (DIST / "static" / "py_bundle.json").write_text(json.dumps(self.bundle(prev)), encoding="utf-8")
        (DIST / "index.html").write_text(self.index(), encoding="utf-8")
        size = sum(p.stat().st_size for p in DIST.rglob("*") if p.is_file())
        zpath = ROOT / "ember-hub-simulator-web.zip"
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(DIST.rglob("*")):
                if f.is_file():
                    z.write(f, f.relative_to(DIST).as_posix())
        print(f"wrote {DIST} ({size / 1024:.0f} kB) and {zpath.name} ({zpath.stat().st_size / 1024:.0f} kB)")
        return DIST


if __name__ == "__main__":
    StaticBuild().build()
