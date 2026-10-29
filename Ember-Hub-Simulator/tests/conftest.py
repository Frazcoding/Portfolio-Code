import pytest

from ember_hub_simulator import Config, HubDesign, ProjectPaths, Simulation
from ember_hub_simulator.runner import SiteCatalogue, Runner


@pytest.fixture(scope="session")
def paths() -> ProjectPaths:
    return ProjectPaths.discover()


@pytest.fixture(scope="session")
def base_config(paths) -> Config:
    return Config.from_toml(paths.baseline)


@pytest.fixture(scope="session")
def listed_sites(paths) -> list[dict]:
    return SiteCatalogue(paths.data).listed()


@pytest.fixture(scope="session")
def baseline(base_config, listed_sites):
    """The sheet baseline (S1 selected, S2 and S3 as alternatives), simulated once for the whole session."""
    return Simulation.from_config(base_config, Runner.alternatives(listed_sites), HubDesign.load(ProjectPaths.discover().data)).run()


@pytest.fixture
def short_config(base_config) -> Config:
    return base_config.with_overrides({"sim.horizon_h": 24})
