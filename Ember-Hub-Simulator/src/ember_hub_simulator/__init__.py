"""Ember Hub Simulator: Ember Bristol-London coach charging hub: operations, cost and site layout simulator (Sim Workbench project)."""
from importlib.metadata import PackageNotFoundError, version

from .config import Config, ConfigError, ProjectPaths
from .design import HubDesign
from .model import DaySimulation, HubModel, Params, SimOutput, Simulation, SiteCase

PROJECT_NAME = "Ember Hub Simulator"

try:
    __version__ = version("ember-hub-simulator")
except PackageNotFoundError:  # running from a source tree without install
    __version__ = "0+unknown"

__all__ = ["PROJECT_NAME", "Config", "ConfigError", "DaySimulation", "HubDesign", "HubModel", "Params",
           "ProjectPaths", "SimOutput", "Simulation", "SiteCase"]
