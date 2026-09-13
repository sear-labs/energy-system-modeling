# -*- coding: utf-8 -*-
"""The facility solar/battery decision, written once so a notebook can be checked.

    from esm.facility import load_facility_instance, annual_bill, solve_site
    inst = load_facility_instance()
    annual_bill(inst)
    solve_site(inst, solar_max=12.0).cost

WHAT THIS IS FOR

`notebooks/capstone/AppA_facility_decision.ipynb` stacks a facility's bill by
hand, works out whether rooftop solar clears, and then wraps the same thing in
PyPSA so a solver can choose the sizes. This module reads the instance from
`data/raw/` and solves the capacity choice through `scipy.optimize.linprog`.

WHAT IS CHECKED INDEPENDENTLY, AND WHAT IS DELIBERATELY NOT

This is the first module here that does NOT re-solve the whole notebook, and
saying exactly where the line falls matters more than where it happens to be.

**Independently re-solved:** the bill, the solar economics, and the capacity
choice WITHOUT storage -- the "do nothing" and "solar only" cases. Those are a
small linear program (two capacity variables, 48 dispatch pairs) and the second
formulation is genuinely independent of PyPSA.

**NOT re-solved: the battery case.** The notebook's optimum builds 10.56 MW of
storage, so checking it would mean reimplementing PyPSA's `StorageUnit` --
state of charge across representative days, cyclic closure, the split of
round-trip efficiency across store and dispatch, and how `snapshot_weightings`
applies to an energy balance rather than to a cost. Those conventions are
exactly what a second implementation would have to guess, and guessing them
would mean testing my reading of PyPSA's documentation rather than testing the
model. An agreement built that way is worth less than no agreement, because it
looks like evidence.

**What replaces it is a check on the answer rather than a re-solve.**
`recompute_objective()` takes the dispatch PyPSA actually returned and rebuilds
the objective from the tariff, the weights and the annualised capital. If PyPSA
reports an objective that its own reported dispatch does not produce, that is
caught -- and an objective assembled with the weighting applied wrongly is the
realistic failure here. It verifies the solution without claiming to have found
it, and the notebook says which of the two it is doing.

WHAT MAY AND MAY NOT BE COMPARED

The capacity decisions here are unique because solar and grid supply differ in
cost structure and the solar bound binds. `solve_site` returns the capacities
and the notebook compares them; if a future edit made two supply options tie,
the capacities would stop being comparable while the cost stayed comparable.

Representative days are a weighting, not a chronology. Summer and winter are
165 and 200 days; nothing carries between them, which is exactly why the
no-storage problem is well posed and the storage one needs a convention.
"""
from __future__ import annotations

from dataclasses import dataclass

from esm.data import table
from esm.lcoe import capital_recovery_factor


@dataclass(frozen=True)
class FacilityInstance:
    params: dict              # name -> float, from facility_system.csv
    seasons: list             # ordered, e.g. ["summer", "winter"]
    load: list                # MW, 48 entries (summer 0-23 then winter 0-23)
    lmp: list                 # $/MWh, 48
    solar_pu: list            # per-unit, 48
    weights: list             # days each snapshot stands for, 48

    @property
    def roof_mw(self):
        return self.params["roof_sqft"] * self.params["w_per_sqft"] / 1e6

    @property
    def retail(self):
        adder = self.params["energy_adder"] + self.params["delivery_vol"]
        return [p + adder for p in self.lmp]

    @property
    def demand_charge_per_mw_yr(self):
        return (self.params["trans_4cp_per_kw_yr"]
                + self.params["dist_demand_per_kw_month"] * 12) * 1000.0

    @property
    def solar_annual_per_mw(self):
        crf = capital_recovery_factor(self.params["discount_rate"],
                                      int(self.params["solar_life_years"]))
        return (self.params["solar_capex_per_mw"] * crf
                + self.params["solar_fom_per_mw_yr"])

    @property
    def solar_mwh_per_mw_yr(self):
        return sum(pu * w for pu, w in zip(self.solar_pu, self.weights))


@dataclass(frozen=True)
class SiteResult:
    cost: float               # $/yr, the objective
    grid_mw: float            # billed peak
    solar_mw: float
    grid_dispatch: list       # MW per snapshot
    solar_dispatch: list      # MW per snapshot


def load_facility_instance(source=None):
    """The site instance, from `data/raw/`.

    The notebook states these inline as closed-form profiles; these tables are
    the package's copy and the agreement assertion is what stops them drifting.
    `float_precision="round_trip"` because the load and solar profiles come
    from exponentials and sines, not short decimals.
    """
    sysm = table("facility_system.csv", source=source,
                 float_precision="round_trip")
    params = dict(zip(sysm["parameter"], sysm["value"].astype(float)))

    prof = table("facility_profiles.csv", source=source,
                 float_precision="round_trip")
    seasons = list(dict.fromkeys(prof["season"]))
    days = {"summer": params["days_summer"], "winter": params["days_winter"]}
    if set(seasons) - set(days):
        raise ValueError(
            f"facility_profiles.csv names season(s) {sorted(set(seasons) - set(days))} "
            f"with no days_<season> row in facility_system.csv."
        )
    total_days = sum(days[s] for s in seasons)
    if abs(total_days - 365.0) > 1e-9:
        raise ValueError(
            f"representative days weigh {total_days:,.0f} days, not 365. The "
            f"weights must tile the year exactly or every annual total is wrong."
        )

    return FacilityInstance(
        params=params, seasons=seasons,
        load=[float(v) for v in prof["load_mw"]],
        lmp=[float(v) for v in prof["lmp_per_mwh"]],
        solar_pu=[float(v) for v in prof["solar_pu"]],
        weights=[days[s] for s in prof["season"]],
    )


