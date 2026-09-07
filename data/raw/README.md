# Authored instance tables

**Still empty.** Session 3 fills it, starting with `power_flow_and_lmp`, and
sessions 4–6 follow the same pattern.

**Read them with `esm.data.table(name)`, never with a bare path or URL.** It
resolves a local copy first and falls back to the published raw URL, so the
same notebook works in a clone, on Colab, and from a bare `pip install` — and,
crucially, a reader who edits a file here sees the edit flow into both the
hand-built model and the agreement check. See `../../src/esm/data.py` for why
local has to win.

## What belongs here, and what does not

The distinction is not stylistic. It falls out of the agreement assertion itself:

> **A number the notebook hands to the package may stay hardcoded — the assertion
> proves both sides used it. A number both sides look up independently must live
> in one file both sides read — nothing else can prove they agree.**

A **knob** is a scalar carrying a concept: a discount rate, a demand charge, a
breakpoint count — anything the prose explains or invites the reader to change. It
**stays written out in the notebook cell**, beside the sentence explaining it, and
is passed into the package explicitly. Seeing it there is the lesson. Do not
refactor knobs into a config file; Part 4 of the standard carves this out on
purpose.

A **table** is instance data: many entries, indexed by the model's own sets, named
nowhere in the prose — bus loads, line reactances, generator costs by technology.
Typing it into the notebook and again into the package duplicates *data* with
nothing comparing the copies, and a mismatch then surfaces as a failed assertion
pointing at the model rather than at the number. **Tables live here, and both
sides read them.**

## Three requirements that make the loaded version teach more, not less

1. **Render the table.** A printed frame reads better than a page of dict literals.
2. **Show the key structure.** Print the dictionary form too, so the index set is
   explicit rather than implied by punctuation — the constraints below look values
   up by exactly that key.
3. **The package takes the data as an argument and never re-reads the file.** Then
   a reader who edits a value sees it flow into both the hand-built model and the
   check, and the assertion stays green. A check that punishes experimenting is a
   check that gets switched off.

## Licence

CC0 — see `../../LICENSE-DATA`. These are authored teaching instances that readers
are told to edit and re-run; attribution conditions on them would be friction with
no benefit. Third-party data is different and goes in `../vendor/` with its own
licence.
