# -*- coding: utf-8 -*-
"""build_grad_m_notebook.py - write `2026 Fall/Notebooks/GRAD_M_Model_Diversity.ipynb`,
the student-facing notebook for GRAD-M (Assignment Catalog Part Four,
IE 5300 / IE 6301 only).

THE DESIGN PROBLEM, AND HOW IT IS SOLVED

The catalog asks the student to "take a system you already solved in PyPSA,
assemble the same system's inputs through PowerGenome and solve it in GenX",
then "separate the cause into a data-assumption difference versus a
model-structure difference", with "OSeMOSYS via its PuLP or Pyomo
implementation" offered as a lighter open-source alternative.

GenX is Julia and PowerGenome is a heavyweight data pipeline; neither runs in a
notebook cell, and a notebook that only *describes* them would fail this
project's standard of actually running what it ships.  The PuLP route the
catalog already sanctions does run, so that is the spine of this notebook: the
student writes the same capacity-expansion problem a second time, from the
algebra, in PuLP - which is what OSeMOSYS_PuLP is - and compares.

That turns out to be better pedagogy than a tool tour, because it makes the
data-versus-structure decomposition *measurable* instead of rhetorical:

  * PyPSA-transport vs PuLP-transport, same data     -> should be identical
  * PyPSA-DC        vs PyPSA-transport, same data    -> pure structure
  * either model     across data scenarios            -> pure data

Part 6 documents the PowerGenome -> GenX route concretely for students who
want the full-weight version.

WHAT WAS MEASURED (PyPSA 1.3.0 + HiGHS, PuLP 3.3.2 + HiGHS, this session):

  * The two models first disagreed by **$1,679,382.69**, which is - to the
    cent, residual $0.00 - the daily capital charge on the 3,000 MW of
    pre-existing capacity on the seven corridors.  PyPSA charges capital only
    on capacity above an extendable asset's existing `s_nom`; the hand-written
    PuLP model charged the whole thing.  A bookkeeping convention, not physics.
    This is the notebook's central worked example and it is left in
    deliberately rather than quietly fixed.
  * With the convention aligned, the two agree to $0.00 under all four data
    scenarios tested (base, WACC 10%, gas $45/MWh, both).
  * The pure structural effect of Kirchhoff's voltage law - PyPSA-DC against
    PyPSA-transport with data held identical - is **$7,203.95, or +0.031%**.
    KVL forces 118 MW of extra capacity on the Houston-Austin corridor and
    5 MW on Houston-San Antonio because flows cannot be routed.
  * The data assumptions move the answer far more: gas at $45/MWh instead of
    $22.14 brings **29,000 MW of wind** into a build that had none.

The headline lesson, which the notebook states plainly: the accounting
convention mattered roughly 200 times more than the physics.  Students expect
the opposite.

Run from Tools/:  python build_grad_m_notebook.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "2026 Fall", "Notebooks",
                   "GRAD_M_Model_Diversity.ipynb")

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
L("# GRAD-M: Model Diversity — the Same System in a Second Tool"),
L("## REE 4301 / IE 5300 / IE 6301 — Energy Systems Modeling"),
L("### Graduate sections only. Individual work. After SB6."),
L(""),
L("Every model in this course has been PyPSA. That is a problem, because you "
  "have no way to tell which of your results are properties of *the system* "
  "and which are properties of *the tool*."),
L(""),
L("This assignment separates them. You will take a system you have already "
  "solved, express its inputs in a tool-neutral form, rebuild the identical "
  "optimisation problem in a second solver stack, and then account for every "
  "dollar of difference between the two answers."),
L(""),
L("**The claim you have to be able to defend at the end:** *this much of the "
  "difference is a data assumption, this much is model structure, and this "
  "much was a bookkeeping convention I had not noticed.*"),
L(""),
L("### Which second tool"),
L(""),
L("The assignment names **PowerGenome → GenX**. That is the full-weight "
  "route, it is what a research group would actually do, and it is documented "
  "in Part 6 — but GenX is Julia and PowerGenome is a substantial data "
  "pipeline, so neither runs inside this notebook."),
L(""),
L("The route taken here is the sanctioned lighter one: **OSeMOSYS via PuLP** "
  "— which, stripped of its own conventions, means *writing the "
  "capacity-expansion linear program yourself, from the algebra, in a "
  "different modelling library*. That is more work than downloading a second "
  "tool and it teaches more, because a difference you cannot explain is a "
  "difference in something you wrote."),
L(""),
L("**You may substitute GenX, OSeMOSYS-Pyomo, or the real OSeMOSYS_PuLP "
  "distribution if you prefer.** The deliverable is the decomposition, not "
  "the tool."),
))

A(code(
L("!pip install -q pypsa highspy pulp gurobipy"),
))

A(code(
L("import numpy as np"),
L("import pandas as pd"),
L("import pypsa"),
L("import pulp"),
L(""),
L("HOURS = 24"),
L("HUBS = ['West Texas', 'Dallas-Fort Worth', 'Houston', 'Austin',"),
L("        'San Antonio']"),
L("SHARE = {'West Texas': 0.127, 'Dallas-Fort Worth': 0.341,"),
L("         'Houston': 0.299, 'Austin': 0.065, 'San Antonio': 0.168}"),
L("PEAK_MW = 45_000.0"),
L(""),
L("# (from, to, km) — great-circle distances between the real hub coordinates"),
L("ARCS = [('West Texas', 'Dallas-Fort Worth', 503),"),
L("        ('West Texas', 'Austin', 455),"),
L("        ('Dallas-Fort Worth', 'Houston', 362),"),
L("        ('Dallas-Fort Worth', 'Austin', 293),"),
L("        ('Houston', 'Austin', 235),"),
L("        ('Austin', 'San Antonio', 118),"),
L("        ('Houston', 'San Antonio', 304)]"),
L("WIND_MAX = {'West Texas': 22_000, 'San Antonio': 4_000,"),
L("            'Dallas-Fort Worth': 3_000}"),
L("SOLAR_MAX = {'West Texas': 18_000, 'San Antonio': 4_000,"),
L("             'Dallas-Fort Worth': 4_000, 'Austin': 2_000, 'Houston': 3_000}"),
L("GAS_MAX = {'Houston': 30_000, 'Dallas-Fort Worth': 12_000}"),
L("GAS_MC = 22.14        # $/MWh-e delivered — from the SB6 unit check"),
L("LINE_CAPEX_PER_MW_KM, LINE_LIFE = 1200.0, 40"),
L("EXISTING_ARC_MW = 3000.0"),
L(""),
L(""),
L("def crf(rate, years):"),
L("    return rate * (1 + rate) ** years / ((1 + rate) ** years - 1)"),
L(""),
L(""),
L("def daily_capital(capex, life, wacc):"),
L("    return capex * crf(wacc, life) / 365.0"),
L(""),
L(""),
L("def profiles(seed=42):"),
L("    h = np.arange(HOURS)"),
L("    shape = np.clip(0.60 + 0.40 * np.sin(np.pi * (h - 6) / 12)"),
L("                    * ((h >= 6) & (h <= 22)), 0.4, 1.0)"),
L("    shape = shape / shape.max()"),
L("    solar = np.zeros(HOURS)"),
L("    for k in range(6, 19):"),
L("        solar[k] = np.sin(np.pi * (k - 6) / 13)"),
L("    rng = np.random.default_rng(seed)"),
L("    wind = np.clip(0.35 + 0.25 * np.cos(2 * np.pi * h / 24)"),
L("                   + 0.10 * rng.normal(0, 1, HOURS), 0.05, 0.85)"),
L("    return shape, np.clip(solar, 0, 1), wind"),
))

# =============================================================== interchange
A(md(
L('---\n'),
L('### Choosing a solver\n'),
L('\n'),
L('This notebook defaults to **Gurobi**. `pip install gurobipy` ships a restricted licence that needs no registration at all and solves models up to **2,000 variables and 2,000 constraints**.\n'),
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
L("SOLVER = 'gurobi'\n"),
L("# SOLVER = 'highs'     # <-- uncomment: open source, no licence, no size cap\n"),
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
L("## Part 1 — The interchange"),
L(""),
L("The first real task in any model comparison is getting the *same system* "
  "into both tools. That means writing your inputs down in a form that "
  "belongs to neither."),
L(""),
L("Five tables is enough for a capacity-expansion problem, and they map "
  "directly onto the five-part formulation this course requires:"),
L(""),
L("| Table | Formulation part |"),
L("|---|---|"),
L("| `demand` | parameters — 24 hours × 5 nodes of load |"),
L("| `tech` | parameters — capital, lifetime, marginal cost per technology |"),
L("| `limit` | constraints — buildable MW per node and technology |"),
L("| `avail` | parameters — hourly capacity factor per technology |"),
L("| `arcs` | parameters — corridors, existing capacity, expansion cost |"),
L(""),
L("**Neither model reads anything else.** If a number is not in these tables, "
  "it is a convention baked into one of the two tools, and finding it is the "
  "point of Part 3."),
))

A(code(
L("def export_tables(wacc=0.07, gas_mc=GAS_MC):"),
L('    """The tool-neutral bundle.  Write it to CSV and both models read it."""'),
L("    shape, solar_cf, wind_cf = profiles()"),
L(""),
L("    demand = pd.DataFrame({h: shape * PEAK_MW * SHARE[h] for h in HUBS},"),
L("                          index=range(HOURS))"),
L(""),
L("    tech = pd.DataFrame(["),
L("        dict(tech='wind',  capex=1_300_000, life=30, mc=0.0),"),
L("        dict(tech='solar', capex=  900_000, life=30, mc=0.0),"),
L("        dict(tech='gas',   capex=1_050_000, life=30, mc=gas_mc),"),
L("    ]).set_index('tech')"),
L("    tech['daily_capital'] = [daily_capital(r.capex, r.life, wacc)"),
L("                             for _, r in tech.iterrows()]"),
L(""),
L("    limit = pd.DataFrame(0.0, index=HUBS, columns=list(tech.index))"),
L("    for hub, mw in WIND_MAX.items():"),
L("        limit.loc[hub, 'wind'] = mw"),
L("    for hub, mw in SOLAR_MAX.items():"),
L("        limit.loc[hub, 'solar'] = mw"),
L("    for hub, mw in GAS_MAX.items():"),
L("        limit.loc[hub, 'gas'] = mw"),
L(""),
L("    avail = pd.DataFrame({'wind': wind_cf, 'solar': solar_cf,"),
L("                          'gas': np.ones(HOURS)}, index=range(HOURS))"),
L(""),
L("    arcs = pd.DataFrame(ARCS, columns=['a', 'b', 'km'])"),
L("    arcs['existing_mw'] = EXISTING_ARC_MW"),
L("    arcs['max_mw'] = 12_000.0"),
L("    arcs['daily_capital'] = [daily_capital(LINE_CAPEX_PER_MW_KM * k,"),
L("                                           LINE_LIFE, wacc)"),
L("                             for k in arcs.km]"),
L("    return dict(demand=demand, tech=tech, limit=limit, avail=avail,"),
L("                arcs=arcs)"),
L(""),
L(""),
L("tables = export_tables()"),
L("print('tech:'); print(tables['tech'].round(2).to_string())"),
L("print('\\nbuildable MW by node and technology:')"),
L("print(tables['limit'].astype(int).to_string())"),
L("print(f\"\\npeak demand {tables['demand'].sum(axis=1).max():,.0f} MW\")"),
))

# ================================================================== pypsa
A(md(
L("---"),
L("## Part 2 — Model A: PyPSA"),
L(""),
L("Two variants, because one of them is needed later to isolate structure:"),
L(""),
L("- **`dc`** — corridors are `Line` components, so PyPSA imposes Kirchhoff's "
  "voltage law: flow is set by impedance and cannot be routed."),
L("- **`transport`** — corridors are `Link` components with `p_min_pu = -1`, "
  "so flow is limited only by capacity and *can* be routed. This is the "
  "transportation formulation of Chapter 17, and it is what most "
  "capacity-expansion tools outside power-systems software actually use."),
L(""),
L("Everything else is identical between the two."),
))

A(code(
L("def pypsa_model(t, network='dc'):"),
L("    n = pypsa.Network()"),
L("    n.set_snapshots(pd.RangeIndex(HOURS, name='hour'))"),
L("    n.add('Carrier', 'AC')"),
L("    for tech in t['tech'].index:"),
L("        n.add('Carrier', tech)"),
L("    for hub in HUBS:"),
L("        n.add('Bus', hub, carrier='AC')"),
L(""),
L("    for _, r in t['arcs'].iterrows():"),
L("        name = f'{r.a[:3].upper()}_{r.b[:3].upper()}'"),
L("        if network == 'dc':"),
L("            n.add('Line', name, bus0=r.a, bus1=r.b, length=r.km,"),
L("                  x=0.0001 * r.km,"),
L("                  s_nom=r.existing_mw, s_nom_min=r.existing_mw,"),
L("                  s_nom_max=r.max_mw, s_nom_extendable=True,"),
L("                  capital_cost=r.daily_capital)"),
L("        else:"),
L("            n.add('Link', name, bus0=r.a, bus1=r.b, length=r.km,"),
L("                  p_min_pu=-1.0,          # bidirectional"),
L("                  p_nom=r.existing_mw, p_nom_min=r.existing_mw,"),
L("                  p_nom_max=r.max_mw, p_nom_extendable=True,"),
L("                  capital_cost=r.daily_capital)"),
L(""),
L("    for hub in HUBS:"),
L("        n.add('Load', f'{hub}_demand', bus=hub,"),
L("              p_set=t['demand'][hub].values)"),
L("        for tech, row in t['tech'].iterrows():"),
L("            cap = t['limit'].loc[hub, tech]"),
L("            if cap <= 0:"),
L("                continue"),
L("            n.add('Generator', f'{hub}_{tech}', bus=hub, carrier=tech,"),
L("                  p_nom_extendable=True, p_nom_max=cap,"),
L("                  p_max_pu=pd.Series(t['avail'][tech].values,"),
L("                                     index=n.snapshots),"),
L("                  capital_cost=row.daily_capital, marginal_cost=row.mc)"),
L("    return n"),
L(""),
L(""),
L("def solve_pypsa(n):"),
L("    status, condition = n.optimize(solver_name=SOLVER, env=ENV,"),
L("                                   log_to_console=False)"),
L("    assert condition == 'optimal', condition"),
L("    return n.objective"),
L(""),
L(""),
L("pypsa_dc = pypsa_model(tables, 'dc')"),
L("obj_dc = solve_pypsa(pypsa_dc)"),
L("pypsa_tr = pypsa_model(tables, 'transport')"),
L("obj_tr = solve_pypsa(pypsa_tr)"),
L("print(f'PyPSA, DC power flow   ${obj_dc:,.2f} / day')"),
L("print(f'PyPSA, transport       ${obj_tr:,.2f} / day')"),
))

# =================================================================== pulp
A(md(
L("---"),
L("## Part 3 — Model B: the same problem, written from the algebra in PuLP"),
L(""),
L("This is the assignment. Do not translate PyPSA's code — write the "
  "formulation out in the five parts the course requires and then type *that* "
  "in. If you paraphrase PyPSA you will reproduce PyPSA's conventions without "
  "knowing which ones you inherited, and the comparison will be worthless."),
L(""),
L("**Sets** — nodes *i*, technologies *g*, hours *h*, arcs *a = (i, j)*."),
L(""),
L("**Parameters** — `daily_capital[g]`, `mc[g]`, `limit[i,g]`, `avail[g,h]`, "
  "`demand[i,h]`, `arc_capital[a]`, `existing[a]`, `arc_max[a]`."),
L(""),
L("**Decision variables** — `cap[i,g] ≥ 0` built capacity; `disp[i,g,h] ≥ 0` "
  "dispatch; `acap[a] ≥ 0` corridor capacity; `flow[a,h]` free (signed)."),
L(""),
L("**Objective** — minimise"),
L(""),
L("&nbsp;&nbsp;&nbsp;&nbsp;Σ<sub>i,g</sub> daily_capital[g]·cap[i,g] "
  "&nbsp;+&nbsp; Σ<sub>a</sub> arc_capital[a]·acap[a] "
  "&nbsp;+&nbsp; Σ<sub>i,g,h</sub> mc[g]·disp[i,g,h]"),
L(""),
L("**Constraints** —"),
L(""),
L("- build limit: cap[i,g] ≤ limit[i,g]"),
L("- availability: disp[i,g,h] ≤ avail[g,h]·cap[i,g]"),
L("- corridor bounds: existing[a] ≤ acap[a] ≤ arc_max[a], and "
  "−acap[a] ≤ flow[a,h] ≤ acap[a]"),
L("- **nodal balance**: Σ<sub>g</sub> disp[i,g,h] + inflow − outflow = "
  "demand[i,h]"),
L(""),
L("Note what is *not* there: no Kirchhoff voltage law. This is a transport "
  "model, so it should be compared against PyPSA's `transport` variant, not "
  "its `dc` one. Comparing it to the DC run would confound structure with "
  "everything else."),
))

A(code(
L("def pulp_model(t, charge_existing=True):"),
L('    """Capacity expansion as a transport LP, built from the formulation.'),
L(""),
L("    charge_existing : whether corridor capital is charged on the whole of"),
L("        acap or only on what is built above the existing capacity.  This is"),
L("        the convention Part 4 is about; leave it True for the first run."),
L('    """'),
L("    T = list(range(HOURS))"),
L("    G = list(t['tech'].index)"),
L("    arcs = t['arcs'].set_index(['a', 'b'])"),
L("    A_ = list(arcs.index)"),
L(""),
L("    m = pulp.LpProblem('capacity_expansion', pulp.LpMinimize)"),
L("    cap = pulp.LpVariable.dicts('cap', (HUBS, G), lowBound=0)"),
L("    disp = pulp.LpVariable.dicts('disp', (HUBS, G, T), lowBound=0)"),
L("    acap = pulp.LpVariable.dicts('acap', A_, lowBound=0)"),
L("    flow = pulp.LpVariable.dicts('flow', (A_, T))     # signed, a -> b"),
L(""),
L("    arc_cost = pulp.lpSum("),
L("        arcs.daily_capital[a] * (acap[a] if charge_existing"),
L("                                 else acap[a] - arcs.existing_mw[a])"),
L("        for a in A_)"),
L("    m += (pulp.lpSum(t['tech'].daily_capital[g] * cap[i][g]"),
L("                     for i in HUBS for g in G)"),
L("          + arc_cost"),
L("          + pulp.lpSum(t['tech'].mc[g] * disp[i][g][h]"),
L("                       for i in HUBS for g in G for h in T))"),
L(""),
L("    for i in HUBS:"),
L("        for g in G:"),
L("            m += cap[i][g] <= t['limit'].loc[i, g]"),
L("            for h in T:"),
L("                m += disp[i][g][h] <= t['avail'][g][h] * cap[i][g]"),
L("    for a in A_:"),
L("        m += acap[a] >= arcs.existing_mw[a]"),
L("        m += acap[a] <= arcs.max_mw[a]"),
L("        for h in T:"),
L("            m += flow[a][h] <= acap[a]"),
L("            m += flow[a][h] >= -acap[a]"),
L("    for i in HUBS:"),
L("        for h in T:"),
L("            inflow = pulp.lpSum(flow[a][h] for a in A_ if a[1] == i)"),
L("            outflow = pulp.lpSum(flow[a][h] for a in A_ if a[0] == i)"),
L("            m += (pulp.lpSum(disp[i][g][h] for g in G)"),
L("                  + inflow - outflow == t['demand'][i][h])"),
L("    return m, cap, acap"),
L(""),
L(""),
L("def solve_pulp(m):"),
L("    m.solve(pulp.HiGHS(msg=False))"),
L("    assert pulp.LpStatus[m.status] == 'Optimal', pulp.LpStatus[m.status]"),
L("    return pulp.value(m.objective)"),
L(""),
L(""),
L("m, cap, acap = pulp_model(tables)"),
L("obj_pulp = solve_pulp(m)"),
L("print(f'PuLP, transport        ${obj_pulp:,.2f} / day')"),
L("print(f'PyPSA, transport       ${obj_tr:,.2f} / day')"),
L("print(f'difference             ${obj_pulp - obj_tr:,.2f}  "
  "({100*(obj_pulp-obj_tr)/obj_tr:+.2f}%)')"),
))

