# -*- coding: utf-8 -*-
"""build_sb1_example_notebook.py -> `notebooks/p1_foundations/02_one_house_balance.ipynb`.

DESIGN NOTE - what changed and why
The previous version was 55 cells and 3,558 words, with section headings like
"The residual is exactly zero. That is bad news" and "Germany comes out ahead.
Do not believe it." Erick's note, 2 Sep: too long, too many this-went-wrong
branches, too declarative - and although the flow table was good, **it never
actually drew a Sankey diagram.**

This is a MINIMAL REPRODUCIBLE EXAMPLE. Its job is to let a student see the
shape of the thing - "oh, it looks like this" - not to walk every branch of
possible logic. It ends with a diagram on the screen.

The system is a HOUSE rather than a country. Students pick cars, houses and
single power plants; a national balance is the wrong scale to imitate, and at
house scale the unit conversions are visible instead of buried in quads.

Structure mirrors the LLNL flow chart, which is the thing being imitated:
sources on the left, end uses in the middle, useful and rejected energy on the
right.

Two results the notebook shows without explaining:
  * the car rejects 78% of all the rejected energy in the house
  * the house looks 63% efficient, against roughly a third for the US as a
    whole - which is a boundary question, and is left as one

Run from Tools/:  python build_sb1_example_notebook.py
"""
import json
import os

# tools/builders/<this file> -> tools/ -> the repository root.
# Three levels, not two: these builders used to live one level higher,
# in the course folder's Tools/.
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "notebooks", "p1_foundations", "02_one_house_balance.ipynb")

_N = [0]


def _id():
    _N[0] += 1
    return "cell-%02d" % _N[0]


def md(*lines):
    return {"cell_type": "markdown", "id": _id(), "metadata": {},
            "source": list(lines)}


def code(*lines):
    return {"cell_type": "code", "id": _id(), "execution_count": None,
            "metadata": {}, "outputs": [], "source": list(lines)}


def L(s):
    return s + "\n"


C = []
A = C.append


def verify():
    THERM, GAL = 29.3, 33.7
    src = {"grid electricity": 10_000.0,
           "natural gas": 600 * THERM,
           "gasoline": 500 * GAL}
    eff = {"grid electricity": 0.90, "natural gas": 0.85, "gasoline": 0.25}
    tot = sum(src.values())
    useful = sum(v * eff[k] for k, v in src.items())
    rej = tot - useful
    car = src["gasoline"] * 0.75
    assert abs(tot - 44_430) < 1, tot
    assert abs(useful / tot - 0.634) < 0.005, useful / tot
    assert abs(car / rej - 0.777) < 0.005, car / rej
    print("arithmetic check: 44,430 kWh in, %.0f%% useful, car is %.0f%% of "
          "all rejected energy" % (100 * useful / tot, 100 * car / rej))


A(md(
L("# An energy balance for one house"),
L("## REE 4301 / IE 5300 - Energy Systems Modeling"),
L(""),
L("A small, complete version of what SB1 asks for, so you can see the shape "
  "before you build your own. It is deliberately short - your system will "
  "have different flows, but the same five moves."),
L(""),
L("The diagram at the end is the same kind of picture as the "
  "[LLNL energy flow charts](https://flowcharts.llnl.gov): sources on the "
  "left, what they were used for in the middle, and useful against rejected "
  "energy on the right."),
))

A(code(
L("!pip install -q plotly"),
))

A(code(
L("import pandas as pd"),
L("import plotly.graph_objects as go"),
))

A(md(
L("---"),
L("## 1. The boundary, in one sentence"),
L(""),
L("*Everything that crosses the property line of one house over one year: "
  "electricity through the meter, gas through the pipe, and gasoline bought "
  "for the car parked there.*"),
L(""),
L("Write yours the same way, and be as specific. Most of the trouble in this "
  "assignment comes from a boundary that was never actually stated."),
))

A(md(
L("## 2. What came in, in the units it was billed in"),
L(""),
L("Bills do not arrive in one unit. Electricity is kWh, gas is therms or "
  "ccf, gasoline is gallons - so the conversion factors go in the table, "
  "where they can be checked."),
))

A(code(
L("KWH_PER_THERM = 29.3      # 1 therm = 100,000 Btu"),
L("KWH_PER_GALLON = 33.7     # gasoline, lower heating value"),
L(""),
L("inputs = pd.DataFrame(["),
L("    ['grid electricity', 10_000, 'kWh',    1.0,            'utility bill'],"),
L("    ['natural gas',         600, 'therms', KWH_PER_THERM,  'gas bill'],"),
L("    ['gasoline',            500, 'gallons', KWH_PER_GALLON, 'fuel receipts'],"),
L("], columns=['source', 'as billed', 'unit', 'kWh per unit', 'where from'])"),
L(""),
L("inputs['kWh'] = inputs['as billed'] * inputs['kWh per unit']"),
L("print(inputs.to_string(index=False))"),
L("print(f\"\\ntotal energy in: {inputs['kWh'].sum():,.0f} kWh\")"),
))

A(md(
L("## 3. What it was used for, and how much of it did the job"),
L(""),
L("Every conversion loses something. The efficiencies below are rough figures "
  "for a furnace, a car and a mixed electrical load - find better ones for "
  "your own system and say where you got them."),
))

