# -*- coding: utf-8 -*-
"""Does `esm.meter`'s synthetic house look like a meter export, and do its
summaries match the pandas route the notebook takes?"""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from esm.meter import (COLUMNS, SYNTHETIC_ESIID, base_load, biggest_steps,  # noqa: E402
                       hourly_profile, synthetic_export, to_kw)


@pytest.fixture(scope="module")
def raw():
    return synthetic_export(seed=4301)


@pytest.fixture(scope="module")
def kw(raw):
    return to_kw(raw)[0]


def test_it_has_the_export_columns_and_no_real_meter_id(raw):
    assert list(raw.columns) == COLUMNS
    assert (raw["ESIID"] == SYNTHETIC_ESIID).all()
    assert len(raw) == 365 * 96


def test_the_same_seed_gives_the_same_house(raw):
    again = synthetic_export(seed=4301).head(2000)
    assert again.equals(raw.head(2000))
    other = synthetic_export(seed=1).head(2000)
    assert not other["USAGE_KWH"].equals(raw.head(2000)["USAGE_KWH"])


def test_it_is_a_plausible_texas_house(raw, kw):
    annual = raw["USAGE_KWH"].sum()
    assert 8_000 < annual < 16_000                 # kWh a year
    assert (raw["USAGE_KWH"] > 0).all()
    summer = kw[kw.index.month == 7].mean()
    spring = kw[kw.index.month == 4].mean()
    assert summer > 2 * spring                     # air conditioning shows
    assert 0.1 < base_load(kw) < 0.6


def test_the_summaries_match_the_pandas_route(kw):
    """The notebook's groupby and diff, against this module's numpy route."""
    by_pandas = kw.groupby([kw.index.day_of_week >= 5, kw.index.hour]).mean().unstack(0)
    by_numpy = hourly_profile(kw)
    assert np.allclose(by_pandas[False].to_numpy(), by_numpy["weekday"].to_numpy(),
                       rtol=1e-12)
    assert np.allclose(by_pandas[True].to_numpy(), by_numpy["weekend"].to_numpy(),
                       rtol=1e-12)
    assert np.allclose(kw.diff().nlargest(10).to_numpy(), biggest_steps(kw, 10))


def test_exports_are_separated_from_consumption(raw):
    with_export = raw.head(8).copy()
    with_export.loc[with_export.index[:2], "CONSUMPTION_SURPLUSGENERATION"] = "Surplus Generation"
    use, exported = to_kw(with_export)
    assert len(use) == 6
    assert exported == pytest.approx(with_export["USAGE_KWH"].iloc[:2].sum())


def test_rows_out_of_order_are_put_in_time_order(raw):
    shuffled = raw.head(500).sample(frac=1, random_state=0)
    use, _ = to_kw(shuffled)
    assert use.index.is_monotonic_increasing
