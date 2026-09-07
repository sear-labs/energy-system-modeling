# -*- coding: utf-8 -*-
"""check_builders.py - does every notebook builder still reproduce its notebook?

WHY THIS EXISTS
CLAUDE.md section 4 says `Tools/build_*.py` are the source of truth and that a
notebook edited directly must have its builder patched too, "or the next
rebuild silently reverts the change". Nothing enforced that. On 2 Sep 2026
seven of twelve builders had drifted from their own artefacts: a facility
question had been added to each notebook as a bare string rather than an
`L(...)`, so the notebooks on disk carried a trailing newline their builders
did not emit. Every notebook looked correct. Every one of them would have lost
its closing coda - run into `### Sources` on the same line - the next time
anyone ran its builder.

That failure is invisible by construction: the artefact is right, the
generator is wrong, and nothing compares them. This script compares them.

HOW IT WORKS, AND WHY IT IS SAFE
For each builder: snapshot every notebook's bytes, run the builder, see which
notebook changed and whether its content differs from the snapshot, then
restore every notebook from the snapshot before moving on. The restore is from
an in-memory copy rather than from git, so it works on a dirty tree and does
not depend on anything being committed. A builder that writes nothing, or
writes something identical, is in sync.

The tree is left exactly as it was found, whether the check passes or fails.

Run from Tools/:  python check_builders.py
Exit status is 1 if any builder has drifted, so it can gate a commit.
"""
import glob
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
NB_DIR = os.path.join(ROOT, "2026 Fall", "Notebooks")

# Builders that generate a notebook. Anything else in Tools/ is out of scope.
SKIP = {"check_builders.py"}


def notebook_builders():
    out = []
    for p in sorted(glob.glob(os.path.join(HERE, "build_*notebook*.py"))):
        if os.path.basename(p) not in SKIP:
            out.append(p)
    return out


def snapshot():
    """Every notebook's exact bytes, so a restore does not depend on git."""
    return {p: io.open(p, "rb").read()
            for p in glob.glob(os.path.join(NB_DIR, "*.ipynb"))}


def restore(snap):
    for p, data in snap.items():
        if io.open(p, "rb").read() != data:
            io.open(p, "wb").write(data)


def main():
    builders = notebook_builders()
    if not builders:
        raise SystemExit("no notebook builders found in %s" % HERE)

    print("checking %d notebook builder(s) against their artefacts\n"
          % len(builders))
    drifted = []

    for b in builders:
        name = os.path.basename(b)
        snap = snapshot()
        r = subprocess.run([sys.executable, b], cwd=HERE,
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0:
            restore(snap)
            print("  %-34s BUILDER FAILED (exit %d)" % (name, r.returncode))
            drifted.append((name, "builder failed to run"))
            continue

        changed = []
        for p in sorted(set(snap) | set(glob.glob(
                os.path.join(NB_DIR, "*.ipynb")))):
            after = io.open(p, "rb").read() if os.path.exists(p) else None
            if snap.get(p) != after:
                changed.append(os.path.basename(p))
        restore(snap)

        if changed:
            print("  %-34s DRIFTED -> %s" % (name, ", ".join(changed)))
            drifted.extend((name, c) for c in changed)
        else:
            print("  %-34s ok" % name)

    print()
    if drifted:
        print("%d builder/notebook pair(s) out of sync." % len(drifted))
        print("The notebook on disk is NOT what its builder produces, so the")
        print("next rebuild will silently change it. Patch the builder to")
        print("match the notebook (CLAUDE.md section 4), not the other way")
        print("round - the notebook is the version that was reviewed.")
        return 1

    print("all builders reproduce their notebooks exactly.")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
