# -*- coding: utf-8 -*-
"""build_transport_notebook.py -> `notebooks/p4_networks/17_pipeline_transport.ipynb`.

WHAT THIS IS
A REORDERING of the Spring `Module_3_Transport_Companion.ipynb`, not a rewrite.
Every cell of Erick's content is carried over verbatim, with exactly ONE
exception, documented at the point it happens below: a units bug in the total-
cost print at the end of Part B.

THE SOURCE IS VENDORED, NOT REACHED FOR ACROSS REPOSITORIES
`tools/builders/sources/Module_3_Transport_Companion.ipynb` is a byte-for-byte
copy of the Spring semester file, taken 2026-09-09. This builder used to read it
from the private course folder via a path built off `ROOT`, which broke the day
`ROOT` was repointed at this repository instead of the course folder -- the
builder went from "reads the course folder" to "reads a path inside itself that
does not exist", silently, because nothing exercised it in between. Vendoring
the one file this builder actually needs makes it self-contained the way the
other eleven already are; they hold their content as Python string literals,
this one holds it as a sibling JSON file, and both are "the builder does not
reach outside the repository it lives in."

THE PROBLEM IT FIXES
The Spring notebook opens with `solve_and_visualize()` (5,744 characters) and
later `solve_pypsa_network()` (5,745), and only afterwards reaches the
`### Step 1..6` walkthrough that narrates the same material one component at a
time.  A student therefore meets the wrapped version twice before meeting the
thing it wraps.

BUT THOSE FUNCTIONS ARE NOT MERE ABSTRACTION - they drive interactive slider
widgets, which is a genuinely different purpose and worth keeping.  So this is
not "move the functions to the bottom".  It is:

    work it by hand  ->  narrate the components  ->  NOW go and play with it

which is the order the widgets deserve.  Explore-after-understand, rather than
a slider you can drag before you know what it is doing.

NEW ORDER (source cell indices in brackets, vendored file)
    Part A  the transport LP in gurobipy, five parts numbered   [7-12]
    Part B  the same problem in PyPSA, Step 1-6, THEN an        [17-30]
            agreement assertion against esm.transport
    Part C  now explore it - both interactive visualisers       [5,6,13,14,15]
    plus a facility-scale coda, matching the book's Part codas

Run from the repository root:  python tools/builders/build_transport_notebook.py
"""
import json
import os

# tools/builders/<this file> -> tools/ -> the repository root.
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sources",
                   "Module_3_Transport_Companion.ipynb")
OUT = os.path.join(ROOT, "notebooks", "p4_networks", "17_pipeline_transport.ipynb")

_N = [0]


def _id():
    _N[0] += 1
    return "cell-%02d" % _N[0]


def md(*lines):
    return {"cell_type": "markdown", "id": _id(), "metadata": {},
            "source": [l + "\n" for l in lines]}


def code(*lines):
    return {"cell_type": "code", "id": _id(), "metadata": {},
            "execution_count": None, "outputs": [],
            "source": [l + "\n" for l in lines]}


