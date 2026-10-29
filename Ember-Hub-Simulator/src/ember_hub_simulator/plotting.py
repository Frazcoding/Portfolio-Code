"""Matplotlib helpers: the ``fraser`` style (with a plain fallback) and SVG + PNG export."""
from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib.pyplot as plt


class PlotStyle:
    """Applies ``plt.style.use("fraser")``; figure sizes follow the style conventions (16 cm full, 7.8 cm half width)."""

    CM = 1 / 2.54
    FULL_W = 16 * CM
    HALF_W = 7.8 * CM
    OKABE_ITO = ("#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9", "#F0E442")

    @classmethod
    def apply(cls) -> None:
        try:
            plt.style.use("fraser")
        except OSError:
            warnings.warn("matplotlib style 'fraser' is not installed (run ~/.claude/plot-style/install.ps1); "
                          "using the default style", stacklevel=2)
        plt.rcParams["svg.fonttype"] = "none"   # keep text as text so Typst renders it in Segoe UI

    @staticmethod
    def save(fig, stem: Path) -> list[Path]:
        """Save ``<stem>.svg`` (vector, for documents) and ``<stem>.png`` (300 dpi, for slides/previews)."""
        stem = Path(stem)
        stem.parent.mkdir(parents=True, exist_ok=True)
        paths = []
        for ext in ("svg", "png"):
            p = stem.with_suffix(f".{ext}")
            fig.savefig(p, format=ext, dpi=300)
            paths.append(p)
        plt.close(fig)
        return paths
