"""Step 3: per-site design optimisation with waste heat, grid-backed wind, network charges and logistics.

For each shortlisted site (data/siting/shortlist.json) and crop, random designs (optimise.py shape space, narrowed by
the first sweep: double glazing only, pitch 12-26 deg, gutter 4.5-6.5 m) are evaluated end to end at the site:
  * weather, light and wind at the site (Open-Meteo ERA5; wind scaled so its hub-height mean equals the Global Wind
    Atlas best cell within ~2 km, shear from the GWA 50/100 m layers)
  * waste heat: direct sources (distillery, paper, food/AD) charge the buffer (greenhouse_fast waste_kw) when the
    source is running (availability(): planned shutdown + an unplanned outage in the coldest week); the R717
    air-source heat pump covers the rest. Waste-water works are the source of an R717 water-source heat pump
    (t_source), limited to the works' annual heat
  * heat pump: always installed and costed at the full design heat load (user, 2026-10-03), so the crop is protected
    through any source outage; the simulation already sizes the unit to the design load
  * heat pump capex and fixed O&M: Danish Energy Agency technology data (Aug 2026 data sheets, chapter 40: air source
    1/3/10 MW 1.15/1.10/1.02 MEUR/MW, waste heat 1/3/10 MW 1.13/0.95/0.95; fixed O&M 2,127 EUR/MW/yr; 25 yr life),
    EUR->GBP 0.8567 (ECB 2025 mean)
  * network: 2026/27 minus 2025/26 TNUoS demand residual by band of peak import (NESO final tariffs) added to the
    DESNZ average price
  * logistics: siting.logistics (TAG costs, DESNZ reefer factor) to the Central Belt RDCs
  * heat price applied afterwards at GBP 0/10/20 per MWh of waste heat used
Writes results/site_opt/<crop>.json (all rows) for site_rank.py.
"""
import json
import math
import os
import sys
import time
import types
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
sys.path.insert(0, str(HERE.parent))           # repo copy of simcore first (cloud has no ../simcore)
sys.path.insert(0, str(HERE))
import config  # noqa: E402
import costing  # noqa: E402
import crop_gh  # noqa: E402
import crops  # noqa: E402
import design as D  # noqa: E402
import energy_grid  # noqa: E402
import greenhouse  # noqa: E402
import greenhouse_fast  # noqa: E402
import optimise  # noqa: E402
import run_crops  # noqa: E402
import transp  # noqa: E402
import siting  # noqa: E402
from simcore import weather  # noqa: E402

# Two tracks (user, 2026-10-03): A = waste-heat site, B = no waste heat (heat pump supplies everything). Select with the
# environment variable CEA_TRACK=A|B; every chain script reads and writes site_opt.OUT. Track B control package: RH 90 % +
# heat-recovery dehumidification (night setpoint drop rejected). Central electricity route for both tracks: owned single
# 2.5 MW turbine (user: grid = baseline, 2.5 MW turbine = priority, private wire = second; all three reported by refine.py)
TRACK = os.environ.get("CEA_TRACK", "A").upper()
OUT = HERE / "results" / ("site_opt" if TRACK == "A" else "site_opt_B")
TRACK_OPTS = {} if TRACK == "A" else {"no_waste": True, "hum_rh": 90.0, "hrd": True}
CENTRAL_ELEC = "own_2p5MW"
WINTER_WASTE = (0.8, "sensitivity only (B7): waste-heat rate x0.8 in Nov-Mar, e.g. the host uses more of its own heat in "
                "winter; the central case keeps the mean rate whenever the source runs (continuous-process sites), "
                "real monthly profiles need operator data (B6)")