def main():
    src = json.load(open(SRC, encoding="utf-8"))["cells"]

    def take(i):
        c = dict(src[i])
        c["id"] = _id()
        c.setdefault("metadata", {})
        if c["cell_type"] == "code":
            c["execution_count"] = None
            c["outputs"] = []
        return c

    C = []

    C.append(md(
        "# Energy transportation and network optimization",
        "## REE 4301 / IE 5300 - Energy Systems Modeling",
        "",
        "Moving energy costs money, and where it can go is limited. This "
        "notebook builds the classic transportation problem three ways and "
        "shows they are the same problem.",
        "",
        "**Read it in order.** It goes:",
        "",
        "1. **By hand, in gurobipy** - all five parts of the linear program "
        "visible, numbered, and yours.",
        "2. **In PyPSA**, one component at a time, with each argument mapped "
        "back to the symbol it replaces.",
        "3. **Then the interactive versions** - sliders that let you push the "
        "pipeline capacity around and watch the answer move.",
        "",
        "The sliders come last on purpose. Dragging one before you know what "
        "is underneath it teaches you the shape of a curve and nothing about "
        "the model. Once you have written the constraints yourself, the same "
        "slider is an experiment."))

    for i in (2, 3, 4):           # installs and imports
        C.append(take(i))

    C.append(md(
        "---",
        "# Part A - The transport problem by hand, in gurobipy",
        "",
        "The five parts, numbered, in the order you will write them for every "
        "model in this course. Watch for the capacity constraint: it can be "
        "switched on and off, and that switch is the whole lesson."))
    for i in (7, 8, 9, 10, 11, 12):
        C.append(take(i))

    C.append(md(
        "---",
        "# Part B - The same problem in PyPSA, one component at a time",
        "",
        "Everything you just wrote by hand - the balance equations, the "
        "capacity limits, the objective - gets written for you here. What you "
        "supply instead is a description of the *system*.",
        "",
        "Each step below names the PyPSA argument and the LP symbol it "
        "replaces. That mapping is the point of this section: `Link.p_nom` is "
        "not a new idea, it is the capacity constraint you already wrote."))
    for i in range(18, 31):       # the Step 1-6 walkthrough
        c = take(i)
        if i == 28:
            # THE ONE DEVIATION FROM "CARRIED OVER VERBATIM".
            #
            # Source cell 28 prints `n.objective * 1000`. That multiplier is
            # correct in the SLIDER functions (source cells 6 and 15, Part C
            # below) because their internal units are THOUSANDS of barrels
            # (supply=[100, 80], p_nom=100). It is wrong here: this walkthrough
            # (Steps 1-6) builds `n` in RAW barrels (p_nom=100000, p_set=70000),
            # so `n.objective` is already real dollars and the `* 1000` inflates
            # the printed total by a thousand -- $490,000/day reported as
            # $490,000,000/day.
            #
            # Caught while writing esm/transport.py: solving this exact
            # instance by hand in gurobipy (Part A's "Kickback" model, whose
            # units genuinely are thousands and whose ObjVal*1000 is correct)
            # and independently via scipy.linprog both gave $490,000. Neither
            # gave $490,000,000. See esm/transport.py's module docstring.
            body = "".join(c["source"])
            old = 'print(f"\\nTotal System Cost: ${n.objective * 1000:,.0f} per day")'
            new = 'print(f"\\nTotal System Cost: ${n.objective:,.0f} per day")'
            assert old in body, "expected buggy print not found in source cell 28"
            body = body.replace(old, new)
            lines = body.split("\n")
            c["source"] = [l + "\n" for l in lines[:-1]] + ([lines[-1]] if lines[-1] else [])
        C.append(c)

    C.append(md(
        "---",
        "### Does the package agree?",
        "",
        "Everything above was built by hand, one PyPSA component at a time, "
        "because that is the lesson. `esm.transport` solves the same instance "
        "once, from the same three tables in `data/raw/`, through "
        "`scipy.optimize.linprog` rather than through PyPSA.",
        "",
        "A different route on purpose: two PyPSA networks built the same way "
        "would share a mistake if the instance data were wrong in the same "
        "place both times. Going through `linprog` is what makes agreement "
        "worth something.",
        "",
        "**What is compared.** Costs on this instance are all distinct - "
        "$1.50, 2.50, 3.00, 3.50, 4.00, 4.50 - so both the total cost and the "
        "per-route flows are unique, and both are asserted. An instance with "
        "two routes tied on cost would need the flow comparison dropped to the "
        "invariant (total cost, and which route is binding) rather than the "
        "per-route split - see Part 6 of the standard on asserting only what "
        "is actually unique."))

    C.append(code(
        "from esm.transport import load_transport_instance, solve_transport",
        "from esm.tolerance import AGREEMENT_RTOL, relative",
        "",
        "inst = load_transport_instance()",
        "packaged = solve_transport(inst)",
        "",
        "# `flows` was defined two cells up, in Step 6 -- a pandas Series",
        "# indexed by the link names this walkthrough gave them.",
        "hand_flows = {",
        "    ('Permian', 'Houston'): flows['Pipe_Permian_Houston'],",
        "    ('Permian', 'Corpus'): flows['Pipe_Permian_Corpus'],",
        "    ('Permian', 'Beaumont'): flows['Pipe_Permian_Beaumont'],",
        "    ('Eagle Ford', 'Houston'): flows['Pipe_EagleFord_Houston'],",
        "    ('Eagle Ford', 'Corpus'): flows['Pipe_EagleFord_Corpus'],",
        "    ('Eagle Ford', 'Beaumont'): flows['Pipe_EagleFord_Beaumont'],",
        "}",
        "",
        "checks = [('total cost', n.objective, packaged.cost)]",
        "checks += [(f'{i} -> {j}', hand_flows[i, j], packaged.flows[i, j])",
        "          for i, j in hand_flows]",
        "",
        "print(f'{\"quantity\":22s} {\"by hand (PyPSA)\":>16s} {\"package\":>12s} {\"rel diff\":>10s}')",
        "for label, hand, pkg in checks:",
        "    print(f'{label:22s} {hand:16.1f} {pkg:12.1f} {relative(hand, pkg):10.1e}')",
        "",
        "worst = max(relative(a, b) for _, a, b in checks)",
        "assert worst < AGREEMENT_RTOL, (",
        "    f'notebook and package disagree by {worst:.2e}, '",
        "    f'which is worse than {AGREEMENT_RTOL:.0e}')",
        "",
        "print()",
        "print(f'notebook and package agree to {worst:.1e}')",
    ))

    C.append(take(16))            # discussion questions for Part B

    C.append(md(
        "---",
        "# Part C - Now go and play with it",
        "",
        "Both cells below wrap what you have just built into a function with a "
        "slider on it. **They are here rather than at the top deliberately.** "
        "You have written the constraints; now you can push them around and "
        "the movement will mean something.",
        "",
        "> **Predict before you drag.** Pick a pipeline capacity, write down "
        "which route you think the oil reroutes through and what that does to "
        "the total cost, and only then move the slider.",
        "",
        "The first is the SciPy version, the second is the PyPSA one. They "
        "solve the same problem and should agree."))
    for i in (5, 6, 13, 14, 15):
        C.append(take(i))

    C.append(md("*Before class: you optimised routes across a whole region. Sitting at one node of that network, which of the numbers you just chose would instead arrive as a price you were quoted?*"))

    C.append(take(31))            # Erick's closing cell

    nb = {"cells": C,
          "metadata": {"kernelspec": {"display_name": "Python 3",
                                      "language": "python", "name": "python3"},
                       "language_info": {"name": "python"},
                       "colab": {"provenance": []}},
          "nbformat": 4, "nbformat_minor": 5}

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)

    code_cells = [c for c in C if c["cell_type"] == "code"]
    print("wrote", os.path.relpath(OUT, ROOT))
    print("  %d cells (%d code, %d markdown)"
          % (len(C), len(code_cells), len(C) - len(code_cells)))
    print("  every code cell carried over verbatim from the Spring notebook,")
    print("  except cell 28's total-cost print (units bug, see docstring)")
    # the inversion is gone: no function definition before the walkthrough
    first_def = next((i for i, c in enumerate(C) if c["cell_type"] == "code"
                      and "def " in "".join(c["source"])), None)
    first_step = next((i for i, c in enumerate(C) if c["cell_type"] == "markdown"
                       and "### Step 1" in "".join(c["source"])), None)
    assert first_def is not None and first_step is not None
    assert first_step < first_def, "a function still precedes the walkthrough"
    print("  first Step-1 cell at %d, first def at %d - walkthrough comes first"
          % (first_step, first_def))
    # the fix actually landed
    fixed = any("n.objective:,.0f" in "".join(c["source"]) for c in code_cells)
    assert fixed, "the units fix did not land in the generated notebook"


if __name__ == "__main__":
    main()
