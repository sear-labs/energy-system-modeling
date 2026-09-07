# -*- coding: utf-8 -*-
"""build_sb6_notebook.py - write `2026 Fall/Notebooks/SB6_Multi_City_Texas_Buildout.ipynb`,
the student-facing notebook for SB6-SPEC (Assignment Catalog Part Four).

Structured as the catalog specifies: Stage 1 turns the 3-node template into
named Texas hubs, Stage 2 adds fuel and material sub-networks feeding
individual generators, Stage 3 goes multi-period and asks for an
interpretation.  The Spring 2026 student reference project
`Texas_Grid_Expansion_PyPSA.ipynb` is the structural model, as the catalog
says - its block layout, its NREL ATB 2024 / EIA 2023 cost basis, and its
`Link`-as-power-plant pattern are all carried over.

REAL DATA USED (not invented):
  - Hub demand shares are the real ERCOT weather-zone shares of daily energy,
    computed from TX-123BT nodal load for 20 January 2021 (a normal winter
    day): NCENT 32.1%, COAST 26.1%, SCENT 16.2%, FWEST+WEST 12.7%, and so on.
    Same dataset the GRAD-N notebook imports, so the two assignments share a
    factual basis.
  - Inter-hub distances are great-circle distances between the real city
    coordinates, so the length-based transmission cost is a real number.

FOUR DEFECTS IN THE SPRING REFERENCE NOTEBOOK, found by rebuilding and running
it, all of which this notebook fixes and then teaches:

  1. `gas_efficiency = 3.412 / heat_rate`.  On a Link whose bus0 carries
     MMBtu/h and whose bus1 carries MW, efficiency must be MWh-e per MMBtu,
     i.e. 1/heat_rate = 0.156 - not the dimensionless thermal efficiency
     0.533.  The reference notebook's own comment says "1/6.4 = 0.1563" while
     its code computes 0.533, so the intent was right and the line is wrong.
     Effect, measured on the Stage 3 model: gas becomes 3.41x cheaper per MWh
     delivered, the solver builds **zero wind** instead of 9.4 GW, less than
     half the storage, and reports a system cost 32% lower.  One unit error,
     an opposite policy conclusion.
  2. A Link's `p_nom` is its **input** capacity.  With a fuel bus on bus0 that
     is MMBtu/h, so `capital_cost` and any stated plant rating must be
     converted with the efficiency too.  Charging $/MW-e against MMBtu/h
     understates plant capital by the heat rate - a factor of 6.4.
  3. `investment_period_weightings = 8760` against 24 hourly snapshots counts
     24 x 8760 = 210,240 hours per period - twenty-four years of operating
     cost charged against one year of capital.  With capital expressed in
     $/MW/day the correct objective weighting is 365.
  4. Renewables are added with no `p_nom_max`, so every city self-supplies,
     no corridor ever binds, and the spatial model answers the one question it
     exists to answer with "transmission does not matter".

EVERYTHING BELOW WAS RUN (PyPSA 1.3.0 + HiGHS 1.15.1, this session):
  Stage 1 solves in ~2.3 s, Stage 2 in ~2.5 s, Stage 3 (72 snapshots,
  multi-period) in ~3.5 s.  Stage 3 optimum: 29.9 GW-e CCGT, 9.4 GW wind,
  30.4 GW solar, 6.0 GW storage, five corridors expanded, objective $35.4 bn
  across three representative years.

Run from Tools/:  python build_sb6_notebook.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "2026 Fall", "Notebooks",
                   "SB6_Multi_City_Texas_Buildout.ipynb")

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

# ================================================================== title
A(md(
L("# A multi-city Texas capacity buildout"),
L("## REE 4301 / IE 5300 / IE 6301 — Energy Systems Modeling"),
L("### Team assignment. Modules 2 and 3, culminating."),
L(""),
L("You have built a 1-node model (temporal only) and a 3-node model (spatial). "
  "This is where they become a system: named Texas load centres with real "
  "demand shares, real distances, a fuel network feeding the thermal plants, "
  "and more than one planning period."),
L(""),
L("**The three stages:**"),
L(""),
L("| Stage | What you add | The question it answers |"),
L("|---|---|---|"),
L("| 1 | Named Texas hubs, real demand and distances | Where does capacity "
  "get built when land and load are in different places? |"),
L("| 2 | Gas and coal sub-networks feeding generators | What does it cost to "
  "*deliver* fuel, and where does that bind? |"),
L("| 3 | Multiple planning periods | What gets built first, and what does the "
  "answer depend on? |"),
L(""),
L("Each stage runs on its own. Get Stage 1 solving before you start Stage 2."),
L(""),
L("**The structural model for this notebook is the Spring 2026 student "
  "reference project `Texas_Grid_Expansion_PyPSA.ipynb`.** You are welcome to "
  "read it. Be warned that it contains four unit and weighting errors, all of "
  "which are corrected here and two of which you will measure in Stage 2 — "
  "finding them is part of what this assignment teaches."),
))

A(code(
L("!pip install -q pypsa highspy gurobipy"),
))

A(code(
L("import numpy as np"),
L("import pandas as pd"),
L("import pypsa"),
L("import matplotlib.pyplot as plt"),
L(""),
L("pd.set_option('display.float_format', '{:,.2f}'.format)"),
L(""),
L("HOURS = 24                     # one representative day"),
L("PERIODS = [2030, 2040, 2050]"),
L("DISCOUNT = 0.07                # WACC"),
L(""),
L(""),
L("def crf(rate, years):"),
L('    """Capital recovery factor — annualises an overnight capital cost."""'),
L("    return rate * (1 + rate) ** years / ((1 + rate) ** years - 1)"),
L(""),
L(""),
L("def daily_capital(capex_per_mw, lifetime_years):"),
L('    """$/MW overnight -> $/MW/day.'),
L(""),
L("    Each period in this model is one 24-hour representative day, so every"),
L("    cost in the objective has to be on a per-day basis.  Mixing $/yr capital"),
L("    with $/day operating is the most common way to get a capacity-expansion"),
L("    answer that is wrong by three orders of magnitude."),
L('    """'),
L("    return capex_per_mw * crf(DISCOUNT, lifetime_years) / 365.0"),
L(""),
L(""),
L("print(f'CRF(7%, 30 yr) = {crf(0.07, 30):.4f}')"),
L("print(f'CRF(7%, 15 yr) = {crf(0.07, 15):.4f}')"),
))

# ================================================================ stage 1
A(md(
L('---\n'),
L('### Choosing a solver\n'),
L('\n'),
L('This notebook defaults to **HiGHS**, and the table below is why. `pip install gurobipy` ships a restricted licence that needs no registration at all, but it solves models only up to **2,000 variables and 2,000 constraints** — and two of the three stages here are past that. Switching costs nothing: HiGHS and Gurobi agree to sixteen significant figures on every model in this notebook.\n'),
L('\n'),
L('That ceiling arrives sooner than you would think. Measured sizes for the models in this course:\n'),
L('\n'),
L('| model | variables | constraints | restricted licence |\n'),
L('|---|---|---|---|\n'),
L('| 1-node, 24 hours | 123 | 291 | fits |\n'),
L('| SB6 Stage 1 | 766 | 1,837 | fits |\n'),
L('| SB6 Stage 2 | 886 | 2,172 | too big |\n'),
L('| SB6 Stage 3 | 2,614 | 6,444 | too big |\n'),
L('| TX-123BT, 24 hours | 16,080 | 38,304 | 19x over |\n'),
L('\n'),
L('When you exceed it, Gurobi returns *"Model too large for size-limited license"*. Two ways past it:\n'),
L('\n'),
L('**In class — switch to HiGHS.** Open source, no licence, no size limit. Uncomment the `SOLVER` line below. There is no accuracy cost: HiGHS and Gurobi agree to sixteen significant figures on every model here. The speed cost is real only when the problem is large — measured on a 1-node model, HiGHS is *marginally faster* at 24 hours, identical at one week, and about **12x slower** on a full 8,760-hour year (22 s against 1.8 s). On a mixed-integer unit-commitment problem with 2,880 binary variables the gap was only **1.8x**.\n'),
L('\n'),
L('**For homework — get an academic licence.** A free Web License Service (WLS) key from gurobi.com works in Colab with **no licence file**: paste the three values into `WLS` below. Build the environment **once** and reuse it — constructing a new one for every solve re-authenticates each time and will exhaust a WLS session partway through a scenario sweep.\n'),
))

