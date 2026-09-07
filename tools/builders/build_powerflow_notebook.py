# -*- coding: utf-8 -*-
"""build_powerflow_notebook.py - write `notebooks/p4_networks/18_power_flow_and_lmp.ipynb`.

WHAT THIS IS
The Spring `Module_3_PowerFlow_Companion.ipynb` already contains the best
teaching in the course: a hand-written 3-bus DCOPF in gurobipy where the LMPs
fall out as dual variables of the nodal balance constraints.  That toy is kept
essentially verbatim - it is not improvable.

WHAT IT ADDS
The Spring notebook's PyPSA side is three monolithic cells (1,990 / 6,174 /
1,966 characters) with no per-component narration.  This version replaces that
with a `### Step N` walkthrough in the same style as
`Module_3_Transport_Companion.ipynb`, one component per cell, each with a
"maps to" comment tying the PyPSA argument back to an LP symbol.

THE CLOSING CELL HAS NO TAKEAWAY LIST, DELIBERATELY
It used to end with `## What you should take from this` and five bolded
morals.  CLAUDE.md section 1 names that exact pattern - a lecture in list
form - and says to keep the derivation and cut the moral.  Every one of
the five was already derived earlier in the notebook (Line vs Link in the
component walkthrough, the dual in the gurobipy toy, prices above cost in
the 3-bus example, loop flow in the reactance comparison, congestion rent
in its own section), so the list restated rather than taught.  What is
left is the facility question, which asks instead of telling.

That question was also a bare string rather than an L(), so it carried no
trailing newline and a rebuild ran it straight into `### Sources`.  The
notebook on disk had the newline and the builder did not, which is the
drift CLAUDE.md section 4 warns about: the artefact was hand-corrected and
the builder was not, so the next rebuild would have silently undone it.

DEFECTS FIXED (all present in the Spring notebook)
1. The line limit was 60 in the gurobi toy, 70 in the reactance comparison,
   and "80 MW" in seven places of prose.  All are now 70 - see verify().
2. The loop-flow narrative was FALSE at 60 MW.  Flow on HOU->WTX is exactly
   120 - 2L, so L=60 is the one value where loop flow vanishes.  At L=70 the
   prose is true: 90 MW of wind, 70 direct and 20 around through Houston.
3. Dallas LMP is $80/MWh - twice the cost of the most expensive generator
   running.  The Spring notebook never points this out.  It is now Part C.

Run from Tools/:  python build_powerflow_notebook.py
"""
import json
import os

# tools/builders/<this file> -> tools/ -> the repository root.
# Three levels, not two: these builders used to live one level higher,
# in the course folder's Tools/.
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "notebooks", "p4_networks", "18_power_flow_and_lmp.ipynb")

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

# ---------------------------------------------------------------- numbers
DEMAND = 120.0     # MW at Dallas
WIND_CAP = 150.0   # MW at West Texas, $0/MWh
GAS_CAP = 100.0    # MW at Houston, $40/MWh
GAS_COST = 40.0
LIMIT = 70.0       # MW, the WTX->DAL thermal limit
X = 0.1            # per-unit reactance, all three lines


def verify():
    """Solve the 3-bus DCOPF by hand so every number in the prose is checked.

    With theta_wtx pinned to 0, theta_dal = d and theta_hou = h:
        F_wd = -d/X     F_dh = (d-h)/X      F_hw = h/X
    Nodal balance at Dallas gives h = 2d + 12 (for X=0.1, D=120), hence
        W = -30d - 120    G = 30d + 240     F_hw = 20d + 120
    Minimising gas cost drives d to its bound, d = -L/X/10 = -L/10.
    """
    d = -LIMIT / 10.0
    h = 2 * d + 12
    f_wd = -d / X * (X / 0.1) * 0.1 / X     # = -d/X
    f_wd = -d / X
    f_dh = (d - h) / X
    f_hw = h / X
    wind = -30 * d - 120
    gas = 30 * d + 240
    assert abs(f_wd - LIMIT) < 1e-9, f_wd
    assert abs(wind + gas - DEMAND) < 1e-9, (wind, gas)
    assert abs(wind - 90.0) < 1e-9, wind
    assert abs(gas - 30.0) < 1e-9, gas
    assert abs(f_hw + 20.0) < 1e-9, f_hw          # 20 MW WTX -> HOU
    assert abs(f_dh + 50.0) < 1e-9, f_dh          # 50 MW HOU -> DAL
    assert 0 <= wind <= WIND_CAP and 0 <= gas <= GAS_CAP
    # loop flow vanishes at exactly L = 60, which is why the Spring
    # notebook's narrative did not match its own code
    assert abs((20 * (-60 / 10.0) + 120)) < 1e-9
    # feasibility floor: gas = 240 - 3L must not exceed its 100 MW cap
    floor = (240.0 - GAS_CAP) / 3.0
    assert abs(floor - 46.6666667) < 1e-5, floor
    assert 240 - 3 * 40 > GAS_CAP, "L=40 must be infeasible for the sweep note"
    assert 240 - 3 * 50 <= GAS_CAP, "L=50 must be feasible"
    print("feasibility floor: L >= %.1f MW (gas cap %.0f MW binds below that)"
          % (floor, GAS_CAP))
    # Part F: LMP_Dallas = LMP_Houston * (1 + X_wd / X_hw)
    for x_hw, expect in ((0.05, 120.0), (0.10, 80.0), (0.20, 60.0)):
        got = GAS_COST * (1 + X / x_hw)
        assert abs(got - expect) < 1e-9, (x_hw, got, expect)
    print("LMP leverage check: X_hw 0.05/0.10/0.20 -> Dallas $120/$80/$60")
    print("algebra check: wind %.0f MW, gas %.0f MW, WTX->DAL %.0f MW (binding),"
          % (wind, gas, f_wd))
    print("               loop flow WTX->HOU %.0f MW, HOU->DAL %.0f MW"
          % (-f_hw, -f_dh))
    return wind, gas, f_hw


