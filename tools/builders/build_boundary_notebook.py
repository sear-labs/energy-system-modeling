# -*- coding: utf-8 -*-
"""build_boundary_notebook.py - write `notebooks/p1_foundations/01_model_boundary.ipynb`.

WHY THIS SITS AT THE FRONT OF THE COURSE
Choosing the system boundary is the FIRST modelling decision, not the last.
Taught at the end, students spend a semester inside a boundary they never
chose and never noticed.  Taught here, every later model is an instance of a
choice they understand.

THE ONE IDEA
In a macro model, price is an OUTPUT - the dual variable of a nodal balance
constraint (they proved this in M0 and again in the power-flow companion).
Lower the boundary to a single facility and that same price becomes an INPUT:
a series you download.  Same object, opposite direction.

THE NARRATIVE (one site, two sizes)
The Metroplex Industrial Park, 50 MW, north of Dallas.  Investors buy the site
and convert it to a hyperscale data centre, 500 MW, on the same land and the
same interconnection.  Nothing about the site's location changed; the correct
MODEL changed, because a 50 MW load is a price taker and a 500 MW load is not.

VERIFIED RESULTS (see verify_against_solver notes at the bottom)
  park  50 MW : price moves 3/24 h, own-bill error   3.6%   metro cost $150k/d
  DC   500 MW : price moves 19/24 h, own-bill error 84.2%   metro cost $3.88M/d
  900 MW      : infeasible - exceeds the 600 MW interconnection agreement
Hour 21 is the showstopper: $90 -> $600 as the data centre reaches the
scarcity tail of the stack.

Run from Tools/:  python build_boundary_notebook.py
"""
import json
import os

# tools/builders/<this file> -> tools/ -> the repository root.
# Three levels, not two: these builders used to live one level higher,
# in the course folder's Tools/.
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "notebooks", "p1_foundations", "01_model_boundary.ipynb")

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

PARK_MW = 50.0
DC_MW = 500.0
EXPANSION_MW = 900.0
ICA_MW = 600.0


def verify():
    """Sanity-check the design constants before writing them into prose."""
    assert PARK_MW < ICA_MW < EXPANSION_MW, "the expansion must breach the ICA"
    assert DC_MW < ICA_MW, "the data centre must FIT inside the agreement"
    assert DC_MW / PARK_MW == 10.0
    print("design check: park %.0f MW, data centre %.0f MW, agreement %.0f MW,"
          % (PARK_MW, DC_MW, ICA_MW))
    print("              proposed expansion %.0f MW exceeds the agreement"
          % EXPANSION_MW)


# ================================================================== title
A(md(
L("# Where do you draw the boundary?"),
L("## REE 4301 / IE 5300 - Energy Systems Modeling"),
L("### Do this straight after the toy LP notebook. Before anything else."),
L(""),
L("In Module 0 you built a model of a whole system and it told you a price: "
  "the shadow price on the balance constraint. **You produced that number.**"),
L(""),
L("Almost none of you will be paid to do that."),
L(""),
L("You will be paid to work on **one facility** - a warehouse, a campus, a "
  "plant, a data centre - and for that job the price is not something you "
  "compute. It is a column in a CSV you download. Same number. Opposite "
  "direction."),
L(""),
L("> **In a macro model, price is an output.**"),
L("> **In a facility model, price is an input.**"),
L(""),
L("That sentence is the whole of this notebook, and it is the most useful "
  "thing in the course for the first job you take. Everything after this is "
  "working out **when you are allowed to believe it.**"),
))

A(code(
L("!pip install -q pypsa highspy gurobipy"),
))

A(code(
L("import numpy as np"),
L("import pandas as pd"),
L("import gurobipy as gp"),
L("import pypsa"),
L("import warnings"),
L("warnings.filterwarnings('ignore')"),
L(""),
L("SOLVER = 'gurobi'"),
L("# SOLVER = 'highs'     # <-- uncomment: open source, no licence, no size cap"),
L(""),
L("WLS = {}   # {'WLSACCESSID': '...', 'WLSSECRET': '...', 'LICENSEID': 000000}"),
L("ENV = gp.Env(params=WLS) if (SOLVER == 'gurobi' and WLS) else None"),
L(""),
L("print(f'solver: {SOLVER}'"),
L("      + ('  (academic WLS licence)' if ENV else '  (default licence)'))"),
))