A(code(
L("SOLVER = 'highs'      # open source, no licence, no size cap - and two of the\n"),
L("                      # three stages below are past Gurobi's free limit\n"),
L("# SOLVER = 'gurobi'   # <-- uncomment if you have an academic WLS key\n"),
L('\n'),
L('# For homework: paste your academic Web License Service key here.\n'),
L('# Leave it empty and Gurobi falls back to its restricted licence.\n'),
L("WLS = {}   # {'WLSACCESSID': '...', 'WLSSECRET': '...', 'LICENSEID': 000000}\n"),
L('\n'),
L('ENV = None\n'),
L("if SOLVER == 'gurobi' and WLS:\n"),
L('    import gurobipy as gp\n'),
L('    ENV = gp.Env(params=WLS)     # ONE environment, reused by every solve\n'),
L('\n'),
L("print(f'solver: {SOLVER}'\n"),
L("      + ('  (academic WLS licence)' if ENV else '  (default licence)'))\n"),
))

A(md(
L("---"),
L("## Stage 1 — From the 3-node template to named Texas hubs"),
L(""),
L("The 3-node model called its buses A, B and C. Naming them changes the "
  "assignment: once a bus is *Houston*, its demand, its resources and its "
  "distance to everywhere else are facts you have to source rather than "
  "choose."),
L(""),
L("### Demand"),
L(""),
L("The hub shares below are the real ERCOT weather-zone shares of daily "
  "energy, computed from the TX-123BT synthetic Texas system's nodal load for "
  "20 January 2021 — a normal winter day. (Same dataset the GRAD-N assignment "
  "imports.) North Central, which is Dallas–Fort Worth, is 32% of state "
  "energy; the Coast, which is Houston, is 26%."),
L(""),
L("> **Requirement.** You must state each node's assumed demand and available "
  "resources **with a citation**. The values here are a defensible starting "
  "point, not the only one. If you use a different source — ERCOT's own "
  "hourly load-by-weather-zone archive, for instance — say so and say why."),
))

A(code(
L("# (latitude, longitude) of each hub"),
L("HUBS = {"),
L("    'Dallas-Fort Worth': (32.7767, -96.7970),"),
L("    'Houston':           (29.7604, -95.3698),"),
L("    'San Antonio':       (29.4241, -98.4936),"),
L("    'Austin':            (30.2672, -97.7431),"),
L("    'West Texas':        (31.9973, -102.0779),"),
L("}"),
L(""),
L("# Share of statewide daily energy, from real ERCOT weather-zone data"),
L("# (TX-123BT nodal load, 20 January 2021).  The eight ERCOT weather zones"),
L("# carry, in order: NCENT 32.1%, COAST 26.1%, SCENT 16.2%, FWEST 9.6%,"),
L("# SOUTH 7.1%, EAST 3.8%, WEST 3.1%, NORTH 2.0%."),
L("#"),
L("# Mapping eight zones onto five hubs is a modelling decision, not a fact."),
L("# The one used here, which you may change if you justify it:"),
L("#   NCENT + NORTH        -> Dallas-Fort Worth"),
L("#   COAST + EAST         -> Houston"),
L("#   SCENT x 0.6 + SOUTH  -> San Antonio"),
L("#   SCENT x 0.4          -> Austin"),
L("#   FWEST + WEST         -> West Texas"),
L("HUB_SHARE = {"),
L("    'Dallas-Fort Worth': 0.341,"),
L("    'Houston':           0.299,"),
L("    'San Antonio':       0.168,"),
L("    'Austin':            0.065,"),
L("    'West Texas':        0.127,"),
L("}"),
L("assert abs(sum(HUB_SHARE.values()) - 1.0) < 1e-9, sum(HUB_SHARE.values())"),
L(""),
L("PEAK_2030_MW = 45_000.0        # statewide winter peak, ERCOT-scale"),
L("GROWTH = {2030: 1.00, 2040: 1.20, 2050: 1.44}   # +20% per decade"),
L(""),
L("for hub, share in HUB_SHARE.items():"),
L("    print(f'  {hub:20s} {share:5.1%}  ->  "
  "{PEAK_2030_MW*share:8,.0f} MW peak in 2030')"),
))

A(md(
L("### Distance, and why it belongs in the cost"),
L(""),
L("Transmission capital scales with length. If every corridor costs the same "
  "regardless of distance, the solver has no reason to prefer a short "
  "interconnection over a long one, and the spatial answer is arbitrary."),
L(""),
L("Great-circle distance between the hub coordinates is close enough for a "
  "planning model, and it is a real number you can defend. A right-of-way "
  "does not follow a great circle, so this understates route length — say so."),
))

A(code(
L("def haversine_km(a, b):"),
L('    """Great-circle distance between two (lat, lon) points, in km."""'),
L("    R = 6371.0"),
L("    lat1, lat2 = np.radians(a[0]), np.radians(b[0])"),
L("    dlat = lat2 - lat1"),
L("    dlon = np.radians(b[1] - a[1])"),
L("    h = (np.sin(dlat / 2) ** 2"),
L("         + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2)"),
L("    return 2 * R * np.arcsin(np.sqrt(h))"),
L(""),
L(""),
L("CORRIDORS = ["),
L("    ('West Texas', 'Dallas-Fort Worth'), ('West Texas', 'Austin'),"),
L("    ('Dallas-Fort Worth', 'Houston'),    ('Dallas-Fort Worth', 'Austin'),"),
L("    ('Houston', 'Austin'),               ('Austin', 'San Antonio'),"),
L("    ('Houston', 'San Antonio'),"),
L("]"),
L("LINE_CAPEX_PER_MW_KM = 1200.0   # $/MW-km, 345 kV double circuit"),
L("LINE_LIFE = 40"),
L(""),
L("for a, b in CORRIDORS:"),
L("    km = haversine_km(HUBS[a], HUBS[b])"),
L("    daily = daily_capital(LINE_CAPEX_PER_MW_KM * km, LINE_LIFE)"),
L("    print(f'  {a:20s} - {b:20s} {km:6.0f} km   "
  "${daily:7.2f} /MW/day')"),
))

A(md(
L("### Resource limits — the constraint that makes a spatial model mean "
  "anything"),
L(""),
L("This is the single most important line of modelling judgement in Stage 1."),
L(""),
L("If you let the solver build unlimited solar and wind at every hub, it will "
  "build them locally at every hub, no corridor will ever bind, and the model "
  "will report that transmission does not matter. That is not a finding — it "
  "is a consequence of forgetting that **land is a resource and it is not "
  "where the load is**."),
L(""),
L("`p_nom_max` per hub is how you express that. The numbers below are "
  "order-of-magnitude and are stated as assumptions, not facts. Changing them "
  "is one of the sensitivities Stage 3 asks for."),
))

A(code(
L("WIND_MAX = {'West Texas': 22_000, 'San Antonio': 4_000,"),
L("            'Dallas-Fort Worth': 3_000}"),
L("SOLAR_MAX = {'West Texas': 18_000, 'San Antonio': 4_000,"),
L("             'Dallas-Fort Worth': 4_000, 'Austin': 2_000, 'Houston': 3_000}"),
L(""),
L(""),
L("def profiles(seed=42):"),
L('    """A 24-hour demand shape and solar/wind capacity factors.'),
L(""),
L("    Placeholders.  Replace them with the profiles from your own"),
L("    Mini-Project 2 run, or with a real ERCOT day, before you submit -"),
L("    a sine wave is not a load shape and the grader will look."),
L('    """'),
L("    h = np.arange(HOURS)"),
L("    shape = np.clip("),
L("        0.60 + 0.40 * np.sin(np.pi * (h - 6) / 12) * ((h >= 6) & (h <= 22)),"),
L("        0.4, 1.0)"),
L("    shape = shape / shape.max()"),
L("    solar = np.zeros(HOURS)"),
L("    for k in range(6, 19):"),
L("        solar[k] = np.sin(np.pi * (k - 6) / 13)"),
L("    rng = np.random.default_rng(seed)"),
L("    wind = np.clip(0.35 + 0.25 * np.cos(2 * np.pi * h / 24)"),
L("                   + 0.10 * rng.normal(0, 1, HOURS), 0.05, 0.85)"),
L("    return shape, np.clip(solar, 0, 1), wind"),
L(""),
L(""),
L("demand_shape, solar_cf, wind_cf = profiles()"),
L("fig, ax = plt.subplots(figsize=(9, 3))"),
L("ax.plot(demand_shape, label='demand shape', color='k', lw=2)"),
L("ax.fill_between(range(HOURS), solar_cf, alpha=0.5, color='#DE6B1A',"),
L("                label='solar CF')"),
L("ax.fill_between(range(HOURS), wind_cf, alpha=0.4, color='#0064B1',"),
L("                label='wind CF')"),
L("ax.set_xlabel('hour'); ax.set_ylabel('per unit'); ax.legend(frameon=False)"),
L("plt.tight_layout(); plt.show()"),
))

