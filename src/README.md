# `src/esm/` — the package

**Only the data layer exists.** `esm.data` decides where an instance table comes
from; the model modules arrive with session 3, starting from what
`notebooks/p4_networks/power_flow_and_lmp.ipynb` builds by hand.

That order is deliberate. The data layer is what a notebook needs to run
anywhere at all, and it is the piece the whole organisation kept re-solving
differently — clone the repo, vendor a second copy of the CSVs into the package,
or hardcode a raw URL. `esm/data.py` picks one and writes down why, and
`tests/test_data_loader.py` pins the resolution order.

**There is still no model code, so no notebook carries an agreement assertion.**
That is Part 4's entire mechanism missing, and `tools/check_notebooks.py` reports
it per notebook rather than letting it pass quietly.

## What it is for

Same model, twice, on purpose. The notebook builds it by hand because that is the
lesson; the package builds it once because that is the code. Deliberate
duplication removes the usual protection — that only one copy exists — so
something has to replace it:

> **Every teaching notebook ends with a cell that imports the package, runs the
> same case, and asserts the two agree.** A teaching notebook without this cell is
> not finished.

`src/` is governed by Parts 1–2 of the standard, `notebooks/` by Part 3, and
neither half gets to win on the other's territory. A step written out by hand in a
notebook that also exists here is **correct**, not duplication — do not DRY it
away. Conversely a helper function in the teaching section of a notebook is not.

## Two things to get right the first time

**The package takes instance data as an argument and never re-reads a file.** A
reader who edits `data/raw/` must see the change flow into both the hand-built
model and the check.

**Tolerances live in one module and nowhere else.** A threshold used in two places
is a parameter, and the duplicate is where a fix does not reach. Import it in the
notebook and in any runner rather than writing it twice — and where it genuinely
cannot be shared, assert the copies against each other.

The package is imported from `src/` by path, as `orteach` is in `teaching-code`,
so a notebook works from a clone without an install step.
