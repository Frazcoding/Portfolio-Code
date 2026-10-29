import json

import pandas as pd

from ember_hub_simulator import Config
from ember_hub_simulator.runner import Runner


def test_run_folder_and_manifest(tmp_path, paths, short_config, listed_sites):
    res = Runner(tmp_path).run(short_config, "unit", inputs=[paths.baseline], sites=listed_sites)
    d = res.run_dir
    assert d.parent == tmp_path / "results" and d.name.endswith("_unit")
    m = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    for key in ("name", "status", "created_utc", "finished_utc", "runtime_s", "git", "simcore_version",
                "input_hashes", "params", "metrics", "artifacts"):
        assert key in m, key
    assert m["status"] == "finished" and m["name"] == "unit"
    assert len(next(iter(m["input_hashes"].values()))) == 64
    assert m["params"]["hub.charge_power_kW"] == short_config.hub.charge_power_kW
    assert m["metrics"]["total_gbp_yr"] == res.output.kpis["total_gbp_yr"]
    assert {"config.toml", "timeline.parquet", "sites.json", "layout.json", "trips.json"} <= set(m["artifacts"])
    frame = pd.read_parquet(d / "timeline.parquet")
    assert len(frame) == 24 * 60
    assert len(json.loads((d / "sites.json").read_text(encoding="utf-8"))) == 3
    # the recorded config.toml reproduces the configuration
    assert Config.from_toml(d / "config.toml") == short_config


def test_latest_and_listing(tmp_path, short_config):
    runner = Runner(tmp_path)
    a = runner.run(short_config, "a", sites=[])
    b = runner.run(short_config, "b", sites=[])
    assert runner.latest() == b.run_dir
    assert [s["name"] for s in runner.summaries()] == [b.run_dir.name, a.run_dir.name]