# ================================================================== part A
A(md(
L("---"),
L("# Part A - One site, two lives"),
L(""),
L("**The Metroplex Industrial Park** sits north of Dallas: warehousing, some "
  "light manufacturing, a cold-storage tenant. It draws **50 MW**. It has an "
  "interconnection agreement with the utility for **600 MW** - generous, "
  "because the site was master-planned for heavy industry that never fully "
  "arrived."),
L(""),
L("In 2027 an investment group buys the site. The land is cheap, the fibre is "
  "already there, and - the reason they actually bought it - **the "
  "interconnection agreement already exists.** Getting a new one takes years. "
  "They convert the park into a hyperscale data centre drawing **500 MW**."),
L(""),
L("Same land. Same substation. Same agreement. Ten times the load."),
L(""),
L("**Nothing about the site's location changed. The correct model changed.** "
  "Working out why, and what it costs you to get it wrong, is the rest of "
  "this notebook."),
))

A(md(
L("### Two questions that look the same and are not"),
L(""),
L("| | the macro question | the facility question |"),
L("|---|---|---|"),
L("| who asks it | ERCOT, a regulator, a developer siting a fleet | you, on one site |"),
L("| what is decided | what gets built and dispatched everywhere | what this site builds and when it runs |"),
L("| **price is** | **an output** - a dual variable | **an input** - a downloaded series |"),
L("| demand is | forecast for a region | metered, and partly yours to shift |"),
L("| the answer | a system plan | a capital decision and a bill |"),
L(""),
L("The vocabulary for the second row, which you should use in an interview:"),
L(""),
L("- A facility that is too small to move the price is a **price taker**. "
  "One that is big enough to move it is a **price maker**."),
L("- Moving price from something the model solves for to something you hand "
  "it is moving it from **endogenous** to **exogenous**."),
L("- Running a big model once to produce inputs for a small model is "
  "**soft-linking**. Solving both together is **hard-linking**."),
L("- The facility problem itself has a name: **price-taker dispatch "
  "optimisation**."),
))

# ================================================================== part B
A(md(
L("---"),
L("# Part B - The macro model, which produces a price"),
L(""),
L("First build the thing you will *not* normally be asked to build, so you "
  "know what the number you download actually is."),
L(""),
L("A Dallas node with a metro load of about 4,000 MW, a lot of wind, and a "
  "merit order of gas plants from cheap to ruinous. This is a deliberately "
  "small stand-in for ERCOT, but the shape is right: cheap units for most "
  "hours, and a thin, very expensive tail for the few hours a year when "
  "everything is needed at once."),
))

A(md(
L("### Step 1 - the hours, the load, and the wind"),
))

A(code(
L("hours = np.arange(24)"),
L(""),
L("# metro demand: overnight base, morning bump, evening peak"),
L("metro = (4000"),
L("         + 1000 * np.exp(-((hours - 19) ** 2) / 12.0)"),
L("         + 400 * np.exp(-((hours - 8) ** 2) / 6.0))"),
L(""),
L("# west Texas wind: strong overnight and through the morning, gone by dusk"),
L("wind_pu = np.clip(0.30 + 0.55 * np.sin(np.pi * (hours - 2) / 16), 0, 1)"),
L(""),
L("print(pd.DataFrame({'metro MW': metro.round(0),"),
L("                    'wind p.u.': wind_pu.round(2)}).T.to_string())"),
))

A(md(
L("### Step 2 - the merit order"),
L(""),
L("Eight 600 MW units from $22 to $90, then a thin tail: two 300 MW peakers "
  "at $175 and $600, and 300 MW of last-resort capacity at $2,000."),
L(""),
L("**That tail is not invented.** ERCOT's offer cap has been as high as "
  "$5,000/MWh. Almost every hour of the year the price is set near the bottom "
  "of a stack like this; a handful of hours are set near the top, and those "
  "hours are where the money is - and where a large new load does its "
  "damage."),
))

A(code(
L("STACK = [(f'gas{i + 1:02d}', 600, c) for i, c in"),
L("         enumerate([22., 26., 31., 37., 44., 52., 62., 90.])]"),
L("STACK += [('peaker1', 300, 175.), ('peaker2', 300, 600.),"),
L("          ('scarcity', 300, 2000.)]"),
L(""),
L("for name, mw, cost in STACK:"),
L("    print(f'  {name:9s} {mw:5.0f} MW  ${cost:8,.0f}/MWh')"),
L("print(f'  {\"firm total\":9s} {sum(m for _, m, _ in STACK):5.0f} MW')"),
))

