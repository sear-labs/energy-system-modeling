# -*- coding: utf-8 -*-
"""One hour of merit-order dispatch with a carbon price or cap, written once.

    from esm.dispatch import Thermal, solve_hour
    gas = Thermal('gas', mw=600, heat_rate=6.370, fuel=3.065, vom=2.10, kg_co2=53.06)
    r = solve_hour([gas, coal], load_mw=1000, wind_mw=150)
    r.output, r.price, r.cap_price

WHAT THIS IS FOR

`notebooks/p3_generation/10_dispatch_and_carbon.ipynb` builds the merit order
by hand, then builds the same hour in PyPSA the way PyPSA wants it: **each fuel
is a bus measured in MWh of heat, and each plant is a Link** that turns heat
into electricity at `efficiency = 3.412 / heat rate`, with its variable O&M
charged per MWh of heat *in*.

This module solves the same hour with `scipy.optimize.linprog`, formulated
directly in MW of electricity: one variable per plant, priced at its marginal
cost `heat rate x fuel + VOM (+ tau x emission rate)`. No fuel buses, no Links,
no efficiencies.

WHY THAT IS A CHECK AND NOT A COPY

The two formulations agree only if every unit conversion in the PyPSA build is
right -- the fuel price per MWh of heat, the Link's `p_nom` in heat units, VOM
divided back through the efficiency, the carrier's CO2 per MWh of heat. Each of
those is a place to be wrong by a factor of 3.412 and still get a plausible
dispatch. Agreeing on the price to 1e-9 rules all of them out at once.

WHAT MAY AND MAY NOT BE COMPARED

The price at the bus and the cap's shadow price are duals, and a dual is unique
only when enough units sit strictly between their limits: one for the energy
balance, and a second whenever the cap binds. If every unit were full or empty,
any price between two neighbouring costs would be optimal and two correct
solvers could disagree. `assert_prices_are_unique` re-derives that from the
solution before anything is compared, so an edit that lands demand on a
capacity boundary fails with an explanation rather than as a mismatch.
"""
from __future__ import annotations

from dataclasses import dataclass, field

#: How far inside its limits a unit must sit to count as marginal, in MW.
MARGINAL_CLEARANCE_MW = 1e-6


@dataclass(frozen=True)
class Thermal:
    name: str
    mw: float                 # electrical nameplate
    heat_rate: float          # MMBtu per MWh of electricity
    fuel: float               # $ per MMBtu at the plant gate
    vom: float                # $ per MWh of electricity
    kg_co2: float             # kg CO2 per MMBtu of fuel
    min_share: float = 0.0    # must-run share of nameplate

    @property
    def marginal_cost(self):
        return self.heat_rate * self.fuel + self.vom

    @property
    def emission_rate(self):
        """t CO2 per MWh of electricity."""
        return self.heat_rate * self.kg_co2 / 1000.0


@dataclass
class HourResult:
    output: dict              # name -> MW of electricity, wind included
    price: float              # $/MWh at the bus: the dual of the balance
    cap_price: float | None   # $/t: the dual of the cap, if there is one
    tonnes: float
    cost: float
    binding: list = field(default_factory=list)


def solve_hour(plants, load_mw, wind_mw=0.0, co2_price=0.0, co2_cap=None):
    """Least-cost dispatch for one hour. Returns None if no dispatch is feasible."""
    from scipy.optimize import linprog

    names = ["wind"] + [p.name for p in plants]
    cost = [0.0] + [p.marginal_cost + co2_price * p.emission_rate for p in plants]
    bounds = [(0.0, wind_mw)] + [(p.min_share * p.mw, p.mw) for p in plants]
    a_eq, b_eq = [[1.0] * len(names)], [load_mw]
    a_ub = b_ub = None
    if co2_cap is not None:
        a_ub = [[0.0] + [p.emission_rate for p in plants]]
        b_ub = [co2_cap]

    res = linprog(cost, A_ub=a_ub, b_ub=b_ub, A_eq=a_eq, b_eq=b_eq,
                  bounds=bounds, method="highs")
    if res.status == 2:
        return None
    if res.status != 0:
        raise RuntimeError(f"dispatch LP did not solve: {res.message}")

    output = dict(zip(names, (float(v) for v in res.x)))
    tonnes = sum(output[p.name] * p.emission_rate for p in plants)
    binding = ["balance"]
    cap_price = None
    if co2_cap is not None:
        # linprog reports d(objective)/d(b_ub), which is <= 0 for a <= limit
        cap_price = float(-res.ineqlin.marginals[0])
        if abs(tonnes - co2_cap) < 1e-6:
            binding.append("co2 cap")
    return HourResult(output=output, price=float(res.eqlin.marginals[0]),
                      cap_price=cap_price, tonnes=tonnes, cost=float(res.fun),
                      binding=binding)


def marginal_units(plants, result, wind_mw):
    """Units strictly inside their limits -- the ones that can set a price."""
    limits = {"wind": (0.0, wind_mw)}
    limits.update({p.name: (p.min_share * p.mw, p.mw) for p in plants})
    return [n for n, (lo, hi) in limits.items()
            if lo + MARGINAL_CLEARANCE_MW < result.output[n] < hi - MARGINAL_CLEARANCE_MW]


def assert_prices_are_unique(plants, result, wind_mw):
    """Fail, with the reason, if the duals are not determined by this instance."""
    free = marginal_units(plants, result, wind_mw)
    need = len(result.binding)
    if len(free) < need:
        raise AssertionError(
            f"{need} binding constraint(s) ({', '.join(result.binding)}) but only "
            f"{len(free)} unit(s) strictly inside their limits ({free or 'none'}). "
            "The price is then any value between two neighbouring costs, and two "
            "correct solvers may report different ones -- compare costs, not prices.")
    return free
