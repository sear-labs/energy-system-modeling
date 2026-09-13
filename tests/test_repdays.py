# -*- coding: utf-8 -*-
"""Does `esm.repdays` reproduce the representative-day method?

This notebook runs on the reader's own interval data, so there is no fixed
instance to test against the way there is for the optimisation modules. These
tests use the seeded stand-in year, and check PROPERTIES of the method that
must hold on any data -- weights accounting for every day, the compressed
estimate bracketed sensibly, the regression satisfying the normal equations --
rather than only the numbers this one year happens to give.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from esm.repdays import (  # noqa: E402
    compression_error, daily_totals, degree_days, fit_degree_day_model,
    normal_equation_residual, pick_representative_days, r_squared_two_ways,
    synthetic_year, ties_in_daily_totals, weighted_annual_estimate,
)


@pytest.fixture(scope="module")
def daily():
    return daily_totals(synthetic_year(0))


@pytest.fixture(scope="module")
def fitted(daily):
    doy = daily.index.dayofyear.to_numpy()
    temp_f = 62 + 22 * np.sin(np.pi * (doy - 110) / 182.5)
    cdd, hdd = degree_days(temp_f, 65.0)
    return daily.values, cdd, hdd, fit_degree_day_model(daily.values, cdd, hdd)


def test_the_stand_in_year_is_reproducible():
    """Seeded with default_rng, whose PCG64 stream is stable across NumPy
    versions -- unlike the legacy global seed."""
    a, b = synthetic_year(0), synthetic_year(0)
    assert np.array_equal(a.values, b.values)
    assert len(a) == 8760
    assert synthetic_year(1).values.tolist() != a.values.tolist()


def test_the_stand_in_year_matches_what_the_notebook_printed(daily):
    y = synthetic_year(0)
    assert abs(y.max() - 3.32) < 0.005
    assert abs(y.mean() - 1.74) < 0.005
    assert abs(float(daily.sum()) - 15_251) < 1.0


def test_weights_account_for_every_day(daily):
    """The failure this guards is a silently lost remainder: 365 days split
    three ways is 121/123/121, not 121/121/121 with four days dropped."""
    for groups in (1, 2, 3, 4, 5, 7, 12):
        picks, weights = pick_representative_days(daily, groups)
        assert len(picks) == len(weights) == groups
        assert sum(weights) == len(daily)
        assert all(w > 0 for w in weights)


def test_the_three_day_pick_matches_the_notebook(daily):
    picks, weights = pick_representative_days(daily, 3)
    assert [d.strftime("%d %b") for d in picks] == ["08 Mar", "08 Nov", "06 Jul"]
    assert weights == [121, 123, 121]


def test_the_compression_error_is_small_and_reported_signed(daily):
    picks, weights = pick_representative_days(daily, 3)
    assert abs(compression_error(daily, picks, weights)) < 0.02
    est = weighted_annual_estimate(daily, picks, weights)
    assert abs(est - 15_331) < 1.0


def test_more_groups_do_not_make_the_estimate_worse_on_average(daily):
    """Not monotone day by day, but the trend must be the right way round.

    If this reversed, the picking rule would be selecting unrepresentative
    days -- the method would be worse the harder it worked.
    """
    errs = {g: abs(compression_error(daily, *pick_representative_days(daily, g)))
            for g in (1, 3, 12, 52)}
    assert errs[52] < errs[1]
    assert errs[12] < errs[1]


def test_picks_are_unambiguous_on_this_data(daily):
    """Part 6's precondition for comparing WHICH dates were picked.

    Two days with identical totals leave the sort order between them
    undetermined, so the date could differ between implementations while the
    total it stands for does not.
    """
    assert ties_in_daily_totals(daily) == []


def test_a_tie_is_detected_when_one_exists(daily):
    """The detector must actually fire, or its silence means nothing."""
    import pandas as pd
    d = daily.copy()
    d.iloc[0] = d.iloc[1]
    assert ties_in_daily_totals(d) == [float(d.iloc[1])]


def test_degree_days_are_never_both_positive():
    """A day is above base or below it, not both."""
    cdd, hdd = degree_days([40.0, 65.0, 90.0], 65.0)
    assert list(cdd) == [0.0, 0.0, 25.0]
    assert list(hdd) == [25.0, 0.0, 0.0]
    assert all(c == 0 or h == 0 for c, h in zip(cdd, hdd))


def test_the_fit_matches_the_notebook(fitted):
    _, _, _, fit = fitted
    assert abs(fit.intercept - 41.6) < 0.05
    assert abs(fit.per_cooling_degree - 0.6) < 0.05
    assert abs(fit.per_heating_degree - (-0.3)) < 0.05
    assert abs(fit.r_squared - 0.877) < 0.001


def test_the_fit_satisfies_the_normal_equations(fitted):
    """A property of any least-squares solution, whatever found it.

    This would catch a fit that BOTH lstsq drivers agree on and that is still
    not the least-squares answer -- something comparing the two cannot do.
    """
    y, cdd, hdd, fit = fitted
    assert normal_equation_residual(y, cdd, hdd, fit) < 1e-12


def test_r_squared_agrees_computed_two_ways(fitted):
    """Equal for OLS with an intercept, unequal otherwise -- so this checks
    the model, not just the number."""
    y, cdd, hdd, fit = fitted
    a, b = r_squared_two_ways(y, cdd, hdd, fit)
    assert abs(a - b) < 1e-12


def test_scipys_gelsy_agrees_with_numpys_gelsd(fitted):
    """The two routes are different LAPACK algorithms, not one import apart."""
    y, cdd, hdd, fit = fitted
    X = np.column_stack([np.ones_like(y), cdd, hdd])
    ref, *_ = np.linalg.lstsq(X, y, rcond=None)
    got = np.array([fit.intercept, fit.per_cooling_degree,
                    fit.per_heating_degree])
    assert np.abs(ref - got).max() < 1e-9


def test_collinear_degree_days_are_refused():
    """If every day is above base, hdd is all zeros and the coefficients are
    not separately identified -- a real limit of the method, not a bug."""
    y = np.linspace(30, 60, 50)
    cdd, hdd = degree_days(np.linspace(70, 95, 50), 65.0)
    assert hdd.max() == 0.0
    with pytest.raises(AssertionError, match="collinear"):
        fit_degree_day_model(y, cdd, hdd)


def test_too_few_days_for_the_requested_groups_is_refused(daily):
    with pytest.raises(ValueError, match="at least one"):
        pick_representative_days(daily.iloc[:2], 5)
