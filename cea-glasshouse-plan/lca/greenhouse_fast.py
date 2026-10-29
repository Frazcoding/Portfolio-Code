"""Numba-compiled version of greenhouse.simulate(): same physics, control and order of operations, one compiled loop.

greenhouse.simulate() stays the reference (thesis reproduction); tests/test_fast.py checks this version against it
month by month. Everything that is not per-hour arithmetic (weather, solar position, climate calendar, price shape,
performance map) is prepared in Python and passed in as arrays.

simulate_fast(cfg, pmap=None) returns the same (H, acc, wx, gr, meta, bufN) tuple as greenhouse.simulate().
"""
import math

import numpy as np
import pandas as pd
from numba import njit

import greenhouse as gh
from greenhouse import CP_A, CP_W, DT, H_FG, H_NAMES, PAR_PER_W, SPEEDS, SUB, build_map, grid, load_weather, solar

HI = {k: j for j, k in enumerate(H_NAMES)}
TANK_CP = 4186.0
_MEMO = {}      # per-process caches of inputs that do not depend on the design (sweeps call simulate_fast many times)


def _memo(key, fn):
    if key not in _MEMO:
        _MEMO[key] = fn()
    return _MEMO[key]


@njit(cache=True)
def _psat_w(T_c):
    if T_c >= 0:
        return 610.94 * math.exp(17.625 * T_c / (T_c + 243.04))
    return 611.21 * math.exp(22.587 * T_c / (T_c + 273.86))


@njit(cache=True)
def _w_sat(T_c):
    ps = _psat_w(T_c)
    return 0.62198 * ps / (101325.0 - ps)


@njit(cache=True)
def _clip(x, lo, hi):
    return min(max(x, lo), hi)


@njit(cache=True)
def _locate(ax, lens, pt, idx, w):
    for j in range(pt.shape[0]):
        L = lens[j]
        v = min(max(pt[j], ax[j, 0]), ax[j, L - 1])
        i = np.searchsorted(ax[j, :L], v) - 1
        i = min(max(i, 0), L - 2)
        idx[j] = i
        w[j] = (v - ax[j, i]) / (ax[j, i + 1] - ax[j, i])


@njit(cache=True)
def _interp(data2, strides, ax, lens, pt, k):
    """Multilinear interpolation, PerfMap.__call__ order (corners as itertools.product((0,1)), first axis most
    significant; weight product in axis order). k >= 0: one output; k < 0: all outputs."""
    nd = pt.shape[0]
    idx = np.empty(nd, np.int64)
    w = np.empty(nd)
    _locate(ax, lens, pt, idx, w)
    nk = data2.shape[1]
    out = np.zeros(nk if k < 0 else 1)
    for c in range(1 << nd):
        wt = 1.0
        flat = 0
        for j in range(nd):
            b = (c >> (nd - 1 - j)) & 1
            wt *= w[j] if b else (1 - w[j])
            flat += (idx[j] + b) * strides[j]
        if wt == 0:
            continue
        if k < 0:
            for q in range(nk):
                out[q] += wt * data2[flat, q]
        else:
            out[0] += wt * data2[flat, k]
    return out


@njit(cache=True)
def _tank_step(T, UA, M, k_cond, dt, m_c, T_c, m_l, T_l, T_amb, Q_c, has_q):
    N = T.shape[0]
    nsub = max(1, int(math.ceil(dt * max(m_c, m_l, 1e-9) / (0.4 * M))))
    nsub = max(nsub, int(math.ceil(dt * k_cond / (0.4 * M * TANK_CP))))
    h = dt / nsub
    F = m_c - m_l
    dE = np.empty(N)
    for _ in range(nsub):
        if has_q and m_c > 0:
            T_c = T[N - 1] + Q_c / (m_c * TANK_CP)
        for j in range(N):
            dE[j] = 0.0
        dE[0] += m_c * TANK_CP * T_c - m_l * TANK_CP * T[0]
        dE[N - 1] += m_l * TANK_CP * T_l - m_c * TANK_CP * T[N - 1]
        for j in range(N - 1):
            flux = F * TANK_CP * (T[j] if F > 0 else T[j + 1])
            dE[j] -= flux
            dE[j + 1] += flux
        for j in range(N - 1):
            cond = k_cond * (T[j] - T[j + 1])
            dE[j] -= cond
            dE[j + 1] += cond
        for j in range(N):
            dE[j] -= UA[j] * (T[j] - T_amb)
        for j in range(N):
            T[j] = T[j] + dE[j] * h / (M * TANK_CP)
        for _m in range(N):
            found = -1
            for j in range(N - 1):
                if T[j + 1] > T[j] + 1e-6:
                    found = j
                    break
            if found < 0:
                break
            T[found] = T[found + 1] = 0.5 * (T[found] + T[found + 1])


