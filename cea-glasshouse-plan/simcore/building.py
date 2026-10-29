"""ISO 13790 / ISO 52016-1 simple hourly 5R1C zone model."""
from dataclasses import dataclass


@dataclass
class Zone5R1C:
    A_f: float                 # conditioned floor area, m2
    H_tr_w: float              # window transmission, W/K
    H_tr_op: float             # opaque transmission, W/K
    C_m_per_m2: float = 165e3  # J/K/m2 (medium)
    A_m_factor: float = 2.5
    theta_m: float = 20.0

    def __post_init__(self):
        self.A_t = 4.5 * self.A_f
        self.A_m = self.A_m_factor * self.A_f
        self.C_m = self.C_m_per_m2 * self.A_f
        self.H_tr_is = 3.45 * self.A_t
        self.H_tr_ms = 9.1 * self.A_m
        self.H_tr_em = 1 / max(1e-9, 1 / self.H_tr_op - 1 / self.H_tr_ms)

    def _solve(self, T_e, T_sup, H_ve, phi_int, phi_sol, phi_hc, theta_m_prev):
        phi_ia = 0.5 * phi_int
        f = (0.5 * phi_int + phi_sol)
        phi_m = self.A_m / self.A_t * f
        phi_st = (1 - self.A_m / self.A_t - self.H_tr_w / (9.1 * self.A_t)) * f
        H1 = 1 / (1 / H_ve + 1 / self.H_tr_is)
        H2 = H1 + self.H_tr_w
        H3 = 1 / (1 / H2 + 1 / self.H_tr_ms)
        phi_mtot = phi_m + self.H_tr_em * T_e + H3 * (
            phi_st + self.H_tr_w * T_e + H1 * ((phi_ia + phi_hc) / H_ve + T_sup)) / H2
        c = self.C_m / 3600
        th_m_t = (theta_m_prev * (c - 0.5 * (H3 + self.H_tr_em)) + phi_mtot) / (c + 0.5 * (H3 + self.H_tr_em))
        th_m = 0.5 * (th_m_t + theta_m_prev)
        th_s = (self.H_tr_ms * th_m + phi_st + self.H_tr_w * T_e + H1 * (T_sup + (phi_ia + phi_hc) / H_ve)) \
            / (self.H_tr_ms + self.H_tr_w + H1)
        th_air = (self.H_tr_is * th_s + H_ve * T_sup + phi_ia + phi_hc) / (self.H_tr_is + H_ve)
        th_op = 0.3 * th_air + 0.7 * th_s
        return th_m_t, th_air, th_s, th_op

    def demand(self, T_e, H_ve, phi_int, phi_sol, set_heat, set_cool, T_sup=None):
        """Ideal heating (>0) / cooling (<0) load to hold the setpoints, W. Does not advance state."""
        T_sup = T_e if T_sup is None else T_sup
        _, t0, _, _ = self._solve(T_e, T_sup, H_ve, phi_int, phi_sol, 0.0, self.theta_m)
        if set_heat <= t0 <= set_cool:
            return 0.0, t0
        target = set_heat if t0 < set_heat else set_cool
        p10 = 10 * self.A_f
        _, t10, _, _ = self._solve(T_e, T_sup, H_ve, phi_int, phi_sol, p10, self.theta_m)
        return p10 * (target - t0) / (t10 - t0), t0

    def step(self, T_e, H_ve, phi_int, phi_sol, phi_hc, T_sup=None):
        """Apply phi_hc W for one hour and advance the thermal mass."""
        T_sup = T_e if T_sup is None else T_sup
        th_m_t, th_air, th_s, th_op = self._solve(T_e, T_sup, H_ve, phi_int, phi_sol, phi_hc, self.theta_m)
        self.theta_m = th_m_t
        return {"T_air": th_air, "T_surf": th_s, "T_mass": th_m_t, "T_op": th_op}
