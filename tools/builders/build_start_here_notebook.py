# -*- coding: utf-8 -*-
"""build_start_here_notebook.py -> `notebooks/p0_start/00_start_here.ipynb`.

THE FRONT DOOR

Every other notebook in this series is a lesson: it builds a model a step at a
time, and several stop at a deliberate blank where a student has to supply
something. That makes them the wrong first thing to meet. A reader who opens
one cold sees scaffolding and an unfinished exercise, not a result.

This notebook is the opposite in every respect:

  fixed instances       it reads what is in data/vendor/ and data/raw/, and
                        changes nothing
  no blanks             nothing here waits for a student; it runs top to bottom
  no teaching           it does not build a model by hand, because that is what
                        the twelve are for
  every model           one headline number from each, so a reader can see the
                        whole series in one run

**It is therefore publishable without any of the assignment-exposure questions
the twelve raise**, because it never does a student's work: there is no work
here to do. That was the point of asking for it.

WHAT IT ACTUALLY DEMONSTRATES

Not the models -- the *property* the series is built on. Each of the twelve
ends by solving its instance a second, independent way and asserting the two
agree. This notebook runs the package half of every one of those pairs in a
single kernel, so the reader sees that the library stands up on its own before
they meet the first lesson.

Run from the repository root:
    python tools/builders/build_start_here_notebook.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "notebooks", "p0_start", "00_start_here.ipynb")

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


C = []
A = C.append

A(md(
    "# Start here",
    "",
    "## Energy System Modeling - the whole series in one run",
    "",
    "Twelve notebooks in this repository teach twelve models. This one teaches "
    "nothing. It runs all of them, on fixed data, and prints one number from "
    "each.",
    "",
    "Open it first. It takes under a minute and it answers the question you "
    "actually have on arrival: **does any of this work, and what is in it?**",
))

A(md(
    "### What makes this notebook different from the other twelve",
    "",
    "| | the twelve | this one |",
    "|---|---|---|",
    "| purpose | teach a model | show the results |",
    "| method | build it by hand, one cell per step | call the library |",
    "| data | fixed instances, sometimes edited to explore | fixed, untouched |",
    "| endings | several stop at a deliberate blank | runs top to bottom |",
    "",
    "Because it stops nowhere and builds nothing by hand, there is no exercise "
    "in it to spoil - which is why it is the one notebook that can be shown to "
    "anybody.",
))

A(md(
    "### The idea the whole series rests on",
    "",
    "Every one of the twelve builds a model **by hand**, narrated a step at a "
    "time, and then ends by solving the same instance a **second, independent "
    "way** and asserting the two agree.",
    "",
    "The second way is deliberately a different route, not a second copy: "
    "where a notebook writes the linear program in `gurobipy`, the package "
    "solves it in `PyPSA`; where a notebook uses `PyPSA`, the package uses "
    "`scipy`; where a notebook fits with NumPy's least squares, the package "
    "uses SciPy's, through a different LAPACK driver. Two transcriptions of "
    "the same algebra share their mistakes. Two genuinely different routes do "
    "not.",
    "",
    "What runs below is the package half of every one of those pairs.",
))

A(md("---", "## Setup"))

A(md(
    "---",
    "## Part 1 - Accounting, before anything is optimised",
    "",
    "Two of the twelve do arithmetic rather than optimisation. They come first "
    "in the course for the same reason they come first here: you cannot "
    "optimise a system you cannot add up.",
))

A(md(
    "### A household energy balance",
    "",
    "Three utility bills in three different units, converted to one, split "
    "into the part that did the job and the part that did not. Taught in "
    "`p1_foundations/02_one_house_balance`.",
))

A(code(
    "from esm.balance import (conservation_residual, load_balance_instance,",
    "                        rejected_share, solve_balance)",
    "",
    "house = solve_balance(load_balance_instance())",
    "print(f'energy in    {house.total_in:>9,.0f} kWh')",
    "print(f'useful       {house.total_useful:>9,.1f} kWh  '",
    "      f'{house.total_useful / house.total_in:.0%}')",
    "print(f'rejected     {house.total_rejected:>9,.1f} kWh  '",
    "      f'{house.total_rejected / house.total_in:.0%}')",
    "print(f'residual     {conservation_residual(house)[\"total\"]:>9.1e} kWh')",
    "print()",
    "print('largest single source of waste: '",
    "      f'{list(rejected_share(house))[0]}')",
))

A(md(
    "### Screening-level LCOE",
    "",
    "What a megawatt-hour costs before anybody optimises anything. Taught in "
    "`p3_generation/09_capital_and_lcoe`.",
))

A(code(
    "from esm.lcoe import lcoe_by_crf, lcoe_by_dcf, load_lcoe_instance",
    "",
    "screen = load_lcoe_instance()",
    "for key in (('coal', 10000), ('gas', 7500)):",
    "    plant = screen.plants[key]",
    "    print(f'{plant.fuel:5s} break-even  '",
    "          f'${lcoe_by_crf(screen, plant):6.2f} /MWh')",
    "",
    "gas = screen.plants[('gas', 7500)]",
    "print()",
    "print('the same gas plant, if its output fell half a percent a year:')",
    "print(f'  shortcut says   ${lcoe_by_crf(screen, gas):6.2f} /MWh')",
    "print(f'  definition says '",
    "      f'${lcoe_by_dcf(screen, gas, degradation=0.005):6.2f} /MWh')",
))

A(md(
    "---",
    "## Part 2 - Optimisation",
    "",
    "> **Predict before you run these.** Three of the four below are least-cost "
    "problems on small networks. Write down which you expect to be limited by "
    "capacity and which by geography, then see.",
))

A(md(
    "### Least-cost transport",
    "",
    "Crude oil from two fields to three refineries, over pipelines with "
    "capacities. Taught in `p4_networks/17_pipeline_transport`.",
))

A(code(
    "from esm.transport import (binding_routes, load_transport_instance,",
    "                          solve_transport)",
    "",
    "pipes = load_transport_instance()",
    "ship = solve_transport(pipes)",
    "print(f'least-cost shipping  ${ship.cost:,.0f} /day')",
    "for route in binding_routes(pipes, ship):",
    "    print(f'  at capacity: {route[0]} -> {route[1]}')",
))

A(md(
    "### Two-stage sourcing, and what resilience costs",
    "",
    "Cobalt from mines through refineries to cell plants, then the same "
    "problem with a cap on how much any one mine may supply. Taught in "
    "`p5_storage_supply/21_material_requirements`.",
))

A(code(
    "from esm.sourcing import load_sourcing_instance, solve_sourcing",
    "",
    "chain = load_sourcing_instance()",
    "base = solve_sourcing(chain)",
    "print(f'least cost           ${base.cost:>8,.0f} /yr')",
    "print(f'sourced from         '",
    "      f'{max(base.by_mine, key=base.by_mine.get)}, alone')",
    "print()",
    "print('what it costs to stop depending on one mine:')",
    "for cap in (0.75, 0.60, 0.50, 0.40):",
    "    capped = solve_sourcing(chain, cap)",
    "    print(f'  no more than {cap:.0%} from any one  '",
    "          f'${capped.cost:>8,.0f} /yr   '",
    "          f'+{capped.cost / base.cost - 1:.0%}')",
))

A(md(
    "### Hourly dispatch, and whether a new load pays its own price",
    "",
    "A day of demand met from a merit order, solved with and without a new "
    "site attached. Taught in `p1_foundations/01_model_boundary`.",
))

A(code(
    "from esm.boundary import bill, load_boundary_instance, solve_dispatch",
    "",
    "grid = load_boundary_instance()",
    "alone = solve_dispatch(grid, 0)",
    "print(f'system cost, no new load   ${alone.cost:>12,.0f} /day')",
    "print()",
    "for mw, who in ((50, 'an industrial park'), (500, 'a data centre')):",
    "    withit = solve_dispatch(grid, mw)",
    "    moved = sum(1 for h in grid.hours",
    "                if abs(withit.lmp[h] - alone.lmp[h]) > 1e-9)",
    "    predicted, actual = bill(alone, mw), bill(withit, mw)",
    "    print(f'{who:20s} {mw:>4} MW')",
    "    print(f'   expected to pay  ${predicted:>10,.0f} /day')",
    "    print(f'   actually pays    ${actual:>10,.0f} /day  '",
    "          f'({actual / predicted - 1:+.0%})')",
    "    print(f'   moved the price in {moved} of {len(grid.hours)} hours')",
))

A(md(
    "### A facility deciding whether to build solar",
    "",
    "The same arithmetic a plant manager actually faces, where the answer "
    "turns on the tariff rather than on the panels. Taught in "
    "`capstone/AppA_facility_decision`.",
))

A(code(
    "from esm.facility import annual_bill, load_facility_instance, solve_site",
    "",
    "site = load_facility_instance()",
    "do_nothing = annual_bill(site)",
    "with_solar = solve_site(site, solar_max=site.roof_mw)",
    "print(f'bill as things stand   ${do_nothing / 1e6:>7.3f} M/yr')",
    "print(f'with the roof built    ${with_solar.cost / 1e6:>7.3f} M/yr')",
    "print(f'saving                 ${(do_nothing - with_solar.cost) / 1e6:>7.3f} M/yr')",
    "print(f'solar built            {with_solar.solar_mw:>7.1f} MW')",
    "print()",
    "no_charge = solve_site(site, solar_max=site.roof_mw, demand_charge=0.0)",
    "print('and the same site on a tariff with no demand charge:')",
    "print(f'  solar built          {no_charge.solar_mw:>7.1f} MW')",
))

A(md(
    "---",
    "## Part 3 - Real data, which arrives broken",
    "",
    "The models above run on instances small enough to check by eye. Real "
    "network data is not, and it does not announce its defects.",
))

A(md(
    "### A 2000-bus synthetic Texas grid",
    "",
    "Parsed from the MATPOWER case vendored in `data/vendor/`, with the fuel "
    "labels that both standard converters throw away. Taught in "
    "`p4_networks/15_real_network_import`.",
))

A(code(
    "from pathlib import Path",
    "",
    "from esm.network_import import (check_matpower_parse, generation_mix,",
    "                               parse_matpower)",
    "",
    "case = Path('../../data/vendor/case_ACTIVSg2000.m')",
    "ppc = parse_matpower(case.read_text(encoding='utf-8'))",
    "check_matpower_parse(ppc)",
    "print(f'{len(ppc[\"bus\"]):,} buses, {len(ppc[\"gen\"])} generators, '",
    "      f'{len(ppc[\"branch\"]):,} branches')",
    "print()",
    "print('installed capacity by fuel, MW:')",
    "for fuel, mw in generation_mix(ppc).items():",
    "    print(f'  {fuel:10s} {mw:>9,.0f}')",
))

A(md(
    "### Distances, checked against the thing that knows them",
    "",
    "Corridor lengths recomputed from hub coordinates by a different formula "
    "from the one the notebook uses - the check that catches a transposed "
    "latitude. Taught in `capstone/AppA_texas_multi_city_buildout`.",
))

A(code(
    "from esm.buildout import (check_demand_shares, coal_cost_per_mwh,",
    "                         corridor_distances, gas_cost_per_mwh,",
    "                         load_buildout_instance)",
    "",
    "texas = load_buildout_instance()",
    "check_demand_shares(texas)",
    "print('corridor lengths, km:')",
    "for (a, b), km in corridor_distances(texas).items():",
    "    print(f'  {a[:14]:14s} - {b[:14]:14s} {km:>6.0f}')",
    "print()",
    "print(f'gas  ${gas_cost_per_mwh(texas):5.2f} /MWh-e all in')",
    "print(f'coal ${coal_cost_per_mwh(texas):5.2f} /MWh-e all in')",
))

A(md(
    "---",
    "## Part 4 - Does it hold together?",
    "",
    "Everything above came from the library. In each of the twelve notebooks, "
    "the same instance is also built **by hand**, and the notebook asserts the "
    "two agree to `AGREEMENT_RTOL`.",
    "",
    "This last cell checks that the library still produces what its own tests "
    "pin it to. If any line below is not `ok`, something has drifted and the "
    "notebook that teaches it will fail too.",
))

A(code(
    "from esm.tolerance import AGREEMENT_RTOL, relative",
    "",
    "# Full precision, not the rounded figures printed above. A pin typed to",
    "# fewer digits than it has is a pin that cannot be checked tightly -- and",
    "# writing one out by eye is how invented digits get in.",
    "pinned = [",
    "    ('house balance, kWh in', house.total_in, 44430.0),",
    "    ('coal break-even, $/MWh',",
    "     lcoe_by_crf(screen, screen.plants[('coal', 10000)]),",
    "     55.47917398532572),",
    "    ('transport, $/day', ship.cost, 490000.0),",
    "    ('sourcing, $/yr', base.cost, 600.0),",
    "    ('dispatch, $/day', alone.cost, 1669377.7545368262),",
    "    ('facility bill, $/yr', do_nothing, 23484661.71359483),",
    "    ('buses parsed', float(len(ppc['bus'])), 2000.0),",
    "]",
    "",
    "worst = max(relative(got, want) for _, got, want in pinned)",
    "for label, got, want in pinned:",
    "    ok = 'ok' if relative(got, want) < AGREEMENT_RTOL else 'DRIFTED'",
    "    print(f'{label:26s} {got:>16,.4f}  {ok}')",
    "",
    "assert worst < AGREEMENT_RTOL, (",
    "    f'the library has drifted from its pinned results by {worst:.2e}')",
    "print()",
    "print(f'every model matches its pinned result to {worst:.1e}')",
))

A(md(
    "---",
    "### Where to go next",
    "",
    "| you want | open |",
    "|---|---|",
    "| the accounting, from nothing | `p1_foundations/02_one_house_balance` |",
    "| what a model boundary is | `p1_foundations/01_model_boundary` |",
    "| your own meter data | `p2_demand/05_representative_days` |",
    "| costs before optimisation | `p3_generation/09_capital_and_lcoe` |",
    "| the transport problem | `p4_networks/17_pipeline_transport` |",
    "| prices on a network | `p4_networks/18_power_flow_and_lmp` |",
    "| a real network, with its defects | `p4_networks/15_real_network_import` |",
    "| a decision to defend | `capstone/AppA_facility_decision` |",
    "| the same model in two tools | `graduate/model_diversity` |",
    "",
    "Each of those builds its model by hand first. This notebook called the "
    "finished library; they are where the library comes from.",
))


def syntax_check(cells):
    bad = 0
    for i, c in enumerate(cells):
        if c["cell_type"] != "code":
            continue
        try:
            compile("".join(c["source"]), f"<cell {i}>", "exec")
        except SyntaxError as e:
            bad += 1
            print(f"cell {i} failed to compile: {e}")
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
    syntax_check(C)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(NOTEBOOK, f, indent=1, ensure_ascii=False)
    print("wrote", os.path.relpath(OUT, ROOT))
    print("cells: %d (%d code, %d markdown)"
          % (len(C), sum(1 for c in C if c["cell_type"] == "code"),
             sum(1 for c in C if c["cell_type"] == "markdown")))
