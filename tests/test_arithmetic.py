# -*- coding: utf-8 -*-
"""Does `esm.arithmetic` give the numbers the book prints for these examples?

The primer notebook's numbers are the book's (sections 2.3, 9.1, 9.3, 9.4 and
12.4), so each test names the book figure it pins. These check the formulas
against the problem, not against the notebook -- the notebook's own agreement
cell does that.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from esm import arithmetic as ea  # noqa: E402


def gas_mc():
    return ea.marginal_cost(6.370, ea.plant_gate_price(2.65, 1.033, 0.50), 2.10)


def coal_mc():
    return ea.marginal_cost(10.745, ea.plant_gate_price(18.76, 15.97, 0.75), 5.06)


def test_energy_and_power():
    assert ea.energy_kwh(3.5, 45 / 60) == pytest.approx(2.625)
    assert ea.average_kw(0.6, 0.25) == pytest.approx(2.4)
    with pytest.raises(ValueError):
        ea.average_kw(1.0, 0)


def test_the_btu_chain():
    """600 therms is about 17,600 kWh of heat (book 2.3)."""
    assert ea.heat_to_kwh(600 * ea.BTU_PER_THERM) == pytest.approx(17_585, abs=1)
    assert ea.MMBTU_PER_MWH == pytest.approx(3.412)


def test_marginal_costs_are_the_books():
    assert round(gas_mc(), 2) == 21.63
    assert round(coal_mc(), 2) == 25.74


def test_emission_rates_are_the_books():
    assert round(ea.emission_rate(6.370, 53.06), 3) == 0.338
    assert round(ea.emission_rate(10.745, 97.72), 3) == 1.050


def test_capacity_factor_sun_and_wind():
    assert ea.annual_mwh(100, 0.35) == pytest.approx(306_600)
    assert ea.solar_kwh_per_kw(5.5, 0.80) == pytest.approx(1606, abs=0.5)
    assert ea.wind_power_mw(1.225, 120, 8.0) == pytest.approx(3.55, abs=0.005)
    assert ea.wind_power_mw(1.225, 120, 8.0) * ea.BETZ == pytest.approx(2.10, abs=0.005)


def test_the_mean_of_the_cube_is_not_the_cube_of_the_mean():
    """The question the notebook asks about a gusty site, as an inequality."""
    steady = ea.wind_power_mw(1.225, 120, 8.0)
    gusty = (ea.wind_power_mw(1.225, 120, 4.0) + ea.wind_power_mw(1.225, 120, 12.0)) / 2
    assert gusty > 1.7 * steady


@pytest.mark.parametrize("cf, book", [(0.30, 63), (0.87, 36)])
def test_lcoe_is_the_books(cf, book):
    v = ea.levelized_cost_crf(1_176_000, 13_730, gas_mc(), 0.07, 30, cf)
    assert v == pytest.approx(book, abs=0.5)


@pytest.mark.parametrize("cf", [0.05, 0.30, 0.87])
@pytest.mark.parametrize("rate", [0.0001, 0.07, 0.15])
def test_the_shortcut_and_the_definition_agree_on_flat_output(cf, rate):
    """CRF shortcut and discounted definition meet when output is flat."""
    a = ea.levelized_cost_crf(1_176_000, 13_730, gas_mc(), rate, 30, cf)
    b = ea.levelized_cost_dcf(1_176_000, 13_730, gas_mc(), rate, 30, cf)
    assert a == pytest.approx(b, rel=1e-12)


def test_the_definition_is_not_a_restatement():
    """Capital spent in year 1 instead of year 0 is a different number in the
    definition, and the shortcut has no way to see it -- so the agreement above
    is a property of the timing, not of the code."""
    a = ea.levelized_cost_dcf(1_176_000, 13_730, gas_mc(), 0.07, 30, 0.30)
    b = ea.levelized_cost_dcf(1_176_000 / 1.07, 13_730, gas_mc(), 0.07, 30, 0.30)
    assert a - b > 1.0


def test_a_plant_that_never_runs_has_no_lcoe():
    with pytest.raises(ValueError):
        ea.levelized_cost_dcf(1_000_000, 10_000, 20.0, 0.07, 30, 0.0)