# ================================================================== debug
A(md(
L("---"),
L("## Part 4 — Account for the difference"),
L(""),
L("The two models disagree. Before reaching for physics, check whether they "
  "built different things — because if the *builds* are identical and only "
  "the *cost* differs, no optimisation decision changed and the difference is "
  "pure accounting."),
))

A(code(
L("pypsa_build = (pypsa_tr.generators.p_nom_opt"),
L("               .groupby(pypsa_tr.generators.carrier).sum())"),
L("pulp_build = pd.Series({g: sum(cap[i][g].value() for i in HUBS)"),
L("                        for g in tables['tech'].index})"),
L("compare = pd.DataFrame({'PyPSA': pypsa_build, 'PuLP': pulp_build})"),
L("compare['difference'] = compare.PyPSA - compare.PuLP"),
L("print('generation capacity built (MW):')"),
L("print(compare.round(1).to_string())"),
L(""),
L("arc_cmp = pd.DataFrame({"),
L("    'PyPSA': pypsa_tr.links.p_nom_opt.values,"),
L("    'PuLP': [acap[a].value() for a in tables['arcs']"),
L("             .set_index(['a', 'b']).index],"),
L("}, index=pypsa_tr.links.index)"),
L("arc_cmp['difference'] = arc_cmp.PyPSA - arc_cmp.PuLP"),
L("print('\\ncorridor capacity (MW):')"),
L("print(arc_cmp.round(1).to_string())"),
))

