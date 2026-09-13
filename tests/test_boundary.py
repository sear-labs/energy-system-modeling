# -*- coding: utf-8 -*-
"""Does `esm.boundary` compute the dispatch the notebook builds in PyPSA?

Physics/economics tests on the package itself: these check the model against
the problem, not against the notebook, so "they agree" cannot be satisfied by
both being wrong the same way.

One test goes further and checks the LP against a merit-order stack computed by
hand, with no solver involved at all. For a dispatch with no coupling between
hours that is not an approximation -- it is the exact answer, arrived at by
sorting rather than by optimising -- so it catches an LP that is quietly solving
a different problem.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from esm.boundary import (  # noqa: E402
    assert_prices_are_unique, bill, load_boundary_instance, marginal_units,
    solve_dispatch,
)


@pytest.fixture(scope="module")
def inst():
    return load_boundary_instance()


@pytest.fixture(scope="module")
def base(inst):
    return solve_dispatch(inst, 0.0)


def test_the_instance_is_the_one_the_notebook_describes(inst):
    assert len(inst.hours) == 24
    assert inst.interconnection_mw == 600.0
    assert inst.generators["wind"]["p_nom"] == 5000.0
    assert inst.generators["wind"]["marginal_cost"] == 0.0
    assert inst.generators["gas01"]["marginal_cost"] == 22.0
    assert inst.generators["scarcity"]["marginal_cost"] == 2000.0
    # eleven firm units plus wind
    assert len(inst.generators) == 12
    # the peak hour the whole notebook turns on
    assert abs(max(inst.metro) - 5000.0) < 1.0


def test_the_profile_table_round_trips_exactly(inst):
    """Written with repr(), read with float_precision="round_trip".

    Asserted as a property of the FILE and the PARSER -- not by recomputing the
    notebook's formulas. An earlier version of this test did recompute them and
    demanded bit-equality, which passed on the authoring machine and failed on
    CI at one index: np.sin may differ by an ulp between platforms, so that
    version was testing the runner's maths library rather than these tables.
    Demand comes from exponentials here, so the values are not short decimals
    and pandas' default parser (fast, not correctly rounded) does lose a bit.
    """
    import csv
    with open(ROOT / "data" / "raw" / "boundary_profile.csv",
              newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 24
    for row, metro, wind in zip(rows, inst.metro, inst.wind_pu):
        # the loader agrees with Python's own correctly-rounded parser
        assert float(row["metro_mw"]) == metro
        assert float(row["wind_pu"]) == wind
        # and the file carries enough digits to name the float uniquely
        assert repr(metro) == row["metro_mw"]
        assert repr(wind) == row["wind_pu"]


def test_the_profile_matches_the_notebooks_closed_form(inst):
    """The tables and the notebook are two copies of one instance.

    Compared with a tolerance rather than bit-exactly, deliberately: the
    notebook evaluates exp() and sin() on whichever machine runs it, and those
    are not required to agree to the last bit across platforms. The slack here
    is still a thousand times tighter than AGREEMENT_RTOL, and the marginal
    unit in every hour sits ~1 MW from its nearest bound -- about 1e12 ulps --
    so a difference at this scale cannot change a price or a dispatch.
    """
    import numpy as np
    hours = np.arange(24)
    metro = (4000
             + 1000 * np.exp(-((hours - 19) ** 2) / 12.0)
             + 400 * np.exp(-((hours - 8) ** 2) / 6.0))
    wind = np.clip(0.30 + 0.55 * np.sin(np.pi * (hours - 2) / 16), 0, 1)
    assert np.allclose(inst.metro, metro, rtol=1e-12, atol=0.0)
    assert np.allclose(inst.wind_pu, wind, rtol=1e-12, atol=1e-15)


def test_no_marginal_unit_sits_near_a_bound(inst):
    """What makes the tolerance above safe, asserted rather than asserted-about.

    A merit-order price is a step function of demand. If a marginal unit sat a
    hair from full or empty, a last-bit difference in demand could tip it and
    move the price by a whole step. Measure the clearance instead of trusting
    that it is large.
    """
    for mw in (0.0, 50.0, 500.0, 600.0):
        r = solve_dispatch(inst, mw)
        for h in inst.hours:
            for g, spec in inst.generators.items():
                cap = spec["p_nom"] * (inst.wind_pu[h] if spec["profile"] else 1.0)
                p = r.dispatch[g][h]
                if 1e-6 < p < cap - 1e-6:
                    assert min(p, cap - p) > 0.1, (mw, h, g, p, cap)


def test_demand_is_met_exactly_every_hour(inst, base):
    for h in inst.hours:
        served = sum(base.dispatch[g][h] for g in inst.generators)
        assert abs(served - inst.metro[h]) < 1e-6


def test_no_generator_exceeds_its_availability(inst, base):
    for g, spec in inst.generators.items():
        for h in inst.hours:
            cap = spec["p_nom"] * (inst.wind_pu[h] if spec["profile"] else 1.0)
            assert -1e-9 <= base.dispatch[g][h] <= cap + 1e-6


def test_the_lp_agrees_with_a_merit_order_stacked_by_hand(inst, base):
    """No solver: sort by cost, fill until demand is met, read off the price.

    With no storage, ramping or commitment this is exact rather than
    approximate. If the LP and the sort disagree, the LP is solving something
    other than the dispatch this notebook describes.
    """
    for h in inst.hours:
        units = sorted(
            ((g, spec["p_nom"] * (inst.wind_pu[h] if spec["profile"] else 1.0),
              spec["marginal_cost"]) for g, spec in inst.generators.items()),
            key=lambda t: t[2])
        remaining = inst.metro[h]
        price = None
        for g, cap, cost in units:
            take = min(cap, remaining)
            remaining -= take
            if take > 1e-9:
                price = cost
            assert abs(base.dispatch[g][h] - take) < 1e-6, (h, g)
            if remaining <= 1e-9:
                break
        assert abs(base.lmp[h] - price) < 1e-6, (h, base.lmp[h], price)


def test_prices_are_unique_at_every_site_size(inst):
    """Part 6's precondition, re-derived rather than assumed.

    A merit-order price is only pinned when one unit is part-loaded. If demand
    ever lands exactly on a capacity boundary the price is ambiguous and must
    not be compared between solvers.
    """
    for mw in (0.0, 50.0, 500.0, 600.0):
        r = solve_dispatch(inst, mw)
        assert assert_prices_are_unique(inst, r) is True
        assert all(len(u) == 1 for u in marginal_units(inst, r))


def test_the_park_moves_the_price_in_three_hours_and_pays_3_6_percent_more(inst, base):
    """The notebook's headline result for the small load."""
    park = solve_dispatch(inst, 50.0)
    moved = [h for h in inst.hours if abs(park.lmp[h] - base.lmp[h]) > 1e-9]
    assert len(moved) == 3
    predicted, actual = bill(base, 50.0), bill(park, 50.0)
    assert abs(predicted - 49_500.0) < 1.0
    assert abs(actual - 51_300.0) < 1.0
    assert abs((actual / predicted - 1) - 0.036) < 0.001


