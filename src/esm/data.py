# -*- coding: utf-8 -*-
"""Where an instance table comes from, decided in one place.

    from esm.data import table
    gens = table("generators.csv")

WHY THIS EXISTS

Part 4 requires that instance tables live in `data/raw/` and that **both** the
notebook and the package read the same file -- because nothing else can prove
the two agree. That is easy in a clone and awkward everywhere else, and the
awkwardness has produced three different workarounds across this organisation's
repositories. This module picks one.

THE FOUR PLACES A NOTEBOOK CAN RUN, AND WHAT EACH ONE HAS

    a local clone                 data/raw/ is right there
    Colab, via the badge          the setup cell clones the repo, so likewise
    Colab, notebook uploaded      the setup cell still clones, so likewise
    `pip install git+https://...` package installed, NO data/ -- a data
                                  directory at the repo root is not package
                                  data and is not in the wheel

That fourth row is the one that bites, and it is documented in the standard's
Part 6 as a defect that shipped: three published repositories carried an Open In
Colab badge pointing at a notebook that could never have run, because the suite
only ever imported the package from a source checkout where the data already
sat in the right place.

THE RESOLUTION ORDER, AND WHY LOCAL MUST WIN

    1. an explicit `source` argument      a test, or a reader's own copy
    2. $ESM_DATA                          an override that needs no code change
    3. data/raw/ beside the package       a clone, or an editable install
    4. data/raw/ relative to the cwd      a notebook that has chdir'd into place
    5. the published URL                  everything else

**Local wins on purpose.** Part 4 asks that a reader who edits a value in
`data/raw/` sees it flow into both the hand-built model and the agreement check,
so that the check stays green while they experiment -- "a check that punishes
experimenting is a check that gets switched off". If the URL won, editing the
file would do nothing and the notebook would silently keep using the published
numbers.

WHY NOT VENDOR THE CSVs INTO THE PACKAGE

That is `advopt-lithiumsc`'s answer -- a second copy under `src/lithium/data/`,
with a test asserting it has not drifted from `data/raw/`. It works, and it is
two copies of every table plus a guard to watch them. The URL fallback needs
neither: there is one copy, and it is the one on the published branch.

The cost of this choice is honest and worth stating: **the fallback needs the
network, and it needs the repository to be public.** A raw file URL on a private
repository returns 404 exactly the way `git clone` fails on one -- measured
2026-09-07. Neither approach buys a way around publishing.

WHY THE URL NAMES A REF

`main` moves. A notebook that fetched `main` would silently change its answer
when someone edited a table, which is the "every number in the prose comes from
a run" rule failing from the outside in. `DATA_REF` is therefore a **release
tag** for anything handed to students, and only `main` during development.
"""
from __future__ import annotations

import io
import os
from pathlib import Path

import pandas as pd

REPO = "sear-labs/energy-system-modeling"

# Set to a release tag before handing a link to students; see the module
# docstring. Part 1 rule 8: tag what you hand out, so ongoing development never
# invalidates a published result.
DATA_REF = "main"

RAW_BASE = f"https://raw.githubusercontent.com/{REPO}/{DATA_REF}/data/raw"

#: Filled in by :func:`table`, so a notebook can print where its numbers came
#: from. A setup that cannot say what it read is a setup nobody can debug.
LAST_SOURCE: str | None = None


def _candidate_dirs(source):
    if source is not None:
        yield Path(source)
    env = os.environ.get("ESM_DATA")
    if env:
        yield Path(env)
    # installed or cloned: src/esm/data.py -> repo root -> data/raw
    yield Path(__file__).resolve().parents[2] / "data" / "raw"
    # a notebook that chdir'd into notebooks/<part>/
    yield Path.cwd() / "data" / "raw"
    yield Path.cwd().parents[1] / "data" / "raw" if len(Path.cwd().parents) > 1 else Path.cwd()


def resolve(name, source=None):
    """Return where `name` would be read from, without reading it.

    A path if a local copy exists, otherwise the published URL. Useful in a
    setup cell: it tells a reader whether they are editing the file the model
    will actually use.
    """
    for d in _candidate_dirs(source):
        try:
            p = d / name
            if p.is_file():
                return p
        except (OSError, ValueError):
            continue
    return f"{RAW_BASE}/{name}"


def table(name, source=None, **read_csv_kwargs):
    """Read one instance table as a DataFrame, local copy first.

    Raises with an explanation rather than a stack trace when neither a local
    copy nor the network is available -- Part 5: a cell that cannot get its data
    must say why.
    """
    global LAST_SOURCE
    where = resolve(name, source)

    if isinstance(where, Path):
        LAST_SOURCE = str(where)
        return pd.read_csv(where, **read_csv_kwargs)

    try:
        import requests
    except ImportError as exc:  # pragma: no cover - requests is a dependency
        raise RuntimeError(
            f"No local copy of {name} and `requests` is not installed, so the "
            f"published copy at {where} cannot be fetched."
        ) from exc

    try:
        # requests carries certifi's CA bundle. urllib -- which pandas would use
        # if handed the URL directly -- uses the SYSTEM store, and that fails on
        # hosts serving an incomplete chain. One of this repository's data
        # sources does exactly that.
        resp = requests.get(where, timeout=60)
        resp.raise_for_status()
    except Exception as exc:
        raise RuntimeError(
            f"Could not read the instance table {name!r}.\n"
            f"  No local copy was found, and fetching {where} failed:\n"
            f"    {type(exc).__name__}: {exc}\n\n"
            f"  If that is a 404, this repository is still private: a raw file "
            f"URL fails the same way a clone does.\n"
            f"  If it is a network error, clone the repository and run from "
            f"inside it, or set ESM_DATA to a directory holding the tables."
        ) from exc

    LAST_SOURCE = where
    return pd.read_csv(io.StringIO(resp.text), **read_csv_kwargs)