A(md(
L("### The builds are identical. So where does the money go?"),
L(""),
L("Nothing the solver decided is different, so the gap has to be a term one "
  "objective contains and the other does not. There is exactly one candidate: "
  "the **3,000 MW of corridor capacity that already exists**."),
L(""),
L("PyPSA charges `capital_cost` only on capacity built *above* an extendable "
  "asset's existing `s_nom`/`p_nom` — existing capacity is treated as sunk. "
  "The PuLP model as written charges the whole of `acap`, existing capacity "
  "included."),
L(""),
L("Test it: the gap should equal the daily capital charge on 3,000 MW across "
  "the seven corridors, exactly."),
))

A(code(
L("sunk = (EXISTING_ARC_MW * tables['arcs'].daily_capital).sum()"),
L("gap = obj_pulp - obj_tr"),
L("print(f'observed gap                            ${gap:>14,.2f}')"),
L("print(f'daily capital on 3,000 MW x 7 corridors ${sunk:>14,.2f}')"),
L("print(f'residual                                ${gap - sunk:>14,.2f}')"),
L("assert abs(gap - sunk) < 1.0, 'the gap is NOT just the sunk-cost convention'"),
L(""),
L("# Align the convention and re-solve."),
L("m2, cap2, acap2 = pulp_model(tables, charge_existing=False)"),
L("obj_pulp2 = solve_pulp(m2)"),
L("print(f'\\nPuLP with PyPSA\\'s sunk-cost convention  ${obj_pulp2:>14,.2f}')"),
L("print(f'PyPSA, transport                        ${obj_tr:>14,.2f}')"),
L("print(f'residual difference                     "
  "${obj_pulp2 - obj_tr:>14,.2f}')"),
))

