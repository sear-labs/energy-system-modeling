# -*- coding: utf-8 -*-
"""build_m4_storage_notebook.py -> `notebooks/p5_storage_supply/19_battery_day.ipynb`.

WHERE THIS COPY CAME FROM, AND THE TERMS IT CAME ON
Brought from the course folder's `Tools/` on 2026-10-22 (course notebook
M4_Storage_Walkthrough, 15 Oct).  ENERGY_SERIES_PLAN maps Chapter 19 to
`teaching-code` notebook 12, so its owner was asked first, and agreed on three
conditions (2026-10-22), each applied here:

  1. Do not re-teach notebook 12.  Its Part E builds this same day step by
     step (StorageUnit, state of charge, the charging-hours tie) and its
     Explore section has battery-size sliders.  So this notebook OPENS by
     pointing there for the build, builds the day in one cell, and spends
     itself on what Module 4 adds: the battery's value, the cyclic rule taken
     away, and 2/4/8 hours.
  2. The agreement assertion is against `esm`, never `orteach`.  It is against
     `esm.storage`, which writes the storage equations out as a plain LP.
  3. If the prose names charging hours, check first that they are unique.
     They are not: solar is curtailed through the middle of the day, so the
     battery can charge in any of several hours at the same cost.  The prose
     names none, says the schedule is one of several, and the assertion
     compares only the day's cost, which is unique.

Other changes from the course copy:
  * the bare `!pip install` is gone (unpinned; the setup cell pins);
  * the Part C table keeps exact savings and rounds only for display, so the
    agreement cell compares the numbers the solver produced, not their
    rounding;
  * course-module references point at the book and at notebook 12 instead.

ANCHORED AT CHAPTER 19: section 19.4 (the state-of-charge constraint) and 19.5
(does the battery pay for itself?).

THE DAY: demand peaking at 110 MW in the evening, 140 MW of solar, a 66 MW gas
unit at $22.14, a 100 MW peaker at $80, a 40 MW / 4 h battery (0.927 each way,
1 %/h standing loss).  verify() re-solves every case through `esm.storage`.

    python build_m4_storage_notebook.py          build (verify + syntax check)
    python build_m4_storage_notebook.py --run    also execute (pypsa needed)
"""
import json
import os
import sys

# tools/builders/<this file> -> tools/ -> the repository root.
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "notebooks", "p5_storage_supply", "19_battery_day.ipynb")
NB12 = ("https://github.com/sear-labs/teaching-code/blob/main/notebooks/"
        "12_energy_systems_pypsa/dispatch_to_pypsa.ipynb")

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


def verify():
    """Every claim the prose makes, re-derived through esm.storage."""
    sys.path.insert(0, os.path.join(ROOT, "src"))
    from esm.storage import BatteryDay, day_cost
    day = BatteryDay.module_0()
    base, _ = day_cost(day)
    four, _ = day_cost(day, 4)
    open_full, end = day_cost(day, 4, cyclic=False, soc_initial=160.0)
    saves = {h: base - day_cost(day, h)[0] for h in (2, 4, 8)}
    assert four < base, "the battery must save something"
    assert open_full < four, "starting full with no cyclic rule must look cheaper"
    assert end < 1e-6, "and it must end the day empty"
    assert saves[2] < saves[4] <= saves[8] < 2 * saves[4], saves
    print("verify: day $%.0f without, $%.0f with 4 h (saves $%.0f); open & full "
          "$%.0f, ends at %.1f MWh; saves 2/4/8 h = $%.0f / $%.0f / $%.0f"
          % (base, four, base - four, open_full, end, saves[2], saves[4], saves[8]))
    return dict(base=base, four=four, open_full=open_full, saves=saves)


C = []
A = C.append

A(md(
L("# What a battery is worth: one day, three questions"),
L(""),
L("Sections 19.4 and 19.5 of the book, on a day you may already have built. "
  "[`teaching-code` notebook 12](" + NB12 + "), Part E, builds it step by step: "
  "the demand, 140 MW of solar, a gas unit and a peaker, and a 40 MW / 160 MWh "
  "battery, with every storage equation PyPSA writes laid out. **Start there if "
  "you have not.** Here the same day is built in one cell, and the notebook asks "
  "what that build alone does not: what the battery is worth, what one line of "
  "its definition is doing, and whether a bigger one is worth more."),
L(""),
L("In Colab, *File › Save a copy in Drive* first so your edits are kept."),
L(""),
L("**Before you run anything:** if the battery held twice as much energy - 8 "
  "hours instead of 4 - would it save the system twice as much? Write down a "
  "yes or no and one reason."),
))
A(code(
L("import numpy as np"),
L("import pandas as pd"),
L("import pypsa"),
))

