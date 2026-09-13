# -*- coding: utf-8 -*-
"""Checks for importing a real network, for `15_real_network_import`.

    from esm.network_import import infer_coordinate_columns, parse_matpower
    infer_coordinate_columns(line, bus)

WHAT THIS IS FOR

`notebooks/p4_networks/15_real_network_import.ipynb` is not about solving a
model. It is about the fact that **real network data arrives broken in ways that
do not raise an exception**, and about finding those breaks before they become
results. Its own subject is three defects: profile arrays oriented differently
from one another, coordinate columns that do not hold what their headers claim,
and a MATPOWER import that silently pins every generator.

So this module is a verifier, not a second solver. There is nothing here to
re-solve. What it does is make each of those checks something the package
performs independently, rather than something the notebook asserts about itself.

WHY THE COORDINATE CHECK IS THE INTERESTING ONE

`Line_data.csv` has four coordinate columns whose headers say from-lat,
from-lon, to-lat, to-lon. Two of them are swapped: the real order is from-lat,
to-lat, from-lon, to-lon.

Nothing about that raises. Every value is a plausible number in a plausible
range, and a map drawn from them looks like a network -- just not the right one.
The only way to catch it is to stop believing the headers and test each column
against something that is independently known: the bus table, which carries each
bus's true latitude and longitude.

`infer_coordinate_columns()` does exactly that. For every candidate column it
computes the mean absolute error against all four possible meanings and returns
the best fit. It never reads a header. A column whose best fit is not what its
header claims is mislabelled, and the function says so.

This is the general shape of the lesson: **a header is a claim, and a claim is
checkable against a second source.**

WHAT MAY AND MAY NOT BE COMPARED

The inference is only decisive when the four candidate meanings are actually
distinguishable, and they are distinguishable for TWO different reasons of very
different strength. Worth separating, because the weaker one is what the check
actually rests on.

**Latitude against longitude is easy.** Texas buses sit near +31 and -97, so
mistaking one axis for the other costs about 128 degrees of error. Nothing
subtle there.

**From-end against to-end is not.** `from_lat` and `to_lat` are both latitudes
of buses on the same line, so the only thing separating them is how far the line
spans. Measured on TX-123BT that is **0.327 degrees on average** -- not 128.

So the margin that matters is small in absolute terms. What makes the inference
decisive anyway is that the correct assignment scores exactly 0.0: the column
either IS that series or it is not. `coordinate_inference_is_decisive()` returns
the comparison, and an exact zero is treated as decisive because nothing can
beat it -- but on data where the best fit were merely close rather than exact,
the ratio test is what would carry the weight, and on a network of very short
lines it could fail. The notebook prints both errors so this is visible rather
than asserted.
"""
from __future__ import annotations

import re

LAT_LON_MEANINGS = ("from_lat", "to_lat", "from_lon", "to_lon")


def true_endpoint_coordinates(line_df, bus_df,
                              bus_col="Bus Number",
                              lat_col="Bus latitude",
                              lon_col="Bus longitude",
                              from_col="From Bus Number",
                              to_col="To Bus Number"):
    """Each line's true endpoint coordinates, taken from the BUS table.

    This is the independent source the column headers get tested against.
    """
    coords = bus_df.set_index(bus_col)
    return {
        "from_lat": coords[lat_col].loc[line_df[from_col]].to_numpy(),
        "to_lat": coords[lat_col].loc[line_df[to_col]].to_numpy(),
        "from_lon": coords[lon_col].loc[line_df[from_col]].to_numpy(),
        "to_lon": coords[lon_col].loc[line_df[to_col]].to_numpy(),
    }


def infer_coordinate_columns(line_df, bus_df, candidate_columns=None, **kw):
    """Decide what each coordinate column REALLY holds, ignoring its header.

    Returns `{column_name: (best_meaning, best_error, second_error)}`, where the
    errors are mean absolute degrees against the bus table. The gap between best
    and second is the evidence that the answer is decisive.
    """
    import numpy as np

    truth = true_endpoint_coordinates(line_df, bus_df, **kw)
    if candidate_columns is None:
        candidate_columns = [c for c in line_df.columns
                             if re.search(r"lat|lon", str(c), re.I)]
    if not candidate_columns:
        raise ValueError(
            "no columns whose names mention lat or lon; pass "
            "candidate_columns explicitly."
        )

    out = {}
    for col in candidate_columns:
        v = np.asarray(line_df[col], dtype=float)
        errs = {k: float(np.abs(v - t).mean()) for k, t in truth.items()}
        order = sorted(errs, key=errs.get)
        out[col] = (order[0], errs[order[0]], errs[order[1]])
    return out


def coordinate_inference_is_decisive(inference, ratio=10.0, atol=1e-9):
    """True when every column's best fit is clearly better than its runner-up.

    Guards against reading a coin toss as a finding. Two ways to be decisive:

      exact          the best fit scores ~0, so the column IS that series and
                     nothing can beat it. This is the ordinary case here.
      by a margin    the best fit beats the runner-up by `ratio`, which is what
                     carries the weight when the match is close but not exact.

    The distinction matters more than it looks. Separating latitude from
    longitude is trivial -- about 128 degrees of error in Texas. Separating the
    FROM end from the TO end is not: both are latitudes of buses on one line, so
    the only thing between them is the line's span, about 0.33 degrees on
    TX-123BT. On a network of very short lines that margin would shrink towards
    nothing, and this would correctly return False rather than guess.
    """
    for _col, (_best, e1, e2) in inference.items():
        if e1 <= atol:
            continue                      # exact: decisive on its own
        if e2 < e1 * ratio:
            return False
    return True


