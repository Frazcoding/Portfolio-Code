"""Imported avocado benchmark: kg CO2e and landed cost per kg delivered to a UK RDC, by origin and mode.

Chain: orchard -> packhouse + carton -> road to port -> reefer container ship (sea-route distance from searoute) ->
UK port -> road to RDC -> ripening. Spain and Morocco come by reefer truck. Air variant for long-haul origins.
Transport loss (3 %) inflates everything upstream of the RDC. Data and sources: data/imports_*.csv,
data/freight_factors.csv, data/chain_stages.csv. The volume-weighted average is the target for UK fruit.

Cost target = CIF unit value at the UK border (Comtrade). It excludes UK port handling, haulage, ripening and
importer margin, so it is the floor the UK greenhouse has to beat at the farm gate, not a retail price.
"""
import csv
import json
import math
from pathlib import Path

import searoute

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"

UK_PORT = ("London Gateway", 51.50, 0.48)
UK_AIRPORT = ("London Heathrow", 51.47, -0.45)
ROAD_PORT_TO_RDC_KM = 190.0     # London Gateway -> Midlands RDC (Daventry), estimated
ROAD_AIRPORT_TO_RDC_KM = 120.0  # Heathrow -> Midlands RDC, estimated
AIR_GCD_UPLIFT = 1.08           # great-circle to flown distance, DESNZ methodology (8 %)
VOLUME_YEAR = 2025


def _read(name):
    with (DATA / name).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _f(x):
    return float(x) if x not in ("", None) else None


def gcd_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def load():
    ff = {r["mode"]: _f(r["kg_co2e_per_tkm"]) + _f(r["wtt_kg_co2e_per_tkm"]) for r in _read("freight_factors.csv")}
    st = {r["stage"]: _f(r["value"]) for r in _read("chain_stages.csv")}
    farm = {r["iso3"]: r for r in _read("imports_farm_ghg.csv")}
    routes = {r["iso3"]: r for r in _read("imports_routes.csv")}
    trade = [t for t in _read("imports_trade.csv") if t.get("crop", "avocado") == "avocado"]
    return ff, st, farm, routes, trade


def chain(iso3, mode, farm_value, ff, st, routes):
    """kg CO2e per kg delivered to the RDC, by stage."""
    r = routes[iso3]
    km = {}
    s = {"farm": farm_value, "packhouse": st["packhouse"], "packaging": st["packaging"]}
    if mode == "sea":
        km["road_origin"] = _f(r["road_to_port_km"])
        km["sea"] = searoute.searoute([_f(r["port_lon"]), _f(r["port_lat"])], [UK_PORT[2], UK_PORT[1]],
                                      units="km")["properties"]["length"]
        km["road_uk"] = ROAD_PORT_TO_RDC_KM
        s["road_origin"] = km["road_origin"] / 1000 * ff["reefer_hgv"]
        s["sea"] = km["sea"] / 1000 * ff["container_ship"]
        s["road_uk"] = km["road_uk"] / 1000 * ff["reefer_hgv"]
    elif mode == "air":
        km["road_origin"] = 100.0  # packhouse to airport, estimated
        km["air"] = gcd_km(_f(r["air_lat"]), _f(r["air_lon"]), UK_AIRPORT[1], UK_AIRPORT[2]) * AIR_GCD_UPLIFT
        km["road_uk"] = ROAD_AIRPORT_TO_RDC_KM
        s["road_origin"] = km["road_origin"] / 1000 * ff["reefer_hgv"]
        s["air"] = km["air"] / 1000 * ff["air_long_haul"]
        s["road_uk"] = km["road_uk"] / 1000 * ff["reefer_hgv"]
    else:  # road
        km["road"] = _f(r["road_to_port_km"]) + _f(r["road_km_europe"])
        s["road"] = km["road"] / 1000 * ff["reefer_hgv"]
    loss = st["transport_loss"]
    upstream = sum(s.values())
    s["transport_loss"] = upstream * loss / (1 - loss)
    s["ripening"] = st["ripening"]
    return s, km