# ================================================================== title
A(md(
L("# Power flow and locational marginal pricing"),
L("## REE 4301 / IE 5300 - Energy Systems Modeling"),
L(""),
L("In the transport companion you moved gas through pipelines. You chose the "
  "flow on every route, and the only limits were capacities. That is a "
  "**transport model**, and it is the right model for pipelines, railways and "
  "shipping."),
L(""),
L("**Electricity does not work that way.** Nobody chooses how power flows. "
  "It divides itself among every available path according to the physics of "
  "the network, and the grid operator's only levers are which generators run "
  "and what the network is built like."),
L(""),
L("This notebook does the same thing twice, as always:"),
L(""),
L("1. **In gurobipy**, where you write the power-flow equations yourself and "
  "pull the prices out of the LP by hand."),
L("2. **In PyPSA**, where you say `Line` instead of `Link` and all of it "
  "happens for you."),
L(""),
L("The point to carry out of here is one sentence: **a locational marginal "
  "price is the dual variable of a nodal balance constraint.** Not an "
  "economic theory bolted on afterwards - a number that falls out of the same "
  "LP you have been writing since Module 0."),
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
L("# For homework: paste your academic Web License Service key here."),
L("WLS = {}   # {'WLSACCESSID': '...', 'WLSSECRET': '...', 'LICENSEID': 000000}"),
L("ENV = gp.Env(params=WLS) if (SOLVER == 'gurobi' and WLS) else None"),
L(""),
L("print(f'solver: {SOLVER}'"),
L("      + ('  (academic WLS licence)' if ENV else '  (default licence)'))"),
))

# ================================================================== part A
A(md(
L("---"),
L("# Part A - The system, and why it needs angles"),
L(""),
L("Three buses in a triangle. Every line has the same reactance, *X* = 0.1."),
L(""),
L("| bus | what is there | capacity | cost |"),
L("|---|---|---|---|"),
L("| West Texas | wind | 150 MW | $0/MWh |"),
L("| Houston | gas | 100 MW | $40/MWh |"),
L("| Dallas | 120 MW of demand | - | - |"),
L(""),
L("**The West Texas to Dallas line can carry only 70 MW.** The other two are "
  "effectively unlimited."),
))

A(md(
L("### First, predict"),
L(""),
L("Wind is free and there is 150 MW of it. Demand is 120 MW. So run 120 MW of "
  "wind and pay nothing - except the direct line to Dallas only holds 70."),
L(""),
L("**Write down your answers before you run anything:**"),
L(""),
L("1. How much wind and how much gas get dispatched?"),
L("2. What is the price of electricity at Dallas?"),
L(""),
L("Most people answer 70 wind / 50 gas for the first, and $40 for the second. "
  "Both are wrong, and the reasons they are wrong are the entire content of "
  "this notebook."),
))

A(md(
L("### The DC power flow equations"),
L(""),
L("A transport model would let you choose each line's flow. Here you cannot. "
  "Instead, each bus gets a **voltage angle** *θ*, and the flow on a line is "
  "fixed by the angle difference across it:"),
L(""),
L("&nbsp;&nbsp;&nbsp;&nbsp;*F<sub>ij</sub>* = ( *θ<sub>i</sub>* − "
  "*θ<sub>j</sub>* ) / *X<sub>ij</sub>*"),
L(""),
L("That single equation is what makes this a power-flow model. The optimiser "
  "picks generation; the angles then *determine* every flow at once. You get "
  "flow on lines you never asked to use."),
L(""),
L("Two consequences worth naming now:"),
L(""),
L("- **Only angle differences matter.** Add 5 to every angle and nothing "
  "changes. So one bus must be pinned - the **reference** or **slack** bus - "
  "or the LP has infinitely many equally good solutions."),
L("- **You cannot route power.** If you want less flow on a path, your only "
  "options are to change what generates where, or to change the network's "
  "reactances. Part E does the second."),
))

