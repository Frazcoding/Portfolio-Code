"""Multi-crop comparison data: imported benchmark and UK glasshouse inputs per crop, for the comparison page.

Imports (per crop): every origin above 1 % of 2025 UK volume gets farm (crops.farm_import) + processing + packaging
(Poore & Nemecek category) + transport (route by country, DESNZ 2025 factors) + 3 % transport loss. Origins without a
route fall into "other", carried at the covered volume-weighted mean. Avocado uses the detailed imports.py benchmark.

UK (per m2 per year): yield, labour, consumables, CO2 dosing (crops.py); heat and electricity from run_crops.py
(avocado: run_step3c.py, beds, no LED, semi-closed). The page recombines these live with the design options, so
only per-m2 quantities are stored here. Writes results/compare.json and ../crop_compare.html.
"""
import csv
import json
import sys
from pathlib import Path

import searoute

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import breakeven  # noqa: E402
import crops  # noqa: E402
import imports  # noqa: E402

MIN_SHARE = 0.01
YEAR = 2025


def _routes():
    rows = list(csv.DictReader((HERE / "data" / "country_routes.csv").open(encoding="utf-8")))
    return {(r["iso3"], r["crop"]): r for r in rows}


def route_for(routes, iso3, crop):
    return routes.get((iso3, crop)) or routes.get((iso3, "*"))


def transport(r, ff):
    f = imports._f
    if r["mode"] == "road":
        return {"road": f(r["road_km"]) / 1000 * ff["reefer_hgv"]}, {"road": f(r["road_km"])}
    if r["mode"] == "sea":
        sea = searoute.searoute([f(r["port_lon"]), f(r["port_lat"])], [imports.UK_PORT[2], imports.UK_PORT[1]],
                                units="km")["properties"]["length"]
        km = {"road_origin": f(r["road_km"]), "sea": sea, "road_uk": imports.ROAD_PORT_TO_RDC_KM}
        return {"road_origin": km["road_origin"] / 1000 * ff["reefer_hgv"], "sea": sea / 1000 * ff["container_ship"],
                "road_uk": km["road_uk"] / 1000 * ff["reefer_hgv"]}, km
    air = imports.gcd_km(f(r["air_lat"]), f(r["air_lon"]), imports.UK_AIRPORT[1], imports.UK_AIRPORT[2]) \
        * imports.AIR_GCD_UPLIFT
    km = {"road_origin": f(r["road_km"]), "air": air, "road_uk": imports.ROAD_AIRPORT_TO_RDC_KM}
    return {"road_origin": km["road_origin"] / 1000 * ff["reefer_hgv"], "air": air / 1000 * ff["air_long_haul"],
            "road_uk": km["road_uk"] / 1000 * ff["reefer_hgv"]}, km


def crop_imports(crop, trade, ff, st, routes):
    c = crops.CROPS[crop]
    pn = crops.PN[c["pn"]]
    rows = [t for t in trade if t["crop"] == crop]
    yr = [t for t in rows if int(t["year"]) == YEAR]
    world = next(t for t in yr if t["iso3"] == "W00")
    wt = float(world["tonnes"])
    tot3 = [t for t in rows if t["iso3"] == "W00"]
    cif3 = sum(float(t["tonnes"]) * float(t["gbp_per_kg_cif"]) for t in tot3) / sum(float(t["tonnes"]) for t in tot3)
    origins, missing = [], []
    for t in sorted(yr, key=lambda t: -float(t["tonnes"])):
        share = float(t["tonnes"]) / wt
        if t["iso3"] == "W00" or share < MIN_SHARE:
            continue
        r = route_for(routes, t["iso3"], crop)
        if r is None:
            missing.append(t["origin"])
            continue
        tr, km = transport(r, ff)
        fc, fl, fh, system, fsrc = crops.farm_import(crop, t["iso3"])
        base = {"farm": fc, "processing": pn["processing"], "packaging": pn["packaging"], **tr}
        loss = st["transport_loss"]
        stages = {**base, "transport_loss": sum(base.values()) * loss / (1 - loss)}
        rng = [(v + sum(base.values()) - fc) / (1 - loss) for v in (fl, fh)]
        origins.append({"origin": t["origin"], "iso3": t["iso3"], "share": share, "tonnes": float(t["tonnes"]),
                        "mode": r["mode"], "region": r["region"], "system": system, "farm_source": fsrc,
                        "stages": stages, "km": km, "total": sum(stages.values()), "low": rng[0], "high": rng[1],
                        "gbp_per_kg_cif": float(t["gbp_per_kg_cif"]), "route_confidence": r["confidence"]})
    cov = sum(o["share"] for o in origins)
    wavg = lambda k: sum(o[k] * o["share"] for o in origins) / cov  # noqa: E731
    return {"uk_imports_t": wt, "share_covered": cov, "missing_routes": missing, "origins": origins,
            "weighted": wavg("total"), "weighted_low": wavg("low"), "weighted_high": wavg("high"),
            "best": min(origins, key=lambda o: o["total"])["origin"], "best_total": min(o["total"] for o in origins),
            "cif_2025": float(world["gbp_per_kg_cif"]), "cif_2023_25": cif3,
            "cheapest": min(origins, key=lambda o: o["gbp_per_kg_cif"])["origin"],
            "cheapest_cif": min(o["gbp_per_kg_cif"] for o in origins), "luc_pn": pn["luc"]}