# ============================================================== the builder
A(code(
L("# Cited cost basis: NREL ATB 2024 (capital, O&M, lifetimes),"),
L("# EIA 2023 (fuel prices and heat contents)."),
L("GAS_PRICE_MMBTU = 2.50 / 1.036      # $2.50/Mcf over 1.036 MMBtu/Mcf"),
L("COAL_PRICE_MMBTU = 20.0 / 13.0      # $20/ton Texas lignite, 13 MMBtu/ton"),
L("GAS_HEAT_RATE = 6.4                 # MMBtu per MWh-e, modern CCGT"),
L("COAL_HEAT_RATE = 10.0               # MMBtu per MWh-e, legacy unit"),
L("GAS_VOM, COAL_VOM = 3.50, 4.50      # $/MWh-e"),
L(""),
L("print(f'gas  ${GAS_PRICE_MMBTU:.3f}/MMBtu  ->  "
  "${GAS_PRICE_MMBTU*GAS_HEAT_RATE + GAS_VOM:.2f}/MWh-e all in')"),
L("print(f'coal ${COAL_PRICE_MMBTU:.3f}/MMBtu  ->  "
  "${COAL_PRICE_MMBTU*COAL_HEAT_RATE + COAL_VOM:.2f}/MWh-e all in')"),
))

A(md(
L("---"),
L("## Stage 1, one component at a time"),
L(""),
L("We are going to type this network out step by step. That is longer than "
  "wrapping it in a function, and it is deliberate: **every line below is a "
  "modelling decision**, and you should see each one before it disappears "
  "into a `build()` call. Once you have seen them, we will wrap them - at "
  "the bottom, where the wrapping belongs."),
L(""),
L("Read the markdown above each cell before you run it. If you run the whole "
  "notebook at once you will get the right answer and learn nothing."),
))

A(md(
L("### Step 1 - the network, and what a snapshot costs you"),
L(""),
L("A **snapshot** is one time step the model solves. We use 24: one "
  "representative day, which then stands in for a whole year."),
L(""),
L("That substitution needs care. The day is weighted by 365 so that the fuel "
  "bill is a *year* of fuel and can be compared against a *year* of capital "
  "charge. Get this weighting wrong and you are setting one day of fuel "
  "against a year of capital - the model then builds almost nothing, burns "
  "gas forever, and hands you an answer that looks entirely plausible."),
))

A(code(
L("n1 = pypsa.Network()"),
L(""),
L("# Stage 1 is a single investment period; Stage 3 adds the rest."),
L("periods = PERIODS[:1]"),
L("snapshots = pd.MultiIndex.from_product("),
L("    [periods, range(HOURS)], names=['period', 'timestep'])"),
L("n1.set_investment_periods(periods=periods)"),
L("n1.set_snapshots(snapshots)"),
L(""),
L("# one representative day standing for a year: 24 h x 365 = 8,760 h"),
L("n1.investment_period_weightings['objective'] = 365.0"),
L("n1.investment_period_weightings['years'] = 10.0"),
L(""),
L("print(f'{len(n1.snapshots)} snapshots, {len(periods)} investment period')"),
))

A(md(
L("### Step 2 - carriers"),
L(""),
L("A **carrier** labels what kind of energy or material something moves. "
  "PyPSA does not need them in order to solve, but every grouped result you "
  "print later - capacity by technology, energy by fuel - groups on this "
  "column. Declaring them now is what makes the results readable later."),
))

A(code(
L("for c in ('AC', 'wind', 'solar', 'battery', 'gas', 'coal',"),
L("          'gas supply', 'coal supply'):"),
L("    n1.add('Carrier', c)"),
L(""),
L("print(list(n1.carriers.index))"),
))

A(md(
L("### Step 3 - the hubs"),
L(""),
L("One **Bus** per city. A bus is a place where power balances: everything "
  "arriving equals everything leaving, in every snapshot. That one equation "
  "per bus per hour is the backbone of the entire model - it is the same "
  "`Bus-nodal_balance` you met in Module 0, just repeated five times."),
))

A(code(
L("for hub in HUBS:"),
L("    n1.add('Bus', hub, carrier='AC')"),
L(""),
L("print(f'{len(n1.buses)} hubs: ' + ', '.join(n1.buses.index))"),
))

A(md(
L("### Step 4 - the corridors between them"),
L(""),
L("A **Line** is AC transmission. Three of the arguments below are worth "
  "stopping on:"),
L(""),
L("- **`x=0.0001 * km`** - reactance grows with length. This is what makes "
  "power split between parallel paths by physics rather than by the solver's "
  "preference, and it is the whole difference between a transport model and "
  "a power-flow model."),
L("- **`s_nom_min=3000`** - what already exists. The solver may add to the "
  "grid but may not tear it down."),
L("- **`capital_cost` scaled by `km`** - a longer line costs more, so "
  "distance enters the optimisation instead of sitting in a comment."),
L(""),
L("`s_nom_max=25_000` is deliberate headroom. A real corridor is limited by "
  "*stability*, well below what the wires could thermally carry, and Stage 3 "
  "adds that limit separately. If the wire itself were the tighter of the "
  "two, the stability limit could never bind and the Stage 3 experiment "
  "would silently measure nothing."),
))

A(code(
L("for a, b in CORRIDORS:"),
L("    km = haversine_km(HUBS[a], HUBS[b])"),
L("    n1.add('Line', f'{a[:3].upper()}_{b[:3].upper()}',"),
L("           bus0=a, bus1=b, length=km,"),
L("           x=0.0001 * km,"),
L("           s_nom=3000, s_nom_min=3000, s_nom_max=25_000,"),
L("           s_nom_extendable=True,"),
L("           capital_cost=daily_capital("),
L("               LINE_CAPEX_PER_MW_KM * km, LINE_LIFE))"),
L(""),
L("cols = ['bus0', 'bus1', 'length', 'x', 's_nom']"),
L("print(n1.lines[cols].round(1).to_string())"),
))

A(md(
L("### Step 5 - demand"),
L(""),
L("Each hub takes a share of the state peak, shaped by the same 24-hour "
  "profile and grown by period."),
L(""),
L("`p_set` is a fixed requirement, not a choice: the model must serve it in "
  "every hour or the problem is infeasible. That is why an unserved-energy "
  "generator is a genuine modelling device rather than a cheat - without "
  "one, a model that cannot cope simply refuses to solve, and tells you "
  "nothing at all about how badly it fell short."),
))

A(code(
L("shape, solar_cf, wind_cf = profiles()"),
L(""),
L("for hub, share in HUB_SHARE.items():"),
L("    series = np.concatenate("),
L("        [shape * PEAK_2030_MW * share * GROWTH[p] for p in periods])"),
L("    n1.add('Load', f'{hub}_demand', bus=hub,"),
L("           p_set=pd.Series(series, index=snapshots))"),
L(""),
L("peak = n1.loads_t.p_set.sum(axis=1).max()"),
L("energy = n1.loads_t.p_set.sum().sum()"),
L("print(f'coincident peak {peak:,.0f} MW')"),
L("print(f'daily energy    {energy:,.0f} MWh')"),
))

A(md(
L("### Step 6 - wind and solar"),
L(""),
L("Two arguments carry the whole meaning here:"),
L(""),
L("- **`p_nom_extendable=True`** - capacity is a *decision*, not an input. "
  "This single argument is what turns a dispatch model into a "
  "capacity-expansion model."),
L("- **`p_nom_max`** - how much can physically be built at that hub. Without "
  "it the model will cheerfully build 200 GW of wind in San Antonio, and the "
  "answer will be arithmetically correct and completely useless."),
L(""),
L("`p_max_pu` is the hourly capacity factor: the *fraction* of whatever gets "
  "built that is actually available in each hour."),
))

