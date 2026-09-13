# -*- coding: utf-8 -*-
"""Two-stage minimum-cost sourcing, written once so a notebook can be checked against it.

    from esm.sourcing import load_sourcing_instance, solve_sourcing
    inst = load_sourcing_instance()
    r = solve_sourcing(inst)
    r.cost, r.flows, r.by_mine

WHAT THIS IS FOR

`notebooks/p5_storage_supply/21_material_requirements.ipynb` builds this same
instance twice by hand: once in gurobipy (Parts A-C, the five numbered parts of
an LP) and once in PyPSA (Part D, mines as generators and plants as loads). This
module solves it a THIRD way, through `scipy.optimize.linprog`.

Three routes rather than two is not belt-and-braces. The notebook's own PyPSA
cell already asserts against its gurobipy cell, and that pair shares a weakness:
both are transcriptions written by the same person from the same table in the
same sitting, so a misread capacity is in both and the assertion passes. Reading
the instance from `data/raw/` and solving it through a third library is what
makes the agreement evidence rather than ceremony.

THE MODEL

Ore flows mine -> processor, metal flows processor -> plant:

    minimise   sum(ship[i,p] * x[i,p])  +  sum(deliver[p,j] * y[p,j])
    subject to sum_p x[i,p] <= mine capacity M_i
               sum_i x[i,p] <= processor capacity P_p
               sum_i x[i,p]  =  sum_j y[p,j]        conservation at p
               sum_p y[p,j]  =  plant demand D_j

The conservation row is the interesting one pedagogically -- it is a nodal
balance wearing different clothes, the same equation `esm.power_flow` writes at
a bus. That is the point of the notebook and the reason this LP is deliberately
the transport LP from `esm.transport` with different labels.

WHAT THE ASSERTION MAY AND MAY NOT COMPARE

**On this instance every flow is unique, and that was measured rather than
assumed.** The test is not "are the costs distinct" -- it is whether the optimal
face is a single point. Verified by fixing total cost at its optimum, then
maximising and minimising each variable subject to that: if any variable has a
range, the optimum is a face and that variable is not comparable. None does.
`assert_flows_are_unique()` below runs exactly that check, so the claim is
re-derived on the current tables rather than trusted from this docstring.

**It is unique by a coincidence that an edit can remove.** China -> Cell Plant A
and China -> Cell Plant B both cost 3.00, as do both Domestic deliveries. So the
split of a processor's output between the two plants is free whenever two
processors are active: only the totals are determined. Here exactly one
processor carries everything, so the two plant demands pin y completely. Change
the tables so both processors run and the per-route y values stop being
comparable while the cost stays comparable -- at which point the agreement
assertion must shed those rows rather than be loosened. This is Part 6's rule,
and `assert_flows_are_unique()` is what turns it from a comment into a check.

A TIGHT CONSTRAINT IS NOT THE SAME AS A RESTRICTIVE ONE

China's processor capacity is 120 kt/yr and the optimum sends exactly 120
through it. The constraint is therefore **active** -- it holds with equality --
but it is **not restrictive**: delete it and the answer does not move, because
the cheapest route is capped at 120 by the DRC mine anyway.

That distinction matters here because the notebook omits processor capacity from
its PyPSA formulation (a bus has no capacity) and the two still agree. They
agree by coincidence, not because the constraint is slack, and the notebook's
Exercise E.1 turns on noticing it. `processor_utilisation()` reports the ratio
so a reader can see 100% rather than infer "not binding" from agreement.
"""
from __future__ import annotations

from dataclasses import dataclass

from esm.data import table


@dataclass(frozen=True)
class SourcingInstance:
    """The tables a two-stage sourcing LP needs, as plain columns."""
    mines: dict               # mine -> capacity kt/yr
    processors: dict          # processor -> capacity kt/yr
    plants: dict              # plant -> required kt/yr
    ship: dict                # (mine, processor) -> $/kt
    deliver: dict             # (processor, plant) -> $/kt


@dataclass(frozen=True)
class SourcingResult:
    cost: float               # $/yr
    flows: dict               # (origin, destination) -> kt/yr, both stages
    by_mine: dict             # mine -> kt/yr shipped
    by_processor: dict        # processor -> kt/yr refined