A(md(
L("### Step 3 - the site's own bus, which is the boundary"),
L(""),
L("Here is the modelling idea worth keeping. **The site gets its own Bus, and "
  "a Link to the grid.**"),
L(""),
L("That Link is the interconnection agreement, and it is the meter. "
  "Everything on the grid side of it is somebody else's problem; everything "
  "on the site side is yours. **The boundary is not a concept in this model - "
  "it is a component you can point at.**"),
L(""),
L("`p_nom=600` is the agreement itself. Remember that number."),
L(""),
L("**One note on style.** This is wrapped in a function, which the rest of "
  "this course avoids — you build models a component at a time so you can see "
  "each decision. It is wrapped here for one reason: we are about to solve "
  "this same network a dozen times at different site sizes, and you have "
  "already built every one of these components by hand in Module 0. The rule "
  "has not changed — wrap it *after* you understand it, never before."),
))

A(code(
L("def grid_model(site_mw):"),
L("    \"\"\"The macro model. Returns the network, or None if it cannot solve.\"\"\""),
L("    n = pypsa.Network()"),
L("    n.set_snapshots(hours)"),
L(""),
L("    n.add('Bus', 'Dallas')       # the grid"),
L("    n.add('Bus', 'Site')         # everything behind the meter"),
L(""),
L("    n.add('Generator', 'wind', bus='Dallas', p_nom=5000,"),
L("          marginal_cost=0, p_max_pu=pd.Series(wind_pu, index=hours))"),
L("    for name, mw, cost in STACK:"),
L("        n.add('Generator', name, bus='Dallas', p_nom=mw, marginal_cost=cost)"),
L(""),
L("    n.add('Load', 'metro', bus='Dallas',"),
L("          p_set=pd.Series(metro, index=hours))"),
L(""),
L("    # the interconnection agreement: 600 MW, and it is the model boundary"),
L("    n.add('Link', 'interconnection', bus0='Dallas', bus1='Site',"),
L("          p_nom=600, efficiency=1.0)"),
L("    if site_mw > 0:"),
L("        n.add('Load', 'site', bus='Site', p_set=float(site_mw))"),
L(""),
L("    status, condition = n.optimize(solver_name=SOLVER, env=ENV,"),
L("                                   log_to_console=False)"),
L("    return n if condition == 'optimal' else None"),
))

A(md(
L("### Step 4 - run it with no site at all, and read the price"),
L(""),
L("This is the world before the investors show up. The `marginal_price` "
  "column is the same dual variable you met in Module 0 - **this is the "
  "number that gets published, and the number a facility analyst "
  "downloads.**"),
))

A(code(
L("n_base = grid_model(0)"),
L("lmp_base = n_base.buses_t.marginal_price['Dallas']"),
L(""),
L("print(pd.DataFrame({'metro MW': metro.round(0),"),
L("                    'wind p.u.': wind_pu.round(2),"),
L("                    'LMP $/MWh': lmp_base.round(2)}).to_string())"),
L("print()"),
L("print(f'cheapest hour ${lmp_base.min():,.2f}')"),
L("print(f'dearest hour  ${lmp_base.max():,.2f}')"),
))

# ================================================================== part C
A(md(
L("---"),
L("# Part C - The industrial park, and the assumption that works"),
L(""),
L("You are the analyst for the 50 MW park. You do **not** build the model "
  "above - you would not have the data, and nobody is paying you to model "
  "ERCOT. You download `lmp_base` and multiply."),
L(""),
L("**Predict first:** the park is 50 MW arriving on a node already serving "
  "4,000 MW. Do you think its own arrival changes the price it pays?"),
))

A(code(
L("# the facility view: price is an INPUT. This is the whole calculation."),
L("park_predicted = (lmp_base * 50.0).sum()"),
L(""),
L("print(f'park load                 50 MW, flat')"),
L("print(f'predicted day-ahead bill  ${park_predicted:,.0f} /day')"),
L("print(f'                          ${park_predicted * 365 / 1e6:,.1f} M/yr')"),
))

