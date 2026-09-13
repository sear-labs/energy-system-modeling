# -*- coding: utf-8 -*-
"""Minimum-cost transportation, written once so a notebook can be checked against it.

    from esm.transport import load_transport_instance, solve_transport
    inst = load_transport_instance()
    r = solve_transport(inst)
    r.cost, r.flows

WHAT THIS IS FOR

`notebooks/p4_networks/17_pipeline_transport.ipynb` builds this same instance
twice by hand: once in gurobipy (the "Kickback" sensitivity model, in thousands
of bbl/d), and once narrated component-by-component in PyPSA (Steps 1-6, in raw
bbl/d) -- which is the version this module is checked against, since that is the
walkthrough a student actually reads cell by cell.

This module solves the SAME instance through `scipy.optimize.linprog` rather
than through PyPSA or gurobipy. That is deliberate, for the same reason
`esm.power_flow` goes through PyPSA where its notebook writes gurobipy by hand:
two transcriptions of the same algebra share their mistakes, so agreement is
only worth something across genuinely different formulations. `linprog` is also
free of any solver licence question -- HiGHS underneath, but through scipy's own
interface rather than through PyPSA's.

WHAT THE ASSERTION MAY AND MAY NOT COMPARE

Unlike DC power flow, a transportation LP's optimum is not always unique in its
flows even when its cost is: with two routes tied on cost, the split between them
can differ between solvers while the total is identical. On THIS instance the
routes are not tied -- costs are 1.50, 2.50, 3.00, 3.50, 4.00, 4.50, all
distinct -- so flows happen to be unique too, and both are asserted. An instance
with tied costs would need the flow comparison dropped to the invariant (total
cost, and the binding capacity) rather than the per-route split.

WHERE THE BUG WAS

Writing this module is what caught it: the notebook's own printed total cost
(`n.objective * 1000`) was 1000x too large, because `n`'s inputs are already in
raw barrels and its objective is already real dollars -- the `* 1000` belongs to
the SEPARATE gurobipy model three cells earlier, whose decision variables are in
THOUSANDS of barrels and therefore does need it. Confirmed by solving both by
hand before touching the notebook: gurobipy's `ObjVal * 1000` and PyPSA's
`n.objective` (no multiplier) both give $490,000; the notebook's own print
statement was the only place computing $490,000,000.
"""
from __future__ import annotations

from dataclasses import dataclass

from esm.data import table


@dataclass(frozen=True)
class TransportInstance:
    """The tables a transportation LP needs, as plain columns."""
    supply_nodes: list
    demand_nodes: list
    supply: dict              # node -> bbl/d
    demand: dict               # node -> bbl/d
    routes: dict                # (supply_node, demand_node) -> {"cost", "capacity"}


@dataclass(frozen=True)
class TransportResult:
    cost: float                 # $/day
    flows: dict                  # (supply_node, demand_node) -> bbl/d


def load_transport_instance(source=None):
    """The Texas crude-oil routing instance, from `data/raw/`.

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
    """
    sup = table("transport_supply.csv", source=source)
    supply = dict(zip(sup["node"], sup["p_nom"].astype(float)))

    dem = table("transport_demand.csv", source=source)
    demand = dict(zip(dem["node"], dem["p_set"].astype(float)))

    rt = table("transport_routes.csv", source=source)
    routes = {
        (row["supply_node"], row["demand_node"]): {
            "cost": float(row["cost_per_bbl"]),
            "capacity": float(row["capacity"]),
        }
        for _, row in rt.iterrows()
    }

    return TransportInstance(
        supply_nodes=list(supply), demand_nodes=list(demand),
        supply=supply, demand=demand, routes=routes,
    )


def solve_transport(inst):
    """Solve the balanced transportation LP and return cost and flows.

    Requires total supply to equal total demand -- true of this instance
    (180,000 bbl/d both sides) and asserted rather than assumed, because an
    unbalanced instance needs a slack node, not a silently infeasible solve.
    """
    from scipy.optimize import linprog

    total_supply = sum(inst.supply.values())
    total_demand = sum(inst.demand.values())
    if abs(total_supply - total_demand) > 1e-6:
        raise ValueError(
            f"unbalanced instance: supply {total_supply:,.0f} != "
            f"demand {total_demand:,.0f} bbl/d. This solver assumes a balanced "
            f"transportation problem; add a slack/dummy node for the gap."
        )

    route_keys = list(inst.routes)
    c = [inst.routes[k]["cost"] for k in route_keys]
    bounds = [(0, inst.routes[k]["capacity"]) for k in route_keys]

    A_eq, b_eq = [], []
    for s in inst.supply_nodes:
        A_eq.append([1.0 if k[0] == s else 0.0 for k in route_keys])
        b_eq.append(inst.supply[s])
    for d in inst.demand_nodes:
        A_eq.append([1.0 if k[1] == d else 0.0 for k in route_keys])
        b_eq.append(inst.demand[d])

    res = linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")
    if not res.success:
        raise RuntimeError(
            f"the transport LP did not solve: {res.message}. An infeasible "
            f"result here usually means a route capacity was tightened below "
            f"what the network needs to balance supply and demand."
        )

    # Shape assert, not a status check. Part 6: a call that returns an empty or
    # malformed result can still report success.
    assert len(res.x) == len(route_keys), "solution vector has the wrong length"

    return TransportResult(
        cost=float(res.fun),
        flows={k: float(x) for k, x in zip(route_keys, res.x)},
    )


def binding_routes(inst, result, tol=1e-6):
    """Which routes are at their capacity limit -- the ones a shadow price
    would move. Used to check the notebook's "the bottleneck" claim in code
    rather than only in prose."""
    return [k for k in inst.routes
            if inst.routes[k]["capacity"] < 1e5
            and result.flows[k] > inst.routes[k]["capacity"] - tol]
