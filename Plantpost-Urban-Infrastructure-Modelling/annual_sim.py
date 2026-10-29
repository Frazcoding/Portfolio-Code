"""Annual (8760 h, 10-min internal steps) Plantpost simulation for London, Edinburgh and Bologna (2023 ERA5).

Uses the validated parameter set in src/config.py and adds:
  PV canopy      8-facet shallow cone (15 deg) of monocrystalline cells (70 % cell coverage), Hay-Davies
                 transposition per facet, Faiman cell temperature, MPPT and BOS losses
  battery        4S LiFePO4 100 Ah equivalent circuit (OCV-SOC curve, temperature-dependent R_int),
                 lumped thermal node in the base, sub-zero charge derate, SOC limits, cycle + calendar ageing
  loads          47.1 W LED dusk-to-dawn with adaptive dimming (50 % 00:30-05:00 when SOC < 60 %),
                 1.5 W BMS + 0.8 W IoT sensors, pump energy from hydraulics
  water          canopy rain harvesting (runoff 0.9, first-flush 0.5 mm per event, filter 0.95), 150 L tank
                 with overflow, four tier substrate moisture buckets (FAO-56 Kc x ET0 with height-dependent
                 wind exposure), pressure-compensating drip pulses when depletion > 45 % of available water
  hydraulics     8 mm PE riser, Darcy-Weisbach (Swamee-Jain), static head to each tier, 2 m emitter head:
                 pressure, flow and water enthalpy at pump outlet and each tier manifold
  ecosystem      PM2.5/PM10 dry deposition on foliage (v_d 5 mm/s, rain wash-off), evaporative cooling
"""
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_legacy"))  # frozen simcore v0.1.0
sys.path.insert(0, str(HERE))

from simcore import grid, solar, weather  # noqa: E402
from simcore.output import Results  # noqa: E402
from src.config import EcosystemConfig, ElectricalConfig, GeometricConfig, HydraulicConfig  # noqa: E402

G, E, HY, EC = GeometricConfig(), ElectricalConfig(), HydraulicConfig(), EcosystemConfig()
DT, SUB = 600.0, 6
CAD_CAL = 0.557
CITIES = {"london": ("London 2023", "london", 180.0, 100.0), "edinburgh": ("Edinburgh 2023", "edinburgh", 180.0, 100.0),
          "bologna": ("Bologna 2023", "bologna", 260.0, 100.0),
          "edinburgh_200ah": ("Edinburgh 2023 · 200 Ah pack", "edinburgh", 180.0, 200.0)}
TIER_Z = list(G.tier_heights_m)
SUBSTRATE_L = 60.0                  # litres of substrate per tier
FC, WP = 0.38, 0.12                 # volumetric field capacity / wilting point
KC = [0.75, 0.85, 0.95, 1.05]       # crop coefficient rising with exposure (lower tiers shaded)
EXPO = [0.7, 0.85, 1.0, 1.15]       # wind/radiation exposure multiplier by tier height


def ocv(soc):
    """LiFePO4 4S open-circuit voltage curve (flat plateau ~13.2 V)."""
    s = np.clip(soc, 0, 1)
    return 12.0 + 1.0 * s + 0.25 * np.tanh((s - 0.05) * 25) - 0.25 + 0.35 * np.maximum(0, s - 0.97) / 0.03


def r_int(T):
    """4S pack internal resistance, ohm (rises steeply in the cold)."""
    return 0.012 * math.exp(0.035 * (25.0 - T))


def friction_head(q_m3s, L, D=HY.pipe_internal_diameter_m):
    if q_m3s <= 0:
        return 0.0
    v = q_m3s / (math.pi * D ** 2 / 4)
    Re = v * D / HY.water_viscosity_m2_s
    f = 64 / Re if Re < 2300 else 0.25 / math.log10(HY.pipe_roughness_m / (3.7 * D) + 5.74 / Re ** 0.9) ** 2
    return f * L / D * v ** 2 / (2 * 9.81) + 0.8 * v ** 2 / (2 * 9.81) * 4      # pipe + fittings (4 x tee/elbow)


