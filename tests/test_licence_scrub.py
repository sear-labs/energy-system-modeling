# -*- coding: utf-8 -*-
"""Does the Gurobi licence scrubber actually remove the banner, and only it?

WHY THIS EXISTS

Gurobi prints a licence banner the first time an environment is created, and it
names the authoring machine's account:

    Set parameter Username
    Set parameter LicenseID to value 2750151
    Academic license - for non-commercial use only - expires 2026-12-04

Five notebooks had that in their outputs after the first executed run. It was
never committed -- `tools/check_notebooks.py` caught it first -- but it was one
commit away, and it would have shipped in every notebook that solves.

A licence id is not a secret the way a WLS secret is. It is still an account
identifier, it is meaningless to a reader, and it expires on a fixed date, so it
has no business in a committed output.

WHY A TEST AND NOT JUST THE SCRUBBER

Part 6: "A guard that has only ever passed is indistinguishable from one that
cannot fail." The scrubber runs on every execution, and if a future edit broke
its regex, every run afterwards would look exactly as green as it does now while
publishing the id. This test feeds it the real banner and checks the id is gone.

The second half matters as much: a scrubber that eats real output would silently
delete results. So it is also checked against lines it must NOT touch --
including "Set parameter Threads", which starts identically to the lines it does
remove.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from execute_notebooks import LICENCE_LINE_RE, scrub_licence  # noqa: E402

LICENCE_ID = "2750151"

BANNER = (
    "Set parameter Username\n"
    "Set parameter LicenseID to value 2750151\n"
    "Academic license - for non-commercial use only - expires 2026-12-04\n"
)

MUST_GO = [
    "Set parameter Username",
    "Set parameter LicenseID to value 2750151",
    "Academic license - for non-commercial use only - expires 2026-12-04",
    "Restricted license - for non-production use only - expires 2026-11-24",
    "INFO:gurobipy:Set parameter LicenseID to value 2750151",
    "INFO:gurobipy:Academic license - for non-commercial use only - expires 2026-12-04",
    "Gurobi Optimizer version 13.0.2 build v13.0.2rc0 (win64 - Windows 11)",
]

# Real output that must survive. "Set parameter Threads" is the trap: it shares
# a prefix with the lines above, and losing it would silently delete a solver
# setting a reader is being taught to notice.
MUST_STAY = [
    "Set parameter Threads to value 4",
    "Set parameter MIPGap to value 0.0001",
    "Optimize a model with 3 rows, 2 columns and 4 nonzeros",
    "objective: $1,328.40",
    "  solar    40.0 MW",
    "Optimal objective  1.328400000e+03",
    "shadow price on balance: $22.14/MWh",
    "2920 snapshots at 3h, 2019-01-01 to 2019-12-31",
]


class FakeCell(dict):
    """Minimal stand-in for an nbformat cell: attribute access plus dict access."""

    def __init__(self, outputs):
        super().__init__(cell_type="code", outputs=outputs)

    @property
    def cell_type(self):
        return self["cell_type"]


class FakeNB:
    def __init__(self, cells):
        self.cells = cells


@pytest.mark.parametrize("line", MUST_GO)
def test_banner_lines_are_removed(line):
    assert LICENCE_LINE_RE.search(line), (
        f"the scrubber does not recognise {line!r} as a licence banner line"
    )


@pytest.mark.parametrize("line", MUST_STAY)
def test_real_output_is_untouched(line):
    assert not LICENCE_LINE_RE.search(line), (
        f"the scrubber would delete real output: {line!r}"
    )


def test_scrub_removes_the_id_from_a_stream_output():
    nb = FakeNB([FakeCell([{
        "output_type": "stream",
        "name": "stdout",
        "text": BANNER + "objective: $1,328.40\n",
    }])])
    n = scrub_licence(nb)
    text = nb.cells[0]["outputs"][0]["text"]
    assert n == 3, f"expected 3 banner lines removed, got {n}"
    assert LICENCE_ID not in text, "the licence id survived the scrub"
    assert "objective: $1,328.40" in text, "the scrub ate the actual result"


def test_scrub_removes_the_id_from_an_execute_result():
    nb = FakeNB([FakeCell([{
        "output_type": "execute_result",
        "data": {"text/plain": BANNER + "1328.4"},
    }])])
    scrub_licence(nb)
    text = nb.cells[0]["outputs"][0]["data"]["text/plain"]
    assert LICENCE_ID not in text
    assert "1328.4" in text


def test_scrub_is_idempotent():
    nb = FakeNB([FakeCell([{
        "output_type": "stream", "name": "stdout", "text": BANNER + "done\n",
    }])])
    scrub_licence(nb)
    first = nb.cells[0]["outputs"][0]["text"]
    assert scrub_licence(nb) == 0, "a second scrub found something to remove"
    assert nb.cells[0]["outputs"][0]["text"] == first


def test_no_committed_notebook_carries_the_banner():
    """The end-to-end claim: nothing in the repository names a licence id.

    This is the one that would fail if the scrubber were removed from the
    execution path rather than broken in itself.
    """
    import json

    root = Path(__file__).resolve().parents[1]
    offenders = []
    for p in sorted((root / "notebooks").rglob("*.ipynb")):
        if ".ipynb_checkpoints" in str(p):
            continue
        nb = json.loads(p.read_text(encoding="utf-8"))
        for cell in nb.get("cells", []):
            if cell.get("cell_type") != "code":
                continue
            for out in cell.get("outputs", []) or []:
                blob = "".join(out.get("text", "")) if "text" in out else ""
                data = out.get("data") or {}
                blob += "".join(data.get("text/plain", ""))
                if LICENCE_LINE_RE.search(blob):
                    offenders.append(p.relative_to(root).as_posix())
                    break
    assert not offenders, (
        "Gurobi licence banner found in committed outputs of: "
        + ", ".join(sorted(set(offenders)))
    )