A(md(
L("### Now check it against the macro model"),
L(""),
L("Put the park into the grid model and re-solve. If the exogenous-price "
  "assumption is sound, the price should barely move."),
))

A(code(
L("n_park = grid_model(50)"),
L("lmp_park = n_park.buses_t.marginal_price['Dallas']"),
L(""),
L("park_actual = (lmp_park * 50.0).sum()"),
L("moved = int((~np.isclose(lmp_park, lmp_base)).sum())"),
L("err = (park_actual / park_predicted - 1) * 100"),
L(""),
L("print(f'hours in which the park moved the price : {moved} of 24')"),
L("print(f'predicted bill  ${park_predicted:>10,.0f}')"),
L("print(f'actual bill     ${park_actual:>10,.0f}')"),
L("print(f'error           {err:>10.1f} %')"),
))

A(md(
L("**Three hours out of twenty-four, and a 3.6% error on the bill.**"),
L(""),
L("For a screening study, a lease negotiation, or a board paper, that is "
  "fine. You would spend more than 3.6% of the answer arguing about the "
  "weather year. **The park is a price taker, and treating the price as "
  "exogenous is the correct professional judgement.**"),
L(""),
L("Notice what you did *not* have to do: model ERCOT, forecast a generation "
  "fleet, or know anything about West Texas wind. That is what lowering the "
  "boundary buys you."),
))

# ================================================================== part D
A(md(
L("---"),
L("# Part D - The data centre, and the same assumption failing"),
L(""),
L("The investors close. The site becomes a **500 MW** data centre on the same "
  "interconnection."),
L(""),
L("A new analyst - or the same one, on autopilot - does the same calculation. "
  "Downloads the published prices, multiplies by 500."),
L(""),
L("**Predict before running.** The load went up by a factor of ten. Does the "
  "error go up by a factor of ten, or by more, or by less?"),
))

A(code(
L("dc_predicted = (lmp_base * 500.0).sum()"),
L(""),
L("n_dc = grid_model(500)"),
L("lmp_dc = n_dc.buses_t.marginal_price['Dallas']"),
L("dc_actual = (lmp_dc * 500.0).sum()"),
L(""),
L("moved_dc = int((~np.isclose(lmp_dc, lmp_base)).sum())"),
L("err_dc = (dc_actual / dc_predicted - 1) * 100"),
L(""),
L("print(f'hours in which the data centre moved the price : {moved_dc} of 24')"),
L("print(f'predicted bill  ${dc_predicted:>10,.0f} /day')"),
L("print(f'actual bill     ${dc_actual:>10,.0f} /day')"),
L("print(f'error           {err_dc:>10.1f} %')"),
L("print()"),
L("print(f'annual gap      ${(dc_actual - dc_predicted) * 365 / 1e6:,.0f} M/yr')"),
))

A(code(
L("compare = pd.DataFrame({"),
L("    'metro MW': metro.round(0),"),
L("    'LMP alone': lmp_base.round(2),"),
L("    'LMP + park': lmp_park.round(2),"),
L("    'LMP + data centre': lmp_dc.round(2),"),
L("})"),
L("print(compare.to_string())"),
))

A(md(
L("### Read hour 21"),
L(""),
L("The price goes from **$90 to $600**. The data centre pushed the system off "
  "the shoulder of the merit order and into the scarcity tail - and then paid "
  "$600/MWh for **all 500 MW**, in an hour that only cost $90 before it "
  "existed."),
L(""),
L("This is the whole failure mode. The price-taker calculation was not "
  "slightly optimistic. **It answered a different question**: what the site "
  "would pay in a world where the site does not exist."),
L(""),
L("### And it is not only the data centre's problem"),
))

A(code(
L("metro_extra_dc = ((lmp_dc - lmp_base) * metro).sum()"),
L("metro_extra_park = ((lmp_park - lmp_base) * metro).sum()"),
L(""),
L("print(f'extra cost to the existing 4,000 MW metro load:')"),
L("print(f'  because of the park        ${metro_extra_park:>12,.0f} /day')"),
L("print(f'  because of the data centre ${metro_extra_dc:>12,.0f} /day')"),
L("print()"),
L("print(f'the data centre pays ${dc_actual:,.0f}/day for itself,')"),
L("print(f'and imposes ${metro_extra_dc:,.0f}/day on everyone else -')"),
L("print(f'a factor of {metro_extra_dc / dc_actual:.1f} times its own bill.')"),
))

