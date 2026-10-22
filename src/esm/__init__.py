# -*- coding: utf-8 -*-
"""`esm` — the package half of the energy-system-modeling series.

Part 4 of the standard: `src/` is governed by Parts 1–2, `notebooks/` by Part 3,
and neither half gets to win on the other's territory. The notebooks build each
model by hand because that is the lesson; this package builds it once because
that is the code; and an agreement assertion at the end of each notebook is what
makes the deliberate duplication safe.

Every notebook in `notebooks/` carries an agreement assertion against one of the
modules here; `tools/check_notebooks.py` reports any that does not.

    from esm.data import table
    gens = table("generators.csv")
"""

__version__ = "0.1.0"

from esm.data import RAW_BASE, resolve, table  # noqa: F401

__all__ = ["table", "resolve", "RAW_BASE", "__version__"]
