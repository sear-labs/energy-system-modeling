# -*- coding: utf-8 -*-
"""Hourly dispatch behind an interconnection, written once so a notebook can be checked.

    from esm.boundary import load_boundary_instance, solve_dispatch
    inst = load_boundary_instance()
    r = solve_dispatch(inst, site_mw=50)
    r.cost, r.lmp, r.dispatch

WHAT THIS IS FOR

`notebooks/p1_foundations/01_model_boundary.ipynb` asks a question that looks
like one question and is two: does a new load at a site change the price it
pays? It answers by solving a 24-hour dispatch with and without the site, and
reading the difference in the Dallas price.

The notebook builds that in PyPSA, as one linear program over all 24 snapshots.
This module solves it **hour by hour, as 24 independent linear programs**,
through `scipy.optimize.linprog`.

WHY HOUR-BY-HOUR IS A DIFFERENT FORMULATION AND NOT A SHORTCUT

The model has no storage, no ramp limits, no minimum up or down time and no
unit commitment. Nothing couples one hour to the next, so the 24-hour problem
separates exactly into 24 one-hour problems. Solving it that way is a genuinely
different formulation that must nevertheless give the same answer -- which is
what makes it worth something as a check, and is also the single most useful
thing a reader can learn about this model. The moment a battery is added the
separation fails, and that is the lesson the next notebook needs.

WHAT THE ASSERTION MAY AND MAY NOT COMPARE

**Prices in a merit order are degenerate exactly when the load lands on a
capacity boundary.** If demand in some hour is met by units that are all either
full or empty, no unit is marginal, and every value between the last loaded
unit's cost and the next unit's cost is a valid price. Two solvers will then
report different prices, both correct, and an assertion comparing them fails
for no reason.

On this instance no hour is degenerate -- measured, at site sizes 0, 50 and 500
-- so prices are compared. `assert_prices_are_unique()` re-derives that from the
current tables rather than trusting this paragraph, and the notebook calls it
before comparing, so an edit that moves demand onto a boundary fails with an
explanation instead of failing as a mismatch.

Total cost is unique whether or not prices are, and dispatch is unique here
because every marginal cost in the stack is distinct.

FLOAT PRECISION, AND EXACTLY HOW FAR IT GOES

`boundary_profile.csv` holds demand computed from exponentials, so its values
are not short decimals like every other instance in this repository. Two things
follow, and only the first is fixable.

**The file round-trips exactly.** pandas' default CSV float parser is fast
rather than correctly rounded and loses about a bit; `repr()` on the way out
plus `float_precision="round_trip"` on the way back in is exact. Worth doing
because a table that does not round-trip is a table whose contents depend on
the reader's pandas version -- though the ~2e-16 it removes would not on its
own have broken a 1e-9 assertion.

**The notebook's formulas do NOT reproduce bit-for-bit across machines, and
cannot be made to.** `exp()` and `sin()` are not required to be identical
between platforms, and are not: the first version of this module's test
recomputed the closed forms and demanded bit-equality, passed on the authoring
machine, and failed on CI at one index of `wind_pu`. Comparing a stored table
against a freshly evaluated transcendental tests the runner's maths library.

That is harmless HERE, and the reason is measured rather than assumed: a
merit-order price is a step function of demand, so a last-bit difference could
in principle tip a marginal unit and move a price by a whole step -- but the
marginal unit in every hour sits about 1 MW from its nearest bound, some 1e12
ulps away. `test_no_marginal_unit_sits_near_a_bound` asserts that clearance, so
the argument stops being an argument.
"""
from __future__ import annotations

from dataclasses import dataclass

from esm.data import table


@dataclass(frozen=True)
class BoundaryInstance:
    """The tables an hourly dispatch needs, as plain columns."""
    hours: list
    metro: list                 # MW, per hour
    wind_pu: list               # per-unit availability, per hour
    generators: dict            # name -> {"p_nom", "marginal_cost", "profile"}
    interconnection_mw: float


@dataclass(frozen=True)
class DispatchResult:
    cost: float                 # $ over the 24 hours
    lmp: list                   # $/MWh at Dallas, per hour
    dispatch: dict              # generator -> list of MW, per hour


def load_boundary_instance(source=None):
    """The Dallas/site instance, from `data/raw/`.

    Read through `esm.data.table`. Like most notebooks in this repository,
    `01_model_boundary.ipynb` states its instance inline -- there as two closed
    form expressions for demand and wind -- rather than reading these files.
    The tables and the notebook are two copies of one instance and the
    agreement assertion is what stops them drifting.

    `float_precision="round_trip"` is not optional here: see the module
    docstring.
    """
    prof = table("boundary_profile.csv", source=source,
                 float_precision="round_trip")
    hours = [int(h) for h in prof["hour"]]
    metro = [float(v) for v in prof["metro_mw"]]
    wind_pu = [float(v) for v in prof["wind_pu"]]

    gens = table("boundary_generators.csv", source=source,
                 float_precision="round_trip")
    generators = {}
    for _, row in gens.iterrows():
        prof_name = row["profile"]
        prof_name = "" if prof_name != prof_name else str(prof_name)  # NaN -> ""
        generators[row["generator"]] = {
            "p_nom": float(row["p_nom_mw"]),
            "marginal_cost": float(row["marginal_cost"]),
            "profile": prof_name,
        }

    sysm = table("boundary_system.csv", source=source,
                 float_precision="round_trip")
    params = dict(zip(sysm["parameter"], sysm["value"].astype(float)))

    return BoundaryInstance(
        hours=hours, metro=metro, wind_pu=wind_pu, generators=generators,
        interconnection_mw=float(params["interconnection_mw"]),
    )


