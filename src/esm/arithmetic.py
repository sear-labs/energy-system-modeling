# -*- coding: utf-8 -*-
"""Energy arithmetic, written once so the primer notebook can be checked.

    from esm import arithmetic as ea
    ea.marginal_cost(6.370, ea.plant_gate_price(2.65, 1.033, 0.50), 2.10)

WHAT THIS IS FOR

`notebooks/p1_foundations/02_energy_arithmetic.ipynb` is the bridge into the
course: kW against kWh, one chain of Btu conversions, heat rate, marginal cost,
emission rate, capacity factor, sun and wind, and the capital recovery factor.
Every one of them is a line of arithmetic, typed out by hand in its own cell,
because watching the units cancel is the lesson.

There is no solver here, so "agreement" cannot mean two searches finding one
optimum. It means the same quantity reached by a route that was written
separately, from the formula rather than from the notebook's cell -- and, for
the levelized cost, by a genuinely different route:

    the notebook   annualise capital with a CRF, divide by one year's MWh, add
                   the marginal cost (the screening shortcut)
    this module    discount every year's cost and every year's energy over the
                   life and divide (the definition)

They agree because the plant's output is the same every year, so both sums pick
up the same annuity factor and it cancels. `esm.lcoe` makes the same argument
for the capital-and-LCOE notebook and tests the case where it fails.

KNOBS, NOT TABLES

Every input here is a scalar the prose names -- a heat rate, a fuel price, a
rotor diameter -- so the notebook passes each one in explicitly and nothing is
read from `data/raw/`. Part 4: a number the notebook hands to the package may
stay written out in the notebook; the assertion proves both sides used it.

The physical constants are the exception, and they are constants rather than
knobs: 3,412 Btu per kWh is not something a reader is invited to change.
"""
from __future__ import annotations

import math

from esm.lcoe import capital_recovery_factor

#: Btu of heat in one kWh of electricity.
BTU_PER_KWH = 3412.0
#: MMBtu of heat in one MWh of electricity. The same constant, a thousand times
#: larger on both sides -- which is exactly the slip it exists to prevent.
MMBTU_PER_MWH = BTU_PER_KWH / 1000.0
BTU_PER_THERM = 100_000.0
#: Gasoline, approximately (EIA).
BTU_PER_GALLON_GASOLINE = 120_000.0
HOURS_PER_YEAR = 8760.0
#: Betz limit: the most any rotor can take from the wind passing through it.
BETZ = 16.0 / 27.0


def energy_kwh(power_kw, hours):
    """Energy is power times time."""
    return power_kw * hours


def average_kw(energy_kwh_, hours):
    """Average power over an interval is the energy divided by its length."""
    if hours <= 0:
        raise ValueError("an interval must have a positive length")
    return energy_kwh_ / hours


def heat_to_kwh(btu):
    """Heat content expressed in kWh-equivalent, through 3,412 Btu/kWh."""
    return btu / BTU_PER_KWH


def plant_gate_price(price_per_unit, mmbtu_per_unit, delivery_adder):
    """$/MMBtu at the plant: the commodity price per unit of heat, plus delivery."""
    return price_per_unit / mmbtu_per_unit + delivery_adder


def efficiency(heat_rate_mmbtu_per_mwh):
    """Electricity out over heat in. A perfect plant needs 3.412 MMBtu per MWh."""
    return MMBTU_PER_MWH / heat_rate_mmbtu_per_mwh


def marginal_cost(heat_rate_mmbtu_per_mwh, fuel_per_mmbtu, vom_per_mwh):
    """$/MWh to run one more MWh: heat rate x fuel price + variable O&M."""
    return heat_rate_mmbtu_per_mwh * fuel_per_mmbtu + vom_per_mwh


def emission_rate(heat_rate_mmbtu_per_mwh, kg_co2_per_mmbtu):
    """Tonnes of CO2 per MWh of electricity."""
    return heat_rate_mmbtu_per_mwh * kg_co2_per_mmbtu / 1000.0


def annual_mwh(mw, capacity_factor, hours=HOURS_PER_YEAR):
    """A year's output from a nameplate and a capacity factor."""
    return mw * hours * capacity_factor


def solar_kwh_per_kw(ghi_kwh_m2_day, performance, days=365):
    """Annual yield of one kW of panels from daily irradiance.

    One kW of panel is rated at 1 kW/m2 of sun, so kWh/m2/day of irradiance is
    also full-sun hours per day; `performance` takes off wiring, heat and
    inverter losses.
    """
    return ghi_kwh_m2_day * performance * days


def wind_power_mw(air_density, rotor_diameter_m, speed_m_s):
    """Power in the wind through a rotor, MW: 1/2 rho A v^3."""
    area = math.pi * (rotor_diameter_m / 2.0) ** 2
    return 0.5 * air_density * area * speed_m_s ** 3 / 1e6


def levelized_cost_crf(capex_per_mw, fixed_om_per_mw_yr, marginal, rate, years,
                       capacity_factor):
    """The screening shortcut: annualised fixed cost per MWh, plus marginal cost."""
    fixed = capex_per_mw * capital_recovery_factor(rate, years) + fixed_om_per_mw_yr
    return fixed / (HOURS_PER_YEAR * capacity_factor) + marginal


def levelized_cost_dcf(capex_per_mw, fixed_om_per_mw_yr, marginal, rate, years,
                       capacity_factor):
    """The definition: discounted lifetime cost over discounted lifetime energy.

    Capital is spent at year 0; fixed O&M and fuel are paid every year; energy
    is produced every year. Not a rearrangement of `levelized_cost_crf` -- the
    two meet only because the energy stream is flat.
    """
    mwh = HOURS_PER_YEAR * capacity_factor          # per MW per year
    if mwh <= 0:
        raise ValueError("a plant that never runs has no levelized cost")
    npv_cost = capex_per_mw + sum(
        (fixed_om_per_mw_yr + marginal * mwh) / (1 + rate) ** t
        for t in range(1, years + 1))
    npv_mwh = sum(mwh / (1 + rate) ** t for t in range(1, years + 1))
    return npv_cost / npv_mwh