@njit(cache=True)
def _run(P, I, wxa, cal, data2, strides, ax, lens, kmap, speeds, T_tank, UA_tank, Hs, acc, bufN):
    """P: float params, I: int/bool params, wxa: hourly inputs (rows), cal: hourly setpoints (rows)."""
    n = wxa.shape[1]
    (A, VOL, A_WALL, A_ROOF, U_COVER, UA_WALL, screen_u, screen_below, infil, tau, hr_flow, hr_eff, hr_sfp, rh_vent,
     ramp, sup_base, sup_curve, t_sup_max, buf_min, hp_margin, shift_boost, m_pipe, m_charge, L_PIPE, K_PIPE, C_air,
     C_floor, C_pipe, M_air, G_floor, G_fb, U_b, UA_coil, co_set, co_approach, co_eer, Q_design, aux_base, aux_pump,
     aux_vent, aux_screen, s, ppfd, led_on_below, dli_target, radiant, led_off_above, lt_wpm2, ph0, ph1,
     field_ua, field_leak, field_T_far, field_cap, M_tank, k_cond_tank, T_set0, hc_rh_set, hc_band, hc_gap,
     hc_pipe_min, waste_T, floor_frac, tr_rad, tr_vpd, v_ach, v_ach_w, v_frac, v_cd, v_cw, v_h) = P
    (air, ground, hr_on, legacy, pump_vsd, ntank, hc_on, cov_u, soil_on) = I
    fr_cov = min(1.0, U_COVER * 0.10)   # ISO 6946 Rsi, upward heat flow
    kQc, kW, kQe, kTe, kwater = kmap[0], kmap[1], kmap[2], kmap[3], kmap[4]
    nd = lens.shape[0]
    pt = np.empty(nd)
    T_a, T_f, T_p = 18.0, 15.0, 30.0
    # GreenLight (Vanthoor 2011) floor and soil layers, used when soil_on
    sh = np.array([0.04, 0.08, 0.16, 0.32, 0.64])
    Ts = np.full(5, 15.0)
    cap_s = sh * 1.73e6 * A
    Cf_s = 0.02 * 2300.0 * 880.0 * A
    Gf1 = A * 2.0 / (0.02 / 1.7 + sh[0] / 0.85)
    Gk = A * 2.0 * 0.85 / (sh[:-1] + sh[1:])
    R_chain = 1.0 / (Gf1 / A)
    for kk in range(4):
        R_chain += 1.0 / (Gk[kk] / A)
    Gb = A / max(1.0 / U_b - R_chain, 0.05)
    fl_q = np.zeros(6)
    w_a = _w_sat(18.0) * 0.8
    integ = 0.0
    dli = 0.0
    T_set = T_set0
    on, off_t, frost, T_g, Q_e_prev, Q_rej = False, 1e9, 0.0, 11.0, 0.0, 0.0
    Q_cool_prev = 0.0
    NC = 20
    dtc = DT / 20
    e1 = 1 - math.exp(-1.0)
    for i in range(n):
        Ta, rh_o, w_o, ghi, wind, sky, cloud, T_b, T_river, hour_loc, cheap = (
            wxa[0, i], wxa[1, i], wxa[2, i], wxa[3, i], wxa[4, i], wxa[5, i], wxa[6, i], wxa[7, i], wxa[8, i],
            wxa[9, i], wxa[10, i] > 0.5)
        Tsoil = wxa[11, i]
        waste_w = wxa[13, i] * 1e3
        tr_rad_i, tr_vpd_i = wxa[14, i], wxa[15, i]
        floor_frac = wxa[16, i]
        day = ghi > 20
        T_cal = cal[0, i] if day else cal[1, i]
        T_vent_set = cal[2, i] if day else cal[3, i]
        T_set += _clip(T_cal - T_set, -ramp, ramp)
        screen = (not day) and Ta < screen_below
        U_roof = U_COVER * (screen_u if screen else 1.0) + 0.06 * wind
        UA_cov = UA_WALL + U_roof * A_ROOF
        I_in = wxa[12, i]
        if UA_coil != 0.0:
            T_coil = (T_g + Q_cool_prev / (7000.0 * s) if ground else T_river) + co_approach
        else:
            T_coil = 0.0
        par_nat = I_in * PAR_PER_W
        if hour_loc == 0:
            dli = 0.0
        led = (ppfd > 0 and ph0 <= hour_loc < ph1 and par_nat < led_on_below and dli < dli_target
               and T_a < led_off_above and wxa[17, i] > 0.5)
        P_led = lt_wpm2 * A if led else 0.0
        dli += (par_nat + (ppfd if led else 0.0)) * 3600 / 1e6
        I_in = I_in + radiant * P_led / A
        Q_led_conv = (1 - radiant) * P_led
        Hs[HW_LED, i], Hs[HPAR_NAT, i], Hs[HPAR_LED, i] = P_led / 1e3, par_nat, ppfd if led else 0.0
        for _s in range(SUB):
            err = T_set - T_a
            integ = _clip(integ + err * DT / 3600 * 6.0, -10.0, 60.0)
            base = sup_base + sup_curve * max(0.0, T_set - Ta)
            T_sup_req = _clip(base + 9.0 * err + integ, 22.0, t_sup_max) if (T_a < T_set + 1.5 or err > -1.0) else 22.0
            if hc_on and not hr_on:
                rh_now = min(100.0, 100 * (w_a * 101325 / (0.62198 + w_a)) / _psat_w(T_a))
                h_sub = _clip((rh_now - hc_rh_set) / hc_band, 0.0, 1.0)
                if h_sub > 0:
                    T_sup_req = max(T_sup_req, 25.0 + (hc_pipe_min - 25.0) * h_sub)
            T_top = T_tank[0]
            heating = T_sup_req > 25
            T_sup = min(T_sup_req, T_top) if heating else T_p
            aQp = aQcov = aQv = aQf = aQs = aLE = aE = acond = aQin = avent = aach = aQcs = amcc = afan = 0.0
            for _c in range(NC):
                pv_a = w_a * 101325 / (0.62198 + w_a)
                rh_in = min(100.0, 100 * pv_a / _psat_w(T_a))
                vent = _clip((T_a - T_vent_set) / 4.0, 0.0, 1.0)
                if hc_on:
                    hum = _clip((rh_in - hc_rh_set) / hc_band, 0.0, 1.0)
                else:
                    hum = _clip((rh_in - rh_vent) / 10.0, 0.0, 1.0)
                if hr_on:
                    m_hr = hum * hr_flow * A * 1.2 / 3600
                else:
                    m_hr = 0.0
                    vent = max(vent, hum * (hc_gap if hc_on else 0.12))
                if v_frac > 0:   # Vanthoor (2011) roof-vent law, per m2 floor -> air changes per hour
                    f_v = v_frac * v_cd / 2 * math.sqrt(abs(9.81 * v_h * (T_a - Ta) / (2 * (0.5 * T_a + 0.5 * Ta + 273.15))
                                                            + v_cw * wind ** 2))
                    ach_vent = f_v * 3600.0 * A / VOL
                else:
                    ach_vent = v_ach + v_ach_w * wind
                ach = (infil + 0.05 * wind) * (0.7 if screen else 1.0) + vent * ach_vent
                m_nat = ach * VOL * 1.2 / 3600
                m_ex = m_nat + m_hr
                m_th = m_nat + m_hr * (1 - hr_eff)
                ach += m_hr * 3600 / (VOL * 1.2)
                afan += m_hr / 1.2 * hr_sfp / NC
                Q_pipe = K_PIPE * L_PIPE * max(T_p - T_a, 0.0) ** 1.25
                Q_in = m_pipe * CP_W * max(T_sup - T_p, 0.0) * e1 if heating else 0.0
                vpd = max(0.0, _psat_w(T_a) - pv_a) / 1000
                LE = (tr_rad_i * I_in * 0.7 + tr_vpd_i * vpd) * A
                E = LE / H_FG
                if cov_u:
                    T_cov = T_a - fr_cov * (T_a - Ta) - (1 - cloud) * 1.5 * fr_cov / 0.65
                else:
                    T_cov = Ta + 0.35 * (T_a - Ta) - (1 - cloud) * 1.5
                cond = max(0.0, 0.0028 * (A_WALL + A_ROOF) * (w_a - _w_sat(T_cov)))
                rad = 0.15 * A_ROOF * (0.4 if screen else 1.0)
                Q_cover = UA_cov * (T_a - Ta) + rad * (T_a - sky)
                Q_vent = m_th * CP_A * (T_a - Ta)
                Q_floor = G_floor * (T_f - T_a)
                Q_sol_air = (1.0 - floor_frac) * I_in * A
                G = UA_cov + rad + m_th * CP_A + G_floor
                if UA_coil != 0.0:
                    ua = UA_coil * _clip((T_a - co_set) / 2.0, 0.0, 1.0) if T_a > T_coil else 0.0
                    m_cc = ua / CP_A * max(0.0, w_a - _w_sat(T_coil))
                    G += ua
                else:
                    ua = 0.0
                    m_cc = 0.0
                src = Q_pipe + Q_sol_air - LE + G_floor * T_f + 0.5 * cond * H_FG + (UA_cov + m_th * CP_A) * Ta \
                    + rad * sky + Q_led_conv + ua * T_coil
                T_a = (T_a * C_air / dtc + src) / (C_air / dtc + G)
                if soil_on:
                    T_f = (T_f * Cf_s / dtc + floor_frac * I_in * A + G_floor * T_a + Gf1 * Ts[0]) / (Cf_s / dtc + G_floor + Gf1)
                    fl_q[0] = Gf1 * (T_f - Ts[0])
                    for kk in range(4):
                        fl_q[kk + 1] = Gk[kk] * (Ts[kk] - Ts[kk + 1])
                    fl_q[5] = Gb * (Ts[4] - T_b)
                    for kk in range(5):
                        Ts[kk] += dtc * (fl_q[kk] - fl_q[kk + 1]) / cap_s[kk]
                else:
                    T_f = (T_f * C_floor / dtc + floor_frac * I_in * A + G_floor * T_a + U_b * A * T_b) / (C_floor / dtc + G_fb)
                T_p += (Q_in - Q_pipe) * dtc / C_pipe
                w_a = (w_a * M_air / dtc + E - cond - m_cc + m_ex * w_o) / (M_air / dtc + m_ex)
                w_a = _clip(w_a, 0.0005, _w_sat(T_a))
                aQp += Q_pipe / NC
                aQcov += Q_cover / NC
                aQv += Q_vent / NC
                aQf += -Q_floor / NC
                aQs += Q_sol_air / NC
                aLE += LE / NC
                aE += E / NC
                acond += cond / NC
                aQin += Q_in / NC
                avent += vent / NC
                aach += ach / NC
                aQcs += ua * (T_a - T_coil) / NC
                amcc += m_cc / NC
            Q_floor = -aQf
            T_ret = T_p - 2.0
            m_draw = aQin / (CP_W * max(T_top - T_ret, 1.0)) if aQin > 0 else 0.0
            Q_cool = aQcs + amcc * H_FG
            W_cool = Q_cool / co_eer if Q_cool > 0 else 0.0
            Q_rej = Q_cool if ground else 0.0
            # ---- heat supply (HeatPumpSupply.step)
            T_src = Ta if air else (T_g - Q_e_prev / (field_ua * s) if ground else T_river - 1.5)
            boost = shift_boost if (cheap and shift_boost > 0 and Ta < 15.0) else 0.0
            floor_ = max(T_sup_req, buf_min) + boost
            want = T_tank[3] < floor_ + 1.0 or (on and T_tank[ntank - 1] < floor_ + hp_margin - 1.0)
            if T_sup_req <= 25 and T_tank[3] > buf_min and not boost:
                want = False
            Q_w = 0.0
            if waste_w > 0:
                if T_tank[3] < max(T_sup_req, buf_min) + hp_margin and T_tank[ntank - 1] < waste_T - 5.0:
                    Q_w = waste_w
            if Q_w >= Q_design or (Q_w > 0 and T_tank[3] >= max(T_sup_req, buf_min) - (0.0 if on else 2.0)):
                want = False
            if (not on) and want and off_t >= DT:
                on = True
                Hs[HSTARTS, i] += 1
            elif on and not want:
                on = False
                off_t = 0.0
            Q_c = W_c = Q_e = 0.0
            if on:
                T_in = T_tank[ntank - 1]
                T_target = floor_ + hp_margin
                Q_target = m_pipe * CP_W * max(T_target - T_in, 1.0) * 0.6 / s
                uaf = max(0.5, 1 - 0.5 * min(frost / 24.0, 1.0))
                if air:
                    pt[0], pt[1], pt[2], pt[4] = Ta, rh_o, T_in, uaf
                    fi = 3
                else:
                    pt[0], pt[1] = T_src, T_in
                    fi = 2
                qs = np.empty(speeds.shape[0])
                for q in range(speeds.shape[0]):
                    pt[fi] = speeds[q]
                    qs[q] = _interp(data2, strides, ax, lens, pt, kQc)[0] * 1e3
                f_cmd = np.interp(Q_target, qs, speeds) if Q_target < qs[-1] else speeds[-1]
                f_cmd = max(speeds[0], f_cmd)
                pt[fi] = f_cmd
                vec = _interp(data2, strides, ax, lens, pt, -1)
                Q_c = vec[kQc] * 1e3
                W_c = vec[kW] * 1e3
                Q_e = vec[kQe] * 1e3
                frac = 1.0
                if air:
                    water = vec[kwater]
                    if vec[kTe] + 1.5 < 0 and water > 0:
                        frost += water * DT
                    if frost >= 14.0:
                        E_def = frost * 338e3 + 2.0e6
                        Hs[HDEFROSTS, i] += 1
                        Hs[HQ_DEF, i] += s * 0.75 * E_def / 3.6e6
                        for j in range(ntank):
                            T_tank[j] -= s * 0.75 * E_def / (M_tank * CP_W * ntank)
                        W_c += 0.25 * E_def / DT
                        frac = 1 - min(DT, 180 + E_def / 30e3) / DT
                        frost = 0.0
                for q in range(vec.shape[0]):
                    acc[q, i] += vec[q] * frac
                Hs[HON_FRAC, i] += frac / SUB
                Hs[HF_CMD, i] += f_cmd * frac / SUB
                Q_c *= frac * s
                W_c *= s
                Q_e *= frac * s
            else:
                off_t += DT
                if air and Ta > 2:
                    frost = max(0.0, frost - 0.003 * (Ta - 2) * DT)
            if ground:
                T_g += (field_leak * s * (field_T_far - T_g) - Q_e + Q_rej) * DT / (field_cap * s)
            Q_e_prev = Q_e
            Q_tot = Q_c + Q_w
            _tank_step(T_tank, UA_tank, M_tank, k_cond_tank, DT, m_charge if Q_tot > 0 else 0.0, 0.0, m_draw, T_ret,
                       15.0, Q_tot, Q_tot > 0)
            Hs[HQ_WASTE, i] += Q_w / 1e3 / SUB
            venting = avent > 0.02
            if legacy:
                W_aux = 150.0 + (1200.0 if aQin > 0 else 0.0) + (1.0 if 900.0 * avent > 0.02 else 0.0) \
                    + (60.0 if screen else 0)
            else:
                pump = 0.0
                if aQin > 0:
                    pump = aux_pump * (max(0.15, min(1.0, aQin / Q_design)) ** 3 if pump_vsd else 1.0)
                W_aux = A * (aux_base + pump + (aux_vent if venting else 0.0) + (aux_screen if screen else 0.0)) + afan
            Hs[HQ_PIPE, i] += aQp / 1e3 / SUB
            Hs[HQ_COVER, i] += aQcov / 1e3 / SUB
            Hs[HQ_VENT, i] += aQv / 1e3 / SUB
            Hs[HQ_FLOOR, i] += -Q_floor / 1e3 / SUB
            Hs[HQ_SOL, i] += aQs / 1e3 / SUB
            Hs[HLE, i] += aLE / 1e3 / SUB
            Hs[HQ_C, i] += Q_c / 1e3 / SUB
            Hs[HQ_E, i] += Q_e / 1e3 / SUB
            Hs[HW_COMP, i] += W_c / 1e3 / SUB
            Hs[HW_AUX, i] += W_aux / 1e3 / SUB
            Hs[HW_TOTAL, i] += (W_c + W_aux + P_led + W_cool) / 1e3 / SUB
            Hs[HQ_COOL, i] += Q_cool / 1e3 / SUB
            Hs[HW_COOL, i] += W_cool / 1e3 / SUB
            Hs[HTRANS, i] += aE * DT
            Hs[HCOND, i] += acond * DT
            Hs[HVENT, i] += avent * 100 / SUB
            Hs[HACH, i] += aach / SUB
            Hs[HT_SUP, i] += T_sup / SUB
            Hs[HT_AIR_MEAN, i] += T_a / SUB
            Hs[HCOOL_COND, i] += amcc * DT
            Hs[HQ_BELOW, i] += (Gb * (T_b - Ts[4]) if soil_on else U_b * A * (T_b - T_f)) / 1e3 / SUB
        Hs[HT_AIR_IN, i], Hs[HT_FLOOR, i], Hs[HT_PIPE, i] = T_a, T_f, T_p
        Hs[HT_SET, i] = T_set
        Hs[HT_COIL, i] = T_coil
        Q_cool_prev = Hs[HQ_COOL, i] * 1e3
        Hs[HRH_IN, i] = min(100.0, 100 * w_a * 101325 / (0.62198 + w_a) / _psat_w(T_a))
        Hs[HVPD, i] = max(0.0, _psat_w(T_a) - w_a * 101325 / (0.62198 + w_a)) / 1000
        Hs[HSCREEN, i] = 100.0 if screen else 0.0
        Hs[HFROST, i] = frost
        Hs[HT_SRC, i] = Ta if air else (T_g - Q_e_prev / (field_ua * s) if ground else T_river - 1.5)
        Hs[HT_GROUND, i] = T_g if ground else (T_river if not air else Tsoil)
        Hs[HUNMET, i] = max(0.0, T_set - 1.0 - T_a)
        m = 0.0
        for j in range(ntank):
            m += (T_tank[j] - 25.0) / (70.0 - 25.0)
        Hs[HBUF_SOC, i] = _clip(m / ntank, 0.0, 1.0) * 100
        for j in range(ntank):
            bufN[i, j] = T_tank[j]
        if Hs[HON_FRAC, i] > 0:
            for q in range(acc.shape[0]):
                acc[q, i] /= Hs[HON_FRAC, i] * SUB
            Hs[HF_CMD, i] /= Hs[HON_FRAC, i]
    return T_g


