# -*- coding: utf-8 -*-
"""`esm` — the package half of the energy-system-modeling series.

Part 4 of the standard: `src/` is governed by Parts 1–2, `notebooks/` by Part 3,
and neither half gets to win on the other's territory. The notebooks build each
model by hand because that is the lesson; this package builds it once because
that is the code; and an agreement assertion at the end of each notebook is what
makes the deliberate duplication safe.

**Only the data layer exists so far.** The model modules arrive with session 3
of ENERGY_SERIES_PLAN.md, and until they do no notebook carries an agreement
assertion — `tools/check_notebooks.py` reports that per notebook rather than
letting it pass quietly.

    from esm.data import table
    gens = table("generators.csv")
"""

__version__ = "0.1.0.dev0"

from esm.data import RAW_BASE, resolve, table  # noqa: F401

__all__ = ["table", "resolve", "RAW_BASE", "__version__"]