def avocado_imports():
    out, s = imports.run()
    sea = [o for o in out if o["mode"] != "air"]
    origins = [{"origin": o["origin"], "iso3": o["iso3"], "share": o["share"], "tonnes": o["tonnes"],
                "mode": o["mode"], "region": "", "system": "orchard",
                "farm_source": "data/imports_farm_ghg.csv (" + o["farm_confidence"] + ")", "stages": o["stages"],
                "km": o["km"], "total": o["kg_co2e_per_kg"], "low": o["low"], "high": o["high"],
                "gbp_per_kg_cif": o["gbp_per_kg_cif"], "route_confidence": ""} for o in sea]
    return {"uk_imports_t": s["uk_imports_t"], "share_covered": s["share_covered"], "missing_routes": [],
            "origins": origins, "weighted": s["weighted_kg_co2e_per_kg"], "weighted_low": s["weighted_low"],
            "weighted_high": s["weighted_high"], "best": s["best_origin"], "best_total": s["best_kg_co2e_per_kg"],
            "cif_2025": s["cif_gbp_per_kg_all_origins"], "cif_2023_25": s["cif_gbp_per_kg_all_origins_2023_25"],
            "cheapest": s["cheapest_origin_cif"],
            "cheapest_cif": min(o["gbp_per_kg_cif"] for o in sea if o["gbp_per_kg_cif"]), "luc_pn": None}


VARIANTS = ("baseline_pc", "baseline_glass", "ctrl_pc", "ctrl_glass", "opt_pc", "opt_glass", "ctrlair_pc", "ctrlair_glass")
BORE_M_PER_UNIT = 16 * 120.0   # thesis field per R717 unit (sim/annual_sim.py: 16 x 120 m, UA 7 kW/K)
# Literature yields are for glass (CBS NL); twin-wall PC passes 0.70 / 0.80 of the light. Fruit-vegetable yield rises
# ~0.7-1 % per 1 % more light (Marcelis et al. 2006, Acta Hort 711:97-104); 0.8 used.
LIGHT_ELASTICITY = 0.8
PC_YIELD_FACTOR = 1 - LIGHT_ELASTICITY * (1 - 0.70 / 0.80)


def electricity(s, es):
    """Delivered electricity price (GBP/kWh) and carbon (kg/kWh) for each supply option, for one simulated case."""
    p_mean, ci_mean = breakeven.P["elec_price"][0], breakeven.SUPPLY["grid_2025"][0]
    out = {"grid_2025": {"price": p_mean * s["price_shape_factor"], "ci": ci_mean * s["ci_shape_factor"]},
           "clean_grid": {"price": p_mean * s["price_shape_factor"], "ci": breakeven.SUPPLY["clean_grid"][0]}}
    for k in ("hybrid", "hybrid_utility", "wind80"):
        e = es[k]
        out[k] = {"price": e["price"], "ci": e["ci"], "wind_W_m2": e["wind_kW"] * 1e3 / 1e4,
                  "battery_Wh_m2": e["battery_kWh"] * 1e3 / 1e4, "self_share": e["self_share"]}
    return out


