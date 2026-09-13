# -*- coding: utf-8 -*-
"""Does `esm.network_import` catch the defects the notebook is about?

Two sources here, deliberately:

The MATPOWER tests run against the real vendored `case_ACTIVSg2000.m`, because
counts and cell-array lengths are only meaningful on a real case.

The coordinate tests run against a tiny hand-built pair of tables, because the
point is to prove the inference DETECTS a swap -- which means constructing one
on purpose, and that cannot be done with a real file.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from esm.network_import import (  # noqa: E402
    check_matpower_parse, check_profile_orientation,
    coordinate_inference_is_decisive, generation_mix, infer_coordinate_columns,
    mislabelled_columns, parse_matpower, true_endpoint_coordinates,
)

CASE = ROOT / "data" / "vendor" / "case_ACTIVSg2000.m"


def tiny_tables(swap=False):
    """Four buses across Texas, three lines. Coordinates far apart in both
    axes, so the inference has something to distinguish."""
    bus = pd.DataFrame({
        "Bus Number": [1, 2, 3, 4],
        "Bus latitude": [31.0, 29.5, 33.2, 27.8],
        "Bus longitude": [-102.0, -95.4, -96.8, -97.4],
    })
    frm, to = [1, 2, 3], [2, 3, 4]
    c = bus.set_index("Bus Number")
    cols = {
        "from_lat": c["Bus latitude"].loc[frm].to_numpy(),
        "to_lat": c["Bus latitude"].loc[to].to_numpy(),
        "from_lon": c["Bus longitude"].loc[frm].to_numpy(),
        "to_lon": c["Bus longitude"].loc[to].to_numpy(),
    }
    # headers in the order the real file claims; the DATA is what varies
    line = pd.DataFrame({"From Bus Number": frm, "To Bus Number": to})
    if swap:   # the real defect: columns 2 and 3 exchanged under their headers
        line["From latitude"] = cols["from_lat"]
        line["From longitude"] = cols["to_lat"]
        line["To latitude"] = cols["from_lon"]
        line["To longitude"] = cols["to_lon"]
    else:
        line["From latitude"] = cols["from_lat"]
        line["From longitude"] = cols["from_lon"]
        line["To latitude"] = cols["to_lat"]
        line["To longitude"] = cols["to_lon"]
    return bus, line


CLAIMED = {"From latitude": "from_lat", "From longitude": "from_lon",
           "To latitude": "to_lat", "To longitude": "to_lon"}


def test_correctly_labelled_columns_are_reported_as_correct():
    bus, line = tiny_tables(swap=False)
    inf = infer_coordinate_columns(line, bus)
    assert mislabelled_columns(inf, CLAIMED) == {}
    for col, (best, e1, _e2) in inf.items():
        assert e1 < 1e-9, (col, best, e1)


def test_a_swapped_column_is_detected_without_reading_the_header():
    """The defect the notebook exists to teach.

    Nothing raises on this data. Every value is a plausible coordinate. Only
    testing each column against the bus table finds it.
    """
    bus, line = tiny_tables(swap=True)
    bad = mislabelled_columns(infer_coordinate_columns(line, bus), CLAIMED)
    assert set(bad) == {"From longitude", "To latitude"}
    assert bad["From longitude"] == ("from_lon", "to_lat")
    assert bad["To latitude"] == ("to_lat", "from_lon")


def test_the_inference_is_decisive_not_a_coin_toss():
    """A best fit means nothing unless it beats the runner-up by a margin.

    Texas latitudes (+26 to +36) and longitudes (-107 to -93) do not overlap,
    so the four meanings are separable. On a network where they did overlap,
    this would be False and the inference must not be used.
    """
    bus, line = tiny_tables(swap=True)
    assert coordinate_inference_is_decisive(infer_coordinate_columns(line, bus))


def test_true_endpoint_coordinates_follow_the_bus_numbers():
    bus, line = tiny_tables()
    truth = true_endpoint_coordinates(line, bus)
    assert list(truth["from_lat"]) == [31.0, 29.5, 33.2]
    assert list(truth["to_lon"]) == [-95.4, -96.8, -97.4]


def test_no_coordinate_columns_at_all_is_an_error():
    bus, _ = tiny_tables()
    plain = pd.DataFrame({"From Bus Number": [1], "To Bus Number": [2],
                          "x": [0.0]})
    with pytest.raises(ValueError, match="lat or lon"):
        infer_coordinate_columns(plain, bus)


def test_profile_orientation_accepts_the_documented_shapes():
    load = np.zeros((24, 123))
    solar = np.zeros((72, 24))
    wind = np.zeros((82, 24))
    assert check_profile_orientation(load, solar, wind, 123, 72, 82) is True


def test_a_transposed_profile_is_caught():
    """Summing the wrong axis gives MW of a plausible magnitude, all day."""
    load = np.zeros((123, 24))          # transposed
    solar = np.zeros((72, 24))
    wind = np.zeros((82, 24))
    with pytest.raises(AssertionError, match="hours, buses"):
        check_profile_orientation(load, solar, wind, 123, 72, 82)


# --- the real vendored case ------------------------------------------------

@pytest.fixture(scope="module")
def ppc():
    if not CASE.exists():
        pytest.skip("case_ACTIVSg2000.m is not vendored here")
    return parse_matpower(CASE.read_text(encoding="utf-8"))


def test_the_case_parses_to_the_documented_shape(ppc):
    assert ppc["bus"].shape == (2000, 17)
    assert ppc["gen"].shape == (544, 25)
    assert ppc["branch"].shape == (3206, 21)
    assert ppc["gencost"].shape == (544, 7)
    assert ppc["baseMVA"] == 100.0


def test_the_cell_arrays_survive_the_parse(ppc):
    """Both standard converters drop these, and they are the only record of
    what each machine burns."""
    assert len(ppc["genfuel"]) == 544
    assert len(ppc["gentype"]) == 544
    assert len(ppc["bus_name"]) == 2000
    assert check_matpower_parse(ppc, 2000, 544, 3206) is True


def test_a_short_cell_array_is_caught(ppc):
    """Every label from the offset onwards would attach to the wrong unit."""
    damaged = dict(ppc)
    damaged["genfuel"] = ppc["genfuel"][:-1]
    with pytest.raises(AssertionError, match="wrong unit"):
        check_matpower_parse(damaged, 2000, 544, 3206)


def test_a_missing_cell_array_is_caught(ppc):
    damaged = {k: v for k, v in ppc.items() if k != "genfuel"}
    with pytest.raises(AssertionError, match="only record"):
        check_matpower_parse(damaged, 2000, 544, 3206)


def test_the_generation_mix_is_a_plausible_texas_fleet(ppc):
    mix = generation_mix(ppc)
    assert set(mix) >= {"ng", "coal", "wind", "nuclear"}
    assert mix["ng"] > mix["coal"] > mix["solar"]
    total = sum(mix.values())
    assert 80_000 < total < 120_000, total
    # ERCOT is gas-dominated; if this flipped, the fuel labels are misaligned
    assert mix["ng"] / total > 0.5