A(md(
L("> **Exercise 4.1.** Neither convention is wrong. Say which one you would "
  "use for **(a)** a report recommending whether to build a new corridor and "
  "**(b)** a report comparing the total cost of two whole system designs, and "
  "why the answer differs between the two."),
L(""),
L("> **Exercise 4.2.** The gap was 7% of system cost, and it came from a "
  "convention neither model documents in its output. Describe the check you "
  "would run *first*, on any future model comparison, to catch this class of "
  "difference before you start looking for real ones. (You have just seen "
  "it: compare the decision variables before comparing the objective.)"),
))

# =============================================================== structure
A(md(
L("---"),
L("## Part 5 — Isolate structure, then isolate data"),
L(""),
L("With the conventions aligned, the two arms of the decomposition can be "
  "measured separately."),
L(""),
L("### Structure, with the data held fixed"),
L(""),
L("`PyPSA-DC` against `PyPSA-transport` is the cleanest structural experiment "
  "available: same tool, same tables, same solver, one difference — whether "
  "Kirchhoff's voltage law is imposed. Any gap is the cost of not being able "
  "to route power."),
))

A(code(
L("delta_structure = obj_dc - obj_tr"),
L("print(f'PyPSA, DC power flow   ${obj_dc:>14,.2f}')"),
L("print(f'PyPSA, transport       ${obj_tr:>14,.2f}')"),
L("print(f'cost of KVL            ${delta_structure:>14,.2f}   "
  "({100*delta_structure/obj_tr:+.3f}%)')"),
L(""),
L("dc_arcs = pypsa_dc.lines.s_nom_opt"),
L("tr_arcs = pypsa_tr.links.p_nom_opt"),
L("extra = (dc_arcs - tr_arcs).round(1)"),
L("print('\\nextra corridor capacity the DC model has to build (MW):')"),
L("print(extra[extra.abs() > 0.5].to_string() or '  none')"),
))

