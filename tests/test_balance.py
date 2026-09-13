# -*- coding: utf-8 -*-
"""Does `esm.balance` reproduce the household energy balance?

This notebook has no solver, so these tests are a different shape from
test_boundary.py's. There is no second search procedure to compare against;
what there is instead is one invariant that arithmetic cannot satisfy by
accident (conservation) and one class of error that actually threatens a
notebook about units (a wrong conversion factor).
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from esm.balance import (  # noqa: E402
    JOULES_PER_BTU, JOULES_PER_KWH, ROUNDED_FACTOR_RTOL, conservation_residual,
    load_balance_instance, rejected_share, si_consistency, solve_balance,
    unverifiable_factors,
)


@pytest.fixture(scope="module")
def inst():
    return load_balance_instance()


@pytest.fixture(scope="module")
def result(inst):
    return solve_balance(inst)


def test_the_instance_is_the_one_the_notebook_describes(inst):
    s = inst.sources
    assert set(s) == {"grid electricity", "natural gas", "gasoline"}
    assert s["grid electricity"]["as_billed"] == 10_000
    assert s["natural gas"]["as_billed"] == 600
    assert s["gasoline"]["as_billed"] == 500
    assert s["gasoline"]["efficiency"] == 0.25


def test_the_headline_numbers(result):
    """Exact values, not the notebook's displayed ones.

    The notebook prints these with {:,.0f}, which rounds half to EVEN: the
    true totals are 28,155.5 and 16,274.5, displayed as 28,156 and 16,274.
    Those look inconsistent and are not. Asserting against what is printed
    rather than what is computed would bake a formatting rule into a physics
    test -- and 0.5 is exactly the half-way case, so it would sit on the
    boundary of its own tolerance.
    """
    assert result.total_in == 44_430.0
    assert result.total_useful == 28_155.5
    assert result.total_rejected == 16_274.5
    assert abs(result.total_useful / result.total_in - 0.634) < 0.001


def test_the_balance_closes_exactly(result):
    """The one thing here that cannot come out right by accident.

    Not a tolerance chosen to pass: input minus useful minus rejected is
    computed from the same joules and must be zero to floating point, per
    source and in total.
    """
    for name, residual in conservation_residual(result).items():
        assert abs(residual) < 1e-9, (name, residual)


def test_no_source_rejects_more_than_it_took_in(result):
    for name in result.kwh_in:
        assert 0.0 <= result.useful[name] <= result.kwh_in[name] + 1e-9
        assert 0.0 <= result.rejected[name] <= result.kwh_in[name] + 1e-9


def test_gasoline_is_most_of_the_waste(result):
    """The notebook's punchline: the biggest input is not the biggest loss."""
    share = rejected_share(result)
    assert list(share)[0] == "gasoline"
    assert abs(share["gasoline"] - 0.78) < 0.01
    # and it is NOT the largest input -- natural gas is
    assert result.kwh_in["natural gas"] > result.kwh_in["gasoline"]


def test_the_therm_factor_matches_its_exact_definition(inst):
    """A therm IS 100,000 Btu, and the Btu is exactly defined.

    So this factor has a true value and can be checked. The table rounds it to
    29.3, which is low by 2.4e-4 -- a deliberate teaching rounding, not an
    error, which is why the tolerance here is ROUNDED_FACTOR_RTOL and not
    AGREEMENT_RTOL. If someone later replaces 29.3 with a typo, this catches it.
    """
    checked = si_consistency(inst)
    got, want, gap = checked["natural gas"]
    assert got == 29.3
    assert abs(want - 29.30710702) < 1e-6
    assert gap < ROUNDED_FACTOR_RTOL
    # the rounding is real, not zero -- pin its direction too
    assert 1e-5 < gap < 1e-3 and got < want


def test_gasoline_is_deliberately_not_checked(inst):
    """There is no exact kWh per gallon, so there is nothing to check against.

    Heating value is a measured property varying by blend and standard; EIA
    gives ~32.9 lower and ~35.3 higher. The table's 33.7 matches neither
    because it is the EPA's MPGe gallon-equivalent, a regulatory convention.
    Asserting a tolerance against a value that does not exist would be
    inventing precision, so the module omits it -- and says so out loud rather
    than leaving a silent gap.
    """
    assert "gasoline" not in si_consistency(inst)
    assert unverifiable_factors(inst) == {"gasoline": "gallons"}


def test_the_si_constants_are_the_defined_ones():
    assert JOULES_PER_BTU == 1055.05585262
    assert JOULES_PER_KWH == 3.6e6


def test_an_efficiency_above_one_is_rejected(tmp_path):
    """Conservation would break silently, producing useful > input."""
    src = ROOT / "data" / "raw" / "house_energy.csv"
    p = tmp_path / "house_energy.csv"
    p.write_text(src.read_text(encoding="utf-8").replace(",0.85,", ",1.85,"),
                 encoding="utf-8")
    with pytest.raises(ValueError, match="efficiency"):
        load_balance_instance(source=tmp_path)


def test_a_local_edit_reaches_the_model(tmp_path):
    """The loader honours the reader's edit.

    This notebook states its instance inline, so an edit here moves the
    PACKAGE's answer only; what it proves is that data/raw is genuinely the
    package's source and not decoration.
    """
    src = ROOT / "data" / "raw" / "house_energy.csv"
    p = tmp_path / "house_energy.csv"
    p.write_text(src.read_text(encoding="utf-8").replace("600,therms",
                                                         "900,therms"),
                 encoding="utf-8")
    base = solve_balance(load_balance_instance())
    edited = solve_balance(load_balance_instance(source=tmp_path))
    assert edited.total_in > base.total_in, (
        "editing data/raw/ changed nothing -- the loader is not reading the "
        "file the reader was told to edit"
    )