def load_sourcing_instance(source=None):
    """The cobalt sourcing instance, from `data/raw/`.

    Read through `esm.data.table`. NOTE that the notebook states its
    instance inline, in its "Sets and Parameters" cell, rather than reading
    these files -- showing the numbers is the teaching point there. So the
    tables and the notebook are two copies of one instance, and the agreement
    assertion is what stops them drifting: change one and the costs stop
    matching, which is what the assertion reports.

    That means editing `data/raw/` alone does NOT change the notebook's own
    answer, unlike `esm.power_flow`, whose notebook does read its tables. A
    reader editing these files to explore should expect the agreement cell to
    fail, and that failure is correct.

    The two route stages share one table, `sourcing_routes.csv`, and are told
    apart by their endpoints. That is derived rather than a declared column on
    purpose: a `stage` column would be a second place to say the same thing,
    and the two could disagree.
    """
    mn = table("sourcing_mines.csv", source=source)
    mines = dict(zip(mn["mine"], mn["capacity_kt"].astype(float)))

    pr = table("sourcing_processors.csv", source=source)
    processors = dict(zip(pr["processor"], pr["capacity_kt"].astype(float)))

    pl = table("sourcing_plants.csv", source=source)
    plants = dict(zip(pl["plant"], pl["demand_kt"].astype(float)))

    # A route's stage is decided by BOTH endpoints, never by the origin alone.
    #
    # "Domestic" is a mine AND a processor in this instance -- a deliberate
    # feature of the example, since a country that digs ore can also refine it.
    # An origin-only test ("if o in mines: ship") therefore files the Domestic
    # PROCESSOR's deliveries to the plants as MINE shipments, and the resulting
    # model is quietly a different problem.
    #
    # It does not fail loudly. The unconstrained optimum never uses the Domestic
    # processor, so the base case still returns $600 and agrees with the
    # notebook. Only a single-source cap tight enough to force a second
    # processor into the solution reveals it -- at a 40% cap the origin-only
    # loader returns $840 against the correct $768. That is why the stage test
    # is written as a pair of endpoint conditions and why the ambiguous case
    # below raises instead of picking.
    if set(processors) & set(plants):
        raise ValueError(
            f"names {sorted(set(processors) & set(plants))} are used for both a "
            f"processor and a plant, so a route's stage cannot be determined "
            f"from its endpoints. Rename one."
        )

    rt = table("sourcing_routes.csv", source=source)
    ship, deliver = {}, {}
    for _, row in rt.iterrows():
        o, d, c = row["origin"], row["destination"], float(row["cost_per_kt"])
        if o in mines and d in processors:
            ship[(o, d)] = c
        elif o in processors and d in plants:
            deliver[(o, d)] = c
        else:
            raise ValueError(
                f"route {o!r} -> {d!r} is neither a mine-to-processor nor a "
                f"processor-to-plant leg. Every row of sourcing_routes.csv must "
                f"be one or the other; check the node name against "
                f"sourcing_mines.csv, sourcing_processors.csv and "
                f"sourcing_plants.csv."
            )

    return SourcingInstance(mines=mines, processors=processors, plants=plants,
                            ship=ship, deliver=deliver)


def _matrices(inst):
    """The LP in column form, shared by the solve and the uniqueness check."""
    xk, yk = list(inst.ship), list(inst.deliver)
    cols = xk + yk
    c = [inst.ship[k] for k in xk] + [inst.deliver[k] for k in yk]

    A_ub, b_ub = [], []
    for i, cap in inst.mines.items():
        A_ub.append([1.0 if k[0] == i else 0.0 for k in xk] + [0.0] * len(yk))
        b_ub.append(cap)
    for p, cap in inst.processors.items():
        A_ub.append([1.0 if k[1] == p else 0.0 for k in xk] + [0.0] * len(yk))
        b_ub.append(cap)

    A_eq, b_eq = [], []
    for p in inst.processors:                       # conservation at p
        A_eq.append([1.0 if k[1] == p else 0.0 for k in xk]
                    + [-1.0 if k[0] == p else 0.0 for k in yk])
        b_eq.append(0.0)
    for j, need in inst.plants.items():             # plant demand
        A_eq.append([0.0] * len(xk)
                    + [1.0 if k[1] == j else 0.0 for k in yk])
        b_eq.append(need)

    return cols, c, A_ub, b_ub, A_eq, b_eq