# ================================================================== part B
A(md(
L("---"),
L("# Part B - By hand, in gurobipy"),
L(""),
L("The same five parts as every other model in this course, numbered the same "
  "way as the transport companion."),
L(""),
L("Watch for one thing in Part 5: we **keep** the three nodal balance "
  "constraint objects in named variables. Usually you would not bother. Here "
  "they are the whole point, because their dual variables are the prices."),
))

A(code(
L("# =========================================="),
L("# 1. Sets and Parameters (Data)"),
L("# =========================================="),
L("buses = ['West Texas', 'Dallas', 'Houston']"),
L(""),
L("demand = {'Dallas': 120.0}                        # D_j,  MW"),
L("gen_costs = {'WTX_Wind': 0.0, 'HOU_Gas': 40.0}    # c_g,  $/MWh"),
L("gen_max = {'WTX_Wind': 150.0, 'HOU_Gas': 100.0}   # Pbar_g,  MW"),
L(""),
L("line_X = {'WTX_DAL': 0.1, 'DAL_HOU': 0.1, 'HOU_WTX': 0.1}   # X_ij, p.u."),
L("line_limit = {'WTX_DAL': 70.0, 'DAL_HOU': 1000.0,"),
L("              'HOU_WTX': 1000.0}                  # Fbar_ij,  MW"),
L(""),
L("# =========================================="),
L("# 2. Model Initialization"),
L("# =========================================="),
L("m = gp.Model('3_Bus_DCOPF', env=ENV) if ENV else gp.Model('3_Bus_DCOPF')"),
L("m.Params.OutputFlag = 0"),
))

A(code(
L("# =========================================="),
L("# 3. Decision Variables"),
L("# =========================================="),
L("# Generator dispatch (MW)"),
L("P_wind = m.addVar(lb=0, ub=gen_max['WTX_Wind'], name='P_wind')"),
L("P_gas = m.addVar(lb=0, ub=gen_max['HOU_Gas'], name='P_gas')"),
L(""),
L("# Voltage angles (radians). These are decision variables too, even though"),
L("# nobody 'decides' them physically - the LP solves for the angles that"),
L("# make the flows consistent with the injections."),
L("theta_wtx = m.addVar(lb=-GRB.INFINITY, name='theta_wtx')"),
L("theta_dal = m.addVar(lb=-GRB.INFINITY, name='theta_dal')"),
L("theta_hou = m.addVar(lb=-GRB.INFINITY, name='theta_hou')"),
L(""),
L("# REFERENCE BUS: pin one angle to zero."),
L("# DCOPF determines only angle DIFFERENCES, so without this the model has"),
L("# infinitely many optimal solutions and the solver may return any of them."),
L("m.addConstr(theta_wtx == 0, 'Ref_Bus')"),
))

A(code(
L("# =========================================="),
L("# 4. Objective Function"),
L("# =========================================="),
L("m.setObjective("),
L("    gen_costs['WTX_Wind'] * P_wind + gen_costs['HOU_Gas'] * P_gas,"),
L("    GRB.MINIMIZE)"),
))

A(code(
L("# =========================================="),
L("# 5. Constraints"),
L("# =========================================="),
L("# --- the DC power flow equation, F_ij = (theta_i - theta_j) / X_ij ---"),
L("# These are linear EXPRESSIONS, not new variables: each one is already"),
L("# determined by the angles."),
L("Flow_WTX_DAL = (theta_wtx - theta_dal) / line_X['WTX_DAL']"),
L("Flow_DAL_HOU = (theta_dal - theta_hou) / line_X['DAL_HOU']"),
L("Flow_HOU_WTX = (theta_hou - theta_wtx) / line_X['HOU_WTX']"),
L(""),
L("# --- thermal limit, in BOTH directions ---"),
L("m.addConstr(Flow_WTX_DAL <= line_limit['WTX_DAL'], 'Limit_WTX_DAL_Pos')"),
L("m.addConstr(Flow_WTX_DAL >= -line_limit['WTX_DAL'], 'Limit_WTX_DAL_Neg')"),
L(""),
L("# --- nodal power balance at every bus (Kirchhoff's current law) ---"),
L("# generation - demand = net flow leaving the bus"),
L("#"),
L("# *** KEEP THESE OBJECTS. Their dual variables are the LMPs. ***"),
L("bal_wtx = m.addConstr("),
L("    P_wind - 0 == Flow_WTX_DAL - Flow_HOU_WTX, 'Balance_WTX')"),
L("bal_dal = m.addConstr("),
L("    0 - demand['Dallas'] == Flow_DAL_HOU - Flow_WTX_DAL, 'Balance_DAL')"),
L("bal_hou = m.addConstr("),
L("    P_gas - 0 == Flow_HOU_WTX - Flow_DAL_HOU, 'Balance_HOU')"),
))

