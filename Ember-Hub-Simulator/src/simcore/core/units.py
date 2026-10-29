"""Unit conversions at the input/output edges. simcore computes in SI throughout."""
from __future__ import annotations

from .constants import Constants


class Units:
    """Conversions between SI and the engineering units used in inputs, plots and reports."""

    @staticmethod
    def C_to_K(T_C):
        return T_C + Constants.T_ZERO_C

    @staticmethod
    def K_to_C(T_K):
        return T_K - Constants.T_ZERO_C

    @staticmethod
    def bar_to_Pa(p_bar):
        return p_bar * 1e5

    @staticmethod
    def Pa_to_bar(p_Pa):
        return p_Pa / 1e5

    @staticmethod
    def W_to_kW(P_W):
        return P_W / 1e3

    @staticmethod
    def kW_to_W(P_kW):
        return P_kW * 1e3

    @staticmethod
    def J_to_kWh(E_J):
        return E_J / 3.6e6

    @staticmethod
    def kWh_to_J(E_kWh):
        return E_kWh * 3.6e6

    @staticmethod
    def J_to_kJ(x_J):
        return x_J / 1e3
