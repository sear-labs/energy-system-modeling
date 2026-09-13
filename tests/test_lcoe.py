# -*- coding: utf-8 -*-
"""Does `esm.lcoe` reproduce the screening calculation the notebook builds?

Like test_balance.py, this notebook has no solver, so these check the
arithmetic against the problem rather than against a second search. The two
things that actually go wrong in a screening study are unit conversions and the
CRF, so those get the most attention.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from esm.lcoe import (  # noqa: E402
    capital_recovery_factor, fuel_cost_per_mwh, fuel_mmbtu_per_mwh,
    lcoe_by_crf, lcoe_by_dcf, lifetime_fuel_bill, load_lcoe_instance,
    screening_table,
)


@pytest.fixture(scope="module")
def inst():
    return load_lcoe_instance()


def test_the_instance_is_the_one_the_notebook_describes(inst):
    assert inst.plant_mw == 250
    assert inst.hours_per_year == 8760
    assert inst.lifetime_years == 30
    assert inst.discount_rate == 0.07
    assert inst.lifetime_mwh == 250 * 8760 * 30 == 65_700_000
    assert len(inst.plants) == 6
    assert inst.plants[("coal", 10000)].heat_content == 13.0
    assert inst.plants[("gas", 7500)].heat_content == 1.036


def test_the_crf_matches_the_notebook(inst):
    crf = capital_recovery_factor(0.07, 30)
    assert abs(crf - 0.0806) < 0.00005


def test_the_two_crf_forms_agree():
    """Both textbook forms, cross-checked inside the function.

    If the assertion inside capital_recovery_factor ever fires, something
    arithmetically impossible has happened -- which in practice means an
    operator precedence error in one of them.
    """
    for rate in (0.0, 0.03, 0.07, 0.12):
        for years in (5, 20, 30, 40):
            crf = capital_recovery_factor(rate, years)
            assert crf > 0
    # a zero rate is just straight-line recovery
    assert capital_recovery_factor(0.0, 25) == 1 / 25


def test_the_heat_rate_conversion_is_a_factor_of_one_thousand():
    """Btu/kWh to MMBtu/MWh. The commonest slip in this whole calculation."""
    assert fuel_mmbtu_per_mwh(10_000) == 10.0
    assert fuel_mmbtu_per_mwh(7_500) == 7.5


def test_the_fuel_only_screening_numbers_match_the_notebook(inst):
    """All six rows of the notebook's comparison table."""
    want = {("coal", 8800): 10.15, ("coal", 10000): 15.38,
            ("coal", 11500): 26.54, ("gas", 6400): 12.36,
            ("gas", 7500): 18.10, ("gas", 9000): 34.75}
    got = screening_table(inst)
    for key, expected in want.items():
        assert abs(got[key] - expected) < 0.005, (key, got[key], expected)


def test_the_break_even_prices_match_the_notebook(inst):
    assert abs(lcoe_by_crf(inst, inst.plants[("coal", 10000)]) - 55.48) < 0.005
    assert abs(lcoe_by_crf(inst, inst.plants[("gas", 7500)]) - 29.50) < 0.005


def test_the_crf_shortcut_equals_the_dcf_definition(inst):
    """The justification for every screening study's shortcut, checked.

    Equal ONLY because annual energy is constant: both the cost sum and the
    energy sum pick up the same annuity factor, which cancels.
    """
    for plant in inst.plants.values():
        a = lcoe_by_crf(inst, plant)
        b = lcoe_by_dcf(inst, plant)
        assert abs(a - b) / a < 1e-12, (plant.fuel, plant.heat_rate, a, b)


def test_the_shortcut_breaks_under_degradation(inst):
    """What makes the test above worth having.

    If the two routes agreed no matter what, they would be the same
    calculation written twice and their agreement would prove nothing. Put a
    falling energy stream in and the cancellation fails: the definition rises
    and the shortcut does not notice.
    """
    plant = inst.plants[("gas", 7500)]
    flat = lcoe_by_dcf(inst, plant, degradation=0.0)
    degrading = lcoe_by_dcf(inst, plant, degradation=0.005)
    assert degrading > flat
    assert 0.03 < (degrading / flat - 1) < 0.07
    # and the shortcut is blind to it, which is exactly the limitation
    assert abs(lcoe_by_crf(inst, plant) - flat) / flat < 1e-12


def test_gas_beats_coal_on_break_even_despite_dearer_fuel(inst):
    """The notebook's punchline, asserted rather than only printed.

    Gas burns a larger fuel bill and still wins, because coal's capital cost
    is nearly four times as much per MW. A screening study that looked only at
    fuel would get this backwards -- and the fuel-only table above says so.
    """
    coal, gas = inst.plants[("coal", 10000)], inst.plants[("gas", 7500)]
    assert lifetime_fuel_bill(inst, gas) > lifetime_fuel_bill(inst, coal)
    assert fuel_cost_per_mwh(inst, gas) > fuel_cost_per_mwh(inst, coal)
    assert lcoe_by_crf(inst, gas) < lcoe_by_crf(inst, coal)


def test_a_dearer_fuel_price_only_raises_the_answer(inst):
    from esm.lcoe import Plant
    base = inst.plants[("gas", 7500)]
    dearer = Plant(**{**base.__dict__, "fuel_price": base.fuel_price * 2})
    assert lcoe_by_crf(inst, dearer) > lcoe_by_crf(inst, base)


def test_a_local_edit_reaches_the_model(tmp_path):
    """The loader honours the reader's edit."""
    src = ROOT / "data" / "raw"
    for name in ("lcoe_system.csv", "lcoe_plants.csv"):
        (tmp_path / name).write_text((src / name).read_text(encoding="utf-8"),
                                     encoding="utf-8")
    p = tmp_path / "lcoe_system.csv"
    p.write_text(p.read_text(encoding="utf-8").replace("discount_rate,0.07",
                                                       "discount_rate,0.12"),
                 encoding="utf-8")
    base = load_lcoe_instance()
    edited = load_lcoe_instance(source=tmp_path)
    assert (lcoe_by_crf(edited, edited.plants[("coal", 10000)])
            > lcoe_by_crf(base, base.plants[("coal", 10000)])), (
        "a higher discount rate must raise the break-even price")