EUR_GBP = 0.8567
DEA = {"air": [(1, 1.15), (3, 1.10), (10, 1.02)], "waste": [(1, 1.13), (3, 0.95), (10, 0.95)]}   # MW, MEUR/MW
DEA_OM_EUR_MW = 2126.745
HP_LIFE = 25.0
# BP34 (2026-10-05) PLACEHOLDERS until sourced (data/input_register.csv): interlighting costs 20 % more per kW than top
# light (more, smaller fixtures and wiring in the crop); half of the labour scales with kg harvested (harvest, grading),
# referenced to the CBS unlit yield at which labour_h was set. Labour is up to ~40 % of Dutch cucumber opex (Rabobank via
# Hortidaily, 12 Aug 2026), so this split matters for lit, high-yield designs.
LED_INTER_COST, LABOUR_KG_SHARE = 0.20, 0.5
# Electric peak boiler (2026-10-05, option hp_boiler): DEA technology data for el. and DH (Aug 2026 data sheets), ch. 41
# 'Electric boiler, small': total investment 0.155 MEUR/MW, fixed O&M 1,138 EUR/MW/yr, efficiency 0.99, life 25 yr
BOILER = dict(meur_mw=0.15457, om_eur_mw=1137.8, eff=0.99, life=25.0)
NET_INC = [(500, 10.0), (1100, 54.35), (2000, 63.62), (math.inf, 211.31)]   # kVA upper, GBP/site/day (26/27 - 25/26)
# Transpiration (R7): lambda*E = A0 (1 - exp(-k LAI)) G + B0 LAI VPD per crop, constants and sources in transp.py
# (tomato validated against GreenLight, cucumber against measured lysimeter data of Nikolaou et al. 2017).
TRANSP = {c: transp.coeffs(c) for c in transp.CROPS}
VENT_AREA_FRAC = 0.117                 # roof vent area / floor area (Katzin 2021 / Vanthoor 2011 tomato glasshouse); the
                                       # Vanthoor vent law gives ~34 ACH open at 3.5 m/s. A design variable, not yet costed
PIPE_M, PIPE_GBP_M = 500.0, 1000.0    # connection to the heat source: placeholder (needs quote / DH pipe source)
# Wind output realism (R10, 2026-10-03): the ideal cubic curve on the GWA best cell within ~2 km gave capacity factors up to
# 54 % (45 m) / 62 % (80 m). Net of availability, wake and electrical losses and capped at the top of the surveyed range:
# Arup (2025) for DESNZ, Renewable Energy Generation Cost and Technical Assumptions 2024, Table 22: net load factor of
# current Scottish/Welsh onshore projects 33.0 / 38.1 / 41.3 % (low / medium / high); losses 15 % (estimate, gross->net)
WIND_NET, WIND_CF_CAP = 0.85, 0.413
T_EFFLUENT = (12.3, 4.0)              # BRE mean; +-4 K seasonal swing, minimum in February (to source)
# BP37c heat source option hp_source = "air" (default) | "ground" | "sea". Sea: monthly mean sea temperature at Millport,
# Firth of Clyde (seatemperature.net monthly averages, secondary; Loch Ryan proxy, a shallow loch may run ~1 K colder in winter)
SEA_T_MONTHLY = (8.3, 7.2, 7.2, 7.8, 9.4, 12.2, 13.9, 14.4, 14.4, 13.3, 11.1, 9.4)
_S = {}
# Heat-source availability: planned shutdown (days, start day of year) by site kind, plus an unplanned outage.
OUTAGE = {  # kind: (planned days, start doy, tier, source)
    "distillery": (28, 196, "sourced (duration) / placeholder (timing)",
                   "Whisky Advocate (McCormick, 2022) 'Go inside Scotland's silent season': 3-4 weeks per year; upper "
                   "end used; mid-July start to confirm with the operator"),
    "paper_board": (10, 213, "sourced (duration) / placeholder (timing)",
                    "Process Barron 'Planning well for an efficient paper mill shutdown': standard annual shutdown "
                    "5-10 days; upper end used; August start to confirm with the operator"),
    "food_drink_ad": (14, 213, "placeholder", "no public source found; operator data needed"),
    "wwtp": (0, 0, "standard", "effluent flows continuously; works do not shut down"),
}
UNPLANNED_DAYS = (7, "placeholder", "one week lost in the coldest week of the weather year (stress case) until "
                  "operator availability data; real example: Cameronbridge strikes 28 Sep-15 Oct 2026 (Food "
                  "Manufacture, 24 Sep 2026)")


