"""simcore — verified physics and simulation library.

Every equation is a method decorated with :class:`simcore.core.Equation`, carrying its LaTeX form, source and
validity ranges; ``Equation.all()`` lists them. Units are SI throughout (K, Pa, W, J, kg, s); convert at the edges
with :class:`simcore.core.Units`.
"""
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("simcore")
except PackageNotFoundError:  # vendored inside standalone repository
    __version__ = "1.0.0.dev0"
