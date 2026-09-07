# -*- coding: utf-8 -*-
"""Execute every notebook and report, one row each, what happened.

Run it from the repository root:

    python tools/execute_notebooks.py                # all of them
    python tools/execute_notebooks.py p4_networks    # a substring filter
    python tools/execute_notebooks.py --inplace      # write the outputs back

WHY A SCRIPT RATHER THAN A COMMAND

`jupyter nbconvert --execute` reports the first exception and stops, which is
the right behaviour for one notebook and the wrong one for a diagnostic across
twelve: you fix one, re-run, and discover the next. This runs all of them,
keeps going, and prints a table -- so the whole shape of the problem is visible
in one pass.

WHAT IT DOES NOT DO

It does not write outputs unless `--inplace` is given. A half-executed notebook
that failed at cell 30 is worse than an unexecuted one, because its committed
outputs are then real for the top half and absent for the bottom, and nothing
in the file says where the line is.
"""
import argparse
import os
import re
import sys
import time
import traceback

import nbformat

# nbclient is imported INSIDE run_one, not here.
#
# Why: tests/test_licence_scrub.py imports this module for LICENCE_LINE_RE and
# scrub_licence, both of which are pure text processing. A top-level nbclient
# import made that test require a notebook-execution client it never uses, and
# CI -- which installs only the checking tools -- failed on
# `ModuleNotFoundError: No module named 'nbclient'` at collection time.
#
# That is the undeclared-dependency defect Part 6 names, caught by the clean
# machine on the first push. A module should not require an execution
# dependency to expose a regex.

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
NB_ROOT = os.path.join(ROOT, "notebooks")

KERNEL = "esm"
TIMEOUT = 900  # seconds per cell; the network-fetching notebooks are the slow ones


def find_notebooks(pattern=None):
    out = []
    for dirpath, _dirnames, filenames in os.walk(NB_ROOT):
        if ".ipynb_checkpoints" in dirpath:
            continue
        for fn in filenames:
            if not fn.endswith(".ipynb"):
                continue
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, ROOT).replace("\\", "/")
            if pattern and pattern not in rel:
                continue
            out.append((rel, p))
    return sorted(out)


# A deliberate blank is Part 5 working, not a failure: "Where the student must
# choose, 'run all' should not produce a bare NameError" -- so the notebook
# raises with an explanation instead. That still stops execution, which collides
# with Part 5's other rule, "ship it executed".
#
# The resolution: a notebook whose ONLY failure is a deliberate blank is shipped
# executed up to that cell, with the blank cell itself left clean. That is
# exactly the state a student opens it in -- everything before their work is
# done, their cell is empty -- and it is why the error output is stripped rather
# than committed.
# The wording varies between notebooks, so match the INTENT rather than one
# sentence. The first pattern below is the one that matters: "the notebook will
# not X for you" is the house phrasing for a blank the student must fill.
#
# This was widened once already: it began as "this notebook will not choose for
# you" and missed "the notebook will not choose for you" in
# end_use_disaggregation -- one article's difference, reported as a hard
# failure. If it misses another, widen it here rather than editing a notebook to
# suit the regex.
DELIBERATE_BLANK_RE = re.compile(
    r"th(is|e) notebook will not \w+( it)? for you"
    r"|write your .{0,40} in the cell above"
    r"|(choose|uncomment) (exactly )?(one|ONE) of the",
    re.I,
)


def is_deliberate_blank(cell):
    for o in cell.get("outputs", []) or []:
        if o.get("output_type") != "error":
            continue
        text = (o.get("evalue", "") or "") + "\n".join(o.get("traceback", []) or [])
        if o.get("ename") == "NameError" and DELIBERATE_BLANK_RE.search(text):
            return True
    return False


# Gurobi prints a licence banner to stdout the first time an environment is
# created, and it names the machine's account:
#
#     Set parameter Username
#     Set parameter LicenseID to value 2750151
#     Academic license - for non-commercial use only - expires 2026-12-04
#
# Committing that publishes the authoring machine's licence id in every notebook
# that solves. It is not a secret the way a WLS secret is, but it identifies an
# account, it is meaningless to a reader, and it goes stale on a fixed date -- so
# it has no business in a committed output.
#
# This strips it on the way out. It is a GUARD, not the fix: the real fix is the
# silent `gp.Env` licence cell that teaching-code uses, which stops the banner
# being printed at all rather than deleting it afterwards. Until a notebook
# carries that cell, this keeps the id out of the repository.
LICENCE_LINE_RE = re.compile(
    r"^(INFO:gurobipy:)?(Set parameter (Username|LicenseID)"
    r"|Academic license|Restricted license|WLS license"
    r"|Gurobi Optimizer version).*$",
    re.M,
)