A(code(
L("# =========================================="),
L("# 6. Optimize and Output"),
L("# =========================================="),
L("m.optimize()"),
L("assert m.Status == GRB.OPTIMAL, f'solver status {m.Status}'"),
L(""),
L("f_wd = Flow_WTX_DAL.getValue()"),
L("f_dh = Flow_DAL_HOU.getValue()"),
L("f_hw = Flow_HOU_WTX.getValue()"),
L(""),
L("# Dallas's balance was written with demand on the LEFT, so its dual comes"),
L("# out with the opposite sign to the other two. Negate it to get the price."),
L("lmp_wtx, lmp_dal, lmp_hou = bal_wtx.Pi, -bal_dal.Pi, bal_hou.Pi"),
L(""),
L("print('dispatch')"),
L("print(f'  wind (West Texas) {P_wind.X:6.1f} MW')"),
L("print(f'  gas  (Houston)    {P_gas.X:6.1f} MW')"),
L("print()"),
L("print('line flows  (positive = in the direction named)')"),
L(f"print(f'  West Texas -> Dallas  {{f_wd:6.1f}} MW   (limit {LIMIT:.0f})')"),
L("print(f'  Dallas -> Houston     {f_dh:6.1f} MW')"),
L("print(f'  Houston -> West Texas {f_hw:6.1f} MW')"),
L("print()"),
L("print('locational marginal prices  (dual of each nodal balance)')"),
L("print(f'  West Texas ${lmp_wtx:6.2f} /MWh')"),
L("print(f'  Dallas     ${lmp_dal:6.2f} /MWh')"),
L("print(f'  Houston    ${lmp_hou:6.2f} /MWh')"),
L("print()"),
L("print(f'total generation cost ${m.ObjVal:,.2f} /hr')"),
))

# ================================================================== part C
A(md(
L("---"),
L("# Part C - Read that output again"),
L(""),
L("Three things happened that are worth more than the rest of the notebook."),
L(""),
L("### 1. The dispatch is not 70 / 50"),
L(""),
L("The direct line is full at 70 MW, but **90 MW of wind is running**, not "
  "70. The extra 20 MW leaves West Texas heading for *Houston*, and reaches "
  "Dallas the long way round. Nobody routed it there. The angles did."),
L(""),
L("That is **loop flow**, and it is the thing a transport model cannot "
  "represent. Power on a mesh network uses every path between two points, in "
  "proportion to how easy each path is."),
L(""),
L("### 2. Dallas costs $80/MWh, and nothing in the system costs $80"),
L(""),
L("The most expensive generator running is gas at **$40**. Dallas's price is "
  "**twice that**. Before reading on: where can an $80 price come from when "
  "nothing in the system costs $80?"),
L(""),
L("Ask what it actually costs to deliver one more MW to Dallas. You cannot "
  "just send more wind - the direct line is full. Pushing one more MW down "
  "that path means the angles have to shift, which pulls flow around the loop "
  "as well, and the only way to keep every bus balanced is to **turn gas up "
  "by more than one MW while turning wind down**. The system pays $40 twice "
  "over to move one MW. Hence $80."),
L(""),
L("This is why prices at a constrained location can exceed every generator's "
  "cost - and, in real markets, why they can go **negative** at a location "
  "that is exporting into a constraint."),
L(""),
L("### 3. The prices came out of the constraints, not out of an economic model"),
L(""),
L("`bal_dal.Pi` is a *dual variable*. You did not write a pricing rule. You "
  "wrote a cost-minimising LP with a balance constraint at each bus, and the "
  "prices were already in there."),
))

A(code(
L("# congestion rent: what the operator collects from the price difference"),
L("# across a line.  rent = flow x (price at the receiving end"),
L("#                              - price at the sending end)"),
L("rent_wd = f_wd * (lmp_dal - lmp_wtx)"),
L("rent_dh = f_dh * (lmp_hou - lmp_dal)"),
L("rent_hw = f_hw * (lmp_wtx - lmp_hou)"),
L(""),
L("print(f'  West Texas -> Dallas  ${rent_wd:9,.2f} /hr')"),
L("print(f'  Dallas -> Houston     ${rent_dh:9,.2f} /hr')"),
L("print(f'  Houston -> West Texas ${rent_hw:9,.2f} /hr')"),
L("print(f'  {\"total\":21s} ${rent_wd + rent_dh + rent_hw:9,.2f} /hr')"),
L(""),
L("print()"),
L("print('Consumers at Dallas pay  ${:,.2f}/hr'.format(120 * lmp_dal))"),
L("print('Generators are paid      ${:,.2f}/hr'.format("),
L("      P_wind.X * lmp_wtx + P_gas.X * lmp_hou))"),
L("print('The difference is the congestion rent above: it does not go to'"),
L("      ' anyone who produced or consumed electricity.')"),
))

