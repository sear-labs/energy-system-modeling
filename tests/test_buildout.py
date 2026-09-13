# -*- coding: utf-8 -*-
"""Does `esm.buildout` check what the Texas capstone claims?

This module verifies inputs and invariants rather than re-solving the model --
esm/buildout.py's docstring says why. These tests therefore concentrate on the
two things that must be true for that to be worth anything: the independent
distance formula really is independent, and each guard actually fires when the
thing it guards against happens.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from esm.buildout import (  # noqa: E402
    EARTH_RADIUS_KM, check_demand_shares, check_resource_limits,
    coal_cost_per_mwh, corridor_distances, daily_capital, gas_cost_per_mwh,
    great_circle_km, line_daily_capital, load_buildout_instance,
)


@pytest.fixture(scope="module")
def inst():
    return load_buildout_instance()


def test_the_instance_is_the_one_the_notebook_describes(inst):
    assert set(inst.hubs) == {"Dallas-Fort Worth", "Houston", "San Antonio",
                              "Austin", "West Texas"}
    assert len(inst.corridors) == 7
    assert inst.hubs["West Texas"]["wind_max_mw"] == 22_000
    assert inst.hubs["West Texas"]["solar_max_mw"] == 18_000
    assert inst.hubs["Dallas-Fort Worth"]["demand_share"] == 0.341


def test_demand_shares_sum_to_one(inst):
    assert check_demand_shares(inst) is True


def test_the_demand_share_guard_fires(tmp_path):
    """A guard that cannot fail says nothing when it passes."""
    src = ROOT / "data" / "raw"
    for name in ("buildout_hubs.csv", "buildout_corridors.csv",
                 "buildout_costs.csv"):
        (tmp_path / name).write_text((src / name).read_text(encoding="utf-8"),
                                     encoding="utf-8")
    p = tmp_path / "buildout_hubs.csv"
    p.write_text(p.read_text(encoding="utf-8").replace(",0.341,", ",0.241,"),
                 encoding="utf-8")
    with pytest.raises(AssertionError, match="sum to"):
        check_demand_shares(load_buildout_instance(source=tmp_path))


def test_the_distances_match_the_notebooks_haversine(inst):
    """Two different great-circle formulas, not one written twice.

    The notebook uses haversine with numpy; this uses the spherical law of
    cosines with the stdlib math module. Agreement means the coordinates and
    the radius are right, which is the thing a spatial model gets wrong
    silently.
    """
    import numpy as np

    def haversine_km(a, b):
        lat1, lat2 = np.radians(a[0]), np.radians(b[0])
        dlat = lat2 - lat1
        dlon = np.radians(b[1] - a[1])
        h = (np.sin(dlat / 2) ** 2
             + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2)
        return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(h))

    for (a, b), km in corridor_distances(inst).items():
        pa = (inst.hubs[a]["lat"], inst.hubs[a]["lon"])
        pb = (inst.hubs[b]["lat"], inst.hubs[b]["lon"])
        assert abs(km - haversine_km(pa, pb)) / km < 1e-9, (a, b)


def test_the_corridor_lengths_are_the_ones_the_notebook_printed(inst):
    d = corridor_distances(inst)
    assert abs(d[("West Texas", "Dallas-Fort Worth")] - 503) < 1
    assert abs(d[("Austin", "San Antonio")] - 118) < 1
    assert abs(d[("Dallas-Fort Worth", "Houston")] - 362) < 1


def test_swapping_lat_and_lon_is_caught(inst):
    """The specific error the distance check exists for.

    A transposed coordinate pair gives a distance that is wrong but entirely
    plausible, and shows up nowhere else in the model.
    """
    dfw = (inst.hubs["Dallas-Fort Worth"]["lat"],
           inst.hubs["Dallas-Fort Worth"]["lon"])
    hou = (inst.hubs["Houston"]["lat"], inst.hubs["Houston"]["lon"])
    right = great_circle_km(dfw, hou)
    swapped = great_circle_km((dfw[1], dfw[0]), (hou[1], hou[0]))
    assert abs(right - swapped) / right > 0.1


def test_the_law_of_cosines_loses_precision_at_zero_distance(inst):
    """The known weakness, measured rather than described.

    At zero separation `cos_d` is 1 and `acos` is at its worst: a relative
    error of ~1e-16 in the cosine becomes sqrt(2e-16) radians, which over the
    earth's radius is about 9 centimetres. Haversine returns exactly zero on
    the same input, because `arcsin(0)` is exact.

    This is why the two formulas are a real cross-check rather than one
    calculation written twice -- and why the largest disagreement across the
    corridors is on the SHORTEST one. It is far below AGREEMENT_RTOL at the
    hundreds of kilometres this model uses, and it is pinned here so that
    stays a measured fact rather than an assumption.
    """
    import numpy as np
    dfw = (inst.hubs["Dallas-Fort Worth"]["lat"],
           inst.hubs["Dallas-Fort Worth"]["lon"])

    slip_km = great_circle_km(dfw, dfw)
    assert 0.0 < slip_km < 1e-3, slip_km          # nonzero, under a metre

    # haversine is exact here, which is the whole reason it exists
    lat = np.radians(dfw[0])
    h = np.sin(0.0) ** 2 + np.cos(lat) * np.cos(lat) * np.sin(0.0) ** 2
    assert 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(h)) == 0.0

    # and it is negligible against the shortest corridor actually modelled
    shortest = min(corridor_distances(inst).values())
    assert slip_km / shortest < 1e-6


def test_the_fuel_costs_match_the_notebook(inst):
    """$2.50/Mcf over 1.036 MMBtu/Mcf at 6.4 MMBtu/MWh, plus $3.50 VOM."""
    assert abs(gas_cost_per_mwh(inst) - (2.50 / 1.036 * 6.4 + 3.50)) < 1e-12
    assert abs(coal_cost_per_mwh(inst) - (20.0 / 13.0 * 10.0 + 4.50)) < 1e-12
    # and the ordering the merit order depends on
    assert gas_cost_per_mwh(inst) < coal_cost_per_mwh(inst)


def test_daily_capital_is_annual_capital_over_365(inst):
    """Mixing $/yr capital with $/day operating is the three-orders-of-
    magnitude error this function exists to prevent."""
    from esm.lcoe import capital_recovery_factor
    annual = 1_000_000.0 * capital_recovery_factor(0.07, 40)
    assert abs(daily_capital(1_000_000.0, 40, 0.07) - annual / 365.0) < 1e-12


def test_line_capital_scales_with_distance(inst):
    a = line_daily_capital(inst, 100.0)
    b = line_daily_capital(inst, 200.0)
    assert abs(b - 2 * a) < 1e-9


def test_resource_limits_pass_when_respected(inst):
    assert check_resource_limits(
        inst, {"West Texas": 20_000.0}, {"West Texas": 15_000.0}) is True


def test_resource_limits_catch_an_overbuild(inst):
    with pytest.raises(AssertionError, match="exceeds the resource limit"):
        check_resource_limits(inst, {"West Texas": 25_000.0}, {})
    with pytest.raises(AssertionError, match="solar at Austin"):
        check_resource_limits(inst, {}, {"Austin": 9_000.0})


def test_a_corridor_naming_an_unknown_hub_is_refused(tmp_path):
    src = ROOT / "data" / "raw"
    for name in ("buildout_hubs.csv", "buildout_corridors.csv",
                 "buildout_costs.csv"):
        (tmp_path / name).write_text((src / name).read_text(encoding="utf-8"),
                                     encoding="utf-8")
    p = tmp_path / "buildout_corridors.csv"
    p.write_text(p.read_text(encoding="utf-8") + "Austin,El Paso\n",
                 encoding="utf-8")
    with pytest.raises(ValueError, match="not in"):
        load_buildout_instance(source=tmp_path)


def test_a_local_edit_reaches_the_model(tmp_path):
    src = ROOT / "data" / "raw"
    for name in ("buildout_hubs.csv", "buildout_corridors.csv",
                 "buildout_costs.csv"):
        (tmp_path / name).write_text((src / name).read_text(encoding="utf-8"),
                                     encoding="utf-8")
    p = tmp_path / "buildout_costs.csv"
    p.write_text(p.read_text(encoding="utf-8").replace("gas_price_per_mcf,2.50",
                                                       "gas_price_per_mcf,5.00"),
                 encoding="utf-8")
    assert (gas_cost_per_mwh(load_buildout_instance(source=tmp_path))
            > gas_cost_per_mwh(load_buildout_instance()))
