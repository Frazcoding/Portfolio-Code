"""Render registered equations for notebooks and documents (one equation per cell)."""
from __future__ import annotations

from typing import Any, Callable

from .equation import EquationInfo


class EquationDisplay:
    """Markdown/LaTeX rendering of an equation's registry record (equation, symbols, validity, source)."""

    @staticmethod
    def info(eq: Callable | EquationInfo) -> EquationInfo:
        if isinstance(eq, EquationInfo):
            return eq
        info = getattr(eq, "__equation__", None)
        if info is None:
            raise TypeError(f"{eq!r} is not decorated with @Equation")
        return info

    @classmethod
    def markdown(cls, eq: Callable | EquationInfo, title: str | None = None) -> str:
        e = cls.info(eq)
        name = title or e.qualname.rsplit(".", 2)[-2] + "." + e.qualname.rsplit(".", 1)[-1]
        lines = [f"**{name}**", "", f"$$ {e.latex} $$", ""]
        if e.symbols:
            lines += ["| Symbol | Meaning [unit] |", "|---|---|"]
            lines += [f"| ${s}$ | {d} |" for s, d in e.symbols.items()]
            lines.append("")
        if e.valid:
            lines.append("Validity: " + "; ".join(f"`{a}` ∈ {r}" for a, r in e.valid.items()))
            lines.append("")
        lines.append(f"Source: {e.source}")
        if e.notes:
            lines += ["", f"_Note: {e.notes}_"]
        lines += ["", f"Code: `{e.qualname}`"]
        return "\n".join(lines)

    @classmethod
    def show(cls, eq: Callable | EquationInfo, title: str | None = None) -> Any:
        """Display in Jupyter (falls back to returning the Markdown string outside IPython)."""
        md = cls.markdown(eq, title)
        try:
            from IPython.display import Markdown, display
        except ImportError:
            return md
        display(Markdown(md))
        return None
