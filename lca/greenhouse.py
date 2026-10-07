"""Parametric annual (8760 h) greenhouse simulation driven by a SiteConfig.

Same physics as sim/annual_sim.py (air/crop, floor and pipe-rail nodes; humidity with transpiration and cover
condensation; night screen; vents; 1.5 m3-per-400 m2 stratified buffer; R717 two-stage heat pump on air, ground or
river), with every size, setpoint and boundary taken from the config:

  * geometry and all per-area plant (pipe rail, flow, buffer, auxiliaries) scale with floor area
  * the heat pump is the thesis R717 unit scaled by `cfg.hp_scale()` (identical per-unit cycle; capacity, source
    field and defrost energy scale linearly)
  * climate setpoints follow a day/night calendar (climate.py)
  * rooftop form: floor couples to the heated building through the deck; wind scaled to roof height
  * any location: weather from the Open-Meteo archive via simcore.weather

`thesis(source)` reproduces the original run; see tests/test_reproduce.py.
"""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SIMCORE = ROOT / "simcore" if (ROOT / "simcore").is_dir() else ROOT.parent / "simcore"
for p in (ROOT.parent, ROOT, ROOT / "sim", HERE):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from simcore import grid, solar, weather  # noqa: E402
from simcore.hx import CP_A, CP_W, H_FG, psat_w, w_sat  # noqa: E402
from simcore.storage import StratifiedTank  # noqa: E402
import annual_sim as _orig  # noqa: E402  (performance maps and scenario params of the original model)
from params import GROUND, RECIP, WATER  # noqa: E402
from simcore.perfmap import PerfMap  # noqa: E402

DT, SUB = 600.0, 6
SPEEDS = _orig.SPEEDS

H_NAMES = ["T_air_in", "RH_in", "T_floor", "T_pipe", "T_sup", "T_set", "Q_pipe", "Q_cover", "Q_vent", "Q_floor", "Q_sol",
           "LE", "trans_kg", "cond_kg", "vent", "screen", "ach", "on_frac", "f_cmd", "Q_c", "W_comp", "W_aux", "W_total",
           "defrosts", "frost", "T_src", "T_ground", "unmet", "starts", "buf_soc", "VPD", "Q_def", "Q_e", "Q_below",
           "T_air_mean", "W_led", "PAR_nat", "PAR_led",
           "Q_cool", "W_cool", "T_coil", "cool_cond_kg", "Q_waste"]
PAR_PER_W = 0.47 * 4.57        # umol/s PAR per W of global radiation (PAR fraction x photons per joule)


def _clip(x, lo, hi):
    """Scalar np.clip (min(max(x, lo), hi)) without numpy call overhead; same result for finite inputs."""
    return min(max(x, lo), hi)


class _FastMap:
    """Faster multilinear lookup on a PerfMap with the same arithmetic, in the same order, as PerfMap.__call__
    (results are bit-identical): Python-list axes with bisect, precomputed corners, and a scalar path for when
    only one output is needed (the compressor-speed scan)."""

    def __init__(self, pm):
        import bisect
        import itertools
        self.pm, self._bisect = pm, bisect.bisect_left
        self.names = pm.names
        self.ax = [pm.axes[n].tolist() for n in self.names]
        self.corners = list(itertools.product((0, 1), repeat=len(self.names)))
        self.data, self.valid, self.nk = pm.data, pm.valid, len(pm.out_keys)

    def _locate(self, pt):
        idx, w = [], []
        for n, a in zip(self.names, self.ax):
            v = min(max(pt[n], a[0]), a[-1])
            i = min(max(self._bisect(a, v) - 1, 0), len(a) - 2)
            idx.append(i)
            w.append((v - a[i]) / (a[i + 1] - a[i]))
        return idx, w

    def __call__(self, **pt):
        idx, w = self._locate(pt)
        out = np.zeros(self.nk)
        ok = 0.0
        for corner in self.corners:
            wt = 1.0
            sl = []
            for c, i, f in zip(corner, idx, w):
                wt *= f if c else (1 - f)
                sl.append(i + c)
            if wt == 0:
                continue
            sl = tuple(sl)
            out += wt * self.data[sl]
            ok += wt * self.valid[sl]
        return out, ok

    def scalar(self, k, **pt):
        idx, w = self._locate(pt)
        out = 0.0
        for corner in self.corners:
            wt = 1.0
            sl = []
            for c, i, f in zip(corner, idx, w):
                wt *= f if c else (1 - f)
                sl.append(i + c)
            if wt == 0:
                continue
            out += wt * self.data[tuple(sl) + (k,)]
        return out