A(code(
L("solar_ts = pd.Series(np.tile(solar_cf, len(periods)), index=snapshots)"),
L("wind_ts = pd.Series(np.tile(wind_cf, len(periods)), index=snapshots)"),
L(""),
L("for hub, cap in WIND_MAX.items():"),
L("    n1.add('Generator', f'{hub}_wind', bus=hub, carrier='wind',"),
L("           p_nom_extendable=True, p_nom_max=cap, p_max_pu=wind_ts,"),
L("           capital_cost=daily_capital(1_300_000, 30), marginal_cost=0.0)"),
L(""),
L("for hub, cap in SOLAR_MAX.items():"),
L("    n1.add('Generator', f'{hub}_solar', bus=hub, carrier='solar',"),
L("           p_nom_extendable=True, p_nom_max=cap, p_max_pu=solar_ts,"),
L("           capital_cost=daily_capital(900_000, 30), marginal_cost=0.0)"),
L(""),
L("print(n1.generators[['bus', 'carrier', 'p_nom_max']].to_string())"),
))

A(md(
L("### Step 7 - storage"),
L(""),
L("`max_hours=4` means the energy store is four times the power rating, so a "
  "100 MW battery holds 400 MWh. The 0.927 efficiencies are one-way, so the "
  "round trip is 0.927 squared - about 86%."),
L(""),
L("`cyclic_state_of_charge=True` forces the battery to end the day where it "
  "started. Leave it off and the model starts every representative day with "
  "a full battery it never had to charge: free energy, 365 times a year."),
))

A(code(
L("for hub in HUBS:"),
L("    n1.add('StorageUnit', f'{hub}_battery', bus=hub, carrier='battery',"),
L("           p_nom_extendable=True, max_hours=4,"),
L("           efficiency_store=0.927, efficiency_dispatch=0.927,"),
L("           cyclic_state_of_charge=True,"),
L("           capital_cost=daily_capital(400_000, 15), marginal_cost=0.001)"),
L(""),
L("rt = 0.927 ** 2"),
L("print(f'{len(n1.storage_units)} batteries, 4-hour, {rt:.1%} round trip')"),
))

A(md(
L("### Step 8 - gas, as a price rather than as a network"),
L(""),
L("In Stage 1 gas is one **Generator** with an all-in marginal cost: fuel "
  "plus variable O&M, in dollars per MWh of electricity out. There is no "
  "pipeline, no wellhead, no fuel bus. Gas is simply available at Houston at "
  "a price."),
L(""),
L("That is a real and extremely common modelling choice, and it is exactly "
  "what Stage 2 takes apart. Notice what it assumes: **unlimited fuel, "
  "delivered instantly, at a price that never moves.** In February 2021 all "
  "three of those assumptions failed at the same time."),
))

A(code(
L("n1.add('Generator', 'Houston_CCGT', bus='Houston', carrier='gas',"),
L("       p_nom_extendable=True,"),
L("       capital_cost=daily_capital(1_050_000, 30) + 15_300 / 365,"),
L("       marginal_cost=GAS_VOM + GAS_PRICE_MMBTU * GAS_HEAT_RATE)"),
L(""),
L("mc = GAS_VOM + GAS_PRICE_MMBTU * GAS_HEAT_RATE"),
L("print(f'gas marginal cost ${mc:.2f}/MWh-e')"),
))

A(md(
L("### Step 9 - solve it"),
L(""),
L("**Predict before you run.** Write down now, in one line each: which "
  "technology gets built the most, and which corridor expands first? A "
  "number you had no expectation about teaches you nothing when it "
  "arrives."),
))

A(code(
L("status, condition = n1.optimize("),
L("    solver_name=SOLVER, env=ENV,"),
L("    multi_investment_periods=False, log_to_console=False)"),
L("assert condition == 'optimal', f'solver returned {status}/{condition}'"),
))
A(code(
L("# Stages 1 and 2 are single-period, so PyPSA ignores the investment-"),
L("# period weighting and the objective is the cost of ONE representative"),
L("# day.  Multiply by 365 for an annual figure."),
L("print(f'Stage 1 solved.  daily system cost ${n1.objective:,.0f}'"),
L("      f'  (~${n1.objective*365/1e9:,.1f} bn/yr)')"),
L("print()"),
L("built = n1.generators.p_nom_opt.groupby(n1.generators.carrier).sum()"),
L("for carrier, mw in built.sort_values(ascending=False).items():"),
L("    print(f'  {carrier:10s} {mw:9,.0f} MW')"),
L("print(f'  {\"storage\":10s} {n1.storage_units.p_nom_opt.sum():9,.0f} MW')"),
L("print()"),
L("expanded = n1.lines[n1.lines.s_nom_opt > n1.lines.s_nom + 1]"),
L("print('corridors the solver chose to expand:')"),
L("if len(expanded) == 0:"),
L("    print('  none')"),
L("for name, r in expanded.iterrows():"),
L("    print(f'  {name:10s} {r.bus0:20s} -> {r.bus1:20s} '"),
L("          f'{r.s_nom:6,.0f} -> {r.s_nom_opt:7,.0f} MW  ({r.length:.0f} km)')"),
))

A(md(
L("---"),
L("## Now the streamlined version"),
L(""),
L("You have watched every component go in, one at a time. From here on we "
  "need the *same* network several more ways - two fuel-efficiency settings, "
  "three stages, a gas-price sweep - and retyping it each time would be both "
  "tedious and an excellent way to introduce a difference you did not "
  "intend."),
L(""),
L("**So now we wrap it.** This is the right moment to do that: after you "
  "know what is inside, not before. The function below is the nine steps you "
  "just ran, plus the Stage 2 and Stage 3 branches, behind a `stage` "
  "switch."),
L(""),
L("The cell after it checks that the wrapper reproduces what you built by "
  "hand. That check is not ceremony - it is how you find out that the "
  "convenient version and the version you actually understand have quietly "
  "drifted apart."),
))