def test_the_data_centre_moves_the_price_in_nineteen_hours(inst, base):
    """The contrast the notebook is built to draw: same model, same method,
    and the price-taker assumption survives one and not the other."""
    dc = solve_dispatch(inst, 500.0)
    moved = [h for h in inst.hours if abs(dc.lmp[h] - base.lmp[h]) > 1e-9]
    assert len(moved) == 19
    predicted, actual = bill(base, 500.0), bill(dc, 500.0)
    assert abs(predicted - 495_000.0) < 1.0
    assert abs(actual - 912_000.0) < 1.0
    assert actual / predicted > 1.8


def test_a_bigger_site_never_lowers_the_price(inst):
    """Monotonicity, and a guard against a sign error in the dual.

    Adding load to a merit-order dispatch can only move up the stack. If a
    future edit flips the sign of the price, cost would still look plausible
    while this reverses.
    """
    prices = [sum(solve_dispatch(inst, mw).lmp) for mw in (0.0, 50.0, 200.0, 500.0)]
    assert prices == sorted(prices)


def test_a_site_larger_than_the_interconnection_is_refused(inst):
    """The notebook's "harder limit": 900 MW behind a 600 MW link.

    This is the model boundary binding, not an infeasible dispatch, and the
    error says so -- a reader who sees "infeasible" will go looking for missing
    generation.
    """
    with pytest.raises(RuntimeError, match="interconnection"):
        solve_dispatch(inst, 900.0)
    # and the boundary itself is feasible, so the limit is where it is claimed
    assert solve_dispatch(inst, 600.0).cost > 0


def test_cost_rises_with_the_site(inst, base):
    for mw in (50.0, 200.0, 500.0):
        assert solve_dispatch(inst, mw).cost > base.cost


def test_a_local_edit_reaches_the_model(tmp_path):
    """The loader honours the reader's edit.

    This notebook states its instance inline as two closed-form expressions, so
    an edit here moves the PACKAGE's answer only. What it proves is that
    `data/raw/` is genuinely the package's source and not decoration.
    """
    src = ROOT / "data" / "raw"
    for name in ("boundary_profile.csv", "boundary_generators.csv",
                 "boundary_system.csv"):
        (tmp_path / name).write_text((src / name).read_text(encoding="utf-8"),
                                     encoding="utf-8")

    # make the cheapest gas dearer than the second; the price must follow
    p = tmp_path / "boundary_generators.csv"
    p.write_text(p.read_text(encoding="utf-8").replace("gas01,600.0,22.0",
                                                       "gas01,600.0,99.0"),
                 encoding="utf-8")
    base = solve_dispatch(load_boundary_instance())
    edited = solve_dispatch(load_boundary_instance(source=tmp_path))
    assert edited.cost > base.cost, (
        "editing data/raw/ changed nothing -- the loader is not reading the "
        "file the reader was told to edit"
    )