def single_stage_params(source):
    """Single-stage R717 on the same source loop, condenser and swept volume as the thesis unit's LP stage."""
    b = GROUND if source == "ground" else WATER
    keys = ("m_w", "UA_c", "SH", "SC", "suction_gain", "dp_suc", "dp_evap", "dp_cond", "dp_dis", "T_dis_max",
            "m_src", "cp_src", "UA_e", "W_src_pump")
    return dict({k: b[k] for k in keys}, fluid="Ammonia", comp=dict(RECIP, disp_m3h=118.0))


# Transcritical CO2 (R744) air-source unit sized to the thesis R717 unit's heating capacity (~110 kW at -4 C air,
# 30 C water in, top speed) so `hp_scale` keeps the same meaning. Same air coil, fan and speed range as the thesis
# unit (params.AIR); low gas-cooler water flow (large temperature rise), as CO2 heat pumps need.
CO2_COMP = dict(f_nom=50, f_min=25, f_max=60, eta_is_max=0.70, pr_opt=2.8, k_pr=0.07, k_f=0.05, f_opt=45,
                clearance=0.04, n_poly=1.25, leak=0.02, eta_motor=0.94, eta_inv=0.97, q_loss_frac=0.08, disp_m3h=23.6)
CO2_AIR = dict(comp=CO2_COMP, SH=5.0, suction_gain=1.0, dp_suc=0.5e5, dp_evap=0.5e5, dp_dis=0.5e5, T_dis_max=140.0,
               P_gc_min=60e5, P_gc_max=130e5, m_air_nom=9.0, UA_e=18000.0, W_fan_max=2600.0, fan_min=0.35,
               m_w=0.9, UA_gc=12000.0)