A(md(
L("> **Exercise C.1.** The congestion rent is collected by the grid operator, "
  "not by any generator or consumer. In ERCOT it is paid out to the holders "
  "of Congestion Revenue Rights. Who *should* receive it, and what would "
  "happen to transmission investment if the answer were 'whoever built the "
  "line'?"),
L(">"),
L("> **Exercise C.2.** Raise the limit from 70 to 80 and re-run. Wind covers "
  "all 120 MW, gas shuts off - and every LMP goes to $0. Explain why the "
  "congestion rent vanishes at the same moment."),
))

# ================================================================== part D
A(md(
L("---"),
L("# Part D - The same model in PyPSA, one component at a time"),
L(""),
L("Everything you just wrote by hand - the angle variables, the reference "
  "bus, the flow equations, the thermal limits, the nodal balances - is "
  "written for you by **one word**: `Line` instead of `Link`."),
L(""),
L("A `Link` is a controllable transport route. You set its flow. A `Line` is "
  "AC transmission, and its flow is decided by physics. That is the entire "
  "difference, and it is worth more than any other single fact in this "
  "module."),
))

A(md(
L("### Step 1: Initialize the network"),
))

A(code(
L("n = pypsa.Network()"),
L(""),
L("# one snapshot: this is a single-hour problem, exactly like the gurobi one"),
L("n.set_snapshots([0])"),
L("print(n)"),
))

A(md(
L("### Step 2: Add the buses"),
L(""),
L("A **Bus** is a place where power balances. Each one becomes exactly the "
  "`Balance_*` constraint you wrote by hand in Part B - and each one gets an "
  "angle variable and a dual variable, for free."),
))

A(code(
L("for b in ['West Texas', 'Dallas', 'Houston']:"),
L("    n.add('Bus', b)"),
L(""),
L("print(list(n.buses.index))"),
))

A(md(
L("### Step 3: Add the generators"),
L(""),
L("`p_nom` is the capacity and `marginal_cost` is the running cost. Note "
  "`p_nom`, not `p_nom_extendable` - this is a **dispatch** problem. Nothing "
  "is being built; we are only deciding what to run."),
))

A(code(
L("# Generator.p_nom         maps to the capacity limit Pbar_g"),
L("# Generator.marginal_cost maps to the cost coefficient c_g"),
L("n.add('Generator', 'WTX_Wind', bus='West Texas',"),
L("      p_nom=150, marginal_cost=0)"),
L("n.add('Generator', 'HOU_Gas', bus='Houston',"),
L("      p_nom=100, marginal_cost=40)"),
L(""),
L("print(n.generators[['bus', 'p_nom', 'marginal_cost']].to_string())"),
))

A(md(
L("### Step 4: Add the demand"),
L(""),
L("`p_set` is a fixed requirement - the *D* on the right-hand side of the "
  "Dallas balance constraint."),
))

A(code(
L("# Load.p_set maps to the demand requirement D_j"),
L("n.add('Load', 'Dallas_Demand', bus='Dallas', p_set=120)"),
L(""),
L("print(n.loads[['bus', 'p_set']].to_string())"),
))

A(md(
L("### Step 5: Add the lines - the step that matters"),
L(""),
L("Two arguments, and they are not interchangeable with anything you used in "
  "the transport notebook:"),
L(""),
L("- **`x`** is the reactance. This is what invokes the flow equation. Give "
  "PyPSA an `x` and it will create the angle variables, write "
  "*F* = (*θ<sub>i</sub>* − *θ<sub>j</sub>*)/*X* for every line, and pin a "
  "reference bus. There is no argument for 'please apply Kirchhoff' - `x` "
  "*is* that argument."),
L("- **`s_nom`** is the thermal rating, enforced in both directions, exactly "
  "like the two `Limit_WTX_DAL_*` constraints you wrote by hand."),
))

A(code(
L("# Line.x     maps to the reactance X_ij in F_ij = (theta_i - theta_j)/X_ij"),
L("# Line.s_nom maps to the thermal limit Fbar_ij (enforced +/-)"),
L("n.add('Line', 'WTX_DAL', bus0='West Texas', bus1='Dallas',"),
L("      x=0.1, s_nom=70)          # <-- the bottleneck"),
L("n.add('Line', 'DAL_HOU', bus0='Dallas', bus1='Houston',"),
L("      x=0.1, s_nom=1000)"),
L("n.add('Line', 'HOU_WTX', bus0='Houston', bus1='West Texas',"),
L("      x=0.1, s_nom=1000)"),
L(""),
L("print(n.lines[['bus0', 'bus1', 'x', 's_nom']].to_string())"),
))