def run():
    ff, st, farm, routes, trade = load()
    yr = [t for t in trade if int(t["year"]) == VOLUME_YEAR]
    world_t = next(_f(t["tonnes"]) for t in yr if t["iso3"] == "W00")
    by_iso = {t["iso3"]: t for t in yr}
    cif3 = {}
    for t in trade:
        cif3.setdefault(t["iso3"], []).append((_f(t["tonnes"]), _f(t["tonnes"]) * _f(t["gbp_per_kg_cif"])))

    out = []
    for iso3, fr in farm.items():
        modes = [routes[iso3]["mode"]] + (["air"] if routes[iso3]["air_from"] else [])
        tr = by_iso.get(iso3)
        tt = cif3.get(iso3, [])
        cif_mean = sum(v for _, v in tt) / sum(t for t, _ in tt) if tt else None
        for mode in modes:
            central, km = chain(iso3, mode, _f(fr["farm_central"]), ff, st, routes)
            lo, _ = chain(iso3, mode, _f(fr["farm_low"]), ff, st, routes)
            hi, _ = chain(iso3, mode, _f(fr["farm_high"]), ff, st, routes)
            out.append({
                "origin": fr["origin"], "iso3": iso3, "mode": mode,
                "kg_co2e_per_kg": sum(central.values()), "low": sum(lo.values()), "high": sum(hi.values()),
                "stages": central, "km": km,
                "sequestration_credit": _f(fr["sequestration_credit"]), "farm_confidence": fr["confidence"],
                "tonnes": _f(tr["tonnes"]) if tr and mode != "air" else 0.0,
                "share": _f(tr["tonnes"]) / world_t if tr and mode != "air" else 0.0,
                "gbp_per_kg_cif": _f(tr["gbp_per_kg_cif"]) if tr else None,
                "gbp_per_kg_cif_2023_25": cif_mean,
            })

    sea = [o for o in out if o["mode"] != "air"]
    covered = sum(o["share"] for o in sea)
    wavg = lambda key: sum(o[key] * o["share"] for o in sea) / covered  # noqa: E731
    w = by_iso["W00"]
    summary = {
        "volume_year": VOLUME_YEAR, "uk_imports_t": world_t, "share_covered": covered,
        "weighted_kg_co2e_per_kg": wavg("kg_co2e_per_kg"),
        "weighted_low": wavg("low"), "weighted_high": wavg("high"),
        "best_origin": min(sea, key=lambda o: o["kg_co2e_per_kg"])["origin"],
        "best_kg_co2e_per_kg": min(o["kg_co2e_per_kg"] for o in sea),
        "cif_gbp_per_kg_all_origins": _f(w["gbp_per_kg_cif"]),
        "cif_gbp_per_kg_all_origins_2023_25": cif3 and (sum(v for _, v in cif3["W00"]) / sum(t for t, _ in cif3["W00"])),
        "cheapest_origin_cif": min((o for o in sea if o["gbp_per_kg_cif"]), key=lambda o: o["gbp_per_kg_cif"])["origin"],
    }
    return out, summary


if __name__ == "__main__":
    out, summary = run()
    (HERE / "results" / "imports_summary.json").write_text(
        json.dumps({"summary": summary, "origins": out}, indent=1, default=float))
    print(f"{'origin':<14}{'mode':<6}{'share':>7}{'farm':>7}{'pack':>7}{'transp':>8}{'ripen':>7}"
          f"{'TOTAL':>8}{'range':>14}{'CIF £/kg':>10}")
    for o in sorted(out, key=lambda o: (o["mode"] == "air", -o["share"])):
        s = o["stages"]
        tr = sum(v for k, v in s.items() if k not in ("farm", "packhouse", "packaging", "ripening"))
        cif = f"{o['gbp_per_kg_cif']:.2f}" if o["gbp_per_kg_cif"] and o["mode"] != "air" else "-"
        print(f"{o['origin']:<14}{o['mode']:<6}{o['share']*100:>6.1f}%{s['farm']:>7.2f}"
              f"{s['packhouse']+s['packaging']:>7.2f}{tr:>8.2f}{s['ripening']:>7.2f}{o['kg_co2e_per_kg']:>8.2f}"
              f"{o['low']:>7.2f}-{o['high']:<6.2f}{cif:>10}")
    print(json.dumps(summary, indent=1, default=float))