def simulate(city, cap_Ah=100.0):
    wx = weather.load(city)
    gr = grid.load()
    n = len(wx)
    lat, lon = weather.SITES[city][:2]
    zen, az, doy = solar.position(wx["time"], lat, lon)
    ghi, dni, dhi = wx.ghi.to_numpy(), wx.dni.to_numpy(), wx.dhi.to_numpy()
    Ta, wind = wx.T_amb.to_numpy(), wx.wind10.to_numpy()
    # PV: 8 facets, each 1/8 of the 3.14 m2 dish, tilted 15 deg outward; 70 % cell coverage
    A_cells = G.area_catchment_m2 * 0.70
    P_stc = A_cells * 1000 * E.pv_efficiency_ref
    p_dc = np.zeros(n)
    T_cell = np.zeros(n)
    G_poa = np.zeros(n)
    for k in range(8):
        b, d, g_, aoi = solar.poa(ghi, dni, dhi, zen, az, doy, 15.0, 45.0 * k)
        P, Tc, Gp = solar.pv_dc(b, d, g_, aoi, Ta, wind, P_stc / 8, gamma=E.pv_temp_coeff_per_k, losses=1 - E.bos_dirt_wiring_efficiency)
        p_dc += P
        T_cell += Tc / 8
        G_poa += Gp / 8
    # calibration to the UNIBO CAD canopy yield (258.1 kWh/yr, London): curvature, rim/luminaire self-shading
    # and string mismatch not resolved by the 8-facet model
    p_pv = p_dc * E.mppt_efficiency * CAD_CAL
    night = zen > 96.0                    # civil twilight
    hl = wx["hour_local"].to_numpy()
    rain = wx.precip.to_numpy()
    et0 = wx.et0.to_numpy()               # mm/h (FAO-56 reference)
    pm = EC.pm_concentrations[city]
    # states
    soc = E.battery_initial_soc
    T_bat = 12.0
    fade = 0.0
    efc = 0.0
    V_tank = HY.tank_initial_volume_l
    theta = np.full(4, 0.30)
    dry_hours = 0.0
    names = ["p_pv", "p_light", "p_aux", "p_pump", "p_batt", "soc", "v_bat", "i_bat", "T_bat", "r_int", "loss_bat", "curtail",
             "unserved", "dim", "rain_cap", "overflow", "v_tank", "irrig", "et_tot", "pump_on", "stress", "pm25", "pm10",
             "cool_w", "first_flush"]
    H = {k: np.zeros(n) for k in names}
    tier = {f"theta{j}": np.zeros(n) for j in range(4)}
    tier.update({f"et{j}": np.zeros(n) for j in range(4)})
    tier.update({f"irr{j}": np.zeros(n) for j in range(4)})
    nodes = {f"N{j}_{f}": np.zeros(n) for j in range(5) for f in ("P", "Q", "H")}
    dry_spell = 0.0
    for i in range(n):
        # SOC-staged adaptive dimming (street-lighting controller practice), deeper after midnight
        level = 1.0 if soc > 0.7 else 0.7 if soc > 0.5 else 0.5 if soc > 0.35 else 0.3
        if 0 <= hl[i] < 5 and soc < 0.8:
            level = min(level, 0.6)
        dimmed = night[i] and level < 1.0
        p_light = E.power_light_w * level if night[i] else 0.0
        p_aux = E.power_aux_w + 0.8
        # rain capture with first flush per event (rain after > 6 dry hours)
        r_mm = rain[i]
        ff = 0.0
        if r_mm > 0.05:
            if dry_spell > 6:
                ff = min(r_mm, 0.5)
            dry_spell = 0.0
        else:
            dry_spell += 1
        cap_l = max(0.0, r_mm - ff) * G.area_catchment_m2 * HY.runoff_coefficient * HY.filter_efficiency
        V_tank += cap_l
        over = max(0.0, V_tank - G.volume_tank_max_l)
        V_tank -= over
        # evapotranspiration per tier (mm over the tier plan area 0.25 m2 -> litres)
        et_l = np.array([KC[j] * EXPO[j] * et0[i] * G.foliage_area_per_tier_m2 for j in range(4)])
        avail = SUBSTRATE_L * (FC - WP)
        theta = np.clip(theta - et_l / SUBSTRATE_L * np.clip((theta - WP) / (0.5 * (FC - WP)), 0, 1), WP * 0.9, FC)
        # direct rain on planters (25 % interception by the canopy above)
        theta = np.minimum(FC, theta + r_mm * G.foliage_area_per_tier_m2 * 0.25 / SUBSTRATE_L)
        # irrigation pulses: each depleted tier gets a pulse restoring 70 % of available water
        q_pump = 0.0
        pump_s = 0.0
        irr = np.zeros(4)
        for j in range(4):
            depletion = (FC - theta[j]) / (FC - WP)
            if depletion > 0.45 and V_tank > 5.0:
                need = min(0.7 * depletion * avail, V_tank - 5.0) / HY.irrigation_drip_efficiency
                irr[j] = need * HY.irrigation_drip_efficiency
                theta[j] += irr[j] / SUBSTRATE_L
                V_tank -= need
                pump_s += need / HY.nominal_flow_rate_l_min * 60
        q = HY.nominal_flow_rate_l_min / 60000 if pump_s > 0 else 0.0
        # hydraulics: riser to the highest tier carries the full flow, splits at each tier
        h_static_tank = 0.5 * (V_tank / G.volume_tank_max_l)
        P_nodes, Q_nodes, H_nodes = [], [], []
        if q > 0:
            heads = []
            for j in range(4):
                qj = q * (4 - j) / 4
                heads.append(friction_head(qj, 1.0))
            H_pump = TIER_Z[-1] + HY.emitter_operating_head_m + sum(heads) - h_static_tank + 0.3
            p_pump = 1000 * 9.81 * q * H_pump / HY.pump_efficiency + 0.6
        else:
            H_pump, p_pump, heads = 0.0, 0.0, [0, 0, 0, 0]
        Hn = H_pump - 0.3 + h_static_tank
        P_nodes.append(Hn * 9.81 * 1000 / 1e5 if q > 0 else 0.0)
        Q_nodes.append(q * 60000)
        H_nodes.append(Hn)
        z_prev = 0.0
        for j in range(4):
            Hn = Hn - (TIER_Z[j] - z_prev) - heads[j] if q > 0 else 0.0
            z_prev = TIER_Z[j]
            P_nodes.append(Hn * 9.81 * 1000 / 1e5 if q > 0 else 0.0)
            Q_nodes.append(q * 60000 * (4 - j) / 4 if q > 0 else 0.0)
            H_nodes.append(Hn)
        E_pump_wh = p_pump * pump_s / 3600
        # ---- battery (10-minute sub-steps)
        e_aux = 0.0
        for s in range(SUB):
            P_net = p_pv[i] - p_light - p_aux - (E_pump_wh * 3600 / 3600 if s == 0 else 0.0) * 6 / SUB
            T_bat += ((Ta[i] + 3.0 * (ghi[i] / 800) - T_bat) / (6 * 3600) + abs(P_net) * 0.03 / (8.0 * 900.0)) * DT
            V = ocv(soc)
            R = r_int(T_bat)
            I = P_net / V
            if I > 0:                      # charging
                I_max = 50.0 * (E.subzero_charge_derate if T_bat < 0 else 1.0)
                if soc >= E.battery_soc_max - 1e-4:
                    H["curtail"][i] += P_net / SUB
                    I = 0.0
                elif I > I_max:
                    H["curtail"][i] += (I - I_max) * V / SUB
                    I = I_max
            else:
                if soc <= E.battery_soc_min + 1e-4:
                    H["unserved"][i] += -P_net / SUB
                    I = 0.0
            loss = I * I * R
            dAh = I * DT / 3600 * (0.995 if I > 0 else 1.0)
            soc = float(np.clip(soc + dAh / (cap_Ah * (1 - fade)), E.battery_soc_min, E.battery_soc_max))
            efc += abs(dAh) / (2 * cap_Ah)
            H["v_bat"][i] += (V + I * R) / SUB
            H["i_bat"][i] += I / SUB
            H["loss_bat"][i] += loss / SUB
            H["p_batt"][i] += I * V / SUB
        fade = 0.02 * (efc / 1000) + 0.015 * (i + 1) / 8760 * (1 + 0.03 * max(0.0, T_bat - 25))
        # ---- ecosystem
        lai_area = 4 * G.foliage_area_per_tier_m2 * 3.0
        washoff = 0.6 if r_mm > 1.0 else 0.0
        # dry deposition: v_d [m/s] x C [ug/m3] x leaf area [m2] x 3600 s -> ug/h -> mg/h
        H["pm25"][i] = EC.pm_deposition_velocity_m_s * pm["pm25"] * (0.6 + 0.08 * wind[i]) * lai_area * 3600 * 1e-3
        H["pm10"][i] = 1.6 * EC.pm_deposition_velocity_m_s * pm["pm10"] * (0.6 + 0.08 * wind[i]) * lai_area * 3600 * 1e-3
        H["cool_w"][i] = (et_l.sum() / 3600) * EC.latent_heat_vaporization_j_kg     # W
        H["p_pv"][i], H["p_light"][i], H["p_aux"][i] = p_pv[i], p_light, p_aux
        H["p_pump"][i] = E_pump_wh
        H["soc"][i], H["T_bat"][i], H["r_int"][i] = soc * 100, T_bat, r_int(T_bat) * 1000
        H["dim"][i] = 100.0 * level if night[i] else 0.0
        H["rain_cap"][i], H["overflow"][i], H["v_tank"][i] = cap_l, over, V_tank
        H["first_flush"][i] = ff * G.area_catchment_m2
        H["irrig"][i], H["et_tot"][i], H["pump_on"][i] = irr.sum(), et_l.sum(), pump_s / 60
        stress = np.clip(((FC - theta) / (FC - WP) - 0.6) / 0.4, 0, 1)
        H["stress"][i] = float(stress.mean()) * 100
        for j in range(4):
            tier[f"theta{j}"][i], tier[f"et{j}"][i], tier[f"irr{j}"][i] = theta[j] * 100, et_l[j], irr[j]
        for j in range(5):
            nodes[f"N{j}_P"][i], nodes[f"N{j}_Q"][i], nodes[f"N{j}_H"][i] = P_nodes[j], Q_nodes[j], H_nodes[j]
    return wx, gr, H, tier, nodes, dict(T_cell=T_cell, G_poa=G_poa, P_stc=P_stc, night=night, fade=fade, efc=efc)


