# -*- coding: utf-8 -*-
"""build_transport_notebook.py -> `2026 Fall/Notebooks/M3_Transport_Companion.ipynb`.

WHAT THIS IS
A REORDERING of the Spring `Module_3_Transport_Companion.ipynb`, not a rewrite.
Every cell of Erick's content is carried over verbatim; only the sequence and
the framing markdown change.

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

NEW ORDER (Spring cell indices in brackets)
    Part A  the transport LP in gurobipy, five parts numbered   [7-12]
    Part B  the same problem in PyPSA, Step 1-6                 [17-30]
    Part C  now explore it - both interactive visualisers       [5,6,13,14,15]
    plus a facility-scale coda, matching the book's Part codas

Run from Tools/:  python build_transport_notebook.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "2026 Spring (First Class)", "Google Drive",
                   "Class Collab Code", "Transport and Power Flow",
                   "Module_3_Transport_Companion.ipynb")
OUT = os.path.join(ROOT, "2026 Fall", "Notebooks",
                   "M3_Transport_Companion.ipynb")

_N = [0]


def _id():
    _N[0] += 1
    return "cell-%02d" % _N[0]


def md(*lines):
    return {"cell_type": "markdown", "id": _id(), "metadata": {},
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
        "# Module 3: Energy Transportation and Network Optimization",
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
        C.append(take(i))
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

    code = [c for c in C if c["cell_type"] == "code"]
    print("wrote", os.path.relpath(OUT, ROOT))
    print("  %d cells (%d code, %d markdown)"
          % (len(C), len(code), len(C) - len(code)))
    print("  every code cell carried over verbatim from the Spring notebook")
    # the inversion is gone: no function definition before the walkthrough
    first_def = next((i for i, c in enumerate(C) if c["cell_type"] == "code"
                      and "def " in "".join(c["source"])), None)
    first_step = next((i for i, c in enumerate(C) if c["cell_type"] == "markdown"
                       and "### Step 1" in "".join(c["source"])), None)
    assert first_def is not None and first_step is not None
    assert first_step < first_def, "a function still precedes the walkthrough"
    print("  first Step-1 cell at %d, first def at %d - walkthrough comes first"
          % (first_step, first_def))


if __name__ == "__main__":
    main()