A(md(
L("### Data, with the structure held fixed"),
L(""),
L("Now vary the tables and re-solve **both** models. If the interchange is "
  "faithful, the two move together under every scenario and the residual "
  "stays at zero."),
))

A(code(
L("scenarios = ["),
L("    ('base (WACC 7%, gas $22.14/MWh)', {}),"),
L("    ('WACC 10%', dict(wacc=0.10)),"),
L("    ('gas $45/MWh', dict(gas_mc=45.0)),"),
L("    ('WACC 10% and gas $45/MWh', dict(wacc=0.10, gas_mc=45.0)),"),
L("]"),
L("rows = []"),
L("for label, kw in scenarios:"),
L("    t = export_tables(**kw)"),
L("    n = pypsa_model(t, 'transport')"),
L("    a = solve_pypsa(n)"),
L("    mm, cc, _ = pulp_model(t, charge_existing=False)"),
L("    b = solve_pulp(mm)"),
L("    built = n.generators.p_nom_opt.groupby(n.generators.carrier).sum()"),
L("    rows.append({"),
L("        'scenario': label,"),
L("        'PyPSA $': round(a, 2), 'PuLP $': round(b, 2),"),
L("        'residual $': round(b - a, 2),"),
L("        'wind MW': round(built.get('wind', 0.0)),"),
L("        'solar MW': round(built.get('solar', 0.0)),"),
L("        'gas MW': round(built.get('gas', 0.0)),"),
L("    })"),
L("print(pd.DataFrame(rows).to_string(index=False))"),
))