def annual_bill(inst):
    """What the site pays with no solar and no battery: energy + demand."""
    energy = sum(l * r * w for l, r, w
                 in zip(inst.load, inst.retail, inst.weights))
    return energy + max(inst.load) * inst.demand_charge_per_mw_yr


def solar_lcoe(inst):
    """$/MWh for the rooftop array, annualised capital over annual output."""
    return inst.solar_annual_per_mw / inst.solar_mwh_per_mw_yr


def solve_site(inst, solar_max=0.0, demand_charge=None, retail=None):
    """Least-cost grid and solar capacity, WITHOUT storage.

    Storage is not modelled here on purpose -- see the module docstring. Passing
    a battery is not silently ignored; there is no parameter for one.

        minimise  demand_charge * P_grid + solar_annual * P_solar
                  + sum_t weight_t * retail_t * grid_t
        s.t.      grid_t + solar_t = load_t
                  solar_t <= solar_pu_t * P_solar
                  grid_t  <= P_grid
    """
    from scipy.optimize import linprog

    dc = inst.demand_charge_per_mw_yr if demand_charge is None else demand_charge
    rt = inst.retail if retail is None else list(retail)
    n = len(inst.load)
    # columns: P_grid, P_solar, grid_0..n-1, solar_0..n-1
    ng, ns = 2 + n, 2 + 2 * n
    c = [dc, inst.solar_annual_per_mw]
    c += [rt[t] * inst.weights[t] for t in range(n)]
    c += [0.0] * n

    A_eq, b_eq = [], []
    for t in range(n):
        row = [0.0] * ns
        row[2 + t] = 1.0
        row[ng + t] = 1.0
        A_eq.append(row)
        b_eq.append(inst.load[t])

    A_ub, b_ub = [], []
    for t in range(n):                       # solar_t - pu_t * P_solar <= 0
        row = [0.0] * ns
        row[1] = -inst.solar_pu[t]
        row[ng + t] = 1.0
        A_ub.append(row)
        b_ub.append(0.0)
    for t in range(n):                       # grid_t - P_grid <= 0
        row = [0.0] * ns
        row[0] = -1.0
        row[2 + t] = 1.0
        A_ub.append(row)
        b_ub.append(0.0)

    bounds = [(0.0, inst.params["ica_mw"]), (0.0, solar_max)]
    bounds += [(0.0, None)] * (2 * n)

    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                  bounds=bounds, method="highs")
    if not res.success:
        raise RuntimeError(
            f"the site LP did not solve: {res.message}. Check that the "
            f"interconnection is at least as large as the peak load."
        )
    assert len(res.x) == ns, "solution vector has the wrong length"

    return SiteResult(
        cost=float(res.fun), grid_mw=float(res.x[0]), solar_mw=float(res.x[1]),
        grid_dispatch=[float(v) for v in res.x[2:ng]],
        solar_dispatch=[float(v) for v in res.x[ng:]],
    )


def recompute_objective(inst, grid_dispatch, grid_mw, solar_mw=0.0,
                        battery_mw=0.0, demand_charge=None):
    """Rebuild a reported solution's cost from the tariff and the weights.

    This VERIFIES an answer; it does not find one. Give it the dispatch a
    solver returned and it says what that dispatch costs. Used for the battery
    case, which this module does not re-solve -- see the module docstring.

    The realistic failure it catches is an objective assembled with the
    representative-day weighting applied to the wrong term, which leaves
    capacities looking sensible and the total wrong by a factor near two.
    """
    dc = inst.demand_charge_per_mw_yr if demand_charge is None else demand_charge
    if len(grid_dispatch) != len(inst.load):
        raise ValueError(
            f"dispatch has {len(grid_dispatch)} snapshots, instance has "
            f"{len(inst.load)}."
        )

    energy = sum(g * r * w for g, r, w
                 in zip(grid_dispatch, inst.retail, inst.weights))
    crf_b = capital_recovery_factor(inst.params["discount_rate"],
                                    int(inst.params["batt_life_years"]))
    batt_annual = (inst.params["batt_capex_per_kwh"] * 1000.0
                   * inst.params["batt_hours"] * crf_b)
    return (energy + grid_mw * dc + solar_mw * inst.solar_annual_per_mw
            + battery_mw * batt_annual)


def battery_annual_per_mw(inst):
    """$/MW-yr for the battery, annualised the same way as the solar."""
    crf = capital_recovery_factor(inst.params["discount_rate"],
                                  int(inst.params["batt_life_years"]))
    return (inst.params["batt_capex_per_kwh"] * 1000.0
            * inst.params["batt_hours"] * crf)