A(code(
L("def build(stage=3, fuel_efficiency='correct', gas_price_mmbtu=None):"),
L('    """Assemble the SB6 network.'),
L(""),
L("    stage 1 : hubs, transmission, renewables, storage; gas as a simple"),
L("              Generator with an all-in marginal cost"),
L("    stage 2 : + gas and coal sub-networks, plants become Links"),
L("    stage 3 : + multiple investment periods"),
L(""),
L("    fuel_efficiency : 'correct' uses 1/heat_rate.  'thermal' reproduces the"),
L("              Spring reference notebook's 3.412/heat_rate so Stage 2 can"),
L("              measure what the error does.  Never use 'thermal' for a"),
L("              result you intend to report."),
L('    """'),
L("    gas_price = (GAS_PRICE_MMBTU if gas_price_mmbtu is None"),
L("                 else gas_price_mmbtu)"),
L("    n = pypsa.Network()"),
L("    periods = PERIODS if stage >= 3 else PERIODS[:1]"),
L("    snapshots = pd.MultiIndex.from_product("),
L("        [periods, range(HOURS)], names=['period', 'timestep'])"),
L("    n.set_investment_periods(periods=periods)"),
L("    n.set_snapshots(snapshots)"),
L(""),
L("    # One 24-hour day stands for a year: 24 snapshots x 365 = 8760 h."),
L("    # The Spring reference weights the day by 8760, which counts 210,240"),
L("    # hours per period - 24 years of fuel against one year of capital."),
L("    n.investment_period_weightings['objective'] = 365.0"),
L("    n.investment_period_weightings['years'] = 10.0"),
L(""),
L("    for c in ('AC', 'wind', 'solar', 'battery', 'gas', 'coal',"),
L("              'gas supply', 'coal supply'):"),
L("        n.add('Carrier', c)"),
L(""),
L("    # ---- hubs and corridors --------------------------------------"),
L("    for hub in HUBS:"),
L("        n.add('Bus', hub, carrier='AC')"),
L("    for a, b in CORRIDORS:"),
L("        km = haversine_km(HUBS[a], HUBS[b])"),
L("        n.add('Line', f'{a[:3].upper()}_{b[:3].upper()}',"),
L("              bus0=a, bus1=b, length=km,"),
L("              x=0.0001 * km,          # reactance grows with length"),
L("              s_nom=3000, s_nom_min=3000, s_nom_max=25_000,"),
L("              # headroom on purpose: a real stability limit sits BELOW"),
L("              # the thermal rating of the wires - see Stage 3"),
L("              s_nom_extendable=True,"),
L("              capital_cost=daily_capital("),
L("                  LINE_CAPEX_PER_MW_KM * km, LINE_LIFE))"),
L(""),
L("    # ---- demand ---------------------------------------------------"),
L("    shape, solar_cf, wind_cf = profiles()"),
L("    for hub, share in HUB_SHARE.items():"),
L("        series = np.concatenate("),
L("            [shape * PEAK_2030_MW * share * GROWTH[p] for p in periods])"),
L("        n.add('Load', f'{hub}_demand', bus=hub,"),
L("              p_set=pd.Series(series, index=snapshots))"),
L(""),
L("    # ---- renewables and storage -----------------------------------"),
L("    solar_ts = pd.Series(np.tile(solar_cf, len(periods)), index=snapshots)"),
L("    wind_ts = pd.Series(np.tile(wind_cf, len(periods)), index=snapshots)"),
L("    for hub, cap in WIND_MAX.items():"),
L("        n.add('Generator', f'{hub}_wind', bus=hub, carrier='wind',"),
L("              p_nom_extendable=True, p_nom_max=cap, p_max_pu=wind_ts,"),
L("              capital_cost=daily_capital(1_300_000, 30), marginal_cost=0.0)"),
L("    for hub, cap in SOLAR_MAX.items():"),
L("        n.add('Generator', f'{hub}_solar', bus=hub, carrier='solar',"),
L("              p_nom_extendable=True, p_nom_max=cap, p_max_pu=solar_ts,"),
L("              capital_cost=daily_capital(900_000, 30), marginal_cost=0.0)"),
L("    for hub in HUBS:"),
L("        n.add('StorageUnit', f'{hub}_battery', bus=hub, carrier='battery',"),
L("              p_nom_extendable=True, max_hours=4,"),
L("              efficiency_store=0.927, efficiency_dispatch=0.927,"),
L("              cyclic_state_of_charge=True,"),
L("              capital_cost=daily_capital(400_000, 15), marginal_cost=0.001)"),
L(""),
L("    if stage < 2:"),
L("        # Gas as a plain Generator: fuel is a price, not a network."),
L("        n.add('Generator', 'Houston_CCGT', bus='Houston', carrier='gas',"),
L("              p_nom_extendable=True,"),
L("              capital_cost=daily_capital(1_050_000, 30) + 15_300 / 365,"),
L("              marginal_cost=GAS_VOM + gas_price * GAS_HEAT_RATE)"),
L("        return n"),
L(""),
L("    # ---- Stage 2: fuel and material sub-networks -------------------"),
L("    # Energy on these buses is MMBtu/h, NOT MW.  Every number that"),
L("    # crosses between a fuel bus and an AC bus needs a conversion."),
L("    n.add('Bus', 'Permian_gas', carrier='gas')"),
L("    n.add('Bus', 'Houston_gas', carrier='gas')"),
L("    n.add('Generator', 'Permian_wellhead', bus='Permian_gas',"),
L("          carrier='gas supply', p_nom=5e5,"),
L("          marginal_cost=gas_price)"),
L("    n.add('Link', 'Permian_Houston_pipeline', bus0='Permian_gas',"),
L("          bus1='Houston_gas', p_nom=3e5, efficiency=1.0,"),
L("          marginal_cost=0.50)          # $/MMBtu transport tariff"),
L(""),
L("    n.add('Bus', 'Lignite_mine', carrier='coal')"),
L("    n.add('Bus', 'SanAntonio_coalyard', carrier='coal')"),
L("    n.add('Generator', 'Lignite_seam', bus='Lignite_mine',"),
L("          carrier='coal supply', p_nom=1e5,"),
L("          marginal_cost=COAL_PRICE_MMBTU)"),
L("    n.add('Link', 'Lignite_rail', bus0='Lignite_mine',"),
L("          bus1='SanAntonio_coalyard', p_nom=5e4, efficiency=1.0,"),
L("          marginal_cost=0.75)          # $/MMBtu rail tariff"),
L(""),
L("    # A power plant is a Link from a fuel bus to an AC bus."),
L("    # efficiency = MWh-e out per MMBtu in = 1 / heat_rate."),
L("    # 3.412/heat_rate is the DIMENSIONLESS thermal efficiency and is wrong"),
L("    # here by exactly 3.412.  See the Stage 2 experiment below."),
L("    if fuel_efficiency == 'correct':"),
L("        eff_gas, eff_coal = 1 / GAS_HEAT_RATE, 1 / COAL_HEAT_RATE"),
L("    else:"),
L("        eff_gas = 3.412 / GAS_HEAT_RATE"),
L("        eff_coal = 3.412 / COAL_HEAT_RATE"),
L(""),
L("    # A Link's p_nom is its bus0 (INPUT) capacity, in MMBtu/h here."),
L("    # $/MW-e figures therefore have to be multiplied by efficiency, and a"),
L("    # plant's MW-e rating divided by it."),
L("    n.add('Link', 'Houston_CCGT', bus0='Houston_gas', bus1='Houston',"),
L("          carrier='gas', efficiency=eff_gas, p_nom_extendable=True,"),
L("          capital_cost=(daily_capital(1_050_000, 30)"),
L("                        + 15_300 / 365) * eff_gas,"),
L("          marginal_cost=GAS_VOM / GAS_HEAT_RATE)   # $/MMBtu of input"),
L("    n.add('Link', 'SanAntonio_coal', bus0='SanAntonio_coalyard',"),
L("          bus1='San Antonio', carrier='coal', efficiency=eff_coal,"),
L("          p_nom=400.0 / eff_coal,      # a 400 MW-e legacy unit"),
L("          p_nom_extendable=False, capital_cost=0.0,   # sunk"),
L("          marginal_cost=COAL_VOM / COAL_HEAT_RATE)"),
L("    return n"),
L(""),
L(""),
L("def solve(n, **kw):"),
L("    status, condition = n.optimize("),
L("        solver_name=SOLVER, env=ENV,"),
L("        multi_investment_periods=len(n.investment_periods) > 1,"),
L("        log_to_console=False, **kw)"),
L("    if condition != 'optimal':"),
L("        raise RuntimeError(f'solver returned {status}/{condition}')"),
L("    return n"),
))

A(md(
L("Same network, same answer - so from here the function is safe to trust:"),
))

A(code(
L("check = solve(build(stage=1))"),
L("rel = abs(check.objective - n1.objective) / n1.objective"),
L(""),
L("print(f'hand-built   ${n1.objective:,.2f}')"),
L("print(f'build(1)     ${check.objective:,.2f}')"),
L("print(f'relative difference {rel:.2e}')"),
L("assert rel < 1e-9, 'the wrapper does not reproduce the hand-built network'"),
L("print()"),
L("print('the wrapper reproduces the hand-built network exactly.')"),
))

A(md(
L("> **Exercise S1.1.** Which corridors expanded, and why those? Relate the "
  "answer to `WIND_MAX` and `SOLAR_MAX` — the corridors that expand are the "
  "ones that connect buildable resource to load."),
L(""),
L("> **Exercise S1.2.** Set every hub's `SOLAR_MAX` to 50,000 and re-solve. "
  "How much transmission does the solver build now? Explain in one sentence "
  "why an unconstrained spatial model is not a spatial model."),
))

# ================================================================ stage 2
A(md(
L("---"),
L("## Stage 2 — Fuel and material sub-networks"),
L(""),
L("In Stage 1 gas was a price: `marginal_cost = VOM + fuel × heat rate`. That "
  "is fine until you want to ask a question about the fuel itself — whether "
  "the pipeline binds, what a transport tariff is worth, what happens when "
  "the wellhead is constrained."),
L(""),
L("Stage 2 makes fuel a network:"),
L(""),
L("```"),
L("Permian wellhead --pipeline--> Houston gas bus --CCGT--> Houston AC bus"),
L("Lignite seam     --rail-----> San Antonio coalyard --plant--> SA AC bus"),
L("```"),
L(""),
L("The plants are now **Links**, not Generators: they consume from a fuel bus "
  "and deliver to an electrical bus."),
L(""),
L("### The unit conversion that decides your answer"),
L(""),
L("Everything on a fuel bus is in **MMBtu/h**. Everything on an AC bus is in "
  "**MW**. A `Link` between them has an `efficiency` that carries the "
  "conversion, and it must be **MWh-e out per MMBtu in**, which is "
  "`1 / heat_rate`. For a 6.4 MMBtu/MWh CCGT that is **0.156**."),
L(""),
L("It is very easy to write `3.412 / heat_rate` instead — 0.533 — because "
  "that is the *thermal* efficiency, the dimensionless number you would "
  "quote a plant by, and 3.412 MMBtu per MWh is a conversion you use "
  "constantly elsewhere. The Spring reference project makes exactly this "
  "mistake, in a line whose own comment states the correct value."),
L(""),
L("Run both and see what it costs you."),
))