A(md(
L("### Read the table before moving on"),
L(""),
L("Three things should be visible in it."),
L(""),
L("1. **The residual is zero in every scenario.** The interchange is faithful: "
  "whatever else differs between these two models, it is not the data."),
L("2. **The data assumptions move the answer a great deal.** Gas at $45/MWh "
  "instead of $22.14 brings tens of gigawatts of wind into a build that had "
  "none. That is not a modelling difference at all — it is one number in one "
  "table."),
L("3. **Set that against the structural effect from the previous cell.** "
  "Kirchhoff's voltage law was worth a fraction of a percent. The accounting "
  "convention in Part 4 was worth seven percent. The fuel price is worth more "
  "than either."),
L(""),
L("That ordering is the result of this assignment, and it is not what most "
  "people expect. **The physics you argued about mattered least.**"),
))

# ============================================================== full weight
A(md(
L("---"),
L("## Part 6 — The full-weight route: PowerGenome → GenX"),
L(""),
L("If you want the version a research group would run, this is it. It does "
  "not fit in a notebook cell, and it is a legitimate substitute for Parts "
  "2–5 if you would rather do the decomposition across two genuinely separate "
  "tools."),
L(""),
L("**GenX** (`github.com/GenXProject/GenX`) is a Julia capacity-expansion "
  "model from MIT. It reads a directory of CSVs — `Generators_data.csv`, "
  "`Load_data.csv`, `Generators_variability.csv`, `Network.csv`, "
  "`Fuels_data.csv` — which is the same interchange idea as Part 1, with a "
  "fixed schema. Install Julia, then `] add GenX`, and run `run_genx_case!`."),
L(""),
L("**PowerGenome** (`github.com/PowerGenome/PowerGenome`) is the data "
  "pipeline that produces those CSVs from public sources — EIA 860/923, NREL "
  "ATB, EPA. It is a Python package with a YAML settings file, and it is "
  "where most of the work is: deciding how to cluster generators, which "
  "vintages to retain, what to do with must-run units."),
L(""),
L("**OSeMOSYS** (`osemosys.readthedocs.io`) has PuLP and Pyomo "
  "implementations that read a single tabular data file. Use the PuLP or "
  "Pyomo versions — the GAMS version needs a commercial licence and is "
  "excluded from this course."),
L(""),
L("### If you take this route"),
L(""),
L("The deliverable does not change: **decompose the difference**. But the "
  "decomposition is harder, because the two tools do not share a formulation, "
  "so you must account for at least these before you can claim a structural "
  "difference:"),
L(""),
L("- time resolution and representative-period weighting"),
L("- whether either tool applies a reserve margin or planning-reserve "
  "constraint by default"),
L("- unit commitment — GenX has commitment options PyPSA's LP relaxation "
  "does not"),
L("- the same sunk-versus-total capital convention you met in Part 4"),
L("- retirement and vintage handling"),
L(""),
L("Each of those is a *structural* difference. None is a difference in the "
  "system. Say which ones you controlled for and which you could not."),
))

