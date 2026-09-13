# -*- coding: utf-8 -*-
"""Does `esm.diversity` solve the tool-neutral bundle correctly?

The notebook's own instance is built by its `export_tables()` and is compared
against PyPSA and PuLP there. These tests use a SMALL bundle whose answer can be
worked out by hand instead -- so a failure points at the LP assembly rather than
at a disagreement between three large models, and so nothing here is a second
copy of the notebook's numbers.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from esm.diversity import (  # noqa: E402
    assert_comparable_quantities_are_unique, build_by_tech, per_hub_ranges,
    solve_expansion, sunk_cost,
)


def bundle(mc_gas=10.0, solar_capital=100.0, arc_capital=5.0,
           existing=0.0, solar_limit=50.0):
    """Two hubs, two technologies, two hours, one corridor.

    Hub A has all the demand and no resource; hub B has the solar. Small
    enough that the optimum can be reasoned about on paper.
    """
    hours = [0, 1]
    demand = pd.DataFrame({"A": [100.0, 100.0], "B": [0.0, 0.0]}, index=hours)
    tech = pd.DataFrame(
        [dict(tech="solar", mc=0.0, daily_capital=solar_capital),
         dict(tech="gas", mc=mc_gas, daily_capital=1.0)]).set_index("tech")
    limit = pd.DataFrame({"solar": {"A": 0.0, "B": solar_limit},
                          "gas": {"A": 1000.0, "B": 0.0}})
    avail = pd.DataFrame({"solar": [1.0, 1.0], "gas": [1.0, 1.0]}, index=hours)
    arcs = pd.DataFrame([dict(a="B", b="A", km=1.0, existing_mw=existing,
                              max_mw=1000.0, daily_capital=arc_capital)])
    return dict(demand=demand, tech=tech, limit=limit, avail=avail, arcs=arcs)


def test_demand_is_met_at_every_hub_and_hour():
    r = solve_expansion(bundle())
    total = {h: sum(v for (hub, t, hh), v in r.dispatch.items() if hh == h)
             for h in (0, 1)}
    assert abs(total[0] - 100.0) < 1e-6
    assert abs(total[1] - 100.0) < 1e-6


def test_expensive_solar_is_not_built_and_gas_serves_everything():
    """Solar at 100/day of capital against gas at 1/day plus 10/MWh.

    Gas costs 1 + 2*10 = 21 per MW of capacity per day; solar costs 100 plus a
    corridor. Gas wins outright.
    """
    r = solve_expansion(bundle(solar_capital=100.0))
    built = build_by_tech(r)
    assert abs(built["gas"] - 100.0) < 1e-6
    assert built["solar"] < 1e-6


def test_cheap_solar_displaces_gas_and_builds_the_corridor():
    """Drop solar's capital below gas's fuel bill and it must enter -- and
    drag corridor capacity with it, since the demand is at the other hub."""
    r = solve_expansion(bundle(solar_capital=1.0, arc_capital=1.0))
    built = build_by_tech(r)
    assert built["solar"] > 1e-6
    assert r.arc_mw[("B", "A")] >= built["solar"] - 1e-6


def test_the_corridor_limit_caps_what_solar_can_serve():
    """Solar is limited to 50 MW at hub B, so gas must cover the rest."""
    r = solve_expansion(bundle(solar_capital=1.0, arc_capital=1.0,
                               solar_limit=50.0))
    built = build_by_tech(r)
    assert abs(built["solar"] - 50.0) < 1e-6
    assert abs(built["gas"] - 50.0) < 1e-6


def test_sunk_cost_is_existing_capacity_times_daily_capital():
    t = bundle(existing=200.0, arc_capital=5.0)
    assert abs(sunk_cost(t) - 1000.0) < 1e-12


def test_the_two_conventions_differ_by_exactly_the_sunk_cost():
    """The notebook's Part 4 identity, on a bundle where it can be checked
    against arithmetic rather than against another solver."""
    t = bundle(existing=200.0, arc_capital=5.0, solar_capital=1.0)
    charged = solve_expansion(t, charge_existing=True)
    free = solve_expansion(t, charge_existing=False)
    assert abs((charged.cost - free.cost) - sunk_cost(t)) < 1e-9


def test_existing_corridor_capacity_is_a_floor_not_a_target():
    """`existing_mw` is a lower bound on corridor capacity: it is already
    built, so the model may use it but cannot un-build it."""
    t = bundle(existing=300.0, solar_capital=100.0)
    r = solve_expansion(t)
    assert r.arc_mw[("B", "A")] >= 300.0 - 1e-6


def test_a_tie_between_technologies_is_detected():
    """The check must fire when the optimum really is a face.

    Give gas and solar the same all-in cost and the split between them stops
    being determined, while the total and the cost do not.
    """
    t = bundle(solar_capital=21.0, arc_capital=0.0, solar_limit=1000.0)
    t["tech"].loc["gas", "daily_capital"] = 1.0
    t["tech"].loc["gas", "mc"] = 10.0
    with pytest.raises(AssertionError, match="not determined"):
        assert_comparable_quantities_are_unique(t)


def test_a_clear_winner_passes_the_uniqueness_check():
    assert assert_comparable_quantities_are_unique(bundle()) is True


def test_per_hub_ranges_reports_a_span_for_an_interchangeable_hub():
    """What the notebook's instance turns out to have: two places to put the
    same technology at the same cost, so the split is free."""
    t = bundle(solar_capital=1.0, arc_capital=0.0, solar_limit=1000.0)
    t["limit"].loc["A", "solar"] = 1000.0      # solar now buildable at BOTH
    ranges = per_hub_ranges(t)
    spans = [hi - lo for (lo, hi) in ranges.values()]
    assert max(spans) > 1.0, ranges


def test_an_infeasible_bundle_raises_with_an_explanation():
    t = bundle(solar_capital=1.0)
    t["limit"].loc["A", "gas"] = 0.0           # no generation reachable
    t["limit"].loc["B", "solar"] = 0.0
    with pytest.raises(RuntimeError, match="did not solve"):
        solve_expansion(t)
