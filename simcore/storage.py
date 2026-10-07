"""One-dimensional stratified sensible heat store (multi-node, upwind advection).

Charge stream enters at the top and leaves at the bottom; load stream is drawn
from the top and returned at the bottom. Conduction between nodes uses an
effective conductivity; temperature inversions are removed by mixing.
"""
import math

import numpy as np

CP = 4186.0
RHO = 985.0


class StratifiedTank:
    def __init__(self, volume_m3, height_m, nodes=12, U_wall=0.35, T_init=45.0, k_eff=1.5):
        self.N = nodes
        self.V = volume_m3
        self.H = height_m
        self.D = math.sqrt(4 * volume_m3 / (math.pi * height_m))
        self.A_x = math.pi * self.D ** 2 / 4
        dz = height_m / nodes
        self.dz = dz
        self.M = RHO * volume_m3 / nodes
        # wall area per node, top and bottom nodes carry the heads
        a_side = math.pi * self.D * dz
        self.UA = np.full(nodes, U_wall * a_side)
        self.UA[0] += U_wall * self.A_x
        self.UA[-1] += U_wall * self.A_x
        self.k_cond = k_eff * self.A_x / dz
        self.T = np.full(nodes, float(T_init))
        self.z = (np.arange(nodes)[::-1] + 0.5) * dz  # node centre height, index 0 = top

    def step(self, dt, m_c, T_c, m_l, T_l, T_amb, Q_c=None, dT_hx=0.0):
        """Advance dt seconds. Returns dict of energy flows (W, averaged) and outlet temps.

        If Q_c (W) is given the charge stream is a heater loop: it leaves the
        bottom node, gains Q_c (less nothing) and returns to the top, so the
        inlet temperature follows the tank every sub-step. dT_hx is the
        approach of an intermediate plate exchanger on that loop."""
        nsub = max(1, int(math.ceil(dt * max(m_c, m_l, 1e-9) / (0.4 * self.M))))
        nsub = max(nsub, int(math.ceil(dt * self.k_cond / (0.4 * self.M * CP))))
        h = dt / nsub
        T = self.T
        q_loss = q_c = q_l = 0.0
        T_top_sum = T_bot_sum = 0.0
        F = m_c - m_l  # net downward mass flow between nodes
        for _ in range(nsub):
            if Q_c is not None and m_c > 0:
                T_c = T[-1] + Q_c / (m_c * CP)
            dE = np.zeros(self.N)
            # boundary streams
            dE[0] += m_c * CP * T_c - m_l * CP * T[0]
            dE[-1] += m_l * CP * T_l - m_c * CP * T[-1]
            # internal advection
            if F > 0:
                flux = F * CP * T[:-1]
            else:
                flux = F * CP * T[1:]
            dE[:-1] -= flux
            dE[1:] += flux
            # conduction
            cond = self.k_cond * (T[:-1] - T[1:])
            dE[:-1] -= cond
            dE[1:] += cond
            loss = self.UA * (T - T_amb)
            dE -= loss
            T_top_sum += T[0]
            T_bot_sum += T[-1]
            q_c += m_c * CP * (T_c - T[-1])
            q_l += m_l * CP * (T[0] - T_l)
            q_loss += loss.sum()
            T = T + dE * h / (self.M * CP)
            # remove inversions (buoyant mixing)
            for _ in range(self.N):
                inv = np.where(T[1:] > T[:-1] + 1e-6)[0]
                if not len(inv):
                    break
                i = inv[0]
                T[i] = T[i + 1] = 0.5 * (T[i] + T[i + 1])
        self.T = T
        return {
            "Q_charge": q_c / nsub, "Q_load": q_l / nsub, "Q_loss": q_loss / nsub,
            "T_top_out": T_top_sum / nsub, "T_bot_out": T_bot_sum / nsub,
        }

    @property
    def energy_kwh(self):
        return float(np.sum(self.M * CP * self.T) / 3.6e6)

    def soc(self, T_cold, T_hot):
        return float(np.clip(np.mean((self.T - T_cold) / (T_hot - T_cold)), 0, 1))

    def mix_number(self):
        """MIX number (Andersen et al.): 0 perfectly stratified, 1 fully mixed."""
        T = self.T
        Tm = T.mean()
        E = self.M * CP
        zc = self.z
        M_E = np.sum(zc * E * (T - Tm))
        Ts = np.sort(T)[::-1]
        M_strat = np.sum(zc * E * (Ts - Tm))
        if abs(M_strat) < 1e-9:
            return 1.0
        return float(np.clip(1 - M_E / M_strat, 0, 1))