A(md(
L("### Step 6: Look at what PyPSA is about to solve"),
L(""),
L("Before solving, ask it what it wrote. Compare this list against the "
  "constraints you typed in Part B."),
))

A(code(
L("lp = n.optimize.create_model()"),
L(""),
L("print('variables:  ', list(lp.variables))"),
L("print()"),
L("print('constraints:', list(lp.constraints))"),
))

A(md(
L("`Bus-nodal_balance` is your three `Balance_*` constraints. "
  "`Line-fix-s_nom-upper` and `-lower` are your two thermal limits. And "
  "`Kirchhoff-Voltage-Law` is the one you had to derive angles for."),
L(""),
L("Notice what PyPSA did *not* need: an explicit angle variable per bus. For "
  "a network this small it solves an equivalent formulation over the "
  "network's independent loops - one KVL constraint per loop instead of one "
  "angle per bus. Same physics, same answer, fewer variables. Another "
  "reminder that the tool is doing bookkeeping you could do yourself, but "
  "would rather not."),
))

A(md(
L("### Step 7: Solve, and read the prices off the buses"),
))

A(code(
L("n.optimize(solver_name=SOLVER, env=ENV)"),
L(""),
L("out = pd.DataFrame({"),
L("    'dispatch MW': n.generators_t.p.iloc[0],"),
L("})"),
L("print(out.to_string())"),
L("print()"),
L("print('line flows (MW, positive = bus0 -> bus1)')"),
L("print(n.lines_t.p0.iloc[0].round(1).to_string())"),
L("print()"),
L("print('locational marginal prices ($/MWh)')"),
L("print(n.buses_t.marginal_price.iloc[0].round(2).to_string())"),
L("print()"),
L("print(f'total generation cost ${n.objective:,.2f} /hr')"),
))

# ============================================================ verification
A(md(
L("### The check that makes the point"),
L(""),
L("`bal_dal.Pi` in your hand-written Gurobi model and "
  "`n.buses_t.marginal_price['Dallas']` in PyPSA are **the same number**, "
  "because they are the same dual variable of the same constraint."),
))

A(code(
L("py_lmp = n.buses_t.marginal_price.iloc[0]"),
L("py_gen = n.generators_t.p.iloc[0]"),
L(""),
L("rows = ["),
L("    ('wind MW', P_wind.X, py_gen['WTX_Wind']),"),
L("    ('gas MW', P_gas.X, py_gen['HOU_Gas']),"),
L("    ('LMP West Texas', lmp_wtx, py_lmp['West Texas']),"),
L("    ('LMP Dallas', lmp_dal, py_lmp['Dallas']),"),
L("    ('LMP Houston', lmp_hou, py_lmp['Houston']),"),
L("    ('total cost', m.ObjVal, n.objective),"),
L("]"),
L(""),
L("print(f'{\"quantity\":16s} {\"gurobipy\":>12s} {\"PyPSA\":>12s}  match')"),
L("for label, a, b in rows:"),
L("    ok = 'yes' if abs(a - b) < 1e-6 else 'NO'"),
L("    print(f'{label:16s} {a:12.2f} {b:12.2f}  {ok}')"),
L(""),
L("assert all(abs(a - b) < 1e-6 for _, a, b in rows), 'the two models differ'"),
L("print()"),
L("print('Same model. PyPSA did not invent new mathematics -'"),
L("      ' it wrote your constraints for you.')"),
))

# ================================================================== part E
A(md(
L("---"),
L("# Part E - Where does the loop flow go?"),
L(""),
L("You saw 20 MW take the long way round at a 70 MW limit. That number is not "
  "a coincidence - for this network you can work it out in closed form. With "
  "all three reactances equal, the flow on Houston to West Texas is exactly"),
L(""),
L("&nbsp;&nbsp;&nbsp;&nbsp;*F<sub>HW</sub>* = 120 − 2*L*"),
L(""),
L("where *L* is the limit on the West Texas to Dallas line."),
L(""),
L("**Predict before running:** at what limit does the loop flow disappear "
  "entirely? And what happens above that?"),
L(""),
L("One of the five rows below will not solve at all. Before you run it, work "
  "out which one and why - it is an arithmetic question about the gas plant, "
  "not about the network."),
))