A(code(
L("runs = {}"),
L("for label in ('correct', 'thermal'):"),
L("    m = solve(build(stage=2, fuel_efficiency=label))"),
L("    runs[label] = m"),
L("    eff = m.links.efficiency['Houston_CCGT']"),
L("    ccgt_mwe = m.links.p_nom_opt['Houston_CCGT'] * eff"),
L("    built = m.generators.p_nom_opt.groupby(m.generators.carrier).sum()"),
L("    print(f'--- efficiency convention: {label}   (eff = {eff:.4f})')"),
L("    print(f'    daily system cost    ${m.objective:>16,.0f}')"),
L("    print(f'    CCGT built           {ccgt_mwe:>12,.0f} MW-e')"),
L("    print(f'    wind built           {built.get(\"wind\", 0):>12,.0f} MW')"),
L("    print(f'    solar built          {built.get(\"solar\", 0):>12,.0f} MW')"),
L("    print(f'    storage built        "
  "{m.storage_units.p_nom_opt.sum():>12,.0f} MW')"),
L("    print()"),
))

A(md(
L("> **Exercise S2.1.** State the percentage difference in system cost "
  "between the two runs, and the difference in wind built. Then explain, in "
  "terms of $/MWh, *why* the wrong efficiency has that particular effect — "
  "what does dividing by 0.533 instead of 0.156 do to the delivered cost of a "
  "MWh of gas-fired electricity?"),
L(""),
L("> **Exercise S2.2.** This is the point of the exercise: **a single unit "
  "error produced a different policy recommendation, and both runs solved to "
  "optimality without a warning.** Describe one check you could build into "
  "your own notebook that would have caught it. (Hint: you know what a CCGT's "
  "marginal cost per MWh-e should be. Compute it from the model's own "
  "parameters and assert it.)"),
))

A(code(
L("# The check Exercise S2.2 asks for.  Assert your units against a number"),
L("# you can compute independently."),
L("m = runs['correct']"),
L("link = m.links.loc['Houston_CCGT']"),
L("implied_mwh = (link.marginal_cost + GAS_PRICE_MMBTU + 0.50) / link.efficiency"),
L("expected = GAS_VOM + (GAS_PRICE_MMBTU + 0.50) * GAS_HEAT_RATE"),
L("print(f'implied delivered cost  ${implied_mwh:6.2f} /MWh-e')"),
L("print(f'expected from the data  ${expected:6.2f} /MWh-e')"),
L("assert abs(implied_mwh - expected) < 0.01, 'unit error in the CCGT Link'"),
L("print('units check out')"),
L(""),
L("bad = runs['thermal'].links.loc['Houston_CCGT']"),
L("print(f\"\\nsame check on the 'thermal' run: \""),
L("      f'${(bad.marginal_cost + GAS_PRICE_MMBTU + 0.50) / bad.efficiency:.2f}'"),
L("      f' /MWh-e  <- {expected/((bad.marginal_cost + GAS_PRICE_MMBTU + 0.50)"),
L("                              / bad.efficiency):.2f}x too cheap')"),
))

A(code(
L("m = runs['correct']"),
L("print('fuel network utilisation:')"),
L("for name in ('Permian_Houston_pipeline', 'Lignite_rail'):"),
L("    flow = m.links_t.p0[name]"),
L("    cap = m.links.at[name, 'p_nom']"),
L("    print(f'  {name:28s} peak {flow.max():10,.0f} of {cap:10,.0f} MMBtu/h'"),
L("          f'  ({100*flow.max()/cap:4.1f}%)')"),
L(""),
L("print('\\nfuel burned over the representative day:')"),
L("supply = (m.generators_t.p.T.groupby(m.generators.carrier).sum().sum(axis=1))"),
L("for c in ('gas supply', 'coal supply'):"),
L("    if c in supply:"),
L("        print(f'  {c:14s} {supply[c]:12,.0f} MMBtu')"),
))

A(md(
L("> **Exercise S2.3.** Neither the pipeline nor the rail link is anywhere "
  "near its capacity. Lower `p_nom` on the pipeline until it binds, and "
  "report what the system does in response — does it build more gas "
  "elsewhere, more renewables, or shed load? That answer is the fuel "
  "network's shadow value, and it is the reason Stage 2 exists."),
))

# ================================================================ stage 3
A(md(
L("---"),
L("## Stage 3 — Multi-period expansion and interpretation"),
L(""),
L("Three planning periods — 2030, 2040, 2050 — each represented by one "
  "24-hour day, with demand growing 20% a decade."),
L(""),
L("### The weighting that has to be right"),
L(""),
L("Each period is one representative day standing for a year. With 24 hourly "
  "snapshots, the objective weighting for the period must be **365**, so that "
  "24 × 365 = 8,760 hours are counted. The Spring reference uses 8,760, which "
  "counts 210,240 hours — twenty-four years of fuel charged against one year "
  "of capital, which systematically over-values anything with a low marginal "
  "cost."),
L(""),
L("If your objective comes out in the hundreds of billions for a 45 GW "
  "system, this is why."),
))

A(code(
L("n3 = solve(build(stage=3))"),
L("print(f'Stage 3 solved.'),"),
L("print(f'  periods           {list(n3.investment_periods)}')"),
L("print(f'  snapshots         {len(n3.snapshots)}')"),
L("print(f'  hours per period  "
  "{len(n3.snapshots)//len(n3.investment_periods) * 365:,}')"),
L("print(f'  objective         ${n3.objective:,.0f}'"),
L("      f'  (three representative years)')"),
))

A(code(
L("eff = n3.links.efficiency['Houston_CCGT']"),
L("built = n3.generators.p_nom_opt.groupby(n3.generators.carrier).sum()"),
L("summary = pd.Series({"),
L("    'CCGT (MW-e)': n3.links.p_nom_opt['Houston_CCGT'] * eff,"),
L("    'coal (MW-e)': (n3.links.p_nom['SanAntonio_coal']"),
L("                    * n3.links.efficiency['SanAntonio_coal']),"),
L("    'wind (MW)': built.get('wind', 0.0),"),
L("    'solar (MW)': built.get('solar', 0.0),"),
L("    'storage (MW)': n3.storage_units.p_nom_opt.sum(),"),
L("})"),
L("print(summary.to_string())"),
L(""),
L("print('\\ncorridor capacity (MW):')"),
L("for name, r in n3.lines.iterrows():"),
L("    mark = '  <- expanded' if r.s_nom_opt > r.s_nom + 1 else ''"),
L("    print(f'  {name:10s} {r.length:5.0f} km  {r.s_nom:6,.0f} -> '"),
L("          f'{r.s_nom_opt:7,.0f}{mark}')"),
))

A(md(
L("### Merit order, and the corridor that binds"),
L(""),
L("The catalog asks for both, in each scenario. Merit order is the order in "
  "which the solver dispatched your technologies; the binding constraint is "
  "whichever line sits at its rating."),
))

A(code(
L("print('merit order — dispatch cost and energy by technology:')"),
L("energy = (n3.generators_t.p.T.groupby(n3.generators.carrier).sum()"),
L("          .sum(axis=1))"),
L("link_e = (n3.links_t.p1.abs().T.groupby(n3.links.carrier).sum().sum(axis=1))"),
L("rows = []"),
L("for carrier, mwh in energy.items():"),
L("    if carrier.endswith('supply') or mwh < 1:"),
L("        continue"),
L("    mc = n3.generators[n3.generators.carrier == carrier].marginal_cost.mean()"),
L("    rows.append((carrier, mc, mwh))"),
L("for carrier in ('gas', 'coal'):"),
L("    if carrier in link_e and link_e[carrier] > 1:"),
L("        hr = GAS_HEAT_RATE if carrier == 'gas' else COAL_HEAT_RATE"),
L("        price = GAS_PRICE_MMBTU + 0.50 if carrier == 'gas' \\"),
L("            else COAL_PRICE_MMBTU + 0.75"),
L("        vom = GAS_VOM if carrier == 'gas' else COAL_VOM"),
L("        rows.append((carrier, vom + price * hr, link_e[carrier]))"),
L("merit = (pd.DataFrame(rows, columns=['technology', '$/MWh-e', 'MWh'])"),
L("         .sort_values('$/MWh-e').reset_index(drop=True))"),
L("print(merit.to_string(index=False))"),
L(""),
L("util = n3.lines_t.p0.abs().div(n3.lines.s_nom_opt, axis=1)"),
L("print('\\nmost-loaded corridors (share of chosen capacity):')"),
L("for name, u in util.max().sort_values(ascending=False).head(4).items():"),
L("    print(f'  {name:10s} {100*u:5.1f}%   "
  "{int((util[name] > 0.999).sum()):2d} of '"),
L("          f'{len(util)} hours at the limit')"),
))

