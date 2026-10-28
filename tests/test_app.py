import pytest
from fastapi.testclient import TestClient

from ember_hub_simulator.cli import Cli


@pytest.fixture
def client(tmp_path, paths):
    return TestClient(Cli.load_app(paths.root, root=tmp_path))


def test_schema(client):
    s = client.get("/api/schema").json()
    keys = {p["key"] for p in s["params"]}
    assert {"timetable.headway_min", "hub.charge_power_kW", "site.area_m2", "route.distance_km"} <= keys
    assert {"key", "label", "unit", "value", "min", "max", "step", "group"} <= set(s["params"][0])
    assert s["text"]["site.id"] == "S1"
    assert {x["id"] for x in s["sites"]} == {"S1", "S2", "S3"} and len(s["screened"]) == 10
    assert {"grid_kVA", "charging", "soc_min"} <= {v["key"] for v in s["variables"]}


def test_evaluate_returns_simrun_without_recording(client, tmp_path, listed_sites):
    r = client.post("/api/evaluate", json={"params": {"timetable.headway_min": 30}, "sites": listed_sites})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["n"] == 48 * 60 and d["dt_s"] == 60
    assert d["vars"][0] == {"key": "t", "label": "Time", "unit": "h"}
    assert all(len(d["data"][v["key"]]) == d["n"] for v in d["vars"])
    assert d["kpis"]["fleet"] == 15
    assert {r["site_id"] for r in d["sites"]} == {"S1", "S2", "S3"}
    assert d["layout"]["name"] == "expansion" and d["layout"]["fits"] is False   # 15 coaches > 11 lanes
    assert not (tmp_path / "results").exists()


def test_run_records_folder_and_reloads(client, tmp_path):
    d = client.post("/api/run", json={"params": {"sim.horizon_h": 24}}).json()
    assert (tmp_path / "results" / d["run_dir"] / "manifest.json").exists()
    runs = client.get("/api/runs").json()
    assert [x["name"] for x in runs] == [d["run_dir"]]
    again = client.get(f"/api/runs/{d['run_dir']}").json()
    assert again["n"] == 24 * 60 and again["kpis"]["fleet"] == d["kpis"]["fleet"]
    assert again["layout"]["name"] == d["layout"]["name"] == "base"
    assert client.get("/api/runs/does-not-exist").status_code == 404


def test_bad_parameter_is_rejected(client):
    assert client.post("/api/evaluate", json={"params": {"hub.efficiency": 5}}).status_code == 422
    assert client.post("/api/evaluate", json={"params": {"bogus": 1}}).status_code == 422
    assert client.post("/api/route", json={"origin": [1], "dest": [0, 0]}).status_code == 422


def test_static_pages_and_gis(client):
    assert "Ember Hub Simulator" in client.get("/").text
    for f in ("bundle.js", "app.js", "ember.css"):
        assert client.get(f"/static/{f}").status_code == 200
    g = client.get("/api/gis").json()
    assert g["route"]["geometry"]["type"] == "LineString" and len(g["candidate_plots"]) > 10


def test_swept_returns_design_checks(client):
    r = client.post("/api/swept", json={"params": {}}).json()
    assert r["drawing"] == "EMB-HUB-003" and r["movements"] == 16 and r["min_clearance_m"] == 0.58
    assert len(r["envelopes"]) == 16
