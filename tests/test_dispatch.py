# -*- coding: utf-8 -*-
"""Does `esm.dispatch` reproduce the hour the dispatch notebook builds?

The numbers are the book's (section 9.4): gas $21.63 and coal $25.74 per MWh,
a $21.65/t carbon price that flips a winter merit order, and a 500 t cap that
forces about 551 MW onto gas with that same price as its shadow price.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from esm import arithmetic as ea  # noqa: E402
from esm.dispatch import Thermal, assert_prices_are_unique, solve_hour  # noqa: E402

GAS_GATE = ea.plant_gate_price(2.65, 1.033, 0.50)
COAL_GATE = ea.plant_gate_price(18.76, 15.97, 0.75)


def fleet(gas_gate=GAS_GATE, coal_min=0.0):
    return [Thermal("Houston CCGT", 600, 6.370, gas_gate, 2.10, 53.06),
            Thermal("San Antonio coal", 600, 10.745, COAL_GATE, 5.06, 97.72,
                    min_share=coal_min)]


def test_gas_runs_first_and_coal_sets_the_price():
    r = solve_hour(fleet(), 1000, wind_mw=150)
    assert r.output == pytest.approx({"wind": 150, "Houston CCGT": 600,
                                      "San Antonio coal": 250})
    assert round(r.price, 2) == 25.74
    assert assert_prices_are_unique(fleet(), r, 150) == ["San Antonio coal"]


def test_winter_gas_puts_coal_first():
    r = solve_hour(fleet(2 * GAS_GATE), 1000, wind_mw=150)
    assert r.output["San Antonio coal"] == pytest.approx(600)
    assert r.output["Houston CCGT"] == pytest.approx(250)


@pytest.mark.parametrize("tau, gas_first", [(0, False), (21.5, False), (21.8, True)])
def test_the_flip_price_is_21_65(tau, gas_first):
    r = solve_hour(fleet(2 * GAS_GATE), 1000, wind_mw=150, co2_price=tau)
    assert (r.output["Houston CCGT"] > r.output["San Antonio coal"]) == gas_first


def test_the_cap_has_the_flip_price_as_its_shadow_price():
    r = solve_hour(fleet(2 * GAS_GATE), 1000, wind_mw=150, co2_cap=500)
    assert round(r.output["Houston CCGT"]) == 551
    assert round(r.cap_price, 2) == 21.65
    assert r.tonnes == pytest.approx(500)
    # two binding constraints, two units strictly inside their limits
    assert len(assert_prices_are_unique(fleet(2 * GAS_GATE), r, 150)) == 2


def test_a_slack_cap_is_free():
    r = solve_hour(fleet(), 1000, wind_mw=150, co2_cap=10_000)
    assert r.cap_price == pytest.approx(0.0, abs=1e-9)
    assert r.binding == ["balance"]


def test_infeasible_returns_none():
    assert solve_hour(fleet(), 1400, wind_mw=150) is None


def test_must_run_coal_pushes_gas_off():
    r = solve_hour(fleet(coal_min=1.0), 700, wind_mw=150)
    assert r.output["San Antonio coal"] == pytest.approx(600)
    assert r.output["Houston CCGT"] == pytest.approx(0, abs=1e-6)


def test_the_uniqueness_guard_fires_on_a_boundary():
    """Load exactly at wind + gas: every unit is full or empty, no price is determined.

    This is the guard watched to fail -- an instance built to sit on the boundary.
    """
    r = solve_hour(fleet(), 750, wind_mw=150)
    with pytest.raises(AssertionError, match="compare costs, not prices"):
        assert_prices_are_unique(fleet(), r, 150)
