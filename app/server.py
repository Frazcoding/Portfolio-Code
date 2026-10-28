"""FastAPI server for the Sim Workbench front end.

    GET  /                  Workbench page (static)
    GET  /api/schema        editable parameters (from the config), text fields, KPI metadata, candidate sites
    POST /api/evaluate      {"params": {...}, "sites": [...]} -> runs the model, returns a SimRun (not recorded; live updates)
    POST /api/run           same, and records a run folder in results/
    GET  /api/runs          run folders in results/
    GET  /api/runs/{name}   one run folder as a SimRun
    GET  /api/gis           Bristol screening layers (route, listed sites, screened plots, substations)
    GET  /api/geocode?q=    place search (Nominatim)
    POST /api/route         {"origin": [lon, lat], "dest": [lon, lat]} -> distance, coach drive time, route line (OSRM)
    POST /api/deadruns      {"origin": [lon, lat], "sites": [{"id", "lon", "lat"}]} -> road dead-runs (OSRM table)
    POST /api/screen        {"origin": [lon, lat], "route": GeoJSON line} -> screened OSM plots around the origin
    POST /api/swept         {"params": {...}} -> swept-path envelopes and clearances of the hub design for that fleet
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ember_hub_simulator import PROJECT_NAME
from ember_hub_simulator.config import Config, ConfigError, ProjectPaths
from ember_hub_simulator.geo import Geocoder, Router, SiteScreener
from ember_hub_simulator.runner import Payloads, Runner
from ember_hub_simulator.webapi import WebApi


class WorkbenchApp:
    """Builds the FastAPI application for a project root (runs are recorded in ``<root>/results``)."""

    HERE = Path(__file__).resolve().parent

    def __init__(self, root: Path | None = None, config_path: Path | None = None):
        self.paths = ProjectPaths(Path(root)) if root is not None else ProjectPaths(self.HERE.parent)
        code = ProjectPaths(self.HERE.parent)
        self.config_path = Path(config_path) if config_path else code.baseline
        self.runner = Runner(self.paths.root)
        self.api = WebApi(self.config_path, self.runner)
        cache = code.cache
        self.geocoder = Geocoder(cache)
        self.router = Router(cache)
        self.screener = SiteScreener(cache, self.router)
        self.app = FastAPI(title=PROJECT_NAME)
        self._routes()

        @self.app.middleware("http")
        async def revalidate(request, call_next):
            """Browsers revalidate the page and static files, so a redeploy reaches every viewer at once."""
            response = await call_next(request)
            if not request.url.path.startswith("/api/"):
                response.headers["Cache-Control"] = "no-cache"
            return response

    def config_from(self, body: dict) -> Config:
        try:
            return self.api.config_from(body)
        except ConfigError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e

    @staticmethod
    async def external(fn, *args):
        """Call an external-service method in a worker thread; network failures become 502 with a readable message."""
        try:
            return await run_in_threadpool(fn, *args)
        except (httpx.HTTPError, ValueError, KeyError) as e:
            raise HTTPException(status_code=502, detail=f"map service unavailable: {e}") from e

    def _routes(self) -> None:
        app = self.app

        @app.get("/api/schema")
        def schema() -> dict:
            return self.api.schema()

        @app.post("/api/evaluate")
        async def evaluate(body: dict[str, Any] | None = Body(default=None)) -> dict:
            body = body or {}
            self.config_from(body)                      # 422 on a bad parameter
            return await run_in_threadpool(self.api.evaluate, body)

        @app.post("/api/run")
        async def run(body: dict[str, Any] | None = Body(default=None)) -> dict:
            body = body or {}
            cfg = self.config_from(body)
            name = str(body.get("name") or "app")
            res = await run_in_threadpool(self.runner.run, cfg, name, [self.config_path.resolve()], False, body.get("sites"))
            payload = Payloads.simrun(res.run_dir.name, res.output)
            payload["run_dir"] = res.run_dir.name
            return payload

        @app.get("/api/runs")
        def runs() -> list[dict]:
            return self.runner.summaries()

        @app.get("/api/runs/{name}")
        def one_run(name: str) -> dict:
            try:
                d = self.runner.resolve(name)
            except FileNotFoundError as e:
                raise HTTPException(status_code=404, detail=f"no run '{name}'") from e
            manifest, frame = self.runner.load(d)
            return Payloads.from_frame(d.name, frame, manifest["metrics"], self.runner.load_extras(d))

        @app.get("/api/gis")
        def gis() -> dict:
            return self.runner.catalogue.gis()

        @app.get("/api/geocode")
        async def geocode(q: str = Query(..., min_length=2, max_length=200)) -> list[dict]:
            return await self.external(self.geocoder.search, q)

        @app.post("/api/route")
        async def route(body: dict[str, Any] = Body(...)) -> dict:
            a, b = self.point(body, "origin"), self.point(body, "dest")
            return await self.external(self.router.route, a, b)

        @app.post("/api/deadruns")
        async def deadruns(body: dict[str, Any] = Body(...)) -> list[dict]:
            origin = self.point(body, "origin")
            sites = body.get("sites") or []
            pts = [(float(s["lon"]), float(s["lat"])) for s in sites]
            res = await self.external(self.router.table_from, origin, pts)
            return [{"id": s["id"], **r} for s, r in zip(sites, res)]

        @app.post("/api/screen")
        async def screen(body: dict[str, Any] = Body(...)) -> dict:
            origin = self.point(body, "origin")
            return await self.external(self.screener.screen, origin, body.get("route"), int(body.get("top", 15)))

        @app.post("/api/swept")
        async def swept(body: dict[str, Any] | None = Body(default=None)) -> dict:
            body = body or {}
            self.config_from(body)
            return await run_in_threadpool(self.api.swept, body)

        @app.get("/")
        def index() -> FileResponse:
            return FileResponse(self.HERE / "static" / "index.html")

        app.mount("/static", StaticFiles(directory=self.HERE / "static"), name="static")

    @staticmethod
    def point(body: dict, key: str) -> tuple[float, float]:
        try:
            lon, lat = body[key]
            lon, lat = float(lon), float(lat)
        except (KeyError, TypeError, ValueError) as e:
            raise HTTPException(status_code=422, detail=f"'{key}' must be [lon, lat]") from e
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            raise HTTPException(status_code=422, detail=f"'{key}' is outside lon/lat range")
        return lon, lat