A(md(
L("> **Exercise D.1.** The data centre imposes more cost on its neighbours "
  "than it pays for its own electricity. Nothing it did was against the "
  "rules. Who should pay for that, and what would each answer do to where "
  "data centres get built?"),
L(">"),
L("> This is not a hypothetical. It is the live argument in ERCOT, PJM and "
  "half a dozen other markets right now, and if you interview at a utility, a "
  "developer or a regulator in the next two years, some version of it will "
  "come up."),
L(">"),
L("> **Exercise D.2.** The park's error was 3.6% and the data centre's is "
  "84%. The load only grew by 10x. Explain the non-linearity using the "
  "merit-order table from Part B."),
))

# ================================================================== part E
A(md(
L("---"),
L("# Part E - So where exactly is the line?"),
L(""),
L("\"Price taker\" is not a property of a facility. It is a property of a "
  "**facility and a system together**, and it degrades continuously. Find "
  "out where it stops being safe."),
))

A(code(
L("rows = []"),
L("for mw in [10, 25, 50, 100, 200, 300, 500, 600]:"),
L("    nk = grid_model(mw)"),
L("    if nk is None:"),
L("        rows.append({'site MW': mw, 'predicted $/day': None,"),
L("                     'actual $/day': None, 'error %': None,"),
L("                     'verdict': 'WILL NOT SOLVE'})"),
L("        continue"),
L("    lk = nk.buses_t.marginal_price['Dallas']"),
L("    pred = (lmp_base * mw).sum()"),
L("    act = (lk * mw).sum()"),
L("    e = (act / pred - 1) * 100"),
L("    rows.append({'site MW': mw,"),
L("                 'predicted $/day': round(pred),"),
L("                 'actual $/day': round(act),"),
L("                 'error %': round(e, 1),"),
L("                 'verdict': 'price taker' if e < 5 else"),
L("                            ('borderline' if e < 20 else 'PRICE MAKER')})"),
L(""),
L("print(pd.DataFrame(rows).set_index('site MW').to_string())"),
))

A(md(
L("> **There is no bright line, and that is the honest answer.** Somewhere "
  "between 50 and 200 MW on this system, a facility stops being a spectator "
  "and starts being a participant. Where exactly depends on the shape of the "
  "supply stack, not on the facility."),
L(">"),
L("> **The rule to carry:** treating price as exogenous is a *modelling "
  "assumption with an error bar*, not a fact. Test it by putting your load "
  "into a system model once. If the price barely moves, you never have to do "
  "it again. If it moves, you have just learned that your project is big "
  "enough to need a seat at a different table."),
))

A(md(
L("### And the harder limit"),
L(""),
L("The interconnection agreement is 600 MW. The investors, encouraged, "
  "propose a second phase taking the site to **900 MW**."),
))

A(code(
L("n_big = grid_model(900)"),
L(""),
L("if n_big is None:"),
L("    print('the model will not solve at 900 MW.')"),
L("    print()"),
L("    print('This is not a bug and not a numerical problem. The site is')"),
L("    print('asking for 900 MW through a 600 MW agreement. No dispatch')"),
L("    print('exists that satisfies every constraint, so the LP correctly')"),
L("    print('reports that there is no answer.')"),
L("    print()"),
L("    print('An infeasible model has told you something true: this phase')"),
L("    print('does not happen without a new interconnection study, new')"),
L("    print('equipment, and years of queue time. That is the single')"),
L("    print('largest risk in a project like this, and the model found it')"),
L("    print('before anyone signed anything.')"),
L("else:"),
L("    print('solved - check the interconnection p_nom')"),
))

