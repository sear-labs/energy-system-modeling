# -*- coding: utf-8 -*-
"""Screening-level LCOE, written once so a notebook can be checked against it.

    from esm.lcoe import load_lcoe_instance, lcoe_by_crf, lcoe_by_dcf
    inst = load_lcoe_instance()
    plant = inst.plants[("gas", 7500)]
    lcoe_by_crf(inst, plant), lcoe_by_dcf(inst, plant)

WHAT THIS IS FOR

`notebooks/p3_generation/09_capital_and_lcoe.ipynb` builds up a break-even
price a step at a time: lifetime energy, then fuel burned, then the fuel bill,
then capital annualised with a capital recovery factor.

Like `esm.balance`, this notebook has no solver, so agreement cannot mean "two
searches found the same optimum". But unlike `esm.balance`, there is a genuinely
different second route available, and it is the one worth teaching.

THE TWO ROUTES, AND THE CONDITION UNDER WHICH THEY AGREE

**The notebook's route** annualises capital with a CRF, adds fixed and fuel
costs, and divides the nominal total by the nominal lifetime energy:

    (overnight * CRF * MW * years + FOM * MW * years + fuel) / lifetime_MWh

**The definition of LCOE** discounts both sides:

    sum_t cost_t / (1+r)^t   /   sum_t energy_t / (1+r)^t

These are not the same calculation, and they are not always equal. They agree
here **because the annual energy is constant over the life** -- both sums pick
up the identical annuity factor, which then cancels. That cancellation is the
entire justification for the shortcut every screening study uses, and it is
usually asserted rather than shown.

`lcoe_by_dcf` therefore is not a paraphrase of `lcoe_by_crf`. It is the
definition, and their agreement is a fact about this instance rather than a
tautology. `test_the_shortcut_breaks_under_degradation` puts 0.5%/yr of panel
degradation into the energy stream and watches the two answers separate by
about 5% -- which is what makes the agreement on the flat case worth anything.

WHAT MAY AND MAY NOT BE COMPARED

Everything here is a deterministic arithmetic chain, so there is no
non-uniqueness to worry about and every quantity is comparable. The risks are
elsewhere, and they are the ones a screening study actually gets wrong: unit
conversions (Btu/kWh to MMBtu/MWh is a factor of 1000, MMBtu per ton and per
Mcf are different numbers), and the CRF formula, which has two algebraically
identical forms that are easy to conflate with the wrong one.

Both forms are implemented and checked against each other in
`capital_recovery_factor`, because "I wrote the other one from memory" is how
that error arrives.
"""
from __future__ import annotations

from dataclasses import dataclass

from esm.data import table


@dataclass(frozen=True)
class Plant:
    fuel: str
    heat_rate: float          # Btu/kWh
    heat_content: float       # MMBtu per fuel unit
    fuel_unit: str
    fuel_price: float         # $ per fuel unit
    overnight_per_mw: float   # $/MW
    fom_per_mw_yr: float      # $/MW-yr


@dataclass(frozen=True)
class LcoeInstance:
    plant_mw: float
    hours_per_year: float
    lifetime_years: int
    discount_rate: float
    plants: dict              # (fuel, heat_rate) -> Plant

    @property
    def lifetime_mwh(self):
        return self.plant_mw * self.hours_per_year * self.lifetime_years


def load_lcoe_instance(source=None):
    """The screening instance, from `data/raw/`.

    The notebook states these numbers inline, since watching them build up is
    the lesson; these tables are the package's copy and the agreement assertion
    is what stops the two drifting.
    """
    sysm = table("lcoe_system.csv", source=source)
    p = dict(zip(sysm["parameter"], sysm["value"].astype(float)))

    rows = table("lcoe_plants.csv", source=source)
    plants = {}
    for _, r in rows.iterrows():
        plants[(str(r["fuel"]), int(r["heat_rate_btu_per_kwh"]))] = Plant(
            fuel=str(r["fuel"]),
            heat_rate=float(r["heat_rate_btu_per_kwh"]),
            heat_content=float(r["heat_content_mmbtu_per_unit"]),
            fuel_unit=str(r["fuel_unit"]),
            fuel_price=float(r["fuel_price_per_unit"]),
            overnight_per_mw=float(r["overnight_per_mw"]),
            fom_per_mw_yr=float(r["fom_per_mw_yr"]),
        )

    return LcoeInstance(
        plant_mw=p["plant_mw"], hours_per_year=p["hours_per_year"],
        lifetime_years=int(p["lifetime_years"]),
        discount_rate=p["discount_rate"], plants=plants,
    )