def energy_variant(s, es, v):
    ground = s["source"] == "ground"
    field = 2.0 if v.startswith("opt") else 1.0   # seasonal store doubles the field (config.optimised)
    return {"source": s["source"], "bore_m_m2": BORE_M_PER_UNIT * s["hp_scale"] * field / s["area_m2"] if ground else 0.0,
            "heat_kWh_m2": s["heat_kWh_m2"], "elec_hp": s["comp_kWh_m2"],
            "elec_aux": s["aux_kWh_m2"] + s["cool_elec_kWh_m2"], "scop": s["scop_unit"],
            "design_kW_m2": s["design_heat_loss_kw"] / s["area_m2"], "hours_above_30": s["hours_above_30"],
            "hours_unmet": s["hours_unmet"], "tsup": s.get("tsup_mean_heating", 0.0), "tsrc": s.get("tsrc_mean_on", 0.0),
            "elec": electricity(s, es)}


def uk_inputs(sim, es, ff, st):
    """Per-m2 UK inputs per crop and system variant. HP electricity = compressor + source pump; aux = fans, pumps,
    controls and semi-closed cooling."""
    haul = breakeven.UK_HAUL_KM / 1000 * ff["reefer_hgv"]
    out = {}
    for key, c in crops.CROPS.items():
        pn = crops.PN[c["pn"]]
        out[key] = {"name": c["name"], "yield_glass": list(c["yield_"]), "pc_factor": PC_YIELD_FACTOR,
                    "yield_source": crops.SOURCES[c["yield_src"]], "yield_note": crops.YIELD_NOTES.get(key, ""),
                    "labour_h": c["labour"], "consumables": c["consumables"], "co2_dose": c["co2_dose"],
                    "pack_gbp": c["pack_gbp"], "per_kg_fixed": pn["processing"] + pn["packaging"] + haul,
                    "climate": [p.__dict__ for p in crops.CLIMATES[key].periods],
                    "variants": {v: energy_variant(sim[f"{key}|{v}"], es[f"{key}|{v}"], v) for v in VARIANTS}}
    av = {v: sim[f"avocado|{v}"] for v in VARIANTS}
    out["avocado"] = {"name": "Avocado", "yield_glass": None, "pc_factor": 1.0,
                      "yield_by_variant": {v: av[v]["crop_yield_t_ha"] / 10 for v in VARIANTS},
                      "yield_source": "Simulated (crop.py): in-ground beds, crop-led climate, CO2, semi-closed, no LED; "
                                      "the cover's light transmission feeds the growth model. Low/high = -15 % / +25 %",
                      "yield_note": "Open-field reference orchards 10-20 t/ha", "labour_h": breakeven.P["labour_h"][0],
                      "consumables": breakeven.FERT[0] * av["opt_glass"]["crop_yield_t_ha"] / 10,
                      "co2_dose": av["opt_glass"]["crop_co2_dosed_kg_m2"], "pack_gbp": breakeven.P["pack_gbp"][0],
                      "per_kg_fixed": st["packhouse"] + st["packaging"] + st["ripening"] + haul, "climate": [],
                      "variants": {v: energy_variant(av[v], es[f"avocado|{v}"], v) for v in VARIANTS}}
    return out