def availability(site, wx, planned=True, unplanned=True):
    """1/0 per hour: is the waste-heat source running?"""
    on = np.ones(8760)
    days, start, *_ = OUTAGE.get(site["kind"], (0, 0))
    if planned and days:
        on[start * 24:(start + days) * 24] = 0.0
    n_un = UNPLANNED_DAYS[0] if site["grade"] != "low" else 0
    if unplanned and n_un:
        t = wx["T_amb"].to_numpy()[:8760]
        wk = np.convolve(t, np.ones(n_un * 24) / (n_un * 24), mode="valid")
        i0 = int(np.argmin(wk))
        on[i0:i0 + n_un * 24] = 0.0
    return on


def hp_gbp_per_kw(mw, kind):
    pts = DEA[kind]
    if mw <= pts[0][0]:
        v = pts[0][1]
    elif mw >= pts[-1][0]:
        v = pts[-1][1]
    else:
        for (m0, v0), (m1, v1) in zip(pts[:-1], pts[1:]):
            if m0 <= mw <= m1:
                f = math.log(mw / m0) / math.log(m1 / m0)
                v = v0 + f * (v1 - v0)
    return v * 1e3 * EUR_GBP          # GBP per kW


def network_inc_gbp(peak_kw):
    kva = peak_kw / 0.95
    for lim, day in NET_INC:
        if kva <= lim:
            return day * 365


def _net_wind(pu):
    """Per-unit output net of losses, scaled down if the capacity factor would exceed WIND_CF_CAP."""
    pu = pu * WIND_NET
    return pu * min(1.0, WIND_CF_CAP / max(float(pu.mean()), 1e-9))


def site_state(site):
    key = site["site_key"]
    if key not in _S:
        weather.SITES.setdefault(key, (site["lat"], site["lon"], 0, site["name"]))
        wx = weather.load(key)
        a100 = site["shear_alpha"]
        v_hub = wx["wind100"].to_numpy()[:8760] * (45.0 / 100.0) ** a100
        v_hub = v_hub * site["wind_hub_best2km"] / v_hub.mean()
        pu = np.clip((v_hub ** 3 - 3.0 ** 3) / (12.0 ** 3 - 3.0 ** 3), 0, 1)
        pu = np.where((v_hub < 3.0) | (v_hub > 25.0), 0.0, pu)
        doy = np.arange(8760) / 8760
        t_src = T_EFFLUENT[0] + T_EFFLUENT[1] * np.sin(2 * np.pi * (doy - 0.37))   # min ~ mid-Feb
        pu = _net_wind(pu)
        v80 = v_hub * (80.0 / 45.0) ** a100                 # multi-MW turbine hub (R10 electricity options)
        pu80 = np.clip((v80 ** 3 - 3.0 ** 3) / (12.0 ** 3 - 3.0 ** 3), 0, 1)
        pu80 = np.where((v80 < 3.0) | (v80 > 25.0), 0.0, pu80)
        pu80 = _net_wind(pu80)
        _S[key] = dict(wx=wx, pu=pu, pu80=pu80, t_src=t_src, log=siting.logistics(site))
    return _S[key]


