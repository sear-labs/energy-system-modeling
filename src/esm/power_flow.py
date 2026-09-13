# -*- coding: utf-8 -*-
"""DC optimal power flow, written once so a notebook can be checked against it.

    from esm.power_flow import load_dcopf3, solve_dcopf
    inst = load_dcopf3()
    r = solve_dcopf(inst)
    r.cost, r.dispatch, r.flows, r.lmp

WHAT THIS IS FOR

`notebooks/p4_networks/18_power_flow_and_lmp.ipynb` builds this same model by
hand, one constraint per cell, because that is the lesson. This module builds it
once because that is the code. Neither is redundant: the notebook ends by running
both and asserting they agree, which is the only thing standing in for the
protection that normally comes from having a single copy.

WHAT THE ASSERTION MAY AND MAY NOT COMPARE

**The voltage angles are not unique and must never be compared.** DC power flow
determines angle *differences*, so the solution is fixed only up to a constant
added to every angle. The notebook pins West Texas to zero; PyPSA picks its own
reference; this module pins the first bus. All three are correct and all three
give different angles.

Flows, dispatch, prices and cost are the same in every optimum, so those are what
agreement is asserted on. This is Part 6's rule -- "where several answers tie,
assert only the invariant quantities and teach the degeneracy" -- and it is the
defect that every serious finding in both reviews of `teaching-code` turned out
to be, so it is worth being explicit rather than lucky.

**The dispatch here happens to be unique** because the two generators have
different costs and the binding line limit fixes the split. If a future instance
gives two generators the same cost, dispatch stops being unique while cost stays
unique, and the assertion has to shed the dispatch rows rather than be loosened.
"""
from __future__ import annotations

from dataclasses import dataclass

from esm.data import table


@dataclass(frozen=True)
class DCOPFInstance:
    """The tables a DC optimal power flow needs, as plain columns."""
    buses: list
    generators: dict          # name -> {"bus", "marginal_cost", "p_nom"}
    loads: dict               # bus -> MW
    lines: dict               # name -> {"bus0", "bus1", "x", "s_nom"}


@dataclass(frozen=True)
class DCOPFResult:
    cost: float               # $/hr
    dispatch: dict            # generator -> MW
    flows: dict               # line -> MW, positive bus0 -> bus1
    lmp: dict                 # bus -> $/MWh


def load_dcopf3(source=None):
    """The three-bus instance, from `data/raw/`.

    Read through `esm.data.table`, so the notebook and this module read the same
    file and a reader who edits it sees the edit on both sides. That is the whole
    reason the tables are not typed into either.
    """
    buses = list(table("dcopf3_buses.csv", source=source)["bus"])

    g = table("dcopf3_generators.csv", source=source)
    generators = {
        row["generator"]: {"bus": row["bus"],
                           "marginal_cost": float(row["marginal_cost"]),
                           "p_nom": float(row["p_nom"])}
        for _, row in g.iterrows()
    }

    ld = table("dcopf3_loads.csv", source=source)
    loads = {row["bus"]: float(row["p_set"]) for _, row in ld.iterrows()}

    ln = table("dcopf3_lines.csv", source=source)
    lines = {
        row["line"]: {"bus0": row["bus0"], "bus1": row["bus1"],
                      "x": float(row["x"]), "s_nom": float(row["s_nom"])}
        for _, row in ln.iterrows()
    }
    return DCOPFInstance(buses=buses, generators=generators, loads=loads, lines=lines)


def solve_dcopf(inst, solver="highs"):
    """Solve the DC OPF and return dispatch, flows, prices and cost.

    Built on PyPSA rather than on a hand-written LP, deliberately: the notebook
    already writes the LP out by hand in gurobipy, and a second hand-written copy
    here would agree with it for the wrong reason -- two transcriptions of the
    same algebra share their mistakes. Going through a different formulation is
    what makes the agreement worth anything.

    `solver` defaults to HiGHS: free, no size cap, and what a student has.
    """
    import logging

    import pypsa

    # Quiet, because this is a library being called from a teaching notebook.
    # PyPSA and linopy narrate every step at INFO, and the consistency check
    # warns about carriers and zero resistance -- true, and irrelevant to a DC
    # model that uses only reactance. Left on, twenty lines of log bury the eight
    # numbers the reader came for.
    #
    # Scoped to this call and restored afterwards: a library that permanently
    # reconfigures the root logger is worse than a noisy one.
    import warnings

    quieted = ["pypsa", "linopy", "pypsa.consistency", "pypsa.optimization.optimize"]
    previous = {name: logging.getLogger(name).level for name in quieted}
    for name in quieted:
        logging.getLogger(name).setLevel(logging.ERROR)

    try:
        with warnings.catch_warnings():
            # PyPSA 1.3 warns that pandas 3 infers `str` where it still
            # coerces to object. That is PyPSA's internal business and says
            # nothing about this model, so it is silenced.
            #
            # Matched on the MESSAGE, not on `module=`: the warning surfaces at
            # this call site rather than inside pypsa, so a module filter misses
            # it. Narrow on purpose -- the other FutureWarning PyPSA raises here,
            # about `include_objective_constant`, is one that could change an
            # answer, and it is dealt with by setting the parameter rather than
            # by hiding the warning.
            warnings.filterwarnings(
                "ignore", category=FutureWarning,
                message=r".*pandas infers the `str` dtype.*")
            return _solve_dcopf(inst, solver)
    finally:
        for name, level in previous.items():
            logging.getLogger(name).setLevel(level)


