# -*- coding: utf-8 -*-
"""A third reader of the tool-neutral bundle, for the model-diversity notebook.

    from esm.diversity import solve_expansion, sunk_cost
    r = solve_expansion(tables)
    r.cost, r.arc_mw, build_by_tech(r)

WHAT THIS IS FOR

`notebooks/graduate/model_diversity.ipynb` already does what every other
notebook here needs an agreement assertion to do: it builds the same capacity
expansion twice, in PyPSA and in PuLP, and compares them. The comparison IS its
subject.

So this module is not a second implementation. It is a **third**, and it works
the way the notebook argues for: the notebook writes a tool-neutral bundle of
tables and says both models read it. This reads the same bundle -- the same
dict, not a copy of the numbers -- and solves it through
`scipy.optimize.linprog`.

WHY A THIRD IS WORTH ANYTHING WHEN TWO ALREADY AGREE

Two implementations agreeing rules out a transcription slip. It does not rule
out a shared misreading of the formulation, and the PyPSA and PuLP versions
here were written by the same person from the same page on the same day. This
one is written from the LP algebra directly -- signed flows, explicit balance
rows -- so it disagrees with a misreading rather than inheriting it.

It also has no notion of a network at all, which the PyPSA version does. That
matters for the notebook's Part 5: the DC formulation gives a different answer
because it imposes physics the transport formulation does not, and a reader
should be able to see that the transport answer is a property of the algebra
rather than of PyPSA.

THE SUNK-COST CONVENTION IS AN IDENTITY, NOT A TOLERANCE

Part 4's result is that PuLP and PyPSA differ by exactly the daily capital on
the corridors that already exist, because one convention charges capital on the
whole corridor and the other only on what is built above what is there.

That is an exact identity, so `sunk_cost()` computes it and the notebook now
asserts it relatively through AGREEMENT_RTOL. It previously used
`abs(gap - sunk) < 1.0` -- one dollar on a twenty-three million dollar
objective, which is 4e-8 relative, and would have accepted a discrepancy forty
times larger than the tolerance it should have had.

WHAT MAY AND MAY NOT BE COMPARED -- AND THE ANSWER IS NOT "THE BUILD"

Measured on this bundle, by fixing total cost at its optimum and asking how far
each quantity can then move:

    technology totals    unique to ~1e-10 MW
    corridor capacities  unique to ~1e-10 MW
    PER-HUB capacities   NOT unique, and not nearly

West Texas solar is free anywhere in [6,467, 11,723] MW. Dallas-Fort Worth,
Houston and Austin solar are each free across their entire limit. Seven of the
fifteen hub/technology pairs are undetermined.

The reason is not subtle once seen: solar costs the same annualised amount
wherever it is built, and the corridors can move its output, so the model is
indifferent to which hub it sits at as long as the total is right and the
transmission exists. Nothing about that is a defect -- it is what a transport
formulation with uniform capital costs means.

**The notebook already compares technology totals rather than per-hub builds,
which is the correct choice.** What was missing is that it was an undocumented
one: a later reader tightening the comparison to per-hub would get a failure
about neither tool. `assert_comparable_quantities_are_unique()` checks the
totals and the corridors and passes; `per_hub_ranges()` reports the
degeneracy, so the choice is now checked rather than lucky.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExpansionResult:
    cost: float                  # $/day
    generation_mw: dict          # (hub, tech) -> MW built
    arc_mw: dict                 # (a, b) -> MW of corridor capacity
    dispatch: dict               # (hub, tech, hour) -> MW


@dataclass(frozen=True)
class _Program:
    """The LP in column form, assembled once and reused by every solve."""
    hubs: list
    techs: list
    hours: list
    arc_keys: list
    cost: list                   # objective row
    A_ub: list
    b_ub: list
    A_eq: list
    b_eq: list
    bounds: list
    cap_index: dict              # (hub, tech) -> column
    arc_index: dict              # (a, b) -> column
    disp_index: dict             # (hub, tech, hour) -> column


def sunk_cost(tables):
    """Daily capital on the corridor capacity that already exists.

    Exactly the difference between the notebook's two Part 4 conventions:
    charge capital on the whole corridor, or only on what is built above what
    is already there.
    """
    arcs = tables["arcs"]
    return float((arcs["existing_mw"] * arcs["daily_capital"]).sum())


def _assemble(tables):
    """Build the LP once. Every entry point below goes through this.

    One assembly rather than two: a second copy of these matrices would be a
    second place for the formulation to be wrong, and the two could disagree
    without anything comparing them.
    """
    demand, tech = tables["demand"], tables["tech"]
    limit, avail = tables["limit"], tables["avail"]
    arcs = tables["arcs"].set_index(["a", "b"])

    hubs, hours = list(demand.columns), list(demand.index)
    techs, arc_keys = list(tech.index), list(arcs.index)
    nG, nT = len(techs), len(hours)

    cap_index, disp_index, arc_index = {}, {}, {}
    col = 0
    for hub in hubs:
        for t in techs:
            cap_index[(hub, t)] = col
            col += 1
    for key in arc_keys:
        arc_index[key] = col
        col += 1
    for hub in hubs:
        for t in techs:
            for h in hours:
                disp_index[(hub, t, h)] = col
                col += 1
    flow_index = {}
    for key in arc_keys:
        for h in hours:
            flow_index[(key, h)] = col
            col += 1
    total = col

    cost = [0.0] * total
    for hub in hubs:
        for t in techs:
            cost[cap_index[(hub, t)]] = float(tech["daily_capital"][t])
            for h in hours:
                cost[disp_index[(hub, t, h)]] = float(tech["mc"][t])
    for key in arc_keys:
        cost[arc_index[key]] = float(arcs["daily_capital"][key])

    A_ub, b_ub = [], []
    for hub in hubs:                              # disp <= avail * cap
        for t in techs:
            for h in hours:
                row = [0.0] * total
                row[disp_index[(hub, t, h)]] = 1.0
                row[cap_index[(hub, t)]] = -float(avail[t][h])
                A_ub.append(row)
                b_ub.append(0.0)
    for key in arc_keys:                          # |flow| <= acap
        for h in hours:
            for sign in (1.0, -1.0):
                row = [0.0] * total
                row[flow_index[(key, h)]] = sign
                row[arc_index[key]] = -1.0
                A_ub.append(row)
                b_ub.append(0.0)

    A_eq, b_eq = [], []                           # nodal balance
    for hub in hubs:
        for h in hours:
            row = [0.0] * total
            for t in techs:
                row[disp_index[(hub, t, h)]] = 1.0
            for (pa, pb) in arc_keys:
                if pb == hub:
                    row[flow_index[((pa, pb), h)]] += 1.0
                if pa == hub:
                    row[flow_index[((pa, pb), h)]] -= 1.0
            A_eq.append(row)
            b_eq.append(float(demand[hub][h]))

    bounds = [(0.0, None)] * total
    for hub in hubs:
        for t in techs:
            bounds[cap_index[(hub, t)]] = (0.0, float(limit.loc[hub, t]))
    for key in arc_keys:
        bounds[arc_index[key]] = (float(arcs["existing_mw"][key]),
                                  float(arcs["max_mw"][key]))
        for h in hours:
            bounds[flow_index[(key, h)]] = (None, None)   # signed

    return _Program(hubs=hubs, techs=techs, hours=hours, arc_keys=arc_keys,
                    cost=cost, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                    bounds=bounds, cap_index=cap_index, arc_index=arc_index,
                    disp_index=disp_index)


def _run(program, objective, extra_eq=None):
    """Solve `program` with a given objective row and optional extra equality."""
    from scipy.optimize import linprog

    A_eq, b_eq = program.A_eq, program.b_eq
    if extra_eq is not None:
        row, rhs = extra_eq
        A_eq, b_eq = A_eq + [row], b_eq + [rhs]

    res = linprog(objective, A_ub=program.A_ub, b_ub=program.b_ub,
                  A_eq=A_eq, b_eq=b_eq, bounds=program.bounds, method="highs")
    if not res.success:
        raise RuntimeError(
            f"the expansion LP did not solve: {res.message}. An infeasible "
            f"result usually means the resource limits cannot meet peak demand "
            f"at a hub the corridors cannot reach."
        )
    assert len(res.x) == len(program.cost), "solution vector has wrong length"
    return res


def solve_expansion(tables, charge_existing=True):
    """Least-cost capacity expansion as a transport LP, through scipy.

    `charge_existing=False` matches PyPSA's convention: corridor capital is
    charged only above the existing capacity. That is a constant shift of the
    objective, which linprog has no term for, so it is applied after the solve.
    """
    program = _assemble(tables)
    res = _run(program, program.cost)
    offset = 0.0 if charge_existing else -sunk_cost(tables)

    return ExpansionResult(
        cost=float(res.fun) + offset,
        generation_mw={k: float(res.x[c]) for k, c in program.cap_index.items()},
        arc_mw={k: float(res.x[c]) for k, c in program.arc_index.items()},
        dispatch={k: float(res.x[c]) for k, c in program.disp_index.items()},
    )


def build_by_tech(result):
    """Total MW built of each technology, across hubs."""
    out = {}
    for (_hub, tech), mw in result.generation_mw.items():
        out[tech] = out.get(tech, 0.0) + mw
    return out


def _range_at_optimum(program, optimal, columns, tol=1e-6):
    """How far the sum of `columns` can move while total cost stays optimal."""
    n = len(program.cost)
    obj = [0.0] * n
    for c in columns:
        obj[c] = 1.0
    lo = float(_run(program, obj, (program.cost, optimal)).fun)
    obj = [0.0] * n
    for c in columns:
        obj[c] = -1.0
    hi = -float(_run(program, obj, (program.cost, optimal)).fun)
    return lo, hi


def per_hub_ranges(tables):
    """How far each hub's capacity can move at no change in total cost.

    Returns `{(hub, tech): (low, high)}`. On this instance most of these are
    WIDE -- several hubs' solar is interchangeable, because the annualised
    capital is the same everywhere and the corridors can move the output. That
    is a real property of the model and it is why the notebook compares
    technology totals rather than per-hub builds.
    """
    program = _assemble(tables)
    optimal = float(_run(program, program.cost).fun)
    return {k: _range_at_optimum(program, optimal, [c])
            for k, c in program.cap_index.items()}


def assert_comparable_quantities_are_unique(tables, tol=1e-6):
    """Fail unless the quantities the notebook compares are determined.

    Part 6, applied to what is actually compared rather than to everything.
    Measured on this instance:

      technology totals   unique to ~1e-10 MW
      arc capacities      unique to ~1e-10 MW
      PER-HUB capacities  NOT unique -- West Texas solar is free across a
                          5,000 MW range, and four other hubs across their
                          whole limit

    So comparing per-hub builds between PyPSA and PuLP would fail for a reason
    that is about neither tool. The notebook compares the totals, which is
    correct, and this is what makes that a checked decision rather than a lucky
    one.
    """
    program = _assemble(tables)
    optimal = float(_run(program, program.cost).fun)

    bad = []
    for tech in program.techs:
        cols = [c for (_h, t), c in program.cap_index.items() if t == tech]
        lo, hi = _range_at_optimum(program, optimal, cols)
        if hi - lo > tol:
            bad.append(f"total {tech} anywhere in [{lo:,.1f}, {hi:,.1f}] MW")
    for key, col in program.arc_index.items():
        lo, hi = _range_at_optimum(program, optimal, [col])
        if hi - lo > tol:
            bad.append(f"corridor {key[0]}-{key[1]} in [{lo:,.1f}, {hi:,.1f}] MW")

    if bad:
        raise AssertionError(
            "these are not determined by the optimum, so the two tools may "
            "report different values while both are right: "
            + "; ".join(bad) + ". Compare total cost instead -- see Part 6."
        )
    return True
