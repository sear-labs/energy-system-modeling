# `src/esm/` — the package

**Not written yet.** Session 3 builds it, starting from what
`notebooks/p4_networks/power_flow_and_lmp.ipynb` builds by hand.

There is deliberately **no stub `__init__.py` here**. A hollow package that
imports and does nothing is worse than an absent one: it makes
`from esm import ...` succeed and then fail somewhere less obvious, and it invites
an agreement assertion to be written against a module that computes nothing.

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