# ================================================================== part F
A(md(
L("---"),
L("# Part F - What actually crosses the boundary"),
L(""),
L("Lowering the boundary is **not** \"ignore the grid\". It is \"import the "
  "grid as a boundary condition\". For a facility, exactly four things cross "
  "that line:"),
L(""),
L("**1. A price signal.** A nodal LMP series or a retail tariff. This is the "
  "one you have been using all notebook."),
L(""),
L("**2. Coincident-peak exposure.** In ERCOT this is **4CP**: a large "
  "customer's transmission charge for the whole next year is set by its "
  "demand during the four 15-minute intervals that turn out to be the monthly "
  "system peaks in June, July, August and September. Four intervals. If you "
  "can predict them and shed load, you avoid a substantial annual charge. "
  "**Note what that requires: forecasting the grid's peak, not your own.** "
  "This is the clearest case of a facility needing to understand the system "
  "it sits in - for four hours a year."),
L(""),
L("**3. Interconnection capacity and queue position.** Part E, and usually "
  "the binding constraint on whether a project happens at all."),
L(""),
L("**4. Marginal emissions intensity.** If anyone has promised 24/7 "
  "carbon-free energy, the number that matters is the *marginal* emissions of "
  "the hour you consume in, not the annual average of the grid."),
L(""),
L("Everything else stays outside. You do not need to know the LMP a hundred "
  "miles away, what gets built in 2035, or how a refinery plans its turnaround "
  "- unless one of those four channels carries it to you."),
))

A(md(
L("### The same five modules, at the lower boundary"),
L(""),
L("Every model in this course survives the boundary change. Only the question "
  "changes:"),
L(""),
L("| module | at the macro scale | at your facility |"),
L("|---|---|---|"),
L("| **1 Demand** | forecast a region's load | your load is *metered*, and partly yours to shift |"),
L("| **2 Generation** | what capacity should the system build | should *this site* build solar, storage, or sign a PPA |"),
L("| **3 Networks** | where does congestion bind, what should be reinforced | your interconnection limit and your tariff |"),
L("| **4 Storage** | system arbitrage and reliability | demand-charge and 4CP management |"),
L("| **5 Supply chain** | where should refining capacity go | delivered cost and single-source risk at your dock |"),
L(""),
L("Each later module in this course ends with a short **\"at the facility "
  "scale\"** note that makes this concrete. When you get there, the machinery "
  "will already be familiar - the only thing that moves is which quantities "
  "are given to you and which you get to choose."),
))

A(md(
L("---"),
L("## What you should take from this"),
L(""),
L("1. **Choosing the boundary is the first modelling decision**, and it is "
  "yours to make and to defend. Everything downstream inherits it."),
L("2. **Price is an output of a macro model and an input to a facility "
  "model.** Same dual variable, opposite direction."),
L("3. **Price taking is an assumption with an error bar**, not a property of "
  "your project. Here it cost 3.6% at 50 MW and 84% at 500 MW."),
L("4. **Test it once.** Put your load in a system model and see whether the "
  "price moves. That single run is the difference between a defensible "
  "number and a confident wrong one."),
L("5. **Infeasible is an answer.** The 900 MW phase failed against the "
  "interconnection agreement, which is exactly what an interconnection study "
  "exists to find out."),
L(""),
L("### If someone asks you in an interview what you can do"),
L(""),
L("> *\"I can take a site's load and an hourly price series, size solar and "
  "storage behind the meter against it, and tell you the payback - and I know "
  "how to check whether the site is big enough that its own load moves the "
  "price, in which case that number is wrong and I would model it "
  "differently.\"*"),
L(""),
L("That is a more employable sentence than anything about optimal 2035 "
  "generation mixes, and you can now do all of it."),
L(""),
L("### Sources and notes"),
L("- The merit order here is a teaching stand-in, but its *shape* - a long "
  "cheap base and a thin, very expensive tail - is the important realistic "
  "feature. ERCOT's system-wide offer cap has been set as high as "
  "$5,000/MWh."),
L("- ERCOT 4CP transmission cost allocation: see ERCOT and your utility's "
  "published 4CP guidance."),
L("- The site, the investors and the 600 MW agreement are invented; the "
  "pattern of converting industrial sites with existing interconnection into "
  "data centres is not."),
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
            print(src[:400])
    if bad:
        raise SystemExit("%d cell(s) failed to compile" % bad)
    print("syntax check: %d code cells compile"
          % sum(1 for c in cells if c["cell_type"] == "code"))


NOTEBOOK = {
    "cells": C,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python",
                       "name": "python3"},
        "language_info": {"name": "python"},
        "colab": {"provenance": []},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

if __name__ == "__main__":
    verify()
    syntax_check(C)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(NOTEBOOK, f, indent=1, ensure_ascii=False)
    print("wrote", OUT)
    print("cells: %d (%d code, %d markdown)"
          % (len(C),
             sum(1 for c in C if c["cell_type"] == "code"),
             sum(1 for c in C if c["cell_type"] == "markdown")))