def sample(rng, site, crop_heat_kwh_m2):
    x = optimise.sample(rng)
    x["glazing"] = str(rng.choice(["dbl_ar_lowe", "dbl_ar"]))
    x["pitch"] = float(rng.uniform(12, 26))
    x["gutter_h"] = float(rng.uniform(4.0, 6.5))             # B8: lower bound 4.5 -> 4.0 m (2026-10-03)
    supported_ha = site["heat_GWh"] * 1e6 / crop_heat_kwh_m2 / 1e4
    hi = 30.0 if TRACK_OPTS.get("no_waste") else max(1.0, min(30.0, 2.0 * supported_ha))
    area = float(np.exp(rng.uniform(np.log(1.0), np.log(hi)))) * 1e4
    aspect = float(np.exp(rng.uniform(np.log(0.5), np.log(4.0))))
    width = math.sqrt(area / aspect)
    x["n_spans"] = max(1, round(width / x["span_w"]))
    x["length"] = area / (x["n_spans"] * x["span_w"])
    return x


def source_series(S, low, o):
    """Heat-pump source temperature (C, hourly) for water sources; None for air and ground (simulated internally)."""
    if low:
        return S["t_src"]
    if o.get("hp_source") == "sea":
        mid = (np.arange(12) + 0.5) * 730.0
        return np.interp(np.arange(8760), np.concatenate([mid - 8760, mid, mid + 8760]), np.tile(SEA_T_MONTHLY, 3))
    return None


def hp_kind(low, o):
    return "waste" if low or o.get("hp_source") in ("sea", "ground") else "air"