def mislabelled_columns(inference, claimed):
    """Columns whose true content is not what their header claims.

    `claimed` maps column name -> what the header says it is.
    """
    bad = {}
    for col, says in claimed.items():
        if col not in inference:
            continue
        best = inference[col][0]
        if best != says:
            bad[col] = (says, best)
    return bad


def check_profile_orientation(load, solar, wind, n_buses, n_solar, n_wind,
                              n_hours=24):
    """The first defect: three arrays, not all oriented the same way.

    TX-123BT stores load as (hours, buses) and the generation profiles as
    (plants, hours). Summing the wrong axis gives a number of exactly the right
    kind -- MW, plausible magnitude -- and is wrong all day.
    """
    problems = []
    if load.shape != (n_hours, n_buses):
        problems.append(f"load is {load.shape}, expected ({n_hours}, {n_buses}) "
                        f"as (hours, buses)")
    if solar.shape != (n_solar, n_hours):
        problems.append(f"solar is {solar.shape}, expected ({n_solar}, "
                        f"{n_hours}) as (plants, hours)")
    if wind.shape != (n_wind, n_hours):
        problems.append(f"wind is {wind.shape}, expected ({n_wind}, {n_hours}) "
                        f"as (plants, hours)")
    if problems:
        raise AssertionError(
            "profile arrays are not oriented as expected, and summing the "
            "wrong axis produces a plausible wrong answer rather than an "
            "error: " + "; ".join(problems))
    return True


def parse_matpower(text):
    """MATPOWER `.m` -> a PYPOWER-style dict, KEEPING the cell arrays.

    The same parser the notebook writes, here so the notebook can check its own
    against it. The cell-array handling is the point: `gentype`, `genfuel` and
    `bus_name` are dropped by both standard converters, and they are the only
    place the case records what each machine burns. Without them there are 544
    anonymous generators and no generation mix to report at all.
    """
    import numpy as np

    ppc = {"version": "2"}
    m = re.search(r"mpc\.baseMVA\s*=\s*([0-9.eE+-]+)\s*;", text)
    ppc["baseMVA"] = float(m.group(1)) if m else 100.0

    for field in ("bus", "gen", "branch", "gencost"):
        m = re.search(r"mpc\.%s\s*=\s*\[(.*?)\n\s*\];" % field, text, re.S)
        if not m:
            continue
        rows = []
        for raw in m.group(1).splitlines():
            s = raw.split("%")[0].strip().rstrip(";").strip()
            if s:
                rows.append([float(x) for x in s.replace(",", " ").split()])
        w = max(len(r) for r in rows)
        ppc[field] = np.array([r + [0.0] * (w - len(r)) for r in rows])

    for field in ("gentype", "genfuel", "bus_name"):
        m = re.search(r"mpc\.%s\s*=\s*\{(.*?)\n\s*\};" % field, text, re.S)
        if m:
            ppc[field] = re.findall(r"'([^']*)'", m.group(1))
    return ppc


def check_matpower_parse(ppc, n_buses=None, n_gens=None, n_branches=None):
    """The third defect class: an import that succeeds while losing things.

    Counts are checked where given, and the cell arrays are checked for
    presence AND for matching the numeric tables in length -- a `genfuel` list
    shorter than `gen` would silently mislabel the generation mix from
    whichever row the offset began.
    """
    problems = []
    for field, want, label in (("bus", n_buses, "buses"),
                               ("gen", n_gens, "generators"),
                               ("branch", n_branches, "branches")):
        if field not in ppc:
            problems.append(f"no {field} table parsed at all")
        elif want is not None and len(ppc[field]) != want:
            problems.append(f"{len(ppc[field])} {label}, expected {want}")

    for field, against in (("genfuel", "gen"), ("gentype", "gen"),
                           ("bus_name", "bus")):
        if field not in ppc:
            problems.append(
                f"{field} is missing -- both standard converters drop the cell "
                f"arrays, and this one is the only record of what each unit is")
        elif against in ppc and len(ppc[field]) != len(ppc[against]):
            problems.append(
                f"{field} has {len(ppc[field])} entries against "
                f"{len(ppc[against])} rows of {against}; every label from the "
                f"offset onwards would be attached to the wrong unit")

    if problems:
        raise AssertionError("MATPOWER parse is incomplete: "
                             + "; ".join(problems))
    return True


def generation_mix(ppc, pmax_column=8):
    """MW of capacity by fuel, from the cell arrays that survived the parse."""
    if "genfuel" not in ppc:
        raise ValueError("no genfuel cell array; see check_matpower_parse")
    out = {}
    for fuel, row in zip(ppc["genfuel"], ppc["gen"]):
        out[fuel] = out.get(fuel, 0.0) + float(row[pmax_column])
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))