A(md(
L("---"),
L("### The constraint that actually binds in Texas"),
L(""),
L("So far every limit in this model has been **thermal** — an `s_nom` on a "
  "line, bounding a current the model computes. That is the only kind of "
  "limit a DC power flow can find on its own."),
L(""),
L("ERCOT's real system is mostly limited by something else. Its binding "
  "interfaces are published as **Generic Transmission Constraints**, and "
  "ERCOT describes them as tools for managing *non-thermal* System Operating "
  "Limits. The two that matter most for a model shaped like this one:"),
L(""),
L("| GTC | What it limits | 2027 | 2030 | Type |"),
L("|---|---|---|---|---|"),
L("| `WESTEX` | export out of West Texas | 12,240 MW | 16,200 MW | static |"),
L("| `N_TO_H` | import into Houston from the north | 5,595 MW | 5,595 MW | "
  "hourly profile from a voltage-stability study |"),
L(""),
L("*(ERCOT, 2025 Regional Transmission Plan Economic Study: Stability "
  "Interface Limits, RPG meeting 29 July 2025. The same table also lists "
  "`PNHNDL` 4,440 MW, `WHARTN` 1,285 MW, `ZAPSTR` 230 MW and `HMLTN` 70 MW; "
  "`MCCAMY` and the Valley constraints are listed at 9,999, which is ERCOT's "
  "notation for \"no limit needed\".)*"),
L(""),
L("Three things about this table are worth more than the numbers in it."),
L(""),
L("1. **`N_TO_H` comes from a voltage-stability study, not a thermal "
  "rating.** No power flow you can write produces it. It is measured "
  "elsewhere and handed to the planner."),
L("2. **A GTC constrains a *cut*, not a line, and in one direction only.** "
  "`WESTEX` bounds the total flow *leaving* West Texas on every path at once. "
  "You cannot express that as an `s_nom`, so it becomes an extra constraint "
  "on the signed sum of the flows. Note that the source table lists Valley "
  "Export and Valley Import as **separate** constraints with their own "
  "limits — so bounding the magnitude of a flow rather than its named "
  "direction imposes a limit nobody published."),
L("3. **`WESTEX` rises from 12,240 to 16,200 MW between 2027 and 2030.** No "
  "wire changed rating: ERCOT plans to *build* into that corridor. A stability "
  "limit is a decision variable at planning timescales even though it is a "
  "hard bound at operating timescales."),
L(""),
L("Note also `MCCAMY`, which carries no limit in these years **because a "
  "specific approved project removed it** — the Bearkat–North McCamey–Sand "
  "Lake 345 kV line, in service 2026. That is the Chapter 17 trade study "
  "happening in public, on a real system."),
))

A(code(
L("# Published ERCOT stability interface limits, mapped onto this model's"),
L("# corridors.  West Texas exports on two paths here, so WESTEX bounds their"),
L("# sum; North-to-Houston is carried by the DFW->Houston corridor."),
L("GTC = {"),
L("    'WESTEX': dict("),
L("        exporting='West Texas',"),
L("        lines=['WES_DAL', 'WES_AUS'],"),
L("        limit={2030: 12_240.0, 2040: 16_200.0, 2050: 16_200.0}),"),
L("    'N_TO_H': dict("),
L("        exporting='Dallas-Fort Worth',"),
L("        lines=['DAL_HOU'],"),
L("        limit={2030: 5_595.0, 2040: 5_595.0, 2050: 5_595.0}),"),
L("}"),
L(""),
L(""),
L("def gtc_constraints(n, snapshots):"),
L('    """Bound the SUM of flows across each interface, per period.'),
L(""),
L("    Passed to `n.optimize(extra_functionality=...)`.  This is the extra"),
L("    linear constraint Chapter 18.4 describes: pick the lines that cross the"),
L("    cut, sign them by direction, and bound the total."),
L('    """'),
L("    m = n.model"),
L("    flow = m['Line-s']"),
L("    for gname, spec in GTC.items():"),
L("        expr = sum("),
L("            (1.0 if n.lines.at[ln, 'bus0'] == spec['exporting'] else -1.0)"),
L("            * flow.sel({'name': ln})"),
L("            for ln in spec['lines'])"),
L("        for period, limit in spec['limit'].items():"),
L("            sel = [s for s in snapshots if s[0] == period]"),
L("            if not sel:"),
L("                continue"),
L("            # ONE-SIDED.  A GTC limits a named direction, not a"),
L("            # magnitude: ERCOT's own table lists Valley Export and"),
L("            # Valley Import as two separate constraints with their own"),
L("            # limits.  Bounding |flow| instead would clamp the reverse"),
L("            # direction at a limit nobody published for it."),
L("            m.add_constraints(expr.sel(snapshot=sel) <= limit,"),
L("                              name=f'GTC-{gname}-{period}')"),
L(""),
L(""),
L("def interface_flow(n, gname):"),
L('    """Total flow across one interface, signed positive in the export'),
L('    direction, for every snapshot."""'),
L("    spec = GTC[gname]"),
L("    total = 0.0"),
L("    for ln in spec['lines']:"),
L("        sign = 1.0 if n.lines.at[ln, 'bus0'] == spec['exporting'] else -1.0"),
L("        total = total + sign * n.lines_t.p0[ln]"),
L("    return total"),
))

A(md(
L("### Does the interface bind, and does it cost anything?"),
L(""),
L("Those are two different questions, and this model answers them "
  "differently. Solve the multi-period case with and without the interface "
  "constraints, at two fuel prices. The second price is not a stress test — "
  "it is roughly what gas cost in 2022, and carrying an unchanged 2023 price "
  "out to 2050 is one of the assumptions this notebook keeps telling you to "
  "challenge."),
))

A(code(
L("# Delivered gas cost is set by the wellhead price:"),
L("#   $/MWh-e = VOM + (wellhead + pipeline tariff) x heat rate"),
L("# The base case is EIA's 2023 wellhead price carried unchanged to 2050."),
L("# The second case is roughly what gas cost in 2022."),
L("HIGH_GAS_MMBTU = 5.98"),
L("for wellhead in (GAS_PRICE_MMBTU, HIGH_GAS_MMBTU):"),
L("    print(f'wellhead ${wellhead:5.3f}/MMBtu  ->  delivered '"),
L("          f'${GAS_VOM + (wellhead + 0.50) * GAS_HEAT_RATE:5.2f}/MWh-e')"),
L(""),
L("rows = []"),
L("solved = {}"),
L("for wellhead in (GAS_PRICE_MMBTU, HIGH_GAS_MMBTU):"),
L("    for label, extra in (('free', None), ('GTC', gtc_constraints)):"),
L("        n = build(stage=3, gas_price_mmbtu=wellhead)"),
L("        kw = dict(solver_name=SOLVER, env=ENV, multi_investment_periods=True,"),
L("                  log_to_console=False)"),
L("        if extra is not None:"),
L("            kw['extra_functionality'] = extra"),
L("        status, condition = n.optimize(**kw)"),
L("        assert condition == 'optimal', condition"),
L("        solved[(wellhead, label)] = n"),
L("        wx = interface_flow(n, 'WESTEX')"),
L("        peaks = {p: wx.loc[[s for s in n.snapshots if s[0] == p]].max()"),
L("                 for p in PERIODS}"),
L("        rows.append({"),
L("            'gas $/MMBtu': round(wellhead, 2), 'case': label,"),
L("            'objective $': n.objective,"),
L("            'wind MW': round("),
L("                n.generators.p_nom_opt.groupby(n.generators.carrier)"),
L("                .sum().get('wind', 0.0)),"),
L("            'WESTEX 2030': round(peaks[2030], 1),"),
L("            'WESTEX 2040': round(peaks[2040], 1),"),
L("        })"),
L("print()"),
L("print(pd.DataFrame(rows).to_string(index=False,"),
L("                                   float_format=lambda v: f'{v:,.1f}'))"),
L("LIMIT_2030 = GTC[\'WESTEX\'][\'limit\'][2030]"),
L("print(f'\\nthe 2030 limit is {LIMIT_2030:,.0f} MW')"),
))