# column indices into Hs (module-level constants are frozen into the compiled function)
for _k, _j in HI.items():
    globals()["H" + _k.upper()] = _j
HPAR_NAT, HPAR_LED, HW_LED = HI["PAR_nat"], HI["PAR_led"], HI["W_led"]
HTRANS, HCOND, HCOOL_COND = HI["trans_kg"], HI["cond_kg"], HI["cool_cond_kg"]


def simulate_fast(cfg, pmap=None, i_floor=None, t_source=None, waste_kw=None):
    """i_floor: hourly light transmitted to the floor (W/m2 floor) from design.analyse(); None = tau x GHI."""
    g, e, loc, cl, hy, heat = cfg.geometry, cfg.envelope, cfg.location, cfg.climate, cfg.hydronics, cfg.heat
    A, VOL, A_WALL, A_ROOF = g.area, g.volume, g.a_wall, g.a_roof
    rooftop = loc.form == "rooftop"
    wx, (lat, lon) = _memo(("wx", loc.site, loc.lat, loc.lon), lambda: load_weather(loc))
    gr = _memo("grid", grid.load)
    n = len(wx)
    doy_all = _memo(("doy", loc.site, lat, lon), lambda: np.asarray(solar.position(wx["time"], lat, lon)[2]))
    Ta_all = wx["T_amb"].to_numpy()
    wind = wx["wind10"].to_numpy()
    if rooftop:
        z = loc.roof_height_m + g.gutter_height
        wind = wind * math.log(z / loc.z0_m) / math.log(10.0 / loc.z0_m)
    T7 = pd.Series(Ta_all).rolling(24 * 7, min_periods=1).mean().to_numpy()
    T_river = np.maximum(1.5, 0.85 * T7 + 2.2)
    if t_source is not None:
        T_river = np.asarray(t_source, float)[:n] + 1.5
    U_b = cfg.u_floor_below()
    T_b_all = np.full(n, loc.t_building_C) if rooftop else wx["T_soil_2m"].to_numpy()
    price = gr.price.to_numpy()
    cheap = _memo(("cheap", hy.shift_quantile), lambda: (price <= pd.Series(price).groupby(
        np.arange(len(price)) // 24).transform(lambda x: x.quantile(hy.shift_quantile)).to_numpy()).astype(float))
    wxa = np.vstack([Ta_all, wx["RH"].to_numpy(), wx["w_amb"].to_numpy(), wx["ghi"].to_numpy(), wind,
                     wx["T_sky"].to_numpy(), wx["cloud"].to_numpy() / 100, T_b_all, T_river,
                     wx["hour_local"].to_numpy().astype(float), cheap[:n], wx["T_soil_2m"].to_numpy(),
                     e.tau_solar * wx["ghi"].to_numpy() if i_floor is None else np.asarray(i_floor)[:n],
                     np.zeros(n) if waste_kw is None else np.asarray(waste_kw, float)[:n],
                     np.full(n, e.transp_rad) if e.transp_hourly is None else np.asarray(e.transp_hourly[0], float)[:n],
                     np.full(n, e.transp_vpd) if e.transp_hourly is None else np.asarray(e.transp_hourly[1], float)[:n],
                     np.full(n, e.floor_sol_frac) if e.floor_frac_hourly is None else np.asarray(e.floor_frac_hourly, float)[:n],
                     np.ones(n) if cfg.lighting.allow_hourly is None else np.asarray(cfg.lighting.allow_hourly, float)[:n]]).astype(float)
    cal = np.empty((4, n))
    for i in range(n):
        d = int(doy_all[i])
        cal[0, i], cal[2, i] = cl.at(d, True)
        cal[1, i], cal[3, i] = cl.at(d, False)

    s = cfg.hp_scale()
    if pmap is None:
        pmap = _memo(("pmap", heat.cycle, heat.source, heat.hx_scale), lambda: build_map(heat))
    air = heat.source == "air"
    names = list(pmap.names)
    want = ["T_air", "RH", "T_w_in", "f", "ua"] if air else ["T_src_in", "T_w_in", "f"]
    if names != want:
        raise ValueError(f"unexpected map axes {names}")
    shape = pmap.data.shape
    nk = shape[-1]
    data2 = np.ascontiguousarray(pmap.data.reshape(-1, nk))
    strides = np.array([int(np.prod(shape[j + 1:-1])) for j in range(len(names))], np.int64)
    lens = np.array([len(pmap.axes[k]) for k in names], np.int64)
    ax = np.zeros((len(names), int(lens.max())))
    for j, k in enumerate(names):
        ax[j, :lens[j]] = pmap.axes[k]
    ki = pmap.kidx
    kmap = np.array([ki["Q_c"], ki["W_tot"], ki["Q_e"], ki.get("Te", 0), ki.get("water", 0)], np.int64)

    v_buf, h_buf = hy.buffer(A)
    tank = gh.StratifiedTank(v_buf, h_buf, nodes=10, U_wall=0.35, T_init=45.0)
    co, lt, hr = cfg.cooling, cfg.lighting, cfg.hrd
    if co.enabled and air:
        raise ValueError("semi-closed cooling needs a ground or river source to take the heat")
    L_PIPE = hy.pipe_m_per_m2 * A
    m_pipe = hy.m_pipe_per_m2 * A
    P = (A, VOL, A_WALL, A_ROOF, e.u_cover, e.wall_ua(g), e.screen_u_factor, e.screen_below_C, e.infiltration_ach,
         e.tau_solar, hr.flow_m3_m2_h, hr.effectiveness, hr.sfp_w_per_m3s, cl.rh_vent_start, cl.ramp_K_per_h,
         hy.sup_base_C, hy.sup_curve_K_per_K, hy.t_sup_max, hy.buf_min_C, hy.hp_margin_K, hy.shift_boost_K, m_pipe,
         m_pipe if heat.charge_m_w is None else heat.charge_m_w * s, L_PIPE, hy.k_pipe,
         1.2 * 1006 * VOL + A * 3 * 1500, A * 0.15 * 2.0e6, hy.c_pipe_per_m * L_PIPE, 1.2 * VOL, 6.0 * A,
         6.0 * A + U_b * A, U_b, co.ua_w_m2K * A if co.enabled else 0.0, co.set_C, co.approach_K, co.eer,
         cfg.design_heat_loss_w(), hy.aux_base_w_m2, hy.aux_pump_w_m2, hy.aux_vent_w_m2, hy.aux_screen_w_m2, s,
         lt.ppfd, lt.on_below_par, lt.dli_target, lt.radiant_frac, lt.off_above_C, lt.w_per_m2,
         float(lt.photoperiod[0]), float(lt.photoperiod[1]), heat.field_ua_w_K, heat.field_leak_w_K,
         heat.field_T_far_C, heat.field_cap_J_K, tank.M, tank.k_cond, cl.at(int(doy_all[0]), wxa[3, 0] > 20)[0],
         cfg.hum.rh_set, cfg.hum.band, cfg.hum.vent_gap, cfg.hum.pipe_min_C, heat.waste_T_C, e.floor_sol_frac, e.transp_rad, e.transp_vpd, e.vent_ach, e.vent_ach_wind,
         e.vent_area_frac, e.vent_cd, e.vent_cw, e.vent_h)
    P = tuple(float(x) for x in P)
    I = (air, heat.source == "ground", hr.enabled, cfg.legacy_aux_vent, hy.pump_vsd, tank.N, cfg.hum.enabled,
         e.cover_t_from_u, e.soil_layers)
    Hs = np.zeros((len(H_NAMES), n))
    acc = np.zeros((nk, n))
    bufN = np.zeros((n, tank.N))
    T_tank = tank.T.copy()
    _run(P, I, wxa, cal, data2, strides, ax, lens, kmap, np.asarray(SPEEDS, float), T_tank, tank.UA.copy(),
               Hs, acc, bufN)
    H = {k: Hs[j] for k, j in HI.items()}
    accd = {k: acc[j] for j, k in enumerate(pmap.out_keys)}
    meta = dict(name=cfg.name, area_m2=A, u_floor=U_b, volume_m3=VOL, a_wall_m2=A_WALL, a_roof_m2=A_ROOF, hp_scale=s,
                design_heat_loss_kw=cfg.design_heat_loss_w() / 1e3, buffer_m3=v_buf, pipe_m=L_PIPE, form=loc.form,
                site=loc.site, lat=lat, lon=lon, climate=cl.name, source=heat.source)
    return H, accd, wx, gr, meta, bufN