A(md(
L("## The day"),
L(""),
L("Notebook 12's demand and solar shapes, as two formulas."),
))
A(code(
L("import warnings"),
L("warnings.filterwarnings('ignore', category=FutureWarning)  # PyPSA's notices about its next version"),
L(""),
L("hours = np.arange(24)"),
L("demand_t = (50 + 60 * np.exp(-((hours - 19) ** 2) / 12.0)     # evening peak"),
L("              + 18 * np.exp(-((hours - 8) ** 2) / 6.0))      # morning bump"),
L("solar_pu = np.clip(np.sin(np.pi * (hours - 6) / 13), 0, 1)"),
L("print(f'peak demand {demand_t.max():.0f} MW at hour {demand_t.argmax()}; '"),
L("      f'140 MW of solar peaks at {140 * solar_pu.max():.0f} MW')"),
))

A(md(
L("## Part A - The same day, without a battery and with one"),
))
A(code(
L("n = pypsa.Network()"),
L("n.set_snapshots(hours)"),
L("n.add('Bus', 'node')"),
L("n.add('Load', 'demand', bus='node', p_set=demand_t)"),
L("n.add('Generator', 'solar',  bus='node', p_nom=140, p_max_pu=solar_pu, marginal_cost=0)"),
L("n.add('Generator', 'gas',    bus='node', p_nom=66,  marginal_cost=22.14)"),
L("n.add('Generator', 'peaker', bus='node', p_nom=100, marginal_cost=80.00)"),
L(""),
L("n.optimize(solver_name='highs')"),
L("cost_without = n.objective"),
L("print(f'day cost without a battery: ${cost_without:,.0f}')"),
))
A(md(
L("Now the battery, exactly as notebook 12 defines it."),
))
A(code(
L("n.add('StorageUnit', 'battery', bus='node', p_nom=40, max_hours=4,"),
L("      efficiency_store=0.927, efficiency_dispatch=0.927,"),
L("      standing_loss=0.01, cyclic_state_of_charge=True, marginal_cost=0.01)"),
L(""),
L("n.optimize(solver_name='highs')"),
L("cost_with = n.objective"),
L("print(f'day cost with it: ${cost_with:,.0f}   saves ${cost_without - cost_with:,.0f}')"),
))
A(md(
L("When it works: positive is discharging, negative is charging; the state of charge is in MWh."),
))
A(code(
L("pd.DataFrame({'battery MW': n.storage_units_t.p['battery'].round(1),"),
L("              'soc MWh': n.storage_units_t.state_of_charge['battery'].round(1),"),
L("              'peaker MW': n.generators_t.p['peaker'].round(1)}).T"),
))
A(md(
L("> It fills while the sun is up and empties after dark. **Which hours it "
  "charges in is not a result:** solar is spilling through the middle of the "
  "day, so several schedules cost exactly the same and the solver hands back one "
  "of them - notebook 12 shows why. Read the table for the pattern. Then: which "
  "generator's megawatt-hours is the battery replacing - and is that the same "
  "thing as the hours with the highest price?"),
))

A(md(
L("## Part B - Take away one line"),
L(""),
L("`cyclic_state_of_charge=True` makes the battery finish the day where it "
  "started. Switch it off, and let the battery start the day full."),
))
A(code(
L("n.storage_units.loc['battery', 'cyclic_state_of_charge'] = False"),
L("n.storage_units.loc['battery', 'state_of_charge_initial'] = 160    # full, MWh"),
L(""),
L("n.optimize(solver_name='highs')"),
L("cost_open = n.objective"),
L("print(f'day cost: ${cost_open:,.0f}   (with the cyclic rule: ${cost_with:,.0f})')"),
L("print('state of charge at 11 pm:',"),
L("      round(n.storage_units_t.state_of_charge['battery'].iloc[-1], 1), 'MWh')"),
))
A(md(
L("> The day got cheaper. Where did that energy come from, and who pays for it "
  "tomorrow? If you were selling this battery to someone, which of the two day "
  "costs would you show them?"),
))

A(md(
L("## Part C - Longer batteries"),
L(""),
L("Put the cyclic rule back, then try 2, 4 and 8 hours of storage at the same "
  "40 MW. The loop repeats one identical step three times; nothing differs "
  "between its turns but the number of hours."),
))
A(code(
L("n.storage_units.loc['battery', 'cyclic_state_of_charge'] = True"),
L(""),
L("rows = []"),
L("for h in (2, 4, 8):"),
L("    n.storage_units.loc['battery', 'max_hours'] = h"),
L("    n.optimize(solver_name='highs')"),
L("    rows.append({'hours': h, 'energy MWh': 40 * h,"),
L("                 'saves $/day': cost_without - n.objective})"),
L("pd.DataFrame(rows).round(0)"),
))
A(md(
L("> Was your prediction right? Going from 4 to 8 hours added 160 MWh. What would "
  "that extra 160 MWh have to cost per year to be worth building? (The capital "
  "recovery factor of the book's section 9.3 turns a build cost into a yearly "
  "one.)"),
))