def _solve_dcopf(inst, solver):
    import pypsa

    n = pypsa.Network()
    n.set_snapshots([0])

    for b in inst.buses:
        n.add("Bus", b)
    for name, g in inst.generators.items():
        n.add("Generator", name, bus=g["bus"],
              p_nom=g["p_nom"], marginal_cost=g["marginal_cost"])
    for bus, mw in inst.loads.items():
        n.add("Load", f"{bus}_load", bus=bus, p_set=mw)
    for name, l in inst.lines.items():
        n.add("Line", name, bus0=l["bus0"], bus1=l["bus1"],
              x=l["x"], s_nom=l["s_nom"])

    # HiGHS and Gurobi write their banners to the process's stdout at the C
    # level, which Python's logging cannot reach -- so they are switched off at
    # the solver instead. Both spell it differently, which is the only reason
    # this is a dict lookup rather than one argument.
    quiet = {"highs": {"output_flag": False},
             "gurobi": {"OutputFlag": 0}}.get(solver, {})

    # `include_objective_constant` is set explicitly rather than left to warn.
    # PyPSA 2.0 flips its default from True to False, and that is a change that
    # could move an objective value -- exactly the "unpinned dependency silently
    # alters results" failure Part 1 rule 3 names. Suppressing the warning would
    # leave the behaviour to whichever PyPSA is installed; setting it pins the
    # behaviour and silences the warning as a side effect.
    #
    # False is chosen because it is the future default and better conditioned.
    # Verified 2026-09-07 that it changes nothing here: this model has no
    # objective constant, and both settings give cost 1200.0 and a Dallas price
    # of 80.0. A model that DID carry a constant would need this re-checked.
    status, condition = n.optimize(solver_name=solver, solver_options=quiet,
                                   include_objective_constant=False)
    if condition != "optimal":
        raise RuntimeError(
            f"the DC OPF did not solve: status {status!r}, condition {condition!r}. "
            "An infeasible result here usually means a line limit was tightened "
            "below what the network needs to serve its load -- which is a real "
            "answer about the network, not a bug."
        )

    # Shape assert, not a status check. Part 6: an API called in the wrong order
    # returns an empty frame that "succeeds", evaluates to zero, and passes any
    # assertion written against it.
    assert len(n.generators_t.p.columns) == len(inst.generators), "empty dispatch"
    assert len(n.buses_t.marginal_price.columns) == len(inst.buses), "empty prices"

    p = n.generators_t.p.iloc[0]
    f = n.lines_t.p0.iloc[0]
    price = n.buses_t.marginal_price.iloc[0]

    return DCOPFResult(
        cost=float(n.objective),
        dispatch={k: float(p[k]) for k in inst.generators},
        flows={k: float(f[k]) for k in inst.lines},
        lmp={b: float(price[b]) for b in inst.buses},
    )


def congestion_rent(inst, result):
    """What the operator collects from the price difference across each line.

    rent = flow x (price at the receiving end - price at the sending end).
    Positive on a congested line and zero on an uncongested one, which is the
    point the notebook makes: it is money that goes to nobody who produced or
    consumed electricity.
    """
    out = {}
    for name, l in inst.lines.items():
        out[name] = result.flows[name] * (result.lmp[l["bus1"]] - result.lmp[l["bus0"]])
    return out


def check_balances(inst, result, atol=None):
    """Every bus balances: generation - load - net outflow == 0.

    A domain invariant, asserted in code rather than stated in prose. If it
    fails, the plumbing is wrong -- a line pointed at the wrong bus, a sign
    flipped -- not the physics.
    """
    if atol is None:
        from esm.tolerance import CONSERVATION_ATOL
        atol = CONSERVATION_ATOL

    residuals = {}
    for b in inst.buses:
        gen = sum(result.dispatch[g] for g, spec in inst.generators.items()
                  if spec["bus"] == b)
        load = inst.loads.get(b, 0.0)
        out = sum(result.flows[n] for n, l in inst.lines.items() if l["bus0"] == b)
        inn = sum(result.flows[n] for n, l in inst.lines.items() if l["bus1"] == b)
        residuals[b] = gen - load - (out - inn)

    worst = max(abs(v) for v in residuals.values())
    if worst > atol:
        raise AssertionError(
            f"bus balance violated by {worst:.3e} MW: {residuals}"
        )
    return residuals
