from pathlib import Path

import jupytext
import nbformat
import pytest
from nbclient import NotebookClient

NOTEBOOKS = sorted((Path(__file__).resolve().parents[1] / "notebooks").glob("*.py"))


@pytest.mark.notebook
@pytest.mark.parametrize("script", NOTEBOOKS, ids=lambda p: p.name)
def test_notebook_executes(script):
    """Convert the Jupytext script and execute every cell in a fresh kernel; any cell error fails the test."""
    nb = jupytext.read(script)
    NotebookClient(nb, timeout=600, kernel_name="python3", resources={"metadata": {"path": str(script.parent)}}).execute()
    errors = [o for c in nb.cells if c.cell_type == "code" for o in c.get("outputs", []) if o.output_type == "error"]
    assert not errors
    nbformat.validate(nb)
