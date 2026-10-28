"""Command line: ``uv run <project> run | app | figures | report | mlflow-index``."""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

from . import PROJECT_NAME
from .config import Config, ConfigError, ProjectPaths
from .runner import Runner


class Cli:
    """Argument parsing and dispatch; the work lives in :class:`Runner`, ``FigureBuilder`` and ``ReportBuilder``."""

    def __init__(self, paths: ProjectPaths | None = None):
        self.paths = paths or ProjectPaths.discover()

    # ------------------------------------------------------------------ parser
    def parser(self) -> argparse.ArgumentParser:
        p = argparse.ArgumentParser(prog=self.paths.root.name, description=PROJECT_NAME)
        sub = p.add_subparsers(dest="command", required=True)
        r = sub.add_parser("run", help="simulate a config and write results/<date>_<name>/")
        r.add_argument("config", nargs="?", type=Path, default=self.paths.baseline, help="TOML config (default: config/baseline.toml)")
        r.add_argument("--name", help="run name (default: config file stem)")
        r.add_argument("--track", action="store_true", help="also log to MLflow (needs the 'tracking' extra)")
        a = sub.add_parser("app", help="serve the Sim Workbench web app")
        a.add_argument("--host", default="127.0.0.1")
        a.add_argument("--port", type=int, default=8000)
        sub.add_parser("figures", help="matplotlib figures (SVG + PNG) from the latest run into docs/figures")
        sub.add_parser("report", help="compile docs/report.typ and docs/slides.typ to PDF")
        sub.add_parser("mlflow-index", help="rebuild the local MLflow index from the run folders")
        return p

    # ------------------------------------------------------------------ commands
    def cmd_run(self, args) -> int:
        cfg = Config.from_toml(args.config)
        name = args.name or Path(args.config).stem
        try:
            res = Runner(self.paths.root).run(cfg, name, inputs=[Path(args.config).resolve()], track=args.track)
        except ImportError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        print(f"run folder: {res.run_dir}")
        for k, v in res.manifest["metrics"].items():
            print(f"  {k:28s} {v:12.4f}")
        return 0

    def cmd_app(self, args) -> int:
        import uvicorn

        app = self.load_app(self.paths.root)
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")
        return 0

    def cmd_figures(self, args) -> int:
        from .figures import FigureBuilder

        for p in FigureBuilder(self.paths.root).build():
            print("wrote", p)
        return 0

    def cmd_report(self, args) -> int:
        from .report import ReportBuilder

        for p in ReportBuilder(self.paths.root, PROJECT_NAME).build():
            print("wrote", p)
        return 0

    def cmd_mlflow_index(self, args) -> int:
        from simcore.results import Run

        try:
            n = Run.rebuild_mlflow_index(self.paths.root)
        except ImportError:
            print("MLflow is not installed. Install the optional extra:  uv sync --extra tracking", file=sys.stderr)
            return 2
        print(f"indexed {n} run(s) into {Run.default_tracking_uri()}")
        return 0

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def load_app(project_root: Path, root: Path | None = None, **kwargs):
        """Import ``app/server.py`` by path and return its FastAPI application.

        ``root`` (default: ``project_root``) is where runs are recorded; tests point it at a temporary folder.
        """
        paths = ProjectPaths(Path(project_root))
        spec = importlib.util.spec_from_file_location("workbench_server", paths.app_server)
        module = importlib.util.module_from_spec(spec)
        sys.modules["workbench_server"] = module
        spec.loader.exec_module(module)
        return module.WorkbenchApp(root or paths.root, **kwargs).app

    def main(self, argv: list[str] | None = None) -> int:
        args = self.parser().parse_args(argv)
        handler = getattr(self, "cmd_" + args.command.replace("-", "_"))
        try:
            return handler(args)
        except (ConfigError, FileNotFoundError, RuntimeError) as e:
            print(f"error: {e}", file=sys.stderr)
            return 1


def main(argv: list[str] | None = None) -> None:
    """Console-script entry point."""
    sys.exit(Cli().main(argv))
