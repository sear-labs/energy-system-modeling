# -*- coding: utf-8 -*-
"""Does `esm.storage` behave like the battery day the notebook builds?

The plain-LP half needs only scipy. The PyPSA comparison at the bottom is the
one that found the standing-loss detail, and it skips where PyPSA is absent --
which is CI, by design (see pyproject.toml: PyPSA is a notebook dependency).
"""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from esm.storage import BatteryDay, day_cost, load_battery_profile  # noqa: E402


@pytest.fixture(scope="module")
def day():
    return BatteryDay.module_0()


def test_the_table_is_the_closed_form(day):
    """The table and the notebook's formulas are two copies of one day."""
    h = np.arange(24)
    demand = 50 + 60 * np.exp(-((h - 19) ** 2) / 12.0) + 18 * np.exp(-((h - 8) ** 2) / 6.0)
    solar = np.clip(np.sin(np.pi * (h - 6) / 13), 0, 1)
    d, s = load_battery_profile()
    # not bit-equality: exp and sin differ in the last bit between platforms
    assert np.allclose(d, demand, rtol=1e-14, atol=0)
    assert np.allclose(s, solar, rtol=1e-14, atol=1e-15)
    assert d.max() == pytest.approx(110, abs=0.1)


def test_a_battery_saves_money(day):
    base, _ = day_cost(day)
    four, _ = day_cost(day, max_hours=4)
    assert four < base


def test_starting_full_without_the_cyclic_rule_looks_cheaper_and_ends_empty(day):
    four, _ = day_cost(day, max_hours=4)
    open_full, end = day_cost(day, max_hours=4, cyclic=False, soc_initial=160)
    assert open_full < four
    assert end == pytest.approx(0.0, abs=1e-6)


def test_twice_the_energy_does_not_save_twice_as_much(day):
    base, _ = day_cost(day)
    saves = {h: base - day_cost(day, max_hours=h)[0] for h in (2, 4, 8)}
    assert saves[2] < saves[4] <= saves[8] < 2 * saves[4]


def test_no_battery_has_no_state_of_charge(day):
    assert day_cost(day)[1] is None


def test_pypsa_agrees_on_every_case(day):
    """The comparison the module docstring describes, including the first-hour
    standing-loss rule. Skips without PyPSA."""
    pypsa = pytest.importorskip("pypsa")
    import logging
    logging.getLogger("pypsa").setLevel(logging.ERROR)
    logging.getLogger("linopy").setLevel(logging.ERROR)
    n = pypsa.Network()
    n.set_snapshots(range(24))
    n.add("Bus", "node")
    n.add("Load", "demand", bus="node", p_set=day.demand)
    n.add("Generator", "solar", bus="node", p_nom=day.solar_mw, p_max_pu=day.solar_pu)
    n.add("Generator", "gas", bus="node", p_nom=day.gas_mw, marginal_cost=day.gas_cost)
    n.add("Generator", "peaker", bus="node", p_nom=day.peaker_mw,
          marginal_cost=day.peaker_cost)
    n.optimize(solver_name="highs", log_to_console=False)
    assert n.objective == pytest.approx(day_cost(day)[0], rel=1e-9)
    n.add("StorageUnit", "battery", bus="node", p_nom=day.battery_mw, max_hours=4,
          efficiency_store=day.efficiency, efficiency_dispatch=day.efficiency,
          standing_loss=day.standing_loss, cyclic_state_of_charge=True,
          marginal_cost=day.dispatch_cost)
    n.optimize(solver_name="highs", log_to_console=False)
    assert n.objective == pytest.approx(day_cost(day, 4)[0], rel=1e-9)
    n.storage_units.loc["battery", "cyclic_state_of_charge"] = False
    n.storage_units.loc["battery", "state_of_charge_initial"] = 160
    n.optimize(solver_name="highs", log_to_console=False)
    assert n.objective == pytest.approx(day_cost(day, 4, False, 160)[0], rel=1e-9)
