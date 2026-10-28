from ember_hub_simulator import HubDesign


def test_variants_follow_the_fleet(paths):
    d = HubDesign.load(paths.data)
    assert d.capacity == 11
    base = d.layout(8, "S1", True)
    assert base["name"] == "base" and base["lanes"] == 8 and base["fits"] and base["drawing"] == "EMB-HUB-003"
    assert sum(s["wired"] for s in base["slots"]) == 4 and base["deadrun_route"]["distance_km"] > 3
    assert d.layout(9, "S1", True)["name"] == "expansion"
    big = d.layout(12, "S1", True)
    assert big["name"] == "expansion" and not big["fits"]
    other = d.layout(9, "S2", False)
    assert not other["site_specific"] and other["deadrun_route"] is None and not other["fits"]