A(code(
L("rows = []"),
L("for limit in [40, 50, 60, 70, 80]:"),
L("    k = pypsa.Network()"),
L("    k.set_snapshots([0])"),
L("    for b in ['West Texas', 'Dallas', 'Houston']:"),
L("        k.add('Bus', b)"),
L("    k.add('Generator', 'WTX_Wind', bus='West Texas',"),
L("          p_nom=150, marginal_cost=0)"),
L("    k.add('Generator', 'HOU_Gas', bus='Houston',"),
L("          p_nom=100, marginal_cost=40)"),
L("    k.add('Load', 'Dallas_Demand', bus='Dallas', p_set=120)"),
L("    k.add('Line', 'WTX_DAL', bus0='West Texas', bus1='Dallas',"),
L("          x=0.1, s_nom=limit)"),
L("    k.add('Line', 'DAL_HOU', bus0='Dallas', bus1='Houston',"),
L("          x=0.1, s_nom=1000)"),
L("    k.add('Line', 'HOU_WTX', bus0='Houston', bus1='West Texas',"),
L("          x=0.1, s_nom=1000)"),
L("    status, condition = k.optimize(solver_name=SOLVER, env=ENV)"),
L(""),
L("    if condition != 'optimal':"),
L("        # not a bug - see the note below the table"),
L("        rows.append({'limit MW': limit, 'wind MW': None, 'gas MW': None,"),
L("                     'HOU->WTX MW': None, 'LMP Dallas': None,"),
L("                     'cost $/hr': None, 'status': 'CANNOT SOLVE'})"),
L("        print(f'  limit {limit} MW: solver said {condition!r}')"),
L("        continue"),
L(""),
L("    g = k.generators_t.p.iloc[0]"),
L("    f = k.lines_t.p0.iloc[0]"),
L("    p = k.buses_t.marginal_price.iloc[0]"),
L("    rows.append({'limit MW': limit,"),
L("                 'wind MW': round(g['WTX_Wind'], 1),"),
L("                 'gas MW': round(g['HOU_Gas'], 1),"),
L("                 'HOU->WTX MW': round(f['HOU_WTX'], 1),"),
L("                 'LMP Dallas': round(p['Dallas'], 2),"),
L("                 'cost $/hr': round(k.objective, 2),"),
L("                 'status': 'optimal'})"),
L(""),
L("sweep = pd.DataFrame(rows).set_index('limit MW')"),
L("print(sweep.to_string())"),
))

A(md(
L("> **The 40 MW row is infeasible, and that is the correct answer.** With "
  "only 40 MW able to reach Dallas directly, the rest has to come from gas - "
  "but the formula says gas would need 240 − 3*L* = 120 MW, and the plant is "
  "only 100 MW. The model refuses. Below **L = 46.7 MW this network cannot "
  "serve Dallas at all**, and no amount of wind in West Texas changes that."),
L(">"),
L("> An infeasible model is information, not a failure. It told you the "
  "system's breaking point without your having to search for it."),
L(">"),
L("> **Now read the `HOU->WTX` column against the formula.** It is +20, 0, "
  "−20, −40 as the limit goes 50, 60, 70, 80 - exactly 120 − 2*L*."),
L(">"),
L("> **At a 60 MW limit the loop flow is exactly zero** - the one setting "
  "where this network happens to behave like a simple transport model. Sitting "
  "either side of it, power flows through Houston in *opposite directions*: "
  "below 60 the gas plant is helping supply West Texas, above 60 the wind "
  "farm is exporting through Houston."),
L(">"),
L("> **Exercise E.1.** At a 60 MW limit, a transport model and a power-flow "
  "model give the same answer. Explain why that is a coincidence and not a "
  "reassurance. What would you have concluded about this network if 60 MW "
  "were the only case you had ever tested?"),
L(">"),
L("> **Exercise E.2.** The Dallas LMP column changes with the limit. At which "
  "limit does congestion pricing switch off, and what is the price then?"),
))

# ================================================================== part F
A(md(
L("---"),
L("# Part F - Reactance steers power"),
L(""),
L("Everything so far used *X* = 0.1 on all three lines. Now change **only** "
  "the reactance of the Houston to West Texas line - the loop path - and "
  "leave every capacity exactly as it was."),
L(""),
L("**Predict first.** The direct West Texas to Dallas line is already full at "
  "70 MW and stays full in every case below. So making the loop path easier "
  "or harder cannot move power onto the direct route. What does it change?"),
L(""),
L("**This is the lever a transmission planner actually has.** You cannot tell "
  "power where to go, but you can change how hard each path is - by building "
  "a parallel line, by choosing a conductor, by switching a series device in "
  "or out."),
))