def build_map(heat):
    """Performance map for the configured cycle; hx_scale multiplies evaporator and condenser UA."""
    if heat.cycle == "co2_tc":
        if heat.source != "air":
            raise ValueError("the CO2 cycle is modelled for air source only")
        from simcore import co2_transcritical as mod
        core = SIMCORE
        p = dict(CO2_AIR, UA_e=CO2_AIR["UA_e"] * heat.hx_scale, UA_gc=CO2_AIR["UA_gc"] * heat.hx_scale)
        axes = _orig.AX_AIR
        o, _ = mod.solve(p, {k: v[len(v) // 2] for k, v in axes.items()})
        return PerfMap(f"greenhouse_co2tc_air_hx{heat.hx_scale:g}", core / "co2_transcritical.py", "solve", p, axes,
                       list(o), deps=[core / "hx.py", core / "thermo.py"])
    if heat.cycle == "two_stage" and heat.hx_scale == 1.0:
        return _orig.build_map(heat.source)
    if heat.cycle == "single_stage" and heat.source == "air":
        raise ValueError("single-stage cycle is modelled for liquid sources only")
    core = SIMCORE
    if heat.cycle == "two_stage":
        p = dict(_orig.SCENARIOS[heat.source]["params"])
        fn, axes = core / "two_stage.py", _orig.SCENARIOS[heat.source]["axes"]
        from simcore import two_stage as mod
    else:
        p = single_stage_params(heat.source)
        fn, axes = core / "single_stage_liquid.py", _orig.AX_LIQ
        from simcore import single_stage_liquid as mod
    p["UA_e"] *= heat.hx_scale
    p["UA_c"] *= heat.hx_scale
    # a point inside every cycle's envelope, used only to list the output keys
    pt = {"T_src_in": 8.0, "T_w_in": 30.0, "f": 40.0} if heat.source != "air" else {k: v[len(v) // 2] for k, v in axes.items()}
    o, _ = mod.solve(p, pt)
    return PerfMap(f"greenhouse_nh3{'ss' if heat.cycle != 'two_stage' else ''}_{heat.source}_hx{heat.hx_scale:g}", fn,
                   "solve", p, axes, list(o), deps=[core / "hx.py", core / "thermo.py"])


def load_weather(loc):
    if loc.lat is not None and loc.site not in weather.SITES:
        weather.SITES[loc.site] = (loc.lat, loc.lon, 0, loc.description or loc.site)
    return weather.load(loc.site), weather.SITES[loc.site][:2]


class HeatPumpSupply:
    """Thesis R717 two-stage unit scaled by `s`. Control logic and state handling as in sim/annual_sim.py."""

    def __init__(self, source, s, pmap, heat, hy):
        self.source, self.s, self.pmap = source, s, pmap
        self.fm = _FastMap(pmap)
        self.heat, self.hy = heat, hy
        self.air = source == "air"
        self.p = _orig.SCENARIOS[source]["params"]
        self.on, self.off_t, self.frost = False, 1e9, 0.0
        self.T_g, self.Q_e_prev = 11.0, 0.0
        self.Q_rej = 0.0                                          # cooling heat put into the source (W), this step

    def t_src(self, Ta, T_river):
        if self.air:
            return Ta
        if self.source == "ground":
            return self.T_g - self.Q_e_prev / (self.heat.field_ua_w_K * self.s)   # thesis: 7 kW/K per unit
        return T_river - 1.5

    def step(self, i, buf, T_sup_req, m_pipe, Ta, rh_o, T_river, H, acc, cheap=False, block=False):
        s, pm, K, hy = self.s, self.pmap, self.pmap.out_keys, self.hy
        T_src = self.t_src(Ta, T_river)
        # price-led charging: in cheap hours of the heating season, hold the buffer `shift_boost_K` above need
        boost = hy.shift_boost_K if (cheap and hy.shift_boost_K > 0 and Ta < 15.0) else 0.0
        floor = max(T_sup_req, hy.buf_min_C) + boost
        want = buf.T[3] < floor + 1.0 or (self.on and buf.T[-1] < floor + hy.hp_margin_K - 1.0)
        if T_sup_req <= 25 and buf.T[3] > hy.buf_min_C and not boost:
            want = False
        if block:                       # direct waste heat covers the load this step
            want = False
        if not self.on and want and self.off_t >= DT:
            self.on = True
            H["starts"][i] += 1
        elif self.on and not want:
            self.on = False
            self.off_t = 0.0
        Q_c = W_c = Q_e = 0.0
        if self.on:
            T_in = buf.T[-1]
            T_target = floor + hy.hp_margin_K
            Q_target = m_pipe * CP_W * max(T_target - T_in, 1.0) * 0.6 / s
            ua = max(0.5, 1 - 0.5 * min(self.frost / 24.0, 1.0))
            kw = dict(T_air=Ta, RH=rh_o, ua=ua) if self.air else dict(T_src_in=T_src)
            kq = pm.kidx["Q_c"]
            qs = np.array([self.fm.scalar(kq, T_w_in=T_in, f=fs, **kw) * 1e3 for fs in SPEEDS])
            f_cmd = float(np.interp(Q_target, qs, SPEEDS)) if Q_target < qs[-1] else SPEEDS[-1]
            f_cmd = max(SPEEDS[0], f_cmd)
            vec, ok = self.fm(T_w_in=T_in, f=f_cmd, **kw)
            Q_c = pm.get(vec, "Q_c") * 1e3
            W_c = pm.get(vec, "W_tot") * 1e3
            Q_e = pm.get(vec, "Q_e") * 1e3
            frac = 1.0
            if self.air:
                water = pm.get(vec, "water")
                if pm.get(vec, "Te") + 1.5 < 0 and water > 0:
                    self.frost += water * DT
                if self.frost >= 14.0:
                    E_def = self.frost * 338e3 + 2.0e6
                    H["defrosts"][i] += 1
                    H["Q_def"][i] += s * 0.75 * E_def / 3.6e6
                    buf.T -= s * 0.75 * E_def / (buf.M * CP_W * buf.N)
                    W_c += 0.25 * E_def / DT
                    frac = 1 - min(DT, 180 + E_def / 30e3) / DT
                    self.frost = 0.0
            for ki, kk in enumerate(K):
                acc[kk][i] += vec[ki] * frac
            H["on_frac"][i] += frac / SUB
            H["f_cmd"][i] += f_cmd * frac / SUB
            Q_c *= frac * s
            W_c *= s
            Q_e *= frac * s
        else:
            self.off_t += DT
            if self.air and Ta > 2:
                self.frost = max(0.0, self.frost - 0.003 * (Ta - 2) * DT)
        if self.source == "ground":
            hs = self.heat
            self.T_g += (hs.field_leak_w_K * s * (hs.field_T_far_C - self.T_g) - Q_e + self.Q_rej) * DT \
                / (hs.field_cap_J_K * s)
        self.Q_e_prev = Q_e
        return Q_c, W_c, Q_e


def simulate(cfg, pmap=None, progress=False, i_floor=None, t_source=None, waste_kw=None):
    """Run one year. Returns (H hourly dict, acc perf-map outputs, wx weather, gr grid, meta)."""
    g, e, loc, cl, hy = cfg.geometry, cfg.envelope, cfg.location, cfg.climate, cfg.hydronics
    A, VOL, A_WALL, A_ROOF, U_COVER = g.area, g.volume, g.a_wall, g.a_roof, e.u_cover
    UA_WALL = e.wall_ua(g)
    hr = cfg.hrd
    hc = cfg.hum
    RSI = 0.10                       # ISO 6946 inside surface resistance, upward heat flow (m2K/W)
    rooftop = loc.form == "rooftop"
    wx, (lat, lon) = load_weather(loc)
    gr = grid.load()
    n = len(wx)
    zen, az, doy_all = solar.position(wx["time"], lat, lon)
    doy_all = np.asarray(doy_all)
    Ta_all, rh_all = wx["T_amb"].to_numpy(), wx["RH"].to_numpy()
    w_out_all = wx["w_amb"].to_numpy()
    ghi = wx["ghi"].to_numpy()
    wind = wx["wind10"].to_numpy()
    if rooftop:
        z = loc.roof_height_m + g.gutter_height
        wind = wind * math.log(z / loc.z0_m) / math.log(10.0 / loc.z0_m)
    sky = wx["T_sky"].to_numpy()
    cloud = wx["cloud"].to_numpy() / 100
    Tsoil2 = wx["T_soil_2m"].to_numpy()
    T7 = pd.Series(Ta_all).rolling(24 * 7, min_periods=1).mean().to_numpy()
    T_river = np.maximum(1.5, 0.85 * T7 + 2.2)
    if t_source is not None:            # low-grade waste heat (effluent, data centre...) as the water source
        T_river = np.asarray(t_source, float)[:n] + 1.5
    U_b = cfg.u_floor_below()                                 # floor to soil / building below, W/m2K
    T_b_all = np.full(n, loc.t_building_C) if rooftop else Tsoil2

    s = cfg.hp_scale()
    if pmap is None:
        pmap = build_map(cfg.heat)
    hp = HeatPumpSupply(cfg.heat.source, s, pmap, cfg.heat, hy)
    # cheap hours: price in the lowest `shift_quantile` of its calendar day (Agile shape)
    price = gr.price.to_numpy()
    day_q = pd.Series(price).groupby(np.arange(len(price)) // 24).transform(lambda x: x.quantile(hy.shift_quantile))
    cheap_all = price <= day_q.to_numpy()
    Q_design = cfg.design_heat_loss_w()

    T_a, T_f, T_p = 18.0, 15.0, 30.0
    # GreenLight (Vanthoor 2011) floor and soil layers, used when e.soil_layers (mirrors greenhouse_fast.py)
    soil_on = e.soil_layers
    sh = np.array([0.04, 0.08, 0.16, 0.32, 0.64])
    Ts = np.full(5, 15.0)
    cap_s = sh * 1.73e6 * A
    Cf_s = 0.02 * 2300.0 * 880.0 * A
    Gf1 = A * 2.0 / (0.02 / 1.7 + sh[0] / 0.85)
    Gk = A * 2.0 * 0.85 / (sh[:-1] + sh[1:])
    R_chain = 1.0 / (Gf1 / A) + sum(1.0 / (Gk[kk] / A) for kk in range(4))
    Gb = A / max(1.0 / U_b - R_chain, 0.05)
    fl_q = np.zeros(6)
    w_a = w_sat(18.0) * 0.8
    v_buf, h_buf = hy.buffer(A)
    buf = StratifiedTank(v_buf, h_buf, nodes=10, U_wall=0.35, T_init=45.0)
    integ = 0.0
    lt = cfg.lighting
    hour_loc = wx["hour_local"].to_numpy()
    dli = 0.0
    T_set = cl.at(int(doy_all[0]), ghi[0] > 20)[0]
    K = pmap.out_keys
    acc = {k: np.zeros(n) for k in K}
    H = {k: np.zeros(n) for k in H_NAMES}
    bufN = np.zeros((n, buf.N))
    m_pipe = hy.m_pipe_per_m2 * A
    m_charge = m_pipe if cfg.heat.charge_m_w is None else cfg.heat.charge_m_w * s
    L_PIPE, K_PIPE = hy.pipe_m_per_m2 * A, hy.k_pipe
    C_air = 1.2 * 1006 * VOL + A * 3 * 1500                  # air + crop/benching
    C_floor = A * 0.15 * 2.0e6
    C_pipe = hy.c_pipe_per_m * L_PIPE
    M_air = 1.2 * VOL
    G_floor = 6.0 * A
    G_fb = G_floor + U_b * A                                  # floor node: to air + to boundary below
    co = cfg.cooling
    if co.enabled and hp.source == "air":
        raise ValueError("semi-closed cooling needs a ground or river source to take the heat")
    UA_coil = co.ua_w_m2K * A if co.enabled else 0.0
    Q_cool_prev = 0.0
    for i in range(n):
        if progress and i % 1000 == 0:
            print(f"  {cfg.name}: hour {i}", flush=True)
        Ta, rh_o, w_o = Ta_all[i], rh_all[i], w_out_all[i]
        day = ghi[i] > 20
        T_cal, T_vent_set = cl.at(int(doy_all[i]), day)
        T_set += float(_clip(T_cal - T_set, -cl.ramp_K_per_h, cl.ramp_K_per_h))
        screen = (not day) and Ta < e.screen_below_C
        U_roof = U_COVER * (e.screen_u_factor if screen else 1.0) + 0.06 * wind[i]
        UA_cov = UA_WALL + U_roof * A_ROOF
        I_in = e.tau_solar * ghi[i] if i_floor is None else i_floor[i]   # i_floor: design.py light, W/m2 floor
        if UA_coil:
            T_coil = (hp.T_g + Q_cool_prev / (7000.0 * s) if hp.source == "ground" else T_river[i]) + co.approach_K
        else:
            T_coil = 0.0
        # ---- LED top-lighting: on in the photoperiod when natural light is low and the day's light integral is short
        par_nat = I_in * PAR_PER_W
        if hour_loc[i] == 0:
            dli = 0.0
        led = (lt.ppfd > 0 and lt.photoperiod[0] <= hour_loc[i] < lt.photoperiod[1] and par_nat < lt.on_below_par
               and dli < lt.dli_target and T_a < lt.off_above_C
               and (lt.allow_hourly is None or lt.allow_hourly[i] > 0.5))
        P_led = lt.w_per_m2 * A if led else 0.0
        dli += (par_nat + (lt.ppfd if led else 0.0)) * 3600 / 1e6
        I_in = I_in + lt.radiant_frac * P_led / A         # LED light behaves like sunlight inside (crop, floor, air)
        Q_led_conv = (1 - lt.radiant_frac) * P_led
        H["W_led"][i], H["PAR_nat"][i], H["PAR_led"][i] = P_led / 1e3, par_nat, lt.ppfd if led else 0.0
        T_b = T_b_all[i]
        floor_frac_i = e.floor_sol_frac if e.floor_frac_hourly is None else e.floor_frac_hourly[i]
        tr_rad_i, tr_vpd_i = (e.transp_rad, e.transp_vpd) if e.transp_hourly is None else (e.transp_hourly[0][i], e.transp_hourly[1][i])
        for _s in range(SUB):
            # ---- climate control
            err = T_set - T_a
            integ = float(_clip(integ + err * DT / 3600 * 6.0, -10, 60))
            base = hy.sup_base_C + hy.sup_curve_K_per_K * max(0.0, T_set - Ta)
            T_sup_req = float(_clip(base + 9.0 * err + integ, 22.0, hy.t_sup_max)) \
                if (T_a < T_set + 1.5 or err > -1.0) else 22.0
            if hc.enabled and not hr.enabled:   # minimum pipe for humidity
                rh_now = min(100.0, 100 * (w_a * 101325 / (0.62198 + w_a)) / psat_w(T_a))
                h_sub = float(_clip((rh_now - hc.rh_set) / hc.band, 0, 1))
                if h_sub > 0:
                    T_sup_req = max(T_sup_req, 25.0 + (hc.pipe_min_C - 25.0) * h_sub)
            # ---- greenhouse climate: 30 s sub-steps
            T_top = buf.T[0]
            heating = T_sup_req > 25
            T_sup = min(T_sup_req, T_top) if heating else T_p
            NC, dtc = 20, DT / 20
            agg = dict(Q_pipe=0.0, Q_cover=0.0, Q_vent=0.0, Q_floor=0.0, Q_sol=0.0, LE=0.0, E=0.0, cond=0.0, Q_in=0.0,
                       vent=0.0, ach=0.0, Qcs=0.0, mcc=0.0, fan_hr=0.0)
            for _c in range(NC):
                pv_a = w_a * 101325 / (0.62198 + w_a)
                rh_in = min(100.0, 100 * pv_a / psat_w(T_a))
                vent = float(_clip((T_a - T_vent_set) / 4.0, 0, 1))
                if hc.enabled:
                    hum = float(_clip((rh_in - hc.rh_set) / hc.band, 0, 1))
                else:
                    hum = float(_clip((rh_in - cl.rh_vent_start) / 10.0, 0, 1))
                if hr.enabled:   # humidity handled by the heat-recovery units instead of the vents
                    m_hr = hum * hr.flow_m3_m2_h * A * 1.2 / 3600
                else:
                    m_hr = 0.0
                    vent = max(vent, hum * (hc.vent_gap if hc.enabled else 0.12))
                if e.vent_area_frac > 0:   # Vanthoor (2011) roof-vent law, per m2 floor -> air changes per hour
                    f_v = e.vent_area_frac * e.vent_cd / 2 * math.sqrt(abs(
                        9.81 * e.vent_h * (T_a - Ta) / (2 * (0.5 * T_a + 0.5 * Ta + 273.15)) + e.vent_cw * wind[i] ** 2))
                    ach_vent = f_v * 3600.0 * A / VOL
                else:
                    ach_vent = e.vent_ach + e.vent_ach_wind * wind[i]
                ach = (e.infiltration_ach + 0.05 * wind[i]) * (0.7 if screen else 1.0) + vent * ach_vent
                m_nat = ach * VOL * 1.2 / 3600
                m_ex = m_nat + m_hr                                  # moisture leaves with all exchanged air
                m_th = m_nat + m_hr * (1 - hr.effectiveness)         # heat leaves with natural air + unrecovered share
                ach += m_hr * 3600 / (VOL * 1.2)
                agg["fan_hr"] += m_hr / 1.2 * hr.sfp_w_per_m3s / NC
                Q_pipe = K_PIPE * L_PIPE * max(T_p - T_a, 0.0) ** 1.25
                Q_in = m_pipe * CP_W * max(T_sup - T_p, 0.0) * (1 - math.exp(-1.0)) if heating else 0.0
                vpd = max(0.0, psat_w(T_a) - pv_a) / 1000
                LE = (tr_rad_i * I_in * 0.7 + tr_vpd_i * vpd) * A
                E = LE / H_FG
                if e.cover_t_from_u:   # inner surface: drop across the inside film = U * Rsi of the total
                    fr = min(1.0, U_COVER * RSI)
                    T_cov = T_a - fr * (T_a - Ta) - (1 - cloud[i]) * 1.5 * fr / 0.65
                else:
                    T_cov = Ta + 0.35 * (T_a - Ta) - (1 - cloud[i]) * 1.5
                cond = max(0.0, 0.0028 * (A_WALL + A_ROOF) * (w_a - w_sat(T_cov)))
                rad = 0.15 * A_ROOF * (0.4 if screen else 1.0)
                Q_cover = UA_cov * (T_a - Ta) + rad * (T_a - sky[i])
                Q_vent = m_th * CP_A * (T_a - Ta)
                Q_floor = G_floor * (T_f - T_a)
                Q_sol_air = (1.0 - floor_frac_i) * I_in * A
                G = UA_cov + rad + m_th * CP_A + G_floor
                if UA_coil:
                    ua = UA_coil * float(_clip((T_a - co.set_C) / 2.0, 0, 1)) if T_a > T_coil else 0.0
                    m_cc = ua / CP_A * max(0.0, w_a - w_sat(T_coil))     # condensate on the coil, kg/s
                    G += ua
                else:
                    ua = m_cc = 0.0
                src = Q_pipe + Q_sol_air - LE + G_floor * T_f + 0.5 * cond * H_FG + (UA_cov + m_th * CP_A) * Ta + rad * sky[i] \
                    + Q_led_conv + ua * T_coil
                T_a = (T_a * C_air / dtc + src) / (C_air / dtc + G)
                if soil_on:
                    T_f = (T_f * Cf_s / dtc + floor_frac_i * I_in * A + G_floor * T_a + Gf1 * Ts[0]) / (Cf_s / dtc + G_floor + Gf1)
                    fl_q[0] = Gf1 * (T_f - Ts[0])
                    for kk in range(4):
                        fl_q[kk + 1] = Gk[kk] * (Ts[kk] - Ts[kk + 1])
                    fl_q[5] = Gb * (Ts[4] - T_b)
                    for kk in range(5):
                        Ts[kk] += dtc * (fl_q[kk] - fl_q[kk + 1]) / cap_s[kk]
                else:
                    T_f = (T_f * C_floor / dtc + floor_frac_i * I_in * A + G_floor * T_a + U_b * A * T_b) / (C_floor / dtc + G_fb)
                T_p += (Q_in - Q_pipe) * dtc / C_pipe
                w_a = (w_a * M_air / dtc + E - cond - m_cc + m_ex * w_o) / (M_air / dtc + m_ex)
                w_a = float(_clip(w_a, 0.0005, w_sat(T_a)))
                for kk, v in (("Q_pipe", Q_pipe), ("Q_cover", Q_cover), ("Q_vent", Q_vent), ("Q_floor", -Q_floor),
                              ("Q_sol", Q_sol_air), ("LE", LE), ("E", E), ("cond", cond), ("Q_in", Q_in), ("vent", vent), ("ach", ach)):
                    agg[kk] += v / NC
                agg["Qcs"] += ua * (T_a - T_coil) / NC
                agg["mcc"] += m_cc / NC
            Q_pipe, Q_cover, Q_vent, Q_floor, Q_sol_air, LE = (agg[k] for k in ("Q_pipe", "Q_cover", "Q_vent", "Q_floor", "Q_sol", "LE"))
            E, cond, Q_in_pipe, vent, ach = agg["E"], agg["cond"], agg["Q_in"], agg["vent"], agg["ach"]
            Q_floor = -Q_floor
            T_ret = T_p - 2.0
            m_draw = Q_in_pipe / (CP_W * max(T_top - T_ret, 1.0)) if Q_in_pipe > 0 else 0.0
            Q_cool = agg["Qcs"] + agg["mcc"] * H_FG                 # sensible + latent heat into the coil water
            W_cool = Q_cool / co.eer if Q_cool > 0 else 0.0
            hp.Q_rej = Q_cool if hp.source == "ground" else 0.0
            # ---- heat supply
            # direct medium-grade waste heat (distillery flue, bakery, paper...) charges the buffer first, up to the
            # same target as the heat pump and only while the source is >= 5 K above the buffer bottom
            Q_w = 0.0
            if waste_kw is not None and waste_kw[i] > 0:
                T_goal = max(T_sup_req, hy.buf_min_C) + hy.hp_margin_K
                if buf.T[3] < T_goal and buf.T[-1] < cfg.heat.waste_T_C - 5.0:
                    Q_w = waste_kw[i] * 1e3
            # waste heat has priority: with it flowing, the heat pump only starts if the buffer keeps falling
            # (more than 2 K below its floor), i.e. the waste heat cannot keep up
            wfloor = max(T_sup_req, hy.buf_min_C)
            # (and, once running, stops as soon as the buffer is back at its floor)
            blk = Q_w >= Q_design or (Q_w > 0 and buf.T[3] >= wfloor - (0.0 if hp.on else 2.0))
            Q_c, W_c, Q_e = hp.step(i, buf, T_sup_req, m_pipe, Ta, rh_o, T_river[i], H, acc, bool(cheap_all[i]),
                                    block=blk)
            Q_tot = Q_c + Q_w
            buf.step(DT, m_charge if Q_tot > 0 else 0.0, 0.0, m_draw, T_ret, 15.0, Q_c=Q_tot if Q_tot > 0 else None)
            H["Q_waste"][i] += Q_w / 1e3 / SUB
            # The original sim writes `900.0 * vent > 0.02` (a 0/1 boolean, i.e. 1 W) where 900 W while venting
            # was intended; legacy_aux_vent keeps that for the reproduction test.
            venting = vent > 0.02
            if cfg.legacy_aux_vent:
                W_aux = 150.0 + (1200.0 if Q_in_pipe > 0 else 0.0) + (900.0 * vent > 0.02) + (60.0 if screen else 0)
            else:
                pump = 0.0
                if Q_in_pipe > 0:
                    pump = hy.aux_pump_w_m2 * (max(0.15, min(1.0, Q_in_pipe / Q_design)) ** 3 if hy.pump_vsd else 1.0)
                W_aux = A * (hy.aux_base_w_m2 + pump
                             + (hy.aux_vent_w_m2 if venting else 0.0) + (hy.aux_screen_w_m2 if screen else 0.0)) + agg["fan_hr"]
            for kk, v in (("Q_pipe", Q_pipe), ("Q_cover", Q_cover), ("Q_vent", Q_vent), ("Q_floor", -Q_floor), ("Q_sol", Q_sol_air),
                          ("LE", LE), ("Q_c", Q_c), ("Q_e", Q_e), ("W_comp", W_c), ("W_aux", W_aux), ("W_total", W_c + W_aux + P_led + W_cool),
                          ("Q_cool", Q_cool), ("W_cool", W_cool)):
                H[kk][i] += v / 1e3 / SUB
            H["trans_kg"][i] += E * DT
            H["cond_kg"][i] += cond * DT
            H["vent"][i] += vent * 100 / SUB
            H["ach"][i] += ach / SUB
            H["T_sup"][i] += T_sup / SUB
            H["T_air_mean"][i] += T_a / SUB
            H["cool_cond_kg"][i] += agg["mcc"] * DT
            H["Q_below"][i] += (Gb * (T_b - Ts[4]) if soil_on else U_b * A * (T_b - T_f)) / 1e3 / SUB    # + = heat from soil / building into floor
        H["T_air_in"][i], H["T_floor"][i], H["T_pipe"][i] = T_a, T_f, T_p
        H["T_set"][i] = T_set
        H["T_coil"][i] = T_coil
        Q_cool_prev = H["Q_cool"][i] * 1e3
        H["RH_in"][i] = min(100.0, 100 * w_a * 101325 / (0.62198 + w_a) / psat_w(T_a))
        H["VPD"][i] = max(0.0, psat_w(T_a) - w_a * 101325 / (0.62198 + w_a)) / 1000
        H["screen"][i] = float(screen) * 100
        H["frost"][i] = hp.frost
        H["T_src"][i] = hp.t_src(Ta, T_river[i])
        H["T_ground"][i] = hp.T_g if hp.source == "ground" else (T_river[i] if not hp.air else Tsoil2[i])
        H["unmet"][i] = max(0.0, T_set - 1.0 - T_a)
        H["buf_soc"][i] = buf.soc(25.0, 70.0) * 100
        bufN[i] = buf.T
        if H["on_frac"][i] > 0:
            for kk in K:
                acc[kk][i] /= H["on_frac"][i] * SUB
            H["f_cmd"][i] /= H["on_frac"][i]
    meta = dict(name=cfg.name, area_m2=A, u_floor=U_b, volume_m3=VOL, a_wall_m2=A_WALL, a_roof_m2=A_ROOF, hp_scale=s,
                design_heat_loss_kw=cfg.design_heat_loss_w() / 1e3, buffer_m3=v_buf, pipe_m=L_PIPE, form=loc.form,
                site=loc.site, lat=lat, lon=lon, climate=cl.name, source=cfg.heat.source)
    return H, acc, wx, gr, meta, bufN


def summary(H, gr, meta):
    """Annual KPIs (per site and per m2) used by the LCA/LCC steps."""
    A = meta["area_m2"]
    Wt = H["W_total"].sum()
    out = dict(meta)
    out.update(
        heat_delivered_MWh=H["Q_c"].sum() / 1e3,
        pipe_heat_MWh=H["Q_pipe"].sum() / 1e3,
        heat_kWh_m2=H["Q_pipe"].sum() / A,
        electricity_MWh=Wt / 1e3,
        electricity_kWh_m2=Wt / A,
        scop_unit=H["Q_c"].sum() / max(H["W_comp"].sum(), 1e-9),
        scop_system=H["Q_c"].sum() / max(Wt, 1e-9),
        peak_heat_kW=H["Q_pipe"].max(),
        peak_elec_kW=H["W_total"].max(),
        co2_t_grid2023=(H["W_total"] * gr.ci.to_numpy()).sum() / 1e6,
        cost_gbp_agile=(H["W_total"] * gr.price.to_numpy()).sum() / 100,
        price_shape_factor=float((H["W_total"] * gr.price.to_numpy()).sum() / max(Wt, 1e-9) / gr.price.mean()),
        ci_shape_factor=float((H["W_total"] * gr.ci.to_numpy()).sum() / max(Wt, 1e-9) / gr.ci.mean()),
        comp_kWh_m2=H["W_comp"].sum() / A,
        aux_kWh_m2=H["W_aux"].sum() / A,
        cool_elec_kWh_m2=H["W_cool"].sum() / A,
        tsup_mean_heating=float(H["T_sup"][H["Q_pipe"] > 0.5].mean()) if (H["Q_pipe"] > 0.5).any() else 0.0,
        tsrc_mean_on=float(H["T_src"][H["on_frac"] > 0].mean()) if (H["on_frac"] > 0).any() else 0.0,
        mean_T_in=H["T_air_in"].mean(),
        hours_unmet=int((H["unmet"] > 0).sum()),
        hours_above_30=int((H["T_air_in"] > 30).sum()),
        hours_rh_above_90=int((H["RH_in"] > 90).sum()),
        transpiration_m3=H["trans_kg"].sum() / 1e3,
        below_kWh_m2=H["Q_below"].sum() / A,
        led_kWh_m2=H["W_led"].sum() / A,
        led_hours=int((H["W_led"] > 0).sum()),
        cool_kWh_m2=H["Q_cool"].sum() / A,
        min_T_ground=float(H["T_ground"].min()),
        max_T_ground=float(H["T_ground"].max()),
    )
    return out


SIM_CACHE = HERE / "results" / "simcache"
_CODE_FILES = [HERE / "greenhouse.py", HERE / "config.py", HERE / "climate.py", ROOT / "sim" / "annual_sim.py",
               ROOT / "sim" / "params.py", *sorted(SIMCORE.glob("*.py"))]


def simulate_cached(cfg, pmap=None):
    """simulate() with an on-disk cache keyed by the full config and a hash of the model code, so an identical case is
    never run twice and any code change invalidates old results. Weather and grid are reloaded, not stored."""
    import hashlib
    import pickle
    h = hashlib.sha1(repr(cfg).encode())
    for f in _CODE_FILES:
        if f.exists():
            h.update(f.read_bytes())
    path = SIM_CACHE / f"{h.hexdigest()[:20]}.pkl"
    if path.exists():
        H, acc, meta, bufN = pickle.loads(path.read_bytes())
        return H, acc, load_weather(cfg.location)[0], grid.load(), meta, bufN
    H, acc, wx, gr, meta, bufN = simulate(cfg, pmap)
    SIM_CACHE.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pickle.dumps((H, acc, meta, bufN)))
    return H, acc, wx, gr, meta, bufN


if __name__ == "__main__":
    import json
    import time

    import config
    import climate

    cases = {
        "thesis_air": config.thesis("air"),
        "thesis_air_croplead": config.with_(config.thesis("air"), name="thesis_air_croplead", climate=climate.crop_led(),
                                            legacy_aux_vent=False),
    }
    for nm in sys.argv[1:] or list(cases):
        t = time.time()
        H, acc, wx, gr, meta, _ = simulate(cases[nm])
        print(nm, f"{time.time() - t:.0f}s", json.dumps(summary(H, gr, meta), indent=1, default=float))