def capital_recovery_factor(rate, years):
    """The CRF, computed both algebraically identical ways and cross-checked.

        r(1+r)^n / ((1+r)^n - 1)      and      r / (1 - (1+r)^-n)

    They are the same expression multiplied above and below by (1+r)^-n. Both
    appear in textbooks, and writing one while believing it is the other is a
    live error rather than a hypothetical -- so both are evaluated and compared
    rather than one being trusted.
    """
    if rate == 0:
        return 1.0 / years
    a = rate * (1 + rate) ** years / ((1 + rate) ** years - 1)
    b = rate / (1 - (1 + rate) ** (-years))
    assert abs(a - b) < 1e-12 * max(abs(a), 1.0), (
        f"the two CRF forms disagree ({a} vs {b}), which is arithmetically "
        f"impossible -- suspect an operator precedence error."
    )
    return a


def fuel_mmbtu_per_mwh(heat_rate_btu_per_kwh):
    """Btu/kWh -> MMBtu/MWh. One thousand, and the commonest slip here."""
    return heat_rate_btu_per_kwh / 1000.0


def lifetime_fuel_bill(inst, plant):
    """$ of fuel burned over the plant's whole life."""
    mmbtu = inst.lifetime_mwh * fuel_mmbtu_per_mwh(plant.heat_rate)
    return mmbtu / plant.heat_content * plant.fuel_price


def fuel_cost_per_mwh(inst, plant):
    """The fuel-only screening number: $/MWh, ignoring capital entirely."""
    return lifetime_fuel_bill(inst, plant) / inst.lifetime_mwh


def lcoe_by_crf(inst, plant):
    """The notebook's route: annualise capital, divide nominal by nominal."""
    crf = capital_recovery_factor(inst.discount_rate, inst.lifetime_years)
    capital = plant.overnight_per_mw * crf * inst.plant_mw * inst.lifetime_years
    fixed = plant.fom_per_mw_yr * inst.plant_mw * inst.lifetime_years
    return (capital + fixed + lifetime_fuel_bill(inst, plant)) / inst.lifetime_mwh


def lcoe_by_dcf(inst, plant, degradation=0.0):
    """The definition: discounted cost over discounted energy.

    `degradation` is the fractional annual loss of output. At zero this must
    equal `lcoe_by_crf`; above zero it must not, and the fact that it does not
    is what shows the agreement at zero was a result rather than a restatement.
    """
    r = inst.discount_rate
    n = inst.lifetime_years
    crf = capital_recovery_factor(r, n)

    annual_cost = (plant.overnight_per_mw * crf * inst.plant_mw
                   + plant.fom_per_mw_yr * inst.plant_mw
                   + lifetime_fuel_bill(inst, plant) / n)
    annual_energy = inst.plant_mw * inst.hours_per_year

    npv_cost = sum(annual_cost / (1 + r) ** t for t in range(1, n + 1))
    npv_energy = sum(annual_energy * (1 - degradation) ** (t - 1) / (1 + r) ** t
                     for t in range(1, n + 1))
    if npv_energy <= 0:
        raise ValueError("discounted lifetime energy is zero or negative")
    return npv_cost / npv_energy


def screening_table(inst):
    """Fuel-only $/MWh for every case in the table, notebook order."""
    return {k: fuel_cost_per_mwh(inst, p) for k, p in inst.plants.items()}