def scrub_licence(nb):
    """Remove Gurobi licence banner lines from every output. Returns a count."""
    removed = 0
    for cell in nb.cells:
        if cell.cell_type != "code":
            continue
        for out in cell.get("outputs", []) or []:
            for key in ("text",):
                if key in out and isinstance(out[key], str):
                    new, n = LICENCE_LINE_RE.subn("", out[key])
                    if n:
                        out[key] = re.sub(r"\n{3,}", "\n\n", new)
                        removed += n
            data = out.get("data")
            if isinstance(data, dict) and isinstance(data.get("text/plain"), str):
                new, n = LICENCE_LINE_RE.subn("", data["text/plain"])
                if n:
                    data["text/plain"] = re.sub(r"\n{3,}", "\n\n", new)
                    removed += n
    return removed


def run_one(path, inplace):
    """Execute one notebook. Returns (status, detail, seconds, n_cells)."""
    from nbclient import NotebookClient
    from nbclient.exceptions import CellExecutionError

    nb = nbformat.read(path, as_version=4)
    n_code = sum(1 for c in nb.cells if c.cell_type == "code")
    client = NotebookClient(
        nb,
        timeout=TIMEOUT,
        kernel_name=KERNEL,
        allow_errors=False,
        resources={"metadata": {"path": os.path.dirname(path)}},
    )
    t0 = time.time()
    try:
        client.execute()
    except CellExecutionError as e:
        dt = time.time() - t0
        # find the cell that actually failed, and the exception's own words
        idx, ename, evalue = None, "", ""
        for i, c in enumerate(nb.cells):
            for o in c.get("outputs", []) or []:
                if o.get("output_type") == "error":
                    idx, ename, evalue = i, o.get("ename", ""), o.get("evalue", "")
                    break
            if idx is not None:
                break
        if idx is not None and is_deliberate_blank(nb.cells[idx]):
            # strip the error so it is not committed, and leave every cell from
            # the blank onward unexecuted -- which is what a student opens
            nb.cells[idx]["outputs"] = []
            nb.cells[idx]["execution_count"] = None
            for c in nb.cells[idx + 1:]:
                if c.cell_type == "code":
                    c["outputs"] = []
                    c["execution_count"] = None
            scrubbed = scrub_licence(nb)
            if inplace:
                nbformat.write(nb, path)
            n_out = sum(1 for c in nb.cells
                        if c.cell_type == "code" and c.get("outputs"))
            return ("blank", f"deliberate blank at cell {idx}; "
                             f"{n_out}/{n_code} cells executed before it", dt, n_code)
        detail = f"cell {idx}: {ename}: {evalue}".strip()
        return "FAIL", detail[:300], dt, n_code
    except Exception as e:  # kernel death, timeout, anything else
        dt = time.time() - t0
        return "ERROR", f"{type(e).__name__}: {e}"[:300], dt, n_code
    dt = time.time() - t0
    scrubbed = scrub_licence(nb)
    if inplace:
        nbformat.write(nb, path)
    n_out = sum(1 for c in nb.cells if c.cell_type == "code" and c.get("outputs"))
    note = f", {scrubbed} licence line(s) scrubbed" if scrubbed else ""
    return "ok", f"{n_out}/{n_code} code cells produced output{note}", dt, n_code


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pattern", nargs="?", default=None)
    ap.add_argument("--inplace", action="store_true",
                    help="write executed outputs back into the notebooks")
    args = ap.parse_args()

    nbs = find_notebooks(args.pattern)
    if not nbs:
        print("no notebooks matched")
        return 1

    print(f"executing {len(nbs)} notebook(s) on kernel {KERNEL!r}, "
          f"{'WRITING OUTPUTS' if args.inplace else 'dry run, outputs discarded'}\n")
    rows = []
    for rel, path in nbs:
        print(f"  ... {rel}", flush=True)
        status, detail, dt, n = run_one(path, args.inplace)
        rows.append((status, rel, dt, detail))
        print(f"      {status:5} {dt:6.1f}s  {detail}", flush=True)

    print("\n" + "=" * 100)
    ok = sum(1 for r in rows if r[0] in ("ok", "blank"))
    print(f"{ok}/{len(rows)} executed clean\n")
    for status, rel, dt, detail in rows:
        print(f"{status:5} {dt:6.1f}s  {rel:52} {detail[:60]}")
    return 0 if ok == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