A(md(
L("---"),
L("## What to hand in"),
L(""),
L("1. **The interchange.** The five tables, and one sentence on what a table "
  "does *not* carry — a convention you found in one tool that had to be set "
  "by hand in the other."),
L("2. **The second model.** Your own formulation, in the five parts, and the "
  "code that implements it. If you paraphrased the first model's code instead "
  "of writing the formulation, say so; it changes what the comparison means."),
L("3. **The reconciliation.** Every dollar of difference between the two "
  "answers, attributed. Do not report \"the models broadly agree\" — report "
  "the residual and what it is."),
L("4. **Where the optimal build differs**, and the cause split into a "
  "**data-assumption** difference and a **model-structure** difference, with "
  "the number for each. Parts 4 and 5 give you the method; the numbers are "
  "yours."),
L("5. **One thing your second tool makes easier to express than PyPSA, and "
  "one thing it makes harder.** Be concrete. \"PuLP made the objective "
  "explicit, so I could see the sunk-cost convention that PyPSA applies "
  "silently; PyPSA made the DC power flow one keyword, and reproducing "
  "Kirchhoff's voltage law by hand in PuLP would have meant building the "
  "cycle basis myself\" is the level of specificity expected."),
L(""),
L("### The trap to avoid"),
L(""),
L("A comparison that ends in \"the two models gave different answers, which "
  "shows the importance of model choice\" has not done the assignment. Any "
  "two models give different answers. **The assignment is the accounting.**"),
))

A(md(
L("---"),
# The facility question is four source elements - rule, blank, the
# question, blank - because that is what the notebook carries. It was
# a bare string here once, which emitted no trailing newline and ran
# the question into the next heading. See Tools/check_builders.py.
L(""),
L("*Before class: these two pipelines disagree. Which would you trust to size a single site's connection, and what is the other one actually answering?*"),
L(""),
L("### Sources"),
L("- **GenX** — github.com/GenXProject/GenX. Jenkins & Sepulveda, MIT Energy "
  "Initiative"),
L("- **PowerGenome** — github.com/PowerGenome/PowerGenome"),
L("- **OSeMOSYS** — osemosys.readthedocs.io. Use the PuLP or Pyomo "
  "implementation; the GAMS version requires a commercial licence"),
L("- **PuLP** — coin-or.github.io/pulp"),
L("- **PyPSA** — pypsa.readthedocs.io"),
L("- Cost basis and hub demand shares as in the SB6 notebook: NREL ATB 2024, "
  "EIA 2023, and ERCOT weather-zone shares computed from TX-123BT (Jin Lu et "
  "al., DOI 10.6084/m9.figshare.22144616, CC BY 4.0)"),
))


def syntax_check(cells):
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