A(code(
L("rows = []"),
L("for label, x_hw in [('easier loop  X=0.05', 0.05),"),
L("                    ('base         X=0.10', 0.10),"),
L("                    ('harder loop  X=0.20', 0.20)]:"),
L("    k = pypsa.Network()"),
L("    k.set_snapshots([0])"),
L("    for b in ['West Texas', 'Dallas', 'Houston']:"),
L("        k.add('Bus', b)"),
L("    k.add('Generator', 'WTX_Wind', bus='West Texas',"),
L("          p_nom=150, marginal_cost=0)"),
L("    k.add('Generator', 'HOU_Gas', bus='Houston',"),
L("          p_nom=100, marginal_cost=40)"),
L("    k.add('Load', 'Dallas_Demand', bus='Dallas', p_set=120)"),
L("    k.add('Line', 'WTX_DAL', bus0='West Texas', bus1='Dallas',"),
L("          x=0.1, s_nom=70)"),
L("    k.add('Line', 'DAL_HOU', bus0='Dallas', bus1='Houston',"),
L("          x=0.1, s_nom=1000)"),
L("    k.add('Line', 'HOU_WTX', bus0='Houston', bus1='West Texas',"),
L("          x=x_hw, s_nom=1000)"),
L("    k.optimize(solver_name=SOLVER, env=ENV)"),
L(""),
L("    g = k.generators_t.p.iloc[0]"),
L("    f = k.lines_t.p0.iloc[0]"),
L("    p = k.buses_t.marginal_price.iloc[0]"),
L("    rows.append({'scenario': label,"),
L("                 'wind MW': round(g['WTX_Wind'], 1),"),
L("                 'gas MW': round(g['HOU_Gas'], 1),"),
L("                 'WTX->DAL MW': round(f['WTX_DAL'], 1),"),
L("                 'HOU->WTX MW': round(f['HOU_WTX'], 1),"),
L("                 'LMP Dallas': round(p['Dallas'], 2),"),
L("                 'cost $/hr': round(k.objective, 2)})"),
L(""),
L("print(pd.DataFrame(rows).set_index('scenario').T.to_string())"),
))

A(md(
L("### Read that table carefully - it contains a trap"),
L(""),
L("**`WTX->DAL` is 70 MW in all three columns.** The direct line is full "
  "regardless. So what actually changed is the *loop*: 40, 20, then 10 MW. "
  "Easier loop path, more wind reaches Dallas the long way - 110 MW, 90 MW, "
  "80 MW - and gas covers whatever wind cannot deliver."),
L(""),
L("**Total cost goes $400, $1,200, $1,600.** Nobody built or removed a single "
  "MW of capacity. The only thing that changed was how hard one path is."),
L(""),
L("Now the trap. Look at the Dallas LMP: **$120, $80, $60.** The price is "
  "*highest* in the cheapest system and *lowest* in the most expensive one. "
  "That is not an error."),
L(""),
L("For this network the relationship is exact:"),
L(""),
L("&nbsp;&nbsp;&nbsp;&nbsp;LMP<sub>Dallas</sub> = LMP<sub>Houston</sub> × "
  "( 1 + *X*<sub>WD</sub> / *X*<sub>HW</sub> )"),
L(""),
L("Check it: 40 × (1 + 0.1/0.05) = 120. 40 × (1 + 0.1/0.1) = 80. "
  "40 × (1 + 0.1/0.2) = 60."),
L(""),
L("The easier the loop path, the more leverage one extra MW at Dallas has "
  "over the whole system - so the *marginal* price climbs even as the *total* "
  "bill falls. **Total cost and marginal price answer different questions.** "
  "Confusing the two is among the most common and most expensive mistakes in "
  "energy analysis: a location with a high LMP is not necessarily a location "
  "where the system is doing badly."),
L(""),
L("> **Exercise F.1.** You are a planner trying to relieve congestion on the "
  "West Texas to Dallas line, and you have budget for exactly one project. "
  "Would you (a) build a second parallel West Texas to Dallas line, or "
  "(b) upgrade the Houston to West Texas line to lower its reactance? Use the "
  "table to argue for one, then test the other by editing the cell above."),
L(">"),
L("> **Exercise F.2.** A generator developer is choosing where to site a new "
  "plant and picks Dallas because its LMP is the highest on the system. Using "
  "the X=0.05 column, explain why that reasoning is dangerous."),
L(">"),
L("> **Exercise F.3 - the one worth putting in a report.** A new data centre "
  "opens at Dallas and demand rises from 120 MW to 200 MW. Is the system "
  "still feasible with the 70 MW limit? Find the largest Dallas demand this "
  "network can serve, and say which constraint stops it."),
))

# ================================================== close: the question, and sources
A(md(
L("---"),
L("*Before class: the price at the constrained bus rose above every "
  "generator's cost. If you were siting a large load, would you rather "
  "sit there or at the cheap bus - and what would your arrival do to "
  "the price you picked it for?*"),
L(""),
L("### Sources"),
L("- DC power-flow approximation and the reference-bus requirement: any "
  "power-systems text; see also the PyPSA docs on `Line` and "
  "`Kirchhoff-Voltage-Law`."),
L("- ERCOT nodal prices and Congestion Revenue Rights: ercot.com market "
  "information."),
L("- The $22.14/MWh delivered gas figure used elsewhere in this course is "
  "built in the SB6 notebook; the $40/MWh here is a round number chosen to "
  "make the arithmetic checkable by hand."),
))


def syntax_check(cells):
    bad = 0
    for i, c in enumerate(cells):
        if c["cell_type"] != "code":
            continue
        src = "".join(c["source"])
        src = "\n".join(l for l in src.splitlines()
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