def site_setup(site, x, crop, o=None):
    """Design, light analysis, simulation config, waste-heat availability and profile for a design at a site."""
    o = {**TRACK_OPTS, **(o or {})}
    S = site_state(site)
    d = optimise.build(x)
    a = D.analyse(d, S["wx"], site["lat"], site["lon"], wall_light=o.get("wall_light", 1.0))
    if a["usable_frac"] <= 0.2:
        return None
    low = site["grade"] == "low" and not o.get("no_waste")   # track B: air source everywhere
    src = "water" if low or o.get("hp_source") == "sea" else o.get("hp_source", "air")
    base = run_crops.variant(run_crops.base_cfg(crop, src), "ctrlair_pc" if src == "air" else "ctrl_pc")
    base = replace(base, location=replace(base.location, site=site["site_key"], lat=site["lat"], lon=site["lon"]))
    night = max(p.heat_night for p in crops.CLIMATES[crop].periods)
    tr = o.get("transp_mult", 1.0)          # sensitivity on the whole transpiration law
    base = replace(base, envelope=replace(base.envelope, infiltration_ach=0.75, cover_t_from_u=True,
                                          transp_rad=TRANSP[crop][0] * tr, transp_vpd=TRANSP[crop][1] * tr,
                                          vent_area_frac=VENT_AREA_FRAC),
                   heat=replace(base.heat, design_outdoor_C=-3.1, design_indoor_C=night, waste_T_C=site["T_C"]),
                   hum=config.HumidityControl(enabled=True, rh_set=o.get("hum_rh", 85.0)))
    if "hum_rh" in o:                                       # R10: humidity setpoint, vents follow
        base = replace(base, climate=replace(base.climate, rh_vent_start=o["hum_rh"]))
    if "pipe_m2" in o:                                      # COP lever (2026-10-05): emitter length, lower supply temperature
        base = replace(base, hydronics=replace(base.hydronics, pipe_m_per_m2=o["pipe_m2"]))
    if "hx_scale" in o:                                     # COP lever: evaporator/condenser area multiplier
        base = replace(base, heat=replace(base.heat, hx_scale=o["hx_scale"]))
    if o.get("light"):                                      # BP34: supplementary LED (config.Lighting fields), default off
        lt = dict(o["light"])
        follow = lt.pop("follow_wind", None)                # lights only while the turbine runs above this per-unit output
        if follow is not None:
            lt["allow_hourly"] = (S["pu80"][:8760] >= follow).astype(float)
        base = replace(base, lighting=replace(base.lighting, **lt))
    if o.get("hrd"):                                        # R10: heat-recovery dehumidification (config.HeatRecoveryDehum)
        base = replace(base, hrd=config.HeatRecoveryDehum(enabled=True))
    cfg = D.to_config(d, a, base)
    doy = S["wx"]["time"].dt.dayofyear.to_numpy()[:8760]
    tr_r, tr_v = transp.hourly_coeffs(crop, doy)
    cfg = replace(cfg, envelope=replace(cfg.envelope, transp_hourly=(tr_r * tr, tr_v * tr), soil_layers=True,
                                        floor_frac_hourly=transp.floor_light_frac(transp.lai_by_doy(crop, doy))))
    out = o.get("outage", "both")
    avail = availability(site, S["wx"], planned=out != "none", unplanned=out == "both")
    if o.get("no_waste"):                                   # R10 track B: no waste heat, the heat pump supplies everything
        avail = np.zeros(8760)
    waste_kw = None if low or o.get("no_waste") else site["heat_GWh"] * 1e6 / 8760 * avail
    if waste_kw is not None and o.get("winter_waste"):
        m = np.minimum(np.arange(8760) // 730, 11)
        waste_kw = waste_kw * np.where((m >= 10) | (m <= 2), WINTER_WASTE[0], 1.0)
    return d, a, cfg, low, avail, waste_kw


def evaluate(site, x, crop, opts=None):
    import simstore
    o = {**TRACK_OPTS, "elec": CENTRAL_ELEC, "resid_fixed_share": float(os.environ.get("CEA_RESID_FIXED", 0.0)), **(opts or {})}
    if os.environ.get("CEA_RESID_ANCHOR", "sac") != "sac":           # BP27: in the cache key only when set
        o.setdefault("resid_anchor", os.environ["CEA_RESID_ANCHOR"])
    return simstore.get_or_compute("evaluate", (site, x, crop, o), lambda: _evaluate(site, x, crop, opts))


def _evaluate(site, x, crop, opts=None):
    """opts (sensitivities): wall_light, wind_capex, rates (costing.rates() variant), capex_mult, network (bool),
    pipe_mult, outage ('both'/'planned'/'none'), battery (bool), size_for_export (bool), hp_frac (heat pump capex at
    this fraction of the design load; the simulation is unchanged), batt_capex, price (hourly GBP/kWh array).
    R10: no_waste (track B, no waste heat or pipe), hum_rh (humidity setpoint %), hrd (heat-recovery dehumidification),
    elec (energy_grid.ELEC_OPTIONS key; multi-MW routes use the 80 m hub wind)."""
    o = {**TRACK_OPTS, "elec": CENTRAL_ELEC, "resid_fixed_share": float(os.environ.get("CEA_RESID_FIXED", 0.0)), **(opts or {})}
    G = optimise._state()
    S = site_state(site)
    setup = site_setup(site, x, crop, o)
    if setup is None:
        return None
    d, a, cfg, low, avail, waste_kw = setup
    H, acc, wx, gr, meta, _ = greenhouse_fast.simulate_fast(cfg, i_floor=a["I_floor"], waste_kw=waste_kw,
                                                            t_source=source_series(S, low, o))
    sm = greenhouse.summary(H, gr, meta)
    A = d.floor
    load = H["W_total"][:8760]
    boiler_frac = o.get("hp_boiler")                       # heat pump at this fraction of design load + electric peak boiler
    boiler_MWh = 0.0
    if boiler_frac is not None:
        qc, wc = H["Q_c"][:8760], H["W_comp"][:8760]
        q_hp = np.minimum(qc, meta["design_heat_loss_kw"] * boiler_frac)
        q_hp_cop = np.where(wc > 0, qc / np.maximum(wc, 1e-9), 1.0)
        load = load - wc + q_hp / q_hp_cop + (qc - q_hp) / BOILER["eff"]
        boiler_MWh = float((qc - q_hp).sum() / 1e3)
    if o.get("elec"):                                      # R10: electricity supply route (energy_grid.ELEC_OPTIONS)
        big = energy_grid.ELEC_OPTIONS[o["elec"]]["kind"] in ("own_fixed", "ppa") or o["elec"] == "farm_share"
        en = energy_grid.supply_option(load, S["pu80"] if big else S["pu"], o.get("price", G["price"]), G["ci"], o["elec"],
                                       battery=o.get("battery", True))
    else:
        en = energy_grid.supply(load, S["pu"], o.get("price", G["price"]), G["ci"], wind_capex=o.get("wind_capex", energy_grid.WIND_CAPEX),
                                battery=o.get("battery", True), size_for_export=o.get("size_for_export", False),
                                batt_capex=o.get("batt_capex"))
    net = network_inc_gbp(en["import_peak_kW"]) if o.get("network", True) else 0.0
    resid, fshare = G["resid"], o["resid_fixed_share"]
    anchor = o.get("resid_anchor", os.environ.get("CEA_RESID_ANCHOR", "sac"))
    if anchor.startswith("wur") and costing.WUR_HA[0] <= A / 1e4 <= costing.WUR_HA[1]:
        resid, fshare = costing.resid_wur(resid, anchor.split(":")[1] if ":" in anchor else "central"), 0.0   # BP27
    cap = costing.capex(d, a, resid, fixed_share=fshare, R=o.get("rates", G["R"]),
                        pipe_m_per_m2=o.get("pipe_m2", 2.25))
    cap["capex_gbp"] *= o.get("capex_mult", 1.0)
    design_kw = meta["design_heat_loss_kw"]
    hp_kw = design_kw * (boiler_frac if boiler_frac is not None else o.get("hp_frac", 1.0))  # standby: full design load
    hp_gbp = hp_kw * hp_gbp_per_kw(max(hp_kw, 1.0) / 1e3, hp_kind(low, o))
    hp_om = hp_kw / 1e3 * DEA_OM_EUR_MW * EUR_GBP
    boiler_kw = design_kw - hp_kw if boiler_frac is not None else 0.0
    hp_gbp += boiler_kw * BOILER["meur_mw"] * 1e3 * EUR_GBP     # same 25-yr life as the heat pump
    hp_om += boiler_kw / 1e3 * BOILER["om_eur_mw"] * EUR_GBP
    pipe_gbp = 0.0 if o.get("no_waste") else PIPE_M * PIPE_GBP_M * o.get("pipe_mult", 1.0)
    waste_used_MWh = float(H["Q_e"].sum() / 1e3) if low else float(H["Q_waste"].sum() / 1e3)
    if low and waste_used_MWh > site["heat_GWh"] * 1e3:
        return None                                        # needs more effluent heat than the works offers
    Dd, u = G["D"], G["uk"][crop]
    ann = lambda n: Dd["rate"] / (1 - (1 + Dd["rate"]) ** -n)  # noqa: E731
    # R8: climate-driven yield (crop_gh.py: photosynthesis + carbon balance on the hourly climate, partition calibrated to the
    # CBS yield on the Westland reference house), with CO2 enrichment as the cost model assumes; dose from the same run
    doy = S["wx"]["time"].dt.dayofyear.to_numpy()[:8760]
    co2cfg = config.CO2(enrich=True, **o.get("co2", {}))   # option co2 (2026-10-05): dosing setpoints, default unchanged
    y_m2, cres = crop_gh.run(H, meta, replace(cfg, co2=co2cfg), crop, doy, crop_gh.load_cal()[crop]["partition"])
    Y = y_m2 * o.get("yield_mult", 1.0) * a["usable_frac"]
    co2_kg_m2 = cres.annual["co2_dosed_kg_m2"]
    lt = cfg.lighting                                      # BP34: LED capex (rates.csv led_kw; interlighting x LED_INTER_COST)
    led_kW = lt.w_per_m2 * A / 1e3 if lt.ppfd > 0 else 0.0
    R_led = o.get("rates", G["R"]).get("led_kw")
    led_gbp = led_kW * R_led["cost_central"] * (1 + LED_INTER_COST * lt.inter_frac) if led_kW else 0.0
    led_life = (R_led["life_yr"] if R_led else 15.0) or 15.0
    labour_h = u["labour_h"]
    if o.get("labour_split"):                              # BP34: part of the labour scales with kg harvested
        labour_h = u["labour_h"] * ((1 - LABOUR_KG_SHARE)
                                    + LABOUR_KG_SHARE * y_m2 * o.get("yield_mult", 1.0) / crop_gh.CBS_REF[crop])
    fixed_m2 = (cap["capex_gbp"] * ann(Dd["structure_life"]) + cap["capex_gbp"] * Dd["om_frac"]
                + hp_gbp * ann(HP_LIFE) + hp_om + pipe_gbp * ann(Dd["structure_life"]) + en["cost_gbp"] + net
                + led_gbp * (ann(led_life) + Dd["om_frac"])) / A \
        + labour_h * Dd["labour_rate"] * a["usable_frac"] + co2_kg_m2 * Dd["co2_price"] * a["usable_frac"]
    mh = np.minimum(np.arange(8760) // 730, 11)
    hourly_net = (cres.hourly["A_net"] * 3600 * 30.03e-6 - cres.hourly["maint"])[:8760]     # g CH2O/m2/h
    crop_m = np.maximum(np.bincount(mh, hourly_net, minlength=12), 0.0)
    trans_m = np.bincount(mh, H["trans_kg"][:8760], minlength=12) / A                      # kg/m2 per month
    rain_m = np.bincount(mh, S["wx"]["precip"].to_numpy()[:8760], minlength=12)             # mm per month
    haul_default = 100.0 / 1000 * siting.REEFER_KG_TKM            # breakeven.UK_HAUL_KM in per_kg_fixed
    kg_m2 = en["carbon_kg"] / A + cap["co2_kg_m2_yr"] + u["consumables"] * a["usable_frac"]
    month = np.minimum(np.arange(8760) // 730, 11)
    light_m = np.bincount(month, a["I_floor"][:8760], minlength=12)
    T_air = H["T_air_in"][:8760]
    return dict(site=site["site_key"], name=site["name"], kind=site["kind"], crop=crop, x=x, area_ha=A / 1e4, Y=Y,
                hours_gt30=int((T_air > 30).sum()), hours_gt32=int((T_air > 32).sum()), heat_stress=cres.annual["heat_stress_factor"],
                co2_dose_kg_m2=co2_kg_m2, yield_m2_ex_usable=y_m2,
                gbp_kg_ex_heat=fixed_m2 / Y + u["pack_gbp"] + S["log"]["gbp_kg"],
                heat_MWh_per_kg=waste_used_MWh / (Y * A), kg_kg=kg_m2 / Y + u["per_kg_fixed"] - haul_default
                + S["log"]["kg_kg_diesel"], kg_kg_ehgv=kg_m2 / Y + u["per_kg_fixed"] - haul_default
                + S["log"]["kg_kg_ehgv"], heat_kWh_m2=sm["heat_kWh_m2"], waste_share=waste_used_MWh * 1e3 / max(
                    float(H["Q_c"].sum() + H["Q_waste"].sum()), 1.0) if not low else 1.0,
                elec_kWh_m2=sm["electricity_kWh_m2"], wind_kW=en["wind_kW"], elec_price=en["price"],
                elec_ci=en["ci"], self_share=en["self_share"], en_cost_gbp=en["cost_gbp"],
                hp_ann_gbp=hp_gbp * ann(HP_LIFE) + hp_om, labour_gbp_m2=labour_h * Dd["labour_rate"] * a["usable_frac"], batt_kWh=en["batt_kWh"], export_MWh=en["export_MWh"],
                import_MWh=en["import_MWh"], batt_MWh_out=en["batt_MWh_out"], hp_kW=hp_kw,
                hp_MWh=float(H["Q_c"].sum() / 1e3), hp_elec_MWh=float(H["W_comp"].sum() / 1e3),
                boiler_kW=boiler_kw, boiler_MWh=boiler_MWh, waste_avail=float(avail.mean()), net_gbp_yr=net, capex_gbp_m2=cap["capex_gbp_m2"],
                hp_gbp_m2=hp_gbp / A, light_rel=float(a["I_floor"].sum() / G["L_ref"]), usable=a["usable_frac"],
                unmet_h=sm["hours_unmet"], logistics_gbp_kg=S["log"]["gbp_kg"], road_km=S["log"]["road_km"],
                monthly_share=(light_m / light_m.sum()).tolist(),
                monthly_share_crop=(crop_m / max(crop_m.sum(), 1e-9)).tolist(), transp_kg_m2_month=trans_m.tolist(),
                rain_mm_month=rain_m.tolist(), placeholder_share=cap["placeholder_share"],
                elec_option=en.get("option", "own_small"), turbine=en.get("turbine"),
                # cost ledger for the cash flow (cashflow.py): capital by item and annual cash items, GBP
                ledger=dict(structure_items=cap["cost_items"], structure_resid_gbp=cap["resid_gbp"],
                            structure_gbp=cap["capex_gbp"], hp_gbp=hp_gbp, hp_om_gbp_yr=hp_om, pipe_gbp=pipe_gbp,
                            om_gbp_yr=cap["capex_gbp"] * Dd["om_frac"], energy_gbp_yr=en["cost_gbp"], network_gbp_yr=net,
                            batt_kWh=en["batt_kWh"], batt_gbp_yr=en.get("batt_gbp_yr", 0.0),
                            labour_gbp_yr=labour_h * Dd["labour_rate"] * a["usable_frac"] * A,
                            led_kW=led_kW, led_gbp=led_gbp, led_life=led_life, led_MWh=float(H["W_led"][:8760].sum() / 1e3),
                            co2_gbp_yr=co2_kg_m2 * Dd["co2_price"] * a["usable_frac"] * A,
                            pack_gbp_kg=u["pack_gbp"], logistics_gbp_kg=S["log"]["gbp_kg"], waste_heat_MWh=waste_used_MWh,
                            area_m2=A, kg_yr=Y * A, labour_h_m2=labour_h, labour_rate=Dd["labour_rate"],
                            rate=Dd["rate"], structure_life=Dd["structure_life"], om_frac=Dd["om_frac"]))


def _job(args):
    site, x, crop = args
    try:
        return evaluate(site, x, crop)
    except Exception as e:
        return {"site": site["site_key"], "crop": crop, "x": x, "error": repr(e)}


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    crop_list = sys.argv[2:] or ["cucumber", "tomato"]
    SL = json.loads((HERE / "data" / "siting" / "shortlist.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    heat_demand = {"cucumber": 330.0, "tomato": 205.0}      # kWh/m2/yr, refined designs after R6-R8 (was 255 / 159 before)
    for crop in crop_list:
        t = time.time()
        rng = np.random.default_rng(7)
        jobs = [(s, sample(rng, s, heat_demand[crop]), crop) for s in SL for _ in range(n)]
        with ProcessPoolExecutor(max_workers=7) as ex:
            res = list(ex.map(_job, jobs, chunksize=8))
        ok = [r for r in res if r and "error" not in r]
        bad = [r for r in res if r and "error" in r]
        (OUT / f"{crop}.json").write_text(json.dumps({"rows": ok, "errors": bad}, default=float))
        print(f"{crop}: {len(ok)} ok, {len(bad)} errors, {len([r for r in res if r is None])} rejected, "
              f"{time.time() - t:.0f} s", flush=True)
        if bad:
            print("  first error:", bad[0]["error"][:300])
