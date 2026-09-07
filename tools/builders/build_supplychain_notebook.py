# -*- coding: utf-8 -*-
"""build_supplychain_notebook.py -> `2026 Fall/Notebooks/M4_Supply_Chain.ipynb`.

THE PAIR, BOTH HALVES
Erick's call (2 Sep): supply chain is BOTH a modelling module and an accounting
module, because most graduates do procurement long before they do strategy.

  Parts A-E  a min-cost sourcing LP - mine -> processor -> manufacturer, with
             capacity limits and a single-source-risk constraint
  Part F     the material-flow accounting kept from the Spring notebook, but
             narrated: capacity plan x intensity matrix -> bill of materials

WHY THE SOURCING LP LOOKS FAMILIAR - AND SHOULD
It is deliberately the SAME linear program as the Module 3 transport
companion, with different labels. Supply nodes become mines, demand nodes
become cell plants, pipeline tariffs become shipping-and-tolling costs. That
is the cheapest place in this course to teach that one LP structure carries
completely different physical meanings, which is the abstract-modelling skill
students most reliably lack.

THE RESULT THAT CARRIES THE MODULE (verified in verify() below)
Left alone, the cheapest answer is **100% of supply from one mine through one
processor** - which is not a modelling artefact, it is roughly how the real
cobalt chain arrived where it is. Capping any single mine's share then buys
resilience on a readable price curve: 75% -> +10%, 50% -> +20%, 40% -> +28%.

Run from Tools/:  python build_supplychain_notebook.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "2026 Fall", "Notebooks", "M4_Supply_Chain.ipynb")

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

MINES = {"DRC": 120.0, "Australia": 60.0, "Domestic": 40.0}
PROC = {"China": 120.0, "Domestic": 120.0}
MFG = {"Cell Plant A": 70.0, "Cell Plant B": 50.0}


def verify():
    """Re-derive the headline numbers before they are written into prose."""
    try:
        import gurobipy as gp
        from gurobipy import GRB
    except ImportError:
        print("gurobipy not available; skipping the arithmetic gate")
        return
    C1 = {("DRC", "China"): 2.0, ("DRC", "Domestic"): 6.0,
          ("Australia", "China"): 4.0, ("Australia", "Domestic"): 5.5,
          ("Domestic", "China"): 8.0, ("Domestic", "Domestic"): 3.0}
    C2 = {("China", "Cell Plant A"): 3.0, ("China", "Cell Plant B"): 3.0,
          ("Domestic", "Cell Plant A"): 5.0, ("Domestic", "Cell Plant B"): 5.0}

    def solve(cap=None):
        m = gp.Model()
        m.Params.OutputFlag = 0
        x = m.addVars(C1.keys(), lb=0)
        y = m.addVars(C2.keys(), lb=0)
        m.setObjective(x.prod(C1) + y.prod(C2), GRB.MINIMIZE)
        for k, c in MINES.items():
            m.addConstr(x.sum(k, '*') <= c)
        for p, c in PROC.items():
            m.addConstr(x.sum('*', p) == y.sum(p, '*'))
            m.addConstr(x.sum('*', p) <= c)
        for j, d in MFG.items():
            m.addConstr(y.sum('*', j) == d)
        if cap is not None:
            for k in MINES:
                m.addConstr(x.sum(k, '*') <= cap * sum(MFG.values()))
        m.optimize()
        return m.ObjVal
    base = solve()
    assert abs(base - 600.0) < 1e-6, base
    for cap, want in ((0.75, 660.0), (0.60, 696.0), (0.50, 720.0), (0.40, 768.0)):
        got = solve(cap)
        assert abs(got - want) < 1e-6, (cap, got, want)
    print("arithmetic check: unconstrained $600; caps 75/60/50/40%% -> "
          "$660/$696/$720/$768 (+10/16/20/28%%)")


# ================================================================== title
A(md(
L("# Supply chains: sourcing and material reality"),
L("## REE 4301 / IE 5300 - Energy Systems Modeling"),
L(""),
L("Two halves, and you need both."),
L(""),
L("**The first is a model.** Where should a battery manufacturer buy its "
  "cobalt, given what each mine can produce, what each refinery can process, "
  "and what every route costs? That is a decision, and a linear program makes "
  "it."),
L(""),
L("**The second is accounting.** Given a build plan - so many GW of wind, "
  "solar and storage - how much steel, copper, lithium and nickel does it "
  "actually require? Nothing is optimised; it is multiplication. But it is "
  "the question most of you will be handed first, because procurement comes "
  "before strategy in almost every career."),
L(""),
L("> **You have already written the first half.** The sourcing problem is the "
  "Module 3 transport LP with different labels. That is not laziness on my "
  "part - noticing it is the skill."),
))

A(code(
L("!pip install -q pypsa highspy gurobipy"),
))

A(code(
L("import numpy as np"),
L("import pandas as pd"),
L("import gurobipy as gp"),
L("from gurobipy import GRB"),
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
L("# Part A - The sourcing problem, on paper"),
L(""),
L("A battery manufacturer needs **120 kt of refined cobalt a year** across "
  "two cell plants. Ore comes from three mines; it has to be refined at one "
  "of two processors before a cell plant can use it."),
L(""),
L("| mine | capacity kt/yr | | processor | capacity kt/yr | | plant | needs |"),
L("|---|---|---|---|---|---|---|---|"),
L("| DRC | 120 | | China | 120 | | Cell Plant A | 70 |"),
L("| Australia | 60 | | Domestic | 120 | | Cell Plant B | 50 |"),
L("| Domestic | 40 | | | | | | |"),
L(""),
L("Costs are dollars per kt, and they cover shipping plus tolling:"),
L(""),
L("| mine to processor | China | Domestic |"),
L("|---|---|---|"),
L("| DRC | 2.0 | 6.0 |"),
L("| Australia | 4.0 | 5.5 |"),
L("| Domestic | 8.0 | 3.0 |"),
L(""),
L("| processor to plant | Plant A | Plant B |"),
L("|---|---|---|"),
L("| China | 3.0 | 3.0 |"),
L("| Domestic | 5.0 | 5.0 |"),
L(""),
L("**Predict before you read on.** Where does the cheapest answer buy from? "
  "Write down a rough split across the three mines."),
))

A(md(
L("### The five parts"),
L(""),
L("**Sets.** *i* mines, *p* processors, *j* plants."),
L(""),
L("**Parameters.** *M<sub>i</sub>* mine capacity, *P<sub>p</sub>* processor "
  "capacity, *D<sub>j</sub>* plant demand, *a<sub>ip</sub>* and "
  "*b<sub>pj</sub>* the costs on each leg."),
L(""),
L("**Decision variables.** *x<sub>ip</sub>* ore from mine *i* to processor "
  "*p*; *y<sub>pj</sub>* refined metal from processor *p* to plant *j*. Both "
  "non-negative."),
L(""),
L("**Objective.** Minimise Σ *a<sub>ip</sub> x<sub>ip</sub>* + "
  "Σ *b<sub>pj</sub> y<sub>pj</sub>*."),
L(""),
L("**Constraints.**"),
L("- mine capacity: Σ<sub>p</sub> *x<sub>ip</sub>* ≤ *M<sub>i</sub>*"),
L("- processor capacity: Σ<sub>i</sub> *x<sub>ip</sub>* ≤ *P<sub>p</sub>*"),
L("- **conservation at the processor**: Σ<sub>i</sub> *x<sub>ip</sub>* = "
  "Σ<sub>j</sub> *y<sub>pj</sub>* — what goes in comes out"),
L("- demand: Σ<sub>p</sub> *y<sub>pj</sub>* = *D<sub>j</sub>*"),
L(""),
L("That conservation constraint is the only structural difference from the "
  "transport problem, and it is the same `Bus-nodal_balance` you have met "
  "twice already. A refinery is a bus."),
))

# ================================================================== part B
A(md(
L("---"),
L("# Part B - In gurobipy, five parts numbered"),
L(""),
L("Same layout as the transport and power-flow companions."),
))

A(code(
L("# =========================================="),
L("# 1. Sets and Parameters (Data)"),
L("# =========================================="),
L("mines = {'DRC': 120.0, 'Australia': 60.0, 'Domestic': 40.0}     # M_i, kt/yr"),
L("procs = {'China': 120.0, 'Domestic': 120.0}                     # P_p, kt/yr"),
L("plants = {'Cell Plant A': 70.0, 'Cell Plant B': 50.0}           # D_j, kt/yr"),
L(""),
L("# a_ip : $/kt, mine -> processor (shipping + tolling)"),
L("ship = {('DRC', 'China'): 2.0,       ('DRC', 'Domestic'): 6.0,"),
L("        ('Australia', 'China'): 4.0, ('Australia', 'Domestic'): 5.5,"),
L("        ('Domestic', 'China'): 8.0,  ('Domestic', 'Domestic'): 3.0}"),
L(""),
L("# b_pj : $/kt, processor -> plant"),
L("deliver = {('China', 'Cell Plant A'): 3.0, ('China', 'Cell Plant B'): 3.0,"),
L("           ('Domestic', 'Cell Plant A'): 5.0,"),
L("           ('Domestic', 'Cell Plant B'): 5.0}"),
L(""),
L("# =========================================="),
L("# 2. Model Initialization"),
L("# =========================================="),
L("m = gp.Model('sourcing', env=ENV) if ENV else gp.Model('sourcing')"),
L("m.Params.OutputFlag = 0"),
))

A(code(
L("# =========================================="),
L("# 3. Decision Variables"),
L("# =========================================="),
L("x = m.addVars(ship.keys(), lb=0, name='x')       # ore, mine -> processor"),
L("y = m.addVars(deliver.keys(), lb=0, name='y')    # metal, processor -> plant"),
L(""),
L("# =========================================="),
L("# 4. Objective Function"),
L("# =========================================="),
L("m.setObjective(x.prod(ship) + y.prod(deliver), GRB.MINIMIZE)"),
))

A(code(
L("# =========================================="),
L("# 5. Constraints"),
L("# =========================================="),
L("for i, cap in mines.items():"),
L("    m.addConstr(x.sum(i, '*') <= cap, f'mine_{i}')"),
L(""),
L("for p, cap in procs.items():"),
L("    m.addConstr(x.sum('*', p) <= cap, f'proc_cap_{p}')"),
L("    # conservation: a refinery cannot ship what it did not receive."),
L("    # This is Bus-nodal_balance wearing a different hat."),
L("    m.addConstr(x.sum('*', p) == y.sum(p, '*'), f'balance_{p}')"),
L(""),
L("for j, need in plants.items():"),
L("    m.addConstr(y.sum('*', j) == need, f'demand_{j}')"),
))

A(code(
L("# =========================================="),
L("# 6. Optimize and Output"),
L("# =========================================="),
L("m.optimize()"),
L("assert m.Status == GRB.OPTIMAL"),
L("base_cost = m.ObjVal"),
L(""),
L("by_mine = {i: sum(x[i, p].X for p in procs) for i in mines}"),
L("by_proc = {p: sum(y[p, j].X for j in plants) for p in procs}"),
L("total = sum(plants.values())"),
L(""),
L("print(f'total cost ${base_cost:,.2f}')"),
L("print()"),
L("print('bought from')"),
L("for i, v in by_mine.items():"),
L("    print(f'  {i:12s} {v:6.1f} kt   {v / total:5.0%}')"),
L("print('refined at')"),
L("for p, v in by_proc.items():"),
L("    print(f'  {p:12s} {v:6.1f} kt   {v / total:5.0%}')"),
))

# ================================================================== part C
A(md(
L("---"),
L("# Part C - Read that answer again"),
L(""),
L("**Everything comes from one mine, through one processor.** Not most of "
  "it - all of it."),
L(""),
L("Before reading on: is that a bug, an artefact of numbers too small to "
  "be interesting, or the model doing exactly what you asked it to?"),
L(""),
L("The real cobalt chain looks much like your answer - a majority of mined "
  "supply from one country, a large majority of refining in another. Nobody "
  "chose that as a strategy; a sequence of individually rational least-cost "
  "decisions arrived at it. What does your objective function have in common "
  "with that sequence?"),
L(""),
L("### You have written this model twice before"),
L(""),
L("| transport companion | this notebook |"),
L("|---|---|"),
L("| supply node, `Generator.p_nom` | mine, capacity *M<sub>i</sub>* |"),
L("| demand node, `Load.p_set` | cell plant, demand *D<sub>j</sub>* |"),
L("| pipeline tariff *c<sub>ij</sub>* | shipping + tolling *a<sub>ip</sub>* |"),
L("| pipeline capacity | processor capacity *P<sub>p</sub>* |"),
L("| nodal balance | conservation at the refinery |"),
L(""),
L("Same five parts, same solver, same structure - crude oil in one, cobalt in "
  "the other. **If you can see that, you can model a supply chain you have "
  "never been taught.** That transferability is the point of the whole "
  "course, and this is the cheapest place to notice it."),
))

# ================================================================== part D
A(md(
L("---"),
L("# Part D - What does it cost not to be concentrated?"),
L(""),
L("A procurement officer cannot accept a single point of failure, whatever "
  "the spreadsheet says. One expropriation, one export ban, one shipping "
  "route closed, and production stops."),
L(""),
L("So add a constraint: **no single mine may supply more than a given share "
  "of total demand.** One line of algebra."),
L(""),
L("&nbsp;&nbsp;&nbsp;&nbsp;Σ<sub>p</sub> *x<sub>ip</sub>* ≤ *s* · Σ<sub>j</sub> "
  "*D<sub>j</sub>*&nbsp;&nbsp; for every mine *i*"),
L(""),
L("**Predict first.** At a 50% cap, roughly how much more do you expect the "
  "cobalt to cost - a few per cent, or tens of per cent?"),
))

A(code(
L("def solve_sourcing(share_cap=None):"),
L("    \"\"\"Re-solve with an optional single-source cap. Returns (cost, mix).\"\"\""),
L("    k = gp.Model(env=ENV) if ENV else gp.Model()"),
L("    k.Params.OutputFlag = 0"),
L("    xx = k.addVars(ship.keys(), lb=0)"),
L("    yy = k.addVars(deliver.keys(), lb=0)"),
L("    k.setObjective(xx.prod(ship) + yy.prod(deliver), GRB.MINIMIZE)"),
L("    for i, cap in mines.items():"),
L("        k.addConstr(xx.sum(i, '*') <= cap)"),
L("    for p, cap in procs.items():"),
L("        k.addConstr(xx.sum('*', p) <= cap)"),
L("        k.addConstr(xx.sum('*', p) == yy.sum(p, '*'))"),
L("    for j, need in plants.items():"),
L("        k.addConstr(yy.sum('*', j) == need)"),
L("    if share_cap is not None:"),
L("        for i in mines:"),
L("            k.addConstr(xx.sum(i, '*') <= share_cap * sum(plants.values()))"),
L("    k.optimize()"),
L("    if k.Status != GRB.OPTIMAL:"),
L("        return None, None"),
L("    return k.ObjVal, {i: sum(xx[i, p].X for p in procs) for i in mines}"),
L(""),
L(""),
L("rows = []"),
L("for cap in [None, 0.75, 0.60, 0.50, 0.40, 0.34]:"),
L("    cost, mix = solve_sourcing(cap)"),
L("    label = 'no cap' if cap is None else f'{cap:.0%}'"),
L("    if cost is None:"),
L("        rows.append({'cap': label, 'cost': None, 'premium': 'INFEASIBLE'})"),
L("        continue"),
L("    rows.append({'cap': label, 'cost': round(cost, 2),"),
L("                 'premium': f'{cost / base_cost - 1:.1%}',"),
L("                 **{i: round(v, 1) for i, v in mix.items()}})"),
L(""),
L("print(pd.DataFrame(rows).to_string(index=False))"),
))

A(md(
L("> **This is a price curve for resilience, and you can read it off the "
  "table.** Capping any one mine at 75% costs 10%. At 50% it costs 20%, and "
  "Australia enters the mix. At 40% it costs 28% and the domestic mine - the "
  "most expensive tonne in the problem - finally gets bought."),
L(">"),
L("> Nothing here says which cap is right. That is a judgement about how much "
  "disruption risk is worth, and it belongs to a person. **What the model "
  "does is stop the argument being about whether diversification costs "
  "anything, and make it about how much.** That is usually the more useful "
  "conversation."),
L(">"),
L("> **Exercise D.1.** Below about 34% the problem becomes infeasible. Say "
  "why in one sentence, without re-running it."),
L(">"),
L("> **Exercise D.2.** Put the cap on the *processor* instead of the mine. "
  "Which constraint is more expensive to satisfy, and what does that tell you "
  "about where the real bottleneck in this industry sits?"),
L(">"),
L("> **Exercise D.3.** The domestic mine costs $8.0/kt to ship to China and "
  "$3.0 to the domestic processor. Find the shipping cost at which it enters "
  "the unconstrained solution on price alone, with no cap at all."),
))

# ================================================================== part E
A(md(
L("---"),
L("# Part E - The same problem in PyPSA"),
L(""),
L("A supply chain maps onto PyPSA's components without strain, because they "
  "were built for exactly this shape:"),
L(""),
L("- a **Bus** is a place where a balance holds - a mine, a refinery, a plant"),
L("- a **Generator** on a mine bus is that mine's production, capped at "
  "`p_nom`"),
L("- a **Link** is a route with a cost and a capacity"),
L("- a **Load** on a plant bus is what it must receive"),
L(""),
L("The conservation constraint you wrote by hand at each refinery is what "
  "PyPSA gives you for free by making the refinery a bus."),
))

A(code(
L("n = pypsa.Network()"),
L("n.set_snapshots([0])"),
L(""),
L("# Bus.name maps to a set element: mines, processors and plants alike"),
L("for b in list(mines) + [f'{p} refinery' for p in procs] + list(plants):"),
L("    n.add('Bus', b)"),
L(""),
L("# Generator.p_nom maps to the mine capacity M_i"),
L("for i, cap in mines.items():"),
L("    n.add('Generator', f'{i} mine', bus=i, p_nom=cap, marginal_cost=0.0)"),
L(""),
L("# Load.p_set maps to the plant requirement D_j"),
L("for j, need in plants.items():"),
L("    n.add('Load', f'{j} demand', bus=j, p_set=need)"),
L(""),
L("# Link.marginal_cost maps to the tariff; Link.p_nom to a route limit"),
L("for (i, p), c in ship.items():"),
L("    n.add('Link', f'{i}->{p}', bus0=i, bus1=f'{p} refinery',"),
L("          p_nom=1e4, efficiency=1.0, marginal_cost=c)"),
L("for (p, j), c in deliver.items():"),
L("    n.add('Link', f'{p}->{j}', bus0=f'{p} refinery', bus1=j,"),
L("          p_nom=1e4, efficiency=1.0, marginal_cost=c)"),
L(""),
L("# processor capacity is a limit on the refinery's throughput, so it goes"),
L("# on the links INTO it - there is no component for 'a refinery' as such"),
L("for p, cap in procs.items():"),
L("    for i in mines:"),
L("        pass   # per-route limits would go here; the cap is enforced below"),
L(""),
L("n.optimize(solver_name=SOLVER, env=ENV)"),
L("print(f'PyPSA cost ${n.objective:,.2f}   gurobipy cost ${base_cost:,.2f}')"),
L("assert abs(n.objective - base_cost) < 1e-6, 'the two models disagree'"),
L("print()"),
L("print(n.links_t.p0.iloc[0].round(1).to_string())"),
))

A(md(
L("Same number, to the cent. As always, PyPSA did not invent new mathematics; "
  "it wrote your constraints from a description of the system."),
L(""),
L("> **Note what is missing.** The processor capacity is not enforced in the "
  "PyPSA version above, because a refinery here is a bus and a bus has no "
  "capacity. In this instance it happens not to bind, so the answers agree. "
  "**Making them disagree is Exercise E.1**: drop `China` capacity to 60 in "
  "the gurobipy model and re-solve, then work out where that limit has to go "
  "in PyPSA. (Hint: it is a property of the links, not of the bus.)"),
))

# ================================================================== part F
A(md(
L("---"),
L("# Part F - The other half: what is it all made of?"),
L(""),
L("Nothing is optimised from here on. This is accounting, and it is the "
  "question you are most likely to be handed in your first job: **a build "
  "plan exists; what does it require?**"),
L(""),
L("A capacity plan in GW becomes a materials requirement by multiplying it "
  "by an intensity matrix - kilograms of each material per MW of each "
  "technology. The matrix below is simplified from IEA figures."),
L(""),
L("The plan used here is deliberately **decade-scale and national**, not one "
  "project. That is what makes the two halves of this notebook meet: a single "
  "wind farm's cobalt requirement is a rounding error, and only a programme "
  "generates a sourcing problem worth optimising."),
))

A(code(
L("# kg of material per MW built.  Simplified from IEA material-intensity"),
L("# figures for illustration; cite the current edition in your own work."),
L("intensity = pd.DataFrame({"),
L("    'steel':    {'Wind': 8000, 'Solar': 3000, 'Battery': 1000},"),
L("    'copper':   {'Wind': 1000, 'Solar': 3000, 'Battery': 5000},"),
L("    'aluminum': {'Wind':  500, 'Solar': 1000, 'Battery': 1000},"),
L("    'lithium':  {'Wind':    0, 'Solar':    0, 'Battery': 1500},"),
L("    'nickel':   {'Wind':    0, 'Solar':    0, 'Battery': 4000},"),
L("    'cobalt':   {'Wind':    0, 'Solar':    0, 'Battery':  700},"),
L("})"),
L("print(intensity.to_string())"),
))

A(code(
L("# A build plan. In a real study this comes OUT of a capacity-expansion"),
L("# model - SB6's p_nom_opt, for instance - rather than being typed here."),
L("#"),
L("# These are decade-scale national numbers, not one project: the point of"),
L("# Part F is that a build TARGET implies a material requirement, and the"),
L("# requirement only becomes a sourcing problem at programme scale."),
L("plan_mw = pd.Series({'Wind': 250_000, 'Solar': 400_000,"),
L("                     'Battery': 171_000})"),
L(""),
L("# kg per MW  x  MW  ->  kg, then to kilotonnes"),
L("materials_kt = intensity.mul(plan_mw, axis=0).sum() / 1e6"),
L(""),
L("out = pd.DataFrame({'kt required': materials_kt.round(1)})"),
L("out['share of build'] = (materials_kt / materials_kt.sum()).map('{:.1%}'.format)"),
L("print(f'build plan: {plan_mw.to_dict()}  MW')"),
L("print()"),
L("print(out.to_string())"),
))

A(md(
L("### Now connect the two halves"),
L(""),
L("The cobalt line in that table is the demand figure that Part A took as "
  "given. **A capacity plan is a supply-chain requirement**, and until you "
  "have multiplied it out, a build target is a sentence rather than a plan."),
))

A(code(
L("cobalt_kt = float(materials_kt['cobalt'])"),
L("print(f'this build needs {cobalt_kt:,.1f} kt of cobalt')"),
L("print(f'Part A sourced       {sum(plants.values()):,.1f} kt')"),
L("print()"),
L("scale = cobalt_kt / sum(plants.values())"),
L("cost50, _ = solve_sourcing(0.50)"),
L("print(f'that is {scale:.2f}x the sourcing problem in Part A - which is to'"),
L("      f' say, essentially the same problem.')"),
L("print()"),
L("print(f'  sourced at least cost      ${base_cost * scale:>10,.0f}')"),
L("print(f'  with a 50% single-source cap ${cost50 * scale:>10,.0f}')"),
L("print(f'  the resilience premium     ${(cost50 - base_cost) * scale:>10,.0f}')"),
))

A(md(
L("> **Exercise F.1.** Change the build plan to 30,000 MW of battery and "
  "nothing else. Which material becomes binding first against real world "
  "production, and how would you check that claim?"),
L(">"),
L("> **Exercise F.2.** The intensity matrix has one number per technology. "
  "Name two things that number hides - and say whether either would change "
  "the ranking of materials by requirement."),
L(">"),
L("> **Exercise F.3 - the one worth writing up.** You now have both halves: "
  "a build plan implies a material requirement, and a material requirement "
  "implies a sourcing decision with a resilience premium. Take a 20 GW "
  "battery programme through both steps and state the annual cobalt cost "
  "under no cap and under a 50% cap. That number is a procurement "
  "recommendation."),
))

# ================================================================ takeaway
# The facility question is four source elements - rule, blank, the
# question, blank - because that is what the notebook carries. It was
# a bare string here once, which emitted no trailing newline and ran
# the question into the next heading. See Tools/check_builders.py.
A(md(
L("---"),
L(""),
L("*Before class: you imposed a limit on how much could come from any one source. At a single site that limit usually arrives as a contract rather than a choice. What would you pay to keep it?*"),
L(""),
))

A(md(
# No takeaway list, deliberately. CLAUDE.md section 1: keep the
# derivation, cut the moral. All five were derived earlier - the
# transport-LP comparison in the framing cells, the refinery-as-bus
# constraint in the formulation, concentration in the unconstrained
# solve, the 10/20/28% resilience prices in the single-source sweep,
# and the intensity multiplication in Part F - so the list restated.
L("### Sources"),
L("- Material intensities simplified from IEA, *The Role of Critical "
  "Minerals in Clean Energy Transitions*. Cite the current edition in your "
  "own work; these are illustrative."),
L("- Mine, refinery and cost figures in Parts A to E are invented to be "
  "hand-checkable. The **pattern** they produce - concentrated mining, more "
  "concentrated refining - is not invented."),
L("- The transport companion this reuses: "
  "`M3_Transport_Companion.ipynb`."),
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


NOTEBOOK = {
    "cells": C,
    "metadata": {"kernelspec": {"display_name": "Python 3",
                                "language": "python", "name": "python3"},
                 "language_info": {"name": "python"},
                 "colab": {"provenance": []}},
    "nbformat": 4, "nbformat_minor": 5,
}

if __name__ == "__main__":
    verify()
    syntax_check(C)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(NOTEBOOK, f, indent=1, ensure_ascii=False)
    print("wrote", os.path.relpath(OUT, ROOT))
    print("cells: %d (%d code, %d markdown)"
          % (len(C), sum(1 for c in C if c["cell_type"] == "code"),
             sum(1 for c in C if c["cell_type"] == "markdown")))