def export(key):
    label, city, ci_static, cap = CITIES[key]
    wx, gr, H, tier, nodes, info = simulate(city, cap)
    n = len(wx)
    R = Results(key, f"{label} · Plantpost energy-water-ecosystem year", n)
    g = "Weather"
    R.ch("T_amb", wx.T_amb, "°C", "Air temperature", g, 1)
    R.ch("RH", wx.RH, "%", "Relative humidity", g, 0)
    R.ch("ghi", wx.ghi, "W/m²", "Global horizontal irradiance", g, 0)
    R.ch("wind", wx.wind10, "m/s", "Wind speed", g, 1)
    R.ch("rain", wx.precip, "mm/h", "Precipitation", g, 2)
    R.ch("et0", wx.et0, "mm/h", "FAO-56 reference ET₀", g, 3)
    R.ch("vpd", wx.vpd, "kPa", "Vapour pressure deficit", g, 2)
    g = "PV canopy"
    R.ch("p_pv", H["p_pv"], "W", "PV power to battery (after MPPT)", g, 1)
    R.ch("G_poa", info["G_poa"], "W/m²", "Mean plane-of-array irradiance", g, 0)
    R.ch("T_cell", info["T_cell"], "°C", "Cell temperature", g, 1)
    R.ch("curtail", H["curtail"], "W", "Curtailed PV (battery full / derated)", g, 1)
    g = "Battery"
    R.ch("soc", H["soc"], "%", "State of charge", g, 1)
    R.ch("v_bat", H["v_bat"], "V", "Terminal voltage", g, 2)
    R.ch("i_bat", H["i_bat"], "A", "Current (+ charge)", g, 2)
    R.ch("p_batt", H["p_batt"], "W", "Battery power (+ charge)", g, 1)
    R.ch("T_bat", H["T_bat"], "°C", "Cell temperature (base enclosure)", g, 1)
    R.ch("r_int", H["r_int"], "mΩ", "Internal resistance", g, 1)
    R.ch("loss_bat", H["loss_bat"], "W", "Ohmic loss", g, 2)
    g = "Loads"
    R.ch("p_light", H["p_light"], "W", "LED luminaire", g, 1)
    R.ch("dim", H["dim"], "%", "Luminaire output level", g, 0)
    R.ch("p_aux", H["p_aux"], "W", "BMS + IoT sensors", g, 1)
    R.ch("p_pump", H["p_pump"], "W", "Pump energy (hourly mean)", g, 2)
    R.ch("unserved", H["unserved"], "W", "Unserved load (SOC floor)", g, 2)
    g = "Water"
    R.ch("v_tank", H["v_tank"], "L", "Tank volume", g, 1)
    R.ch("rain_cap", H["rain_cap"], "L/h", "Rain harvested", g, 2)
    R.ch("first_flush", H["first_flush"], "L/h", "First-flush diverted", g, 2)
    R.ch("overflow", H["overflow"], "L/h", "Tank overflow", g, 2)
    R.ch("irrig", H["irrig"], "L/h", "Irrigation delivered", g, 2)
    R.ch("et_tot", H["et_tot"], "L/h", "Plant evapotranspiration", g, 3)
    R.ch("pump_on", H["pump_on"], "min/h", "Pump run time", g, 1)
    R.ch("stress", H["stress"], "%", "Mean plant water stress index", g, 0)
    for j in range(4):
        gt = f"Tier {j + 1} ({TIER_Z[j]:.0f} m)"
        R.ch(f"theta{j + 1}", tier[f"theta{j}"], "% vol", f"Tier {j + 1} substrate moisture", gt, 1)
        R.ch(f"et{j + 1}", tier[f"et{j}"], "L/h", f"Tier {j + 1} evapotranspiration", gt, 3)
        R.ch(f"irr{j + 1}", tier[f"irr{j}"], "L/h", f"Tier {j + 1} irrigation", gt, 2)
    names = ["Pump outlet (base)", "Tier 1 manifold", "Tier 2 manifold", "Tier 3 manifold", "Tier 4 manifold"]
    T_w = np.clip(wx.T_amb.to_numpy() * 0.6 + 6, 1, 30)
    for j in range(5):
        P = nodes[f"N{j}_P"]
        R.state_point(f"N{j}", names[j], "Irrigation riser", "Water",
                      {"T": T_w, "P": P + 1.013, "h": 4.186 * T_w + P * 0.1, "m": nodes[f"N{j}_Q"] / 60})
        R.ch(f"N{j}_head", nodes[f"N{j}_H"], "m", f"{names[j]} · pressure head", "Hydraulics", 2)
    g = "Ecosystem"
    R.ch("pm25", H["pm25"], "mg/h", "PM2.5 captured", g, 3)
    R.ch("pm10", H["pm10"], "mg/h", "PM10 captured", g, 3)
    R.ch("cool_w", H["cool_w"], "W", "Evaporative cooling", g, 1)
    R.ch("ci", gr.ci, "gCO₂/kWh", "GB grid carbon intensity", g, 0)
    R.start = int(np.argmax(np.where(info["night"], -np.abs(np.arange(n) - 24 * 15), -1e9)))
    k = R.kpi
    pv = H["p_pv"].sum() / 1000
    k("PV energy to battery", pv, "kWh", "Energy", 1)
    k("LED lighting energy", H["p_light"].sum() / 1000, "kWh", "Energy", 1)
    k("Pump energy", H["p_pump"].sum() / 1000, "kWh", "Energy", 3)
    k("Curtailed PV", H["curtail"].sum() / 1000, "kWh", "Energy", 1)
    k("Unserved load", H["unserved"].sum() / 1000, "kWh", "Energy", 2)
    dark = info["night"].sum()
    k("Lighting availability", 100 * (1 - (H["unserved"] > 0.5).sum() / max(dark, 1)), "%", "Reliability", 2)
    k("Night hours dimmed", float(((H["dim"] > 0) & (H["dim"] < 99)).sum()), "h", "Reliability", 0)
    k("Mean night light level", float(H["dim"][info["night"]].mean()), "%", "Reliability", 1)
    k("Minimum SOC", H["soc"].min(), "%", "Reliability", 1)
    k("Days SOC < 30 %", float((H["soc"] < 30).sum() / 24), "d", "Reliability", 1)
    k("Equivalent full cycles", info["efc"], "", "Battery", 1)
    k("Capacity fade (year 1)", info["fade"] * 100, "%", "Battery", 2)
    k("Min battery temperature", H["T_bat"].min(), "°C", "Battery", 1)
    k("Rain harvested", H["rain_cap"].sum(), "L", "Water", 0)
    k("Irrigation delivered", H["irrig"].sum(), "L", "Water", 0)
    k("Tank overflow", H["overflow"].sum(), "L", "Water", 0)
    k("Days tank < 10 L", float((H["v_tank"] < 10).sum() / 24), "d", "Water", 1)
    k("Water self-sufficiency", 100 * min(1.0, H["rain_cap"].sum() / max(H["irrig"].sum(), 1e-9)), "%", "Water", 1)
    k("Hours of plant water stress > 50 %", float((H["stress"] > 50).sum()), "h", "Water", 0)
    k("PM2.5 captured", H["pm25"].sum() / 1000, "g", "Ecosystem", 1)
    k("PM10 captured", H["pm10"].sum() / 1000, "g", "Ecosystem", 1)
    k("Evaporative cooling", H["cool_w"].sum() / 1000, "kWh", "Ecosystem", 1)
    ci = ci_static
    k("CO₂ avoided vs grid LED (50 W)", 50 * info["night"].sum() / 1000 * ci / 1000, "kg", "Carbon", 1)
    k("CO₂ avoided vs HPS (150 W)", 150 * info["night"].sum() / 1000 * ci / 1000, "kg", "Carbon", 1)
    R.diagrams.append({"type": "profile", "title": "Tier substrate moisture (top → base)", "xLabel": "% vol",
                       "series": [{"label": "Moisture", "keys": ["theta4", "theta3", "theta2", "theta1"], "color": "#15803d"}]})
    R.diagrams.append({"type": "profile", "title": "Riser pressure head (top → base)", "xLabel": "m",
                       "series": [{"label": "Head", "keys": ["N4_head", "N3_head", "N2_head", "N1_head", "N0_head"], "color": "#2f5bd3"}]})
    R.diagrams.append({"type": "bars", "title": "Power now (W)", "items": [
        {"key": "p_pv", "label": "PV"}, {"key": "p_light", "label": "LED"}, {"key": "p_aux", "label": "Aux"},
        {"key": "p_pump", "label": "Pump"}, {"key": "loss_bat", "label": "Batt loss"}, {"key": "curtail", "label": "Curtail"}]})
    return R


if __name__ == "__main__":
    import time
    for c in (sys.argv[1:] or CITIES):
        t = time.time()
        R = export(c)
        print(c, "%.0fs" % (time.time() - t))
        for kp in R.kpis:
            print(f"  {kp['label']:<40} {kp['value']:.2f} {kp['unit']}")