def defaults():
    P, S = breakeven.P, breakeven.SUPPLY
    return {
        "elec_ci": {"clean_grid": S["clean_grid"][0]},
        "co2_price": P["co2_price"][0], "structure_capex": P["structure_capex"][0],
        "structure_co2": P["structure_co2"][0], "om_frac": P["om_frac"][0],
        # heat plant, from the project's own capex model (CALCULATIONS_WHITE_PAPER.md §6.1)
        "hp_skid_gbp_kw": 850.0, "air_src_gbp_kw": 140.0, "borehole_gbp_m": 75.0, "install_frac": 0.18,
        "borehole_life": 50.0, "borehole_co2_kg_m": 15.0,
        "labour_rate": P["labour_rate"][0], "rate": breakeven.RATE, "structure_life": P["structure_life"][0],
        "hp_life": P["hp_life"][0], "heat_mult": 1.0, "price_mult": 1.0,
        # optimised-system extras (estimates): grow pipes, double boreholes for the seasonal store, larger plate HX
        "opt_pipe_gbp_m2": 35.0, "opt_hx_frac": 0.10, "vsd_gbp_m2": 3.0,
        "sources": {k: v[3] for k, v in P.items()} | {f"ci_{k}": v[1] for k, v in S.items()} | {
            "opt_pipe_gbp_m2": "Estimate: +2.25 m/m2 of 51 mm grow pipe at ~GBP 15/m installed",
            "hp_skid_gbp_kw": "Packaged ammonia heat pump skid, CALCULATIONS_WHITE_PAPER.md §6.1 (project capex model)",
            "air_src_gbp_kw": "Air-source coil acoustics and supports, CALCULATIONS_WHITE_PAPER.md §6.1",
            "borehole_gbp_m": "Vertical borehole drilling incl. loop and grout, CALCULATIONS_WHITE_PAPER.md §6.1; UK quotes "
                              "GBP 40-150/m depending on geology (installer guides 2025-26)",
            "install_frac": "Mechanical/electrical installation, 18 % of equipment (CALCULATIONS_WHITE_PAPER.md §6.1)",
            "borehole_co2_kg_m": "Drilling 12.5 kg CO2e/m (CALCULATIONS_WHITE_PAPER.md §5) + ~2.5 kg/m HDPE U-loop "
                                 "(1.9 kg CO2e/kg)",
            "bore_field": "Field = thesis 16 x 120 m per R717 unit, scaled with heat-pump size; seasonal store x2",
            "opt_hx_frac": "Estimate: larger evaporator and condenser plates, +10 % of heat-pump capex",
            "vsd_gbp_m2": "Estimate: variable-speed drives on the circulation pumps",
            "light_yield": "Marcelis et al. (2006) Acta Hort 711: ~0.7-1 % yield per 1 % light; 0.8 used"},
    }


def build():
    ff, st, *_ = imports.load()
    trade = list(csv.DictReader((HERE / "data" / "imports_trade.csv").open(encoding="utf-8")))
    routes = _routes()
    sim = {r["case"]: r for r in json.loads((HERE / "results" / "crops_sim.json").read_text())}
    esj = json.loads((HERE / "results" / "energy_systems.json").read_text())
    uk = uk_inputs(sim, esj["cases"], ff, st)
    imp = {k: crop_imports(k, trade, ff, st, routes) for k in crops.CROPS}
    imp["avocado"] = avocado_imports()
    order = ["tomato", "cucumber", "pepper", "aubergine", "lettuce", "strawberry", "raspberry", "blueberry", "grape",
             "avocado"]
    return {"order": order, "uk": uk, "imports": imp, "defaults": defaults(), "wind": esj["inputs"],
            "wind_cf": esj["wind_cf"],
            "notes": {"labour": crops.LABOUR_NOTE, "sources": crops.SOURCES,
                      "heat": "Simulated heat omits heating for humidity control; Dutch sector energy use is ~0.99 GJ/m2 "
                              "(WUR24, all energy incl. electricity). Use the heat multiplier to test higher demand.",
                      "season": "Unlit UK production is seasonal for most crops; imports fill the winter. Annual "
                                "per-kg figures do not show this.",
                      "wind": "Wind + battery + grid sizes are least-cost for each crop's hourly demand with the heat "
                              "pump running (energy_systems.py); with waste heat the same price and carbon per kWh are "
                              "applied to the smaller demand (approximation)."}}


if __name__ == "__main__":
    data = build()
    (HERE / "results" / "compare.json").write_text(json.dumps(data, indent=1, default=float))
    tpl = (HERE / "crop_compare_template.html").read_text(encoding="utf-8")
    page = tpl.replace("/*__DATA__*/null", json.dumps(data, default=float, separators=(",", ":")))
    (HERE.parent / "crop_compare.html").write_text(page, encoding="utf-8")
    print(f"{'crop':<12}{'imp kg/kg':>10}{'range':>13}{'CIF £/kg':>9}{'cover':>7}  missing")
    for k in data["order"]:
        i = data["imports"][k]
        print(f"{k:<12}{i['weighted']:>10.2f}{i['weighted_low']:>6.2f}-{i['weighted_high']:<6.2f}{i['cif_2023_25']:>9.2f}"
              f"{i['share_covered']*100:>6.0f}%  {', '.join(i['missing_routes'])}")
