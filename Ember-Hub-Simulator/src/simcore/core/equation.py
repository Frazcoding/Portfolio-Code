"""Equation metadata and validity-range enforcement.

Every physics equation in simcore is a method decorated with :class:`Equation`. The decorator

* records the equation (LaTeX, symbols with units, source, validity ranges) in a registry that the
  analysis notebook and ``docs/THEORY.md`` are built from, and
* checks the named inputs against their validity ranges on every call.

Out-of-range inputs are handled by the global :class:`Validity` policy: ``"warn"`` (default; emits
:class:`RangeWarning`, which the test suite promotes to an error), ``"raise"`` (:class:`RangeError`) or
``"ignore"``. Solvers that probe outside the range while iterating should wrap the iteration in
``with Validity.policy("ignore"):`` and check the converged result instead.
"""
from __future__ import annotations

import functools
import inspect
import warnings
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, ClassVar

import numpy as np


class RangeWarning(UserWarning):
    """An equation was evaluated outside its stated validity range."""


class RangeError(ValueError):
    """An equation was evaluated outside its stated validity range (policy ``"raise"``)."""


@dataclass(frozen=True)
class Range:
    """Closed validity interval ``lo <= x <= hi`` for one argument; ``None`` means unbounded."""

    lo: float | None = None
    hi: float | None = None
    unit: str = ""

    def contains(self, value: Any) -> bool:
        if isinstance(value, (int, float)):
            lo_v = hi_v = value
        else:
            arr = np.asarray(value, dtype=float)
            if arr.size == 0 or np.all(np.isnan(arr)):
                return True
            lo_v, hi_v = np.nanmin(arr), np.nanmax(arr)
        if lo_v != lo_v:  # NaN scalar: nothing to check
            return True
        return (self.lo is None or lo_v >= self.lo) and (self.hi is None or hi_v <= self.hi)

    def __str__(self) -> str:
        lo = "-inf" if self.lo is None else f"{self.lo:g}"
        hi = "+inf" if self.hi is None else f"{self.hi:g}"
        return f"[{lo}, {hi}] {self.unit}".strip()


@dataclass(frozen=True)
class EquationInfo:
    """Registry record for one equation."""

    qualname: str
    latex: str
    source: str
    symbols: dict[str, str] = field(default_factory=dict)
    valid: dict[str, Range] = field(default_factory=dict)
    notes: str = ""

    @property
    def module(self) -> str:
        return self.qualname.rsplit(".", 2)[0]


class Validity:
    """Global policy for out-of-range inputs: ``"warn"``, ``"raise"`` or ``"ignore"``."""

    _policy: ClassVar[str] = "warn"
    _POLICIES: ClassVar[tuple[str, ...]] = ("warn", "raise", "ignore")

    @classmethod
    def set_policy(cls, policy: str) -> None:
        if policy not in cls._POLICIES:
            raise ValueError(f"policy must be one of {cls._POLICIES}, got {policy!r}")
        cls._policy = policy

    @classmethod
    def get_policy(cls) -> str:
        return cls._policy

    @classmethod
    @contextmanager
    def policy(cls, policy: str):
        """Temporarily change the policy, e.g. ``with Validity.policy("ignore"):`` inside a solver."""
        old = cls._policy
        cls.set_policy(policy)
        try:
            yield
        finally:
            cls._policy = old

    @classmethod
    def report(cls, qualname: str, arg: str, value: Any, rng: Range) -> None:
        if cls._policy == "ignore":
            return
        shown = value if isinstance(value, (int, float)) else f"array spanning [{np.nanmin(value):g}, {np.nanmax(value):g}]"
        msg = f"{qualname}: {arg}={shown} outside validity range {rng}"
        if cls._policy == "raise":
            raise RangeError(msg)
        warnings.warn(msg, RangeWarning, stacklevel=4)


class Equation:
    """Decorator that registers an equation and enforces its validity ranges.

    Usage (always innermost, under ``@staticmethod`` / ``@classmethod``)::

        class Psychrometrics:
            @staticmethod
            @Equation(
                latex=r"p_{ws} = 610.94\\,\\exp\\left(\\frac{17.625\\,t}{t + 243.04}\\right)",
                source="Alduchov & Eskridge (1996), J. Appl. Meteor. 35, eq. 21 (AERK)",
                symbols={"p_{ws}": "saturation vapour pressure [Pa]", "t": "temperature [°C]"},
                valid={"T_K": Range(233.15, 323.15, "K")},
            )
            def saturation_pressure(T_K: float) -> float: ...
    """

    registry: ClassVar[dict[str, EquationInfo]] = {}

    def __init__(
        self,
        latex: str,
        source: str,
        symbols: dict[str, str] | None = None,
        valid: dict[str, Range] | None = None,
        notes: str = "",
    ) -> None:
        if not latex or not source:
            raise ValueError("every equation needs both `latex` and `source`")
        self.latex = latex
        self.source = source
        self.symbols = symbols or {}
        self.valid = valid or {}
        self.notes = notes

    def __call__(self, fn: Callable) -> Callable:
        qualname = f"{fn.__module__}.{fn.__qualname__}"
        params = list(inspect.signature(fn).parameters)
        unknown = set(self.valid) - set(params)
        if unknown:
            raise TypeError(f"{qualname}: validity ranges for unknown arguments {sorted(unknown)}")
        # Pre-compute argument positions so the per-call check stays cheap in hourly loops.
        checks = [(name, params.index(name), rng) for name, rng in self.valid.items()]
        info = EquationInfo(qualname, self.latex, self.source, dict(self.symbols), dict(self.valid), self.notes)
        Equation.registry[qualname] = info

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if Validity._policy != "ignore":
                for name, pos, rng in checks:
                    if name in kwargs:
                        value = kwargs[name]
                    elif pos < len(args):
                        value = args[pos]
                    else:
                        continue  # default value: assumed valid by construction
                    if not rng.contains(value):
                        Validity.report(qualname, name, value, rng)
            return fn(*args, **kwargs)

        wrapper.__equation__ = info
        return wrapper

    @classmethod
    def all(cls, module_prefix: str = "simcore") -> list[EquationInfo]:
        """Registered equations, in definition order, optionally filtered by module prefix."""
        return [e for q, e in cls.registry.items() if q.startswith(module_prefix)]
