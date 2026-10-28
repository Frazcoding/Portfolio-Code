"""The JSON API of the web app, shared by the FastAPI server (``app/server.py``) and the browser build (Pyodide, see
``tools/build_static.py``). Pure Python: no web framework and no network access; the callers fetch external data
(OSRM, Nominatim, Overpass) themselves and hand it in.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import PROJECT_NAME
from .config import Config
from .model import HubModel, Params, SiteCase
from .runner import Payloads, Runner


class WebApi:
    """``schema``, ``evaluate``, ``swept`` and the pure half of the site screening, as JSON-ready dicts."""

    def __init__(self, config_path: Path, runner: Runner):
        self.runner = runner
        self.base = Config.from_toml(config_path)

    def config_from(self, body: dict) -> Config:
        """Baseline with the request's dotted-key overrides (raises ``ConfigError``)."""
        return self.base.with_overrides(body.get("params") or {})

    def schema(self) -> dict:
        return Payloads.schema(self.base, PROJECT_NAME, self.runner.catalogue)

    def gis(self) -> dict:
        return self.runner.catalogue.gis()

    def evaluate(self, body: dict) -> dict:
        out = self.runner.evaluate(self.config_from(body), body.get("sites"))
        return Payloads.simrun("live", out)

    def swept(self, body: dict) -> dict:
        """The design's own swept-path checks (scripts/hub_design.py) for the variant that holds this fleet."""
        cfg = self.config_from(body)
        sel = HubModel(Params.from_config(cfg)).evaluate(SiteCase.from_config(cfg))
        lay = self.runner.design.layout(sel.fleet_total, cfg.site.id, sel.area_ok)
        clear = lay["summary"]["clearances"]
        return {"variant": lay["name"], "drawing": lay["drawing"], "site_specific": lay["site_specific"],
                "envelopes": [f for f in lay["features"] if f["kind"] == "swept"],
                "clearances": [{"id": c[0], "desc": c[1], "clearance_m": c[2]} for c in clear],
                "min_clearance_m": min(c[2] for c in clear), "movements": len(clear)}

    @staticmethod
    def screen_score(data: dict, origin: list[float], route: dict | None, top: int = 15) -> dict:
        from .geo import SiteScreener
        return SiteScreener().score(data, tuple(origin), route, top)

    @staticmethod
    def screen_finalize(scored: dict, roads: list[dict]) -> dict:
        from .geo import SiteScreener
        return SiteScreener().finalize(scored, roads)

    @staticmethod
    def screen_query(origin: list[float]) -> str:
        from .geo import SiteScreener
        return SiteScreener.query_text(*origin)

    # ------------------------------------------------------------------ browser bridge
    def call(self, method: str, payload: str) -> str:
        """JSON in, JSON out (the Pyodide entry point: ``api.call("evaluate", JSON.stringify(body))``)."""
        args: Any = json.loads(payload) if payload else {}
        if method in ("schema", "gis"):
            res = getattr(self, method)()
        elif method in ("evaluate", "swept"):
            res = getattr(self, method)(args)
        elif method == "screen_query":
            res = self.screen_query(args["origin"])
        elif method == "screen_score":
            res = self.screen_score(args["data"], args["origin"], args.get("route"), int(args.get("top", 15)))
        elif method == "screen_finalize":
            res = self.screen_finalize(args["scored"], args["roads"])
        else:
            raise ValueError(f"unknown method {method}")
        return json.dumps(res, separators=(",", ":"), allow_nan=False, default=float)