def _capacity(inst, name, h):
    """A generator's usable MW in hour h -- its rating, derated by a profile."""
    g = inst.generators[name]
    if g["profile"] == "wind_pu":
        return g["p_nom"] * inst.wind_pu[h]
    if g["profile"]:
        raise ValueError(
            f"generator {name!r} names an unknown profile {g['profile']!r}; "
            f"boundary_profile.csv has no such column."
        )
    return g["p_nom"]


def solve_dispatch(inst, site_mw=0.0):
    """Solve all 24 hours and return cost, hourly prices and dispatch.

    `site_mw` is a flat load behind the interconnection. Raises rather than
    returning a sentinel when the site cannot be served -- the notebook's
    "harder limit" at 900 MW is exactly this, and it is a real statement about
    the interconnection agreement rather than a solver failure.
    """
    from scipy.optimize import linprog

    if site_mw > inst.interconnection_mw + 1e-9:
        raise RuntimeError(
            f"a {site_mw:,.0f} MW site cannot be served through a "
            f"{inst.interconnection_mw:,.0f} MW interconnection. This is the "
            f"model boundary binding, not an infeasible dispatch: no amount of "
            f"generation at Dallas reaches a load behind too small a link."
        )

    names = list(inst.generators)
    c = [inst.generators[n]["marginal_cost"] for n in names]

    cost = 0.0
    lmp = []
    dispatch = {n: [] for n in names}

    for h in inst.hours:
        load = inst.metro[h] + site_mw
        bounds = [(0.0, _capacity(inst, n, h)) for n in names]
        available = sum(b[1] for b in bounds)
        if available < load - 1e-6:
            raise RuntimeError(
                f"hour {h}: {available:,.1f} MW available cannot serve "
                f"{load:,.1f} MW of load. Generation capacity, not the link, "
                f"is the binding limit here."
            )

        res = linprog(c, A_eq=[[1.0] * len(names)], b_eq=[load],
                      bounds=bounds, method="highs")
        if not res.success:
            raise RuntimeError(f"hour {h} did not solve: {res.message}")

        # Shape assert, not a status check. Part 6: a call that returns an empty
        # or malformed result can still report success.
        assert len(res.x) == len(names), f"hour {h}: wrong solution length"

        cost += float(res.fun)
        # The dual of the balance row IS the locational price: the cost of one
        # more MW of demand. scipy reports eqlin marginals as d(objective)/d(b),
        # which for a minimisation with demand on the right-hand side is already
        # the positive price -- asserted below rather than assumed, because a
        # sign convention is exactly the kind of thing that changes quietly.
        price = float(res.eqlin.marginals[0])
        assert price >= -1e-9, (
            f"hour {h}: price {price} is negative, which this model cannot "
            f"produce -- every generator has a non-negative cost. Check "
            f"scipy's dual sign convention."
        )
        lmp.append(price)
        for n, v in zip(names, res.x):
            dispatch[n].append(float(v))

    return DispatchResult(cost=cost, lmp=lmp, dispatch=dispatch)


def marginal_units(inst, result, tol=1e-6):
    """Per hour, the generators that are strictly part-loaded.

    Exactly one such unit means the price is pinned by it. None means the load
    sits on a capacity boundary and the price is ambiguous -- see
    `assert_prices_are_unique`.
    """
    out = []
    for h in inst.hours:
        interior = [n for n in inst.generators
                    if tol < result.dispatch[n][h] < _capacity(inst, n, h) - tol]
        out.append(interior)
    return out


def assert_prices_are_unique(inst, result):
    """Fail unless every hour has a marginal unit, so prices may be compared.

    Part 6's precondition for this model. A merit-order price is the cost of the
    unit that is partly loaded; when demand lands exactly on a capacity
    boundary, every unit is full or empty, and any price between the adjacent
    two costs is equally optimal. Two solvers then disagree while both are
    right.

    Raises AssertionError naming the hours, so a reader who moves demand gets
    told what happened rather than watching the agreement assertion fail.
    """
    bad = [h for h, units in zip(inst.hours, marginal_units(inst, result))
           if len(units) != 1]
    if bad:
        raise AssertionError(
            f"hours {bad} have no single marginal unit, so the price there is "
            f"not unique and must not be compared between solvers. Total cost "
            f"is still comparable. See Part 6."
        )
    return True


def bill(result, mw):
    """What a flat `mw` load pays over the 24 hours at these prices."""
    return sum(p * mw for p in result.lmp)
