# -*- coding: utf-8 -*-
"""One day with a battery, as a plain LP, written once so a notebook can be checked.

    from esm.storage import BatteryDay, day_cost, load_battery_profile
    day = BatteryDay.module_0()                    # or BatteryDay(...) with your knobs
    day_cost(day)                                  # no battery
    day_cost(day, max_hours=4)                     # 40 MW / 160 MWh, cyclic
    day_cost(day, max_hours=4, cyclic=False, soc_initial=160)

WHAT THIS IS FOR

`notebooks/p5_storage_supply/19_battery_day.ipynb` takes the day built in
`teaching-code` notebook 12 (one bus, solar, a gas unit, a peaker, a 40 MW / 4 h
battery) and asks three questions PyPSA answers in a line each: what the battery
is worth, what happens when it is not made to end the day where it began, and
whether twice the energy saves twice as much.

PyPSA writes the storage equations for you. This module writes them out:

    soc[t] = (1 - standing_loss) * soc[t-1] + eff_store * charge[t]
             - discharge[t] / eff_dispatch
    soc[-1] = soc[23]                      if cyclic
    soc[-1] = soc_initial, with NO loss    otherwise

The last line is the one that was found rather than assumed. PyPSA applies the
standing loss to the previous hour's state of charge, but not to
`state_of_charge_initial` in the first snapshot. Writing it the obvious way --
loss on the initial charge too -- left a $32 gap on the start-full case and
closed it exactly when changed (course builder, 15 Oct 2026). A check that had
written the equations from PyPSA's documentation instead of measuring them
would have reported PyPSA wrong.

WHAT MAY AND MAY NOT BE COMPARED

**Only the day's cost.** The charging schedule is not unique on this instance:
solar is curtailed through the middle of the day, so the battery can take its
energy in any of several hours at the same cost, and the solver's choice is a
path, not a result. `teaching-code` notebook 12 teaches exactly that tie. The
cost is unique whatever the schedule, so it is the one thing asserted.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class BatteryDay:
    demand: np.ndarray        # MW, 24 values
    solar_pu: np.ndarray      # per unit of solar_mw, 24 values
    solar_mw: float
    gas_mw: float
    gas_cost: float           # $/MWh
    peaker_mw: float
    peaker_cost: float
    battery_mw: float
    efficiency: float         # each way
    standing_loss: float      # fraction of state of charge lost per hour
    dispatch_cost: float      # $/MWh discharged; a tiny cost that stops free cycling

    @classmethod
    def module_0(cls, source=None):
        """The day from teaching-code notebook 12, Part E, with its own knobs.

        The notebook passes its knobs explicitly; this is the default set, for
        the tests.
        """
        demand, solar_pu = load_battery_profile(source)
        return cls(demand=demand, solar_pu=solar_pu,
                   solar_mw=140.0, gas_mw=66.0, gas_cost=22.14,
                   peaker_mw=100.0, peaker_cost=80.0, battery_mw=40.0,
                   efficiency=0.927, standing_loss=0.01, dispatch_cost=0.01)


def load_battery_profile(source=None):
    """(demand MW, solar per unit), 24 values each, from `data/raw/`.

    The notebook states the same day as two closed forms, the way notebook 12
    does; this table is the package's copy and the agreement assertion is what
    stops the two drifting. `float_precision="round_trip"` because the values
    come from exponentials and a sine -- see `esm.boundary`, which has the same
    table shape and records why a last-bit difference cannot move a cost here.
    """
    from esm.data import table

    prof = table("battery_day_profile.csv", source=source,
                 float_precision="round_trip")
    if [int(h) for h in prof["hour"]] != list(range(24)):
        raise ValueError("battery_day_profile.csv must hold hours 0..23 in order")
    return (prof["demand_mw"].to_numpy(dtype=float),
            prof["solar_pu"].to_numpy(dtype=float))


def day_cost(day, max_hours=None, cyclic=True, soc_initial=0.0):
    """Least cost of the day. With `max_hours=None` there is no battery.

    Returns (cost, end_of_day_state_of_charge); the second is None without a
    battery.
    """
    from scipy.optimize import linprog

    n = len(day.demand)
    k = 6 if max_hours else 3          # solar, gas, peaker[, charge, discharge, soc]
    col = lambda i, t: i * n + t
    cost = np.zeros(k * n)
    cost[n:2 * n] = day.gas_cost
    cost[2 * n:3 * n] = day.peaker_cost
    upper = [day.solar_mw * day.solar_pu, np.full(n, day.gas_mw),
             np.full(n, day.peaker_mw)]
    a_eq, b_eq = [], []

    for t in range(n):                 # supply meets demand every hour
        row = np.zeros(k * n)
        row[[col(0, t), col(1, t), col(2, t)]] = 1.0
        if max_hours:
            row[col(3, t)], row[col(4, t)] = -1.0, 1.0
        a_eq.append(row)
        b_eq.append(day.demand[t])

    if max_hours:
        cost[4 * n:5 * n] = day.dispatch_cost
        upper += [np.full(n, day.battery_mw), np.full(n, day.battery_mw),
                  np.full(n, day.battery_mw * max_hours)]
        for t in range(n):             # state of charge carries hour to hour
            row = np.zeros(k * n)
            row[col(5, t)] = 1.0
            row[col(3, t)] = -day.efficiency
            row[col(4, t)] = 1.0 / day.efficiency
            rhs = 0.0
            if t > 0 or cyclic:
                row[col(5, (t - 1) % n)] = -(1.0 - day.standing_loss)
            else:
                rhs = soc_initial      # no standing loss on the initial charge
            a_eq.append(row)
            b_eq.append(rhs)

    res = linprog(cost, A_eq=np.array(a_eq), b_eq=np.array(b_eq),
                  bounds=list(zip(np.zeros(k * n), np.concatenate(upper))),
                  method="highs")
    if res.status != 0:
        raise RuntimeError(f"battery-day LP did not solve: {res.message}")
    end = float(res.x[col(5, n - 1)]) if max_hours else None
    return float(res.fun), end