A(md(
L("---"),
L("### Does the package agree?"),
L(""),
L("`esm.storage` writes the storage equations out by hand as one linear program "
  "and solves it with `scipy` - the state of charge carried hour to hour, the "
  "standing loss, the cyclic rule or a starting charge. It takes this "
  "notebook's own numbers, read back from the network, and the day's shape from "
  "`data/raw/battery_day_profile.csv`, the same two formulas written to a table."),
L(""),
L("**Only the day's cost is compared**, never the schedule, for the reason in "
  "Part A. One detail was found rather than assumed: PyPSA applies the standing "
  "loss to each hour's charge from the hour before, but not to the starting "
  "charge in the first hour. Written the obvious way, Part B's two answers "
  "differ by about $32; written PyPSA's way, they agree."),
))
A(code(
L("from esm.storage import BatteryDay, day_cost, load_battery_profile"),
L("from esm.tolerance import AGREEMENT_RTOL, relative"),
L(""),
L("g, b = n.generators, n.storage_units"),
L("profile_demand, profile_solar = load_battery_profile()"),
L("day = BatteryDay(demand=profile_demand, solar_pu=profile_solar,"),
L("                 solar_mw=g.at['solar', 'p_nom'],"),
L("                 gas_mw=g.at['gas', 'p_nom'], gas_cost=g.at['gas', 'marginal_cost'],"),
L("                 peaker_mw=g.at['peaker', 'p_nom'],"),
L("                 peaker_cost=g.at['peaker', 'marginal_cost'],"),
L("                 battery_mw=b.at['battery', 'p_nom'],"),
L("                 efficiency=b.at['battery', 'efficiency_store'],"),
L("                 standing_loss=b.at['battery', 'standing_loss'],"),
L("                 dispatch_cost=b.at['battery', 'marginal_cost'])"),
L(""),
L("checks = [('no battery', cost_without, day_cost(day)[0]),"),
L("          ('4 h, cyclic', cost_with, day_cost(day, 4)[0]),"),
L("          ('4 h, starts full', cost_open, day_cost(day, 4, cyclic=False, soc_initial=160)[0])]"),
L("checks += [(f'saves, {r[\"hours\"]} h', r['saves $/day'],"),
L("            cost_without - day_cost(day, r['hours'])[0]) for r in rows]"),
L("for label, hand, pkg in checks:"),
L("    print(f'{label:18s} {hand:12,.2f} {pkg:12,.2f}   {relative(hand, pkg):.1e}')"),
L(""),
L("worst = max(relative(a, c) for _, a, c in checks)"),
L("assert worst < AGREEMENT_RTOL, f'notebook and package disagree by {worst:.2e}'"),
L("print(f'\\nnotebook and package agree to {worst:.1e}')"),
))
A(md(
L("*Before class: the site in the book's Chapter 23 pays a demand charge on its "
  "single highest 15 minutes of the month. Would you size its battery by energy "
  "(MWh) or by power (MW) - and what would you look at to decide?*"),
L(""),
L("### Sources"),
L("- System and battery: [`teaching-code` notebook 12](" + NB12 + "), Part E "
  "(round trip 0.927² ≈ 86%, typical of lithium-ion; NREL ATB 2024)."),
))


def syntax_check(cells):
    bad = 0
    for i, c in enumerate(cells):
        if c["cell_type"] != "code":
            continue
        try:
            compile("".join(c["source"]), "<cell %d>" % i, "exec")
        except SyntaxError as e:
            bad += 1
            print("SYNTAX ERROR in cell %d: %s" % (i, e))
    if bad:
        raise SystemExit("%d cell(s) failed to compile" % bad)
    print("syntax check: %d code cells compile"
          % sum(1 for c in cells if c["cell_type"] == "code"))


def run(cells, expect):
    import io, contextlib, logging
    logging.disable(logging.CRITICAL)
    ns = {}
    for i, c in enumerate(cells):
        if c["cell_type"] != "code":
            continue
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile("".join(c["source"]), "<cell %d>" % i, "exec"), ns)
    tol = lambda a, b: abs(a - b) < 1.0          # dollars
    for k, nk in (("base", "cost_without"), ("four", "cost_with"), ("open_full", "cost_open")):
        assert tol(ns[nk], expect[k]), (k, ns[nk], expect[k])
    saves = {r["hours"]: r["saves $/day"] for r in ns["rows"]}
    for h in (2, 4, 8):
        assert tol(saves[h], expect["saves"][h]), (h, saves[h])
    assert ns["worst"] < 1e-9
    print("run: PyPSA matches esm.storage - without $%.0f, with $%.0f, open $%.0f; "
          "agreement %.1e" % (ns["cost_without"], ns["cost_with"], ns["cost_open"],
                              ns["worst"]))


NOTEBOOK = {"cells": C,
            "metadata": {"kernelspec": {"display_name": "Python 3",
                                        "language": "python", "name": "python3"},
                         "language_info": {"name": "python"},
                         "colab": {"provenance": []}},
            "nbformat": 4, "nbformat_minor": 5}

if __name__ == "__main__":
    expect = verify()
    syntax_check(C)
    if "--run" in sys.argv:
        run(C, expect)
    words = sum(len("".join(c["source"]).split()) for c in C if c["cell_type"] == "markdown")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(NOTEBOOK, f, indent=1, ensure_ascii=False)
    print("wrote", os.path.relpath(OUT, ROOT))
    print("cells: %d (%d code, %d markdown), %d words of prose"
          % (len(C), sum(1 for c in C if c["cell_type"] == "code"),
             sum(1 for c in C if c["cell_type"] == "markdown"), words))