def solve_sourcing(inst, single_source_cap=None):
    """Solve the sourcing LP and return cost and flows.

    `single_source_cap` is the resilience constraint the notebook's Part C
    sweeps: no one mine may supply more than that fraction of total demand.
    Passing 0.50 reproduces the "50% cap" row of its price curve.

    Raises rather than returning a sentinel when the LP is infeasible, which a
    tight enough cap will genuinely make it -- at 1/3 the three mines cannot
    cover demand between them, and that infeasibility is a real answer about the
    supply chain rather than a bug.
    """
    from scipy.optimize import linprog

    total_demand = sum(inst.plants.values())
    if sum(inst.mines.values()) < total_demand - 1e-9:
        raise ValueError(
            f"mine capacity {sum(inst.mines.values()):,.1f} kt cannot cover "
            f"plant demand {total_demand:,.1f} kt."
        )

    cols, c, A_ub, b_ub, A_eq, b_eq = _matrices(inst)

    if single_source_cap is not None:
        for i in inst.mines:
            A_ub.append([1.0 if (k in inst.ship and k[0] == i) else 0.0
                         for k in cols])
            b_ub.append(single_source_cap * total_demand)

    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                  bounds=[(0, None)] * len(cols), method="highs")
    if not res.success:
        raise RuntimeError(
            f"the sourcing LP did not solve: {res.message}. With a "
            f"single-source cap this usually means the cap is below "
            f"1/(number of mines) and no feasible split exists -- which is a "
            f"real statement about the supply chain, not a solver failure."
        )

    # Shape assert, not a status check. Part 6: a call that returns an empty or
    # malformed result can still report success.
    assert len(res.x) == len(cols), "solution vector has the wrong length"

    flows = {k: float(v) for k, v in zip(cols, res.x)}
    return SourcingResult(
        cost=float(res.fun),
        flows=flows,
        by_mine={i: sum(v for k, v in flows.items()
                        if k in inst.ship and k[0] == i) for i in inst.mines},
        by_processor={p: sum(v for k, v in flows.items()
                             if k in inst.deliver and k[0] == p)
                      for p in inst.processors},
    )


def processor_utilisation(inst, result):
    """Throughput / capacity at each processor.

    Exists so "the capacity does not bind" can be checked rather than assumed.
    A value of 1.0 means the constraint is ACTIVE -- which on this instance it
    is, at China -- even though deleting it would not move the answer. See the
    module docstring on tight versus restrictive.
    """
    return {p: sum(v for k, v in result.flows.items()
                   if k in inst.deliver and k[0] == p) / cap
            for p, cap in inst.processors.items()}


def assert_flows_are_unique(inst, tol=1e-7):
    """Fail unless the optimum is a single point, so flows may be compared.

    Part 6 forbids asserting on a quantity that ties. Rather than reason about
    which costs are distinct -- which is the step that goes wrong, because
    distinctness of the inputs is neither necessary nor sufficient -- this pins
    total cost at its optimal value and then maximises and minimises each
    variable subject to that. A variable with any range is one the optimum does
    not determine.

    Raises AssertionError naming the offending routes. Called by the notebook's
    agreement cell BEFORE it compares flows, so that an edit to `data/raw/` that
    introduces a tie fails with an explanation instead of failing as a mismatch.
    """
    from scipy.optimize import linprog

    cols, c, A_ub, b_ub, A_eq, b_eq = _matrices(inst)
    base = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                   bounds=[(0, None)] * len(cols), method="highs")
    if not base.success:
        raise RuntimeError(f"the sourcing LP did not solve: {base.message}")

    A_eq2 = A_eq + [c]
    b_eq2 = b_eq + [float(base.fun)]
    bounds = [(0, None)] * len(cols)

    ambiguous = []
    for idx, key in enumerate(cols):
        obj = [0.0] * len(cols)
        obj[idx] = 1.0
        lo = linprog(obj, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq2, b_eq=b_eq2,
                     bounds=bounds, method="highs")
        hi = linprog([-v for v in obj], A_ub=A_ub, b_ub=b_ub,
                     A_eq=A_eq2, b_eq=b_eq2, bounds=bounds, method="highs")
        if lo.success and hi.success and (-hi.fun) - lo.fun > tol:
            ambiguous.append((key, float(lo.fun), float(-hi.fun)))

    if ambiguous:
        detail = "; ".join(f"{o} -> {d} anywhere in [{a:.3f}, {b:.3f}]"
                           for (o, d), a, b in ambiguous)
        raise AssertionError(
            f"the optimum is a face, not a point, so per-route flows are not "
            f"comparable between solvers: {detail}. Compare total cost and the "
            f"per-mine totals instead, and teach the tie -- see Part 6."
        )
    return True
