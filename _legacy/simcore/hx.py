"""Heat exchanger and psychrometric helpers (effectiveness-NTU)."""
import math

CP_W = 4186.0   # J/kg/K, water
CP_A = 1006.0   # J/kg/K, dry air
CP_V = 1860.0   # J/kg/K, water vapour
H_FG = 2501e3   # J/kg
H_SF = 333.5e3  # J/kg, ice fusion


def eps_phase_change(ntu):
    return 1 - math.exp(-ntu)


def eps_counterflow(ntu, cr):
    if cr < 1e-6:
        return 1 - math.exp(-ntu)
    if abs(cr - 1) < 1e-6:
        return ntu / (1 + ntu)
    e = math.exp(-ntu * (1 - cr))
    return (1 - e) / (1 - cr * e)


def eps_crossflow_unmixed(ntu, cr):
    if cr < 1e-6:
        return 1 - math.exp(-ntu)
    return 1 - math.exp(ntu ** 0.22 / cr * (math.exp(-cr * ntu ** 0.78) - 1))


def psat_w(T_c):
    """Saturation vapour pressure of water over liquid/ice, Pa (Magnus)."""
    if T_c >= 0:
        return 610.94 * math.exp(17.625 * T_c / (T_c + 243.04))
    return 611.21 * math.exp(22.587 * T_c / (T_c + 273.86))


def w_sat(T_c, p=101325.0):
    ps = psat_w(T_c)
    return 0.62198 * ps / (p - ps)


def h_air(T_c, w):
    return CP_A * T_c + w * (H_FG + CP_V * T_c)


def rh_from_w(T_c, w, p=101325.0):
    pv = w * p / (0.62198 + w)
    return min(100.0, 100 * pv / psat_w(T_c))


def T_from_h_w(h, w):
    return (h - w * H_FG) / (CP_A + w * CP_V)


def coil_cooling(T_in, w_in, m_air, UA, T_ref, p=101325.0):
    """Air-side duty of a refrigerant evaporator coil at mean refrigerant temperature T_ref.

    Sensible heat follows the dry effectiveness to the refrigerant. Moisture
    transfer follows the Lewis analogy with the same effectiveness, driven by
    the humidity difference to saturation at the mean fin/tube surface
    temperature; below 0 C the deposit is frost (sublimation enthalpy).
    Returns duty W, outlet T, outlet w, condensate/frost kg/s and sensible heat ratio.
    """
    cpm = CP_A + w_in * CP_V
    ntu = UA / (m_air * cpm)
    eps = 1 - math.exp(-ntu)
    q_sens = eps * m_air * cpm * (T_in - T_ref)
    T_out = T_in - q_sens / (m_air * cpm)
    # Mean fin/tube surface temperature: the refrigerant-side film and fin
    # conduction carry roughly 35 % of the total air-to-refrigerant resistance.
    T_surf = T_ref + 0.35 * (T_in - T_ref)
    ws = w_sat(T_surf, p)
    if ws < w_in:
        water = eps * m_air * (w_in - ws)
        h_phase = H_FG + (H_SF if T_surf < 0 else 0.0)
        q_lat = water * h_phase
        w_out = w_in - water / m_air
        return q_sens + q_lat, T_out, w_out, water, q_sens / (q_sens + q_lat)
    return q_sens, T_out, w_in, 0.0, 1.0


def water_hx_outlet(T_in, m, Q):
    return T_in + Q / (m * CP_W)
