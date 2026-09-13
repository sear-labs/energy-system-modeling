# -*- coding: utf-8 -*-
"""Representative days and degree-day regression, written once so a notebook can be checked.

    from esm.repdays import pick_representative_days, weighted_annual_estimate
    picks, weights = pick_representative_days(daily_kwh)
    estimate = weighted_annual_estimate(daily_kwh, picks, weights)

WHAT THIS IS FOR, AND WHY IT IS SHAPED DIFFERENTLY

`notebooks/p2_demand/05_representative_days.ipynb` runs on the reader's OWN
interval data, falling back to a synthetic year when there is no export to
load. So unlike every other module here, there is no fixed instance to check
against: the instance is whatever the student uploaded.

**What is shared is therefore the METHOD, not the data.** The notebook's
agreement cell runs these functions on whatever `daily_kwh` it ended up with --
real export or stand-in -- and asserts they reproduce what it computed inline.
That check is worth the same on a student's data as on the fallback, which is
the property a bring-your-own-data notebook needs and a fixed instance could
not give.

The one thing that IS fixed is the stand-in year, because it is seeded. The
notebook builds it inline (showing how a stand-in is made is part of the
lesson) and this module carries the same construction for its tests. Those are
two copies of one formula, so the notebook's agreement cell compares them
whenever it is running on the stand-in -- a duplicate that is checked rather
than merely regretted.

WHY THE REGRESSION GOES THROUGH A DIFFERENT ROUTE

The notebook fits with `numpy.linalg.lstsq`, which calls LAPACK's `gelsd`
(SVD-based). This module uses `scipy.linalg.lstsq` with `lapack_driver="gelsy"`
(complete orthogonal factorisation) -- a genuinely different algorithm, not the
same one behind a different import.

It also checks the fit against the normal equations directly, which is a
property rather than a re-implementation: any least-squares solution must
satisfy `X'X b = X'y`, whatever route found it. `normal_equation_residual()`
reports that, so a fit can be wrong in a way BOTH lstsq calls agree on and
still be caught.

R-SQUARED IS COMPUTED TWICE ON PURPOSE

`1 - SS_res/SS_tot` and the squared Pearson correlation between fitted and
observed are equal for ordinary least squares WITH an intercept, and unequal
otherwise. Comparing them is therefore a check on the model having an intercept
and on the fit being a genuine least-squares solution -- not merely a second
way of printing the same number. `r_squared_two_ways()` returns both.

WHAT MAY AND MAY NOT BE COMPARED

Representative-day picks are positions in a sorted series. Where two days have
identical totals the sort order between them is not determined, so WHICH date
is picked can differ between implementations while the total it stands for does
not. On float data from meters or from the stand-in, exact ties do not occur;
`ties_in_daily_totals()` reports any, and the notebook checks it before
comparing dates rather than assuming.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DegreeDayFit:
    intercept: float          # kWh/day at base temperature
    per_cooling_degree: float # kWh per degF-day above base
    per_heating_degree: float # kWh per degF-day below base
    r_squared: float


def synthetic_year(seed=0):
    """The stand-in year the notebook uses when no export is present.

    Kept here so the tests have a fixed instance. This is a second copy of the
    notebook's own construction, which is why the notebook's agreement cell
    compares the two whenever it is running on the stand-in.

    `numpy.random.default_rng` is stream-stable across NumPy versions (PCG64),
    so the same seed gives the same year on any machine -- unlike the legacy
    `numpy.random.seed` global, which is not guaranteed in the same way.
    """
    import numpy as np
    import pandas as pd

    idx = pd.date_range("2025-01-01", periods=8760, freq="1h")
    hour, doy = idx.hour.to_numpy(), idx.dayofyear.to_numpy()
    shape = (0.9 + 0.45 * np.exp(-((hour - 19) ** 2) / 6.0)
             + 0.20 * np.exp(-((hour - 7) ** 2) / 4.0))
    cooling = 1 + 0.55 * np.clip(np.sin(np.pi * (doy - 100) / 240), 0, 1)
    rng = np.random.default_rng(seed)
    kw = 1.4 * shape * cooling * rng.normal(1.0, 0.05, len(idx))
    return pd.Series(np.clip(kw, 0.15, None), index=idx)


def daily_totals(hourly_kw):
    """Hourly mean kW -> kWh per day. One kW held for one hour is one kWh."""
    return hourly_kw.resample("1D").sum()


def pick_representative_days(daily, groups=3):
    """Sort the days, split into equal groups, take the middle day of each.

    Returns `(picks, weights)`: the chosen dates and how many days each stands
    for. Weights sum to the number of days by construction -- the remainder
    after equal division goes to the middle group, so a 365-day year with three
    groups gives 121/123/121 rather than 121/121/121 and a silently lost four.

    The picks are the (2k+1)/(2*groups) quantiles of the sorted daily totals:
    for three groups, the 1/6th, median and 5/6th days.
    """
    order = daily.sort_values()
    n = len(order)
    if groups < 1 or n < groups:
        raise ValueError(
            f"cannot split {n} days into {groups} groups; need at least one "
            f"day per group."
        )

    picks = [order.index[(2 * k + 1) * n // (2 * groups)] for k in range(groups)]

    base = n // groups
    weights = [base] * groups
    weights[groups // 2] += n - base * groups     # remainder to the middle

    assert sum(weights) == n, "weights must account for every day of the year"
    return picks, weights


def weighted_annual_estimate(daily, picks, weights):
    """What the representative days claim the year totalled."""
    if len(picks) != len(weights):
        raise ValueError("picks and weights must be the same length")
    return sum(float(daily[d]) * w for d, w in zip(picks, weights))


def compression_error(daily, picks, weights):
    """Relative error of the compressed estimate against the measured year."""
    actual = float(daily.sum())
    return weighted_annual_estimate(daily, picks, weights) / actual - 1.0


def ties_in_daily_totals(daily):
    """Days sharing an identical total, which make the pick order ambiguous.

    Returns the tied values. Empty is the ordinary case for meter data; a
    non-empty result means WHICH date is picked is not determined, even though
    the total it stands for is.
    """
    counts = {}
    for v in daily.values:
        counts[float(v)] = counts.get(float(v), 0) + 1
    return sorted(v for v, c in counts.items() if c > 1)


def degree_days(temp_f, base=65.0):
    """Cooling and heating degree-days about `base`, elementwise."""
    import numpy as np
    t = np.asarray(temp_f, dtype=float)
    return np.clip(t - base, 0, None), np.clip(base - t, 0, None)


def fit_degree_day_model(daily_values, cdd, hdd):
    """Least squares through scipy's gelsy driver, not numpy's gelsd.

    A different LAPACK algorithm rather than the same one behind a different
    import -- see the module docstring.
    """
    import numpy as np
    from scipy.linalg import lstsq

    y = np.asarray(daily_values, dtype=float)
    X = np.column_stack([np.ones_like(y), np.asarray(cdd, dtype=float),
                         np.asarray(hdd, dtype=float)])
    beta, _, rank, _ = lstsq(X, y, lapack_driver="gelsy")

    # Shape assert, not a status check: a rank-deficient design matrix still
    # returns a "solution", and it would be a different model from the one the
    # notebook describes.
    assert rank == X.shape[1], (
        f"design matrix has rank {rank}, not {X.shape[1]} -- cooling and "
        f"heating degree-days are collinear here, so the coefficients are not "
        f"separately identified."
    )

    pred = X @ beta
    ss_res = float(((y - pred) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    return DegreeDayFit(
        intercept=float(beta[0]),
        per_cooling_degree=float(beta[1]),
        per_heating_degree=float(beta[2]),
        r_squared=1.0 - ss_res / ss_tot,
    )


def normal_equation_residual(daily_values, cdd, hdd, fit):
    """max |X'X b - X'y|, scaled. Zero for any true least-squares solution.

    A property of the answer rather than a second computation of it, so it
    catches a fit that both lstsq calls agree on and that is still not the
    least-squares solution.
    """
    import numpy as np
    y = np.asarray(daily_values, dtype=float)
    X = np.column_stack([np.ones_like(y), np.asarray(cdd, dtype=float),
                         np.asarray(hdd, dtype=float)])
    b = np.array([fit.intercept, fit.per_cooling_degree, fit.per_heating_degree])
    residual = X.T @ X @ b - X.T @ y
    return float(np.abs(residual).max() / max(np.abs(X.T @ y).max(), 1.0))


def r_squared_two_ways(daily_values, cdd, hdd, fit):
    """(1 - SS_res/SS_tot, squared Pearson correlation of fitted and observed).

    Equal for OLS with an intercept and unequal otherwise, so comparing them
    checks the model rather than restating its R-squared.
    """
    import numpy as np
    y = np.asarray(daily_values, dtype=float)
    X = np.column_stack([np.ones_like(y), np.asarray(cdd, dtype=float),
                         np.asarray(hdd, dtype=float)])
    b = np.array([fit.intercept, fit.per_cooling_degree, fit.per_heating_degree])
    pred = X @ b
    ss_res = float(((y - pred) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    return 1.0 - ss_res / ss_tot, float(np.corrcoef(pred, y)[0, 1] ** 2)