A(code(
L("efficiency = {'grid electricity': 0.90,   # lights, appliances, some heat"),
L("              'natural gas': 0.85,        # a decent furnace"),
L("              'gasoline': 0.25}           # tank to wheels"),
L(""),
L("flows = inputs[['source', 'kWh']].copy()"),
L("flows['efficiency'] = flows['source'].map(efficiency)"),
L("flows['useful'] = flows['kWh'] * flows['efficiency']"),
L("flows['rejected'] = flows['kWh'] - flows['useful']"),
L(""),
L("cols = {'kWh': 0, 'efficiency': 2, 'useful': 0, 'rejected': 0}"),
L("print(flows.round(cols).to_string(index=False))"),
))

A(md(
L("## 4. Does it close?"),
L(""),
L("In minus out. Here it closes exactly, because the efficiencies were "
  "*assumed* rather than measured - so the rejected column was calculated as "
  "the leftover."),
L(""),
L("Your balance will not close exactly, and that is the interesting part. "
  "Report the residual and say what it is."),
))

A(code(
L("total_in = flows['kWh'].sum()"),
L("useful = flows['useful'].sum()"),
L("rejected = flows['rejected'].sum()"),
L(""),
L("print(f'in        {total_in:>9,.0f} kWh')"),
L("print(f'useful    {useful:>9,.0f} kWh   {useful / total_in:.0%}')"),
L("print(f'rejected  {rejected:>9,.0f} kWh   {rejected / total_in:.0%}')"),
L("print(f'residual  {total_in - useful - rejected:>9,.0f} kWh')"),
))

A(md(
L("---"),
L("## 5. Draw it"),
L(""),
L("Widths come from the numbers above. Nothing is drawn by hand."),
))

A(code(
L("labels = list(flows['source']) + ['useful energy', 'rejected energy']"),
L("i_useful, i_rejected = len(flows), len(flows) + 1"),
L(""),
L("source_idx, target_idx, value = [], [], []"),
L("for i, row in flows.iterrows():"),
L("    source_idx += [i, i]"),
L("    target_idx += [i_useful, i_rejected]"),
L("    value += [row['useful'], row['rejected']]"),
L(""),
L("fig = go.Figure(go.Sankey("),
L("    node=dict(label=labels, pad=20, thickness=20,"),
L("              color=['#4C72B0', '#DD8452', '#937860', '#55A868', '#C44E52']),"),
L("    link=dict(source=source_idx, target=target_idx, value=value),"),
L("))"),
L("fig.update_layout(title_text='One house, one year (kWh)',"),
L("                  font_size=12, height=420)"),
L("fig.show()"),
))

A(md(
L("### Read your own diagram"),
L(""),
L("Look at the rejected block and work out which source is feeding most of "
  "it. Then check:"),
))

A(code(
L("share = (flows.set_index('source')['rejected'] / rejected).sort_values("),
L("    ascending=False)"),
L("print('share of all rejected energy\\n')"),
L("print(share.map('{:.0%}'.format).to_string())"),
))

A(md(
L("> One source produces most of the waste in this house, and it is not the "
  "one with the largest bill. Why?"),
L(""),
L("> This house comes out around 63% efficient. The LLNL chart puts the whole "
  "United States at roughly a third. Same physics, very different number - "
  "what is inside their boundary that is outside yours?"),
))

A(md(
L("---"),
L("## What you do for your own system"),
L(""),
L("Same five moves, your own numbers:"),
L(""),
L("1. State the boundary in one sentence."),
L("2. Table every flow in the unit it was measured in, with the conversion "
  "factor and the source alongside."),
L("3. Split each flow into what did the job and what did not."),
L("4. Report the residual, and say what it is rather than adjusting it away."),
L("5. Generate the diagram from the table."),
L(""),
L("A car, a single power plant, a building and a small factory all work. "
  "Pick something you can find real numbers for."),
))

A(md(
L("*Before class: this balance was drawn around one house. If you drew it "
  "around the power station instead, which flows would move from outside the "
  "boundary to inside it?*"),
))


def syntax_check(cells):
    bad = 0
    for i, c in enumerate(cells):
        if c["cell_type"] != "code":
            continue
        src = "\n".join(l for l in "".join(c["source"]).splitlines()
                        if not l.strip().startswith("!"))
        try:
            compile(src, "<cell %d>" % i, "exec")
        except SyntaxError as e:
            bad += 1
            print("SYNTAX ERROR in cell %d: %s" % (i, e))
    if bad:
        raise SystemExit("%d cell(s) failed to compile" % bad)
    print("syntax check: %d code cells compile"
          % sum(1 for c in cells if c["cell_type"] == "code"))


NOTEBOOK = {"cells": C,
            "metadata": {"kernelspec": {"display_name": "Python 3",
                                        "language": "python", "name": "python3"},
                         "language_info": {"name": "python"},
                         "colab": {"provenance": []}},
            "nbformat": 4, "nbformat_minor": 5}

if __name__ == "__main__":
    verify()
    syntax_check(C)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(NOTEBOOK, f, indent=1, ensure_ascii=False)
    words = sum(len("".join(c["source"]).split()) for c in C
                if c["cell_type"] == "markdown")
    print("wrote", os.path.relpath(OUT, ROOT))
    print("cells: %d (%d code, %d markdown), %d words of prose"
          % (len(C), sum(1 for c in C if c["cell_type"] == "code"),
             sum(1 for c in C if c["cell_type"] == "markdown"), words))