A(code(
L("print('what the constraint did:\\n')"),
L("for wellhead in (GAS_PRICE_MMBTU, HIGH_GAS_MMBTU):"),
L("    free = solved[(wellhead, 'free')]"),
L("    held = solved[(wellhead, 'GTC')]"),
L("    d = held.objective - free.objective"),
L("    rel = abs(d) / free.objective"),
L("    sel30 = [s for s in free.snapshots if s[0] == 2030]"),
L("    f0 = interface_flow(free, 'WESTEX').loc[sel30].max()"),
L("    f1 = interface_flow(held, 'WESTEX').loc[sel30].max()"),
L("    print(f'wellhead ${wellhead:5.3f}/MMBtu')"),
L("    print(f'    WESTEX peak 2030   {f0:10,.2f}  ->  {f1:10,.2f} MW')"),
L("    print(f'    system cost        ${d:+,.2f}   '"),
L("          f'(relative {rel:.1e})')"),
L("    verdict = ('binding, and it costs something' if rel > 1e-8"),
L("               else 'binding, and it costs NOTHING' if abs(f0 - f1) > 1"),
L("               else 'not binding')"),
L("    print(f'    verdict            {verdict}\\n')"),
))

A(md(
L("### The result"),
L(""),
L("At the base fuel price nothing binds: the solver never builds out West "
  "Texas, so there is nothing to export and the limit is irrelevant. Whether "
  "an interface matters is a scenario question before it is a network "
  "question."),
L(""),
L("At the higher price the constraint **binds exactly** — the 2030 peak "
  "export is clipped from 12,366.6 MW to 12,240.00 MW, the published figure — "
  "and it costs **nothing**. Not a small amount: zero, to sixteen significant "
  "figures. The solver simply moves the same energy along a different path."),
L(""),
L("A constraint that binds exactly and costs nothing to satisfy. Before "
  "reading on: what would have to be true of this network for that to be "
  "possible?"),
L(""),
L("This model gives West Texas **two** export corridors that substitute for "
  "each other at no cost, because transmission here is lossless and both have "
  "spare capacity. Squeeze one interface and the power takes the other route "
  "for free. ERCOT operates West Texas export as one constrained interface, "
  "where binding it is expensive."),
L(""),
L("So the model reproduced the constraint. Did it reproduce the consequence? "
  "Compare that against the aggregation trap in Chapter 18.4, and say what "
  "you would have had to change to see the difference."),
))

A(md(
L("> **Exercise S3.1.** State, with the numbers, the difference between "
  "\"the constraint binds\" and \"the constraint is expensive\". Why can a "
  "model show the first and not the second?"),
L(""),
L("> **Exercise S3.2.** The `WESTEX` limit relaxes from 12,240 MW in 2027 to "
  "16,200 MW in 2030 with no line in your model changing rating. What is that "
  "relaxation representing, and what does it imply about treating stability "
  "limits as fixed inputs in a study that runs to 2050?"),
L(""),
L("> **Exercise S3.3.** Make the constraint expensive. Force the "
  "substitution away — cap `WES_AUS` at its existing 3,000 MW so West Texas "
  "has effectively one export path — and re-run. Report the new cost of the "
  "limit and explain what you changed about the *model* rather than about "
  "Texas."),
L(""),
L("> **Exercise S3.4.** This model has one West Texas node, so the `PNHNDL` "
  "constraint — 4,440 MW out of the Panhandle — has nowhere to attach: the "
  "Panhandle and West Texas are the same bus here, and a constraint between "
  "them cannot exist. Say what that does to your results and in which "
  "direction. This is the same trap as above, one level further in."),
L(""),
L("> **Exercise S3.5.** `N_TO_H` is defined as a limit on flow *into* Houston "
  "from the north, and the constraint above is written one-sided for that "
  "reason — ERCOT's own table lists Valley Export and Valley Import as "
  "separate constraints. Re-run with a two-sided limit (bound the magnitude "
  "instead of the direction) and report what it costs. You are now enforcing "
  "a limit nobody published; say how large the error is."),
))

A(md(
L("### What to hand in"),
L(""),
L("**Stage 1**"),
L("1. Each hub's assumed demand and available resources, **with a citation** "
  "for both. If you use the values in this notebook, cite them as given here "
  "and say what you would have preferred."),
L("2. The corridor table with lengths and length-based costs."),
L("3. Exercises S1.1 and S1.2."),
L(""),
L("**Stage 2**"),
L("4. At least one fuel or material sub-network feeding a generator, working."),
L("5. Exercises S2.1, S2.2 and S2.3. S2.2 — the unit assertion you would "
  "write — is worth more than the rest of Stage 2 put together."),
L(""),
L("**Stage 3**"),
L("6. Solutions for at least two planning years or scenarios."),
L("7. **The merit order and the binding transmission constraint in each "
  "scenario.**"),
L("8. **One assumption in your build that would most change the answer if it "
  "were wrong** — and the re-run that shows by how much. Candidates, in "
  "roughly descending order of leverage:"),
L("   - `WIND_MAX` / `SOLAR_MAX`: how much land you assume is buildable, and "
  "where"),
L("   - the demand shape, which here is a sine wave and should be your own "
  "Mini-Project 2 profile"),
L("   - `LINE_CAPEX_PER_MW_KM`, and the great-circle distance understating "
  "real route length"),
L("   - the fuel prices, which are 2023 figures used unchanged for 2050"),
L("   - **the representative day itself**: one smooth day cannot contain a "
  "week-long wind lull, so this model will under-build firm capacity and "
  "over-build storage. Say so."),
L(""),
L("Do not report a number without its unit, and do not report a build without "
  "the assumption that produced it."),
))

A(md(
L("---"),
# The facility question is four source elements - rule, blank, the
# question, blank - because that is what the notebook carries. It was
# a bare string here once, which emitted no trailing newline and ran
# the question into the next heading. See Tools/check_builders.py.
L(""),
L("*Before class: you decided what a whole state should build. A site at one of these hubs decides none of it. Given that this gets built around you, which of your results still matters, and which does not?*"),
L(""),
L("### Sources"),
L("- **NREL Annual Technology Baseline 2024** — capital costs, fixed and "
  "variable O&M, lifetimes (atb.nrel.gov)"),
L("- **EIA** — natural gas wellhead price and heat content; Texas lignite "
  "price and heat content (eia.gov)"),
L("- **ERCOT weather-zone demand shares** — computed from TX-123BT nodal "
  "load, 20 January 2021. Jin Lu et al., DOI 10.6084/m9.figshare.22144616, "
  "CC BY 4.0. The same dataset the GRAD-N assignment imports directly."),
L("- **Structural model** — `Texas_Grid_Expansion_PyPSA.ipynb`, Spring 2026 "
  "student reference project. Corrected here as described in Stages 2 and 3."),
L("- **PyPSA** — pypsa.readthedocs.io, multi-investment-period capacity "
  "expansion"),
))


def syntax_check(cells):
    """Compile every code cell before writing."""
    bad = idx = 0
    for c in cells:
        if c["cell_type"] != "code":
            continue
        idx += 1
        src = chr(10).join(l for l in "".join(c["source"]).splitlines()
                           if not l.strip().startswith("!"))
        try:
            compile(src, "<cell %d>" % idx, "exec")
        except SyntaxError as e:
            bad += 1
            print("cell %d line %s: %s" % (idx, e.lineno, e.msg))
            for j, l in enumerate(src.splitlines(), 1):
                if abs(j - (e.lineno or 0)) <= 1:
                    print("   %3d| %s" % (j, l))
    if bad:
        raise SystemExit("%d code cell(s) failed the syntax check" % bad)
    print("syntax check: %d code cells compile" % idx)


NOTEBOOK = {
    "cells": C,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python",
                       "name": "python3"},
        "language_info": {"name": "python", "pygments_lexer": "ipython3"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

if __name__ == "__main__":
    syntax_check(C)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(NOTEBOOK, f, indent=1, ensure_ascii=False)
    print("wrote", OUT)
    print("cells:", len(C), "(%d code, %d markdown)" % (
        sum(1 for c in C if c["cell_type"] == "code"),
        sum(1 for c in C if c["cell_type"] == "markdown")))
