# Energy System Modeling — companion code

> **The rules are not in this file.** Everything portable — archetypes, naming, the teaching
> standard, the engineering/teaching boundary, verification, licensing, working alongside other
> sessions — lives in one document and is deliberately **not restated** here:
>
>     https://github.com/sear-labs/code-standard    canonical - the same from any machine
>     a local clone, if you have one                faster; check its branch, then git pull
>
> **Read it first and last.** First because it decides how the work is done; last because a change
> you are about to make may be one it already settles. A clone can be clean and still wrong: a
> working copy on a feature branch reads exactly like the standard while serving text nobody
> approved.
>
> Everything below this line is *Part 11 — this project specifically*.

---

# Part 11 — This project specifically

**Archetype A + T.** `src/esm/` will be Parts 1–2 territory; `notebooks/` is Part 3 territory;
Part 4 governs the boundary. Neither half gets to win on the other's territory.

**[ENERGY_SERIES_PLAN.md](ENERGY_SERIES_PLAN.md) is the specification** and outranks this file on
anything structural: the chapter mapping, the layout, the seven unwritten notebooks, the vendored
data licences, and the six-session sequence. This file holds the decisions the plan does not.

## The four axes, answered

Part 2c requires these answered before the first commit, because two of the four are expensive to
change afterwards — a remote cannot be un-published and a history cannot be un-recorded.

**How sensitive is it?** *May reach a public host.* Nothing here is sensitive: the notebooks teach
energy-system models on public and synthetic data. What is sensitive stayed in the course folder —
live exam banks, a Canvas quiz backup carrying full question content, an in-progress manuscript, and
anything about a student. None of it crossed, and `.gitignore` blocks each class by pattern with the
reason written beside it, verified with `git check-ignore` in **both** directions before the first
commit.

**Is it actively developed?** *Yes, heavily* — five of six planned sessions remain. So it wants git,
and sensitivity does not enter this decision: activity does.

**Is it in a syncing folder?** *No.* It sits at `dev/repo/teaching/`, outside OneDrive, so `.git`
lives in place and there is no pointer file and no `GIT-OWNER.md`. This is the reason the repository
was created here rather than beside its source: the course folder is inside OneDrive and needs the
separated-gitdir treatment, and this one does not.

**How many devices edit it?** *One writer at a time, with GitHub as the sync.* Other machines clone
from the remote rather than sharing a worktree, so the single-writer constraint that the pointer
treatment imposes does not apply here.

## Fresh history, and why filtering was not an option

The source is a private course folder with 51 commits, and the exams and the manuscript are **in
those commits**. Filtering the working tree would have left both in history, and git history is
permanent. So this repository was started with `git init` and a verified copy of 25 files — never a
clone, a filter or a push of that folder.

**The course folder keeps its own copy of everything that crossed.** This is not a move. If a
builder here is repointed or a notebook renamed, the course folder's copy does not follow, and the
two will drift. That is accepted for now — the course is being taught from that folder this term —
and it is resolved when the course starts teaching from this repository instead.

## What is deliberately absent, so nobody reports it as damage

- **No `M0_Toy_LP_to_PyPSA`, and no `build_toy_lp_notebook.py`.** That notebook is already published,
  executed and verified, as `teaching-code` notebook 12. The plan gives it a README pointer in
  `p1_foundations/` rather than a slot, which is the series/topic-library boundary working: the
  method library teaches the method, the series carries the case. Copying it here would create a
  second copy with nothing comparing them.
- **No deck builders.** `build_m0.py` through `build_m4.py` and `build_m5_deck.py` build PowerPoint,
  not notebooks, and pull in six local helpers (`searkit`, `deckmerge`, `restyle`, `reductions`,
  `band_trims`, `fitpass`). Only `build_m5_notebook.py` from that name family is a notebook builder.
  `check_builders.py` globs `build_*notebook*.py`, which is the same distinction, arrived at
  independently.
- **No `src/esm`, and therefore no agreement assertion in any notebook.** Twelve notebooks build
  models by hand with nothing to check them against. That is Part 4's whole mechanism missing, and
  it is session 3's work. `tools/check_notebooks.py` reports it per notebook rather than letting it
  pass quietly.
- **No outputs after a deliberate blank.** Two notebooks stop where the student must choose, and
  they are committed executed up to exactly that cell. That is the state a student opens them in,
  not an interrupted run.

## The builders still point at the folder they came from

Every `tools/builders/build_*.py` computes its output path as
`ROOT/"2026 Fall"/"Notebooks"/<old name>.ipynb`, and `tools/check_builders.py` looks for notebooks
there too. **Their output paths have not been repaired**, so a builder run today writes into a
directory that does not exist here. Session 3 repoints them, along with the notebook renames.

**Their CONTENT is patched in step with the notebooks, and that is not optional.** Four notebooks
were edited here and all four builders were edited identically in the same commit — the rule exists
because on 2 September seven of twelve builders had silently drifted from their own artifacts, and
every notebook looked correct while every one of them would have lost its change on the next
rebuild.

Two things are deliberately *not* in the builders: the Colab badge, because it contains a path that
changes when a notebook moves, and the executed outputs, because a builder emits source. Both have
an idempotent tool, and `tools/builders/README.md` gives the three-command sequence to run after any
rebuild.

## BLOCKING, before this repository goes public: seven notebooks are assignments

**Seven of the twelve share a name and a subject with a graded assignment** in
`2026 Fall/Assignments/`, and one of the assignment specs names its notebook
outright — SB6-SPEC reads *"Companion notebook:
SB6_Multi_City_Texas_Buildout.ipynb · Submit one PDF plus your notebook."*

Publishing a fully executed notebook is therefore, for some of these, publishing
a completed submission. Jones's rule, 2026-09-07: *"there are assignments in the
class and I shouldn't do those assignments for the students and put that on the
public repo."*

| notebook | assignment | asks for the student's own instance | stops at a blank |
|---|---|---|---|
| `end_use_disaggregation` | 1N | yes | **yes** — cell 51 |
| `one_house_balance` | SB1-SPEC | yes | no |
| `representative_days` | SB2 | yes | no |
| `capital_and_lcoe` | SB3 | yes | no |
| `texas_multi_city_buildout` | SB6-SPEC | yes | no |
| `model_diversity` | GRAD-M | yes | no |
| `real_network_import` | GRAD-N | yes | no |
| `facility_decision` | *(not an assignment)* | — | **yes** — cell 66 |

**This is a teaching judgement per notebook and it is Jones's, not a session's.**
Two of them are described in the course's own `CLAUDE.md` as deliberate worked
examples — SB1 and SB3 are named there as "the two rebuilt examples" — so being
fully worked is the point for those. The others have not been ruled on.

**The remedy already exists in this repository and needs no invention.** Part 5's
deliberate blank is exactly the device: `end_use_disaggregation` and
`facility_decision` each raise with an explanation at the point where the
student's own work begins, and `tools/execute_notebooks.py` ships them executed
up to that cell with the blank clean. Extending that pattern is the fix wherever
a notebook currently works a student's instance through to the answer.

> **Do not flip this repository to public until that triage is done.** It is the
> one remaining decision that is expensive to reverse: a public commit is public,
> and retiring an assignment costs the course a piece of assessment.

## Where an instance table comes from, decided once

**`esm.data.table(name)` is the only way a notebook or the package should read a
table.** Resolution order, and local wins:

    explicit source -> $ESM_DATA -> data/raw beside the package
                    -> data/raw under the cwd -> the published raw URL

**Local winning is not a preference, it is what Part 4 rests on.** A reader is
told to edit `data/raw/` and re-run, and the agreement assertion is supposed to
stay green because both halves picked up the edit. If the URL ever won, the edit
would do nothing, silently, and the notebook would keep reporting the numbers on
the published branch. `tests/test_data_loader.py` pins that case specifically.

### Why not vendor the CSVs into the package

That is `advopt-lithiumsc`'s answer — a second copy under `src/lithium/data/`
with a test asserting it has not drifted from `data/raw/`. It works, and it is
two copies of every table plus a guard to watch them. The URL fallback needs
neither: one copy, on the published branch.

The reason either is needed at all is that **`pip install git+https://…` ships
the package and not `data/`** — a data directory at the repo root is not package
data and never enters the wheel. The standard's Part 6 records that shipping in
three published repositories.

### What this does NOT buy

**It does not get round the repository being private.** Measured 2026-09-07: a
raw `raw.githubusercontent.com` URL on this repository returns **404**, exactly
as `git clone` fails on it. Public is the prerequisite for a student running any
of this, and no data-loading trick changes that.

**`DATA_REF` must become a release tag before a link is handed to students.** It
is `main` during development, and `main` moves — a notebook fetching `main`
would silently change its answer when someone edited a table, which is "every
number in the prose comes from a run" failing from the outside in. Part 1 rule 8:
tag what you hand out.

> **This question is not local to this repository.** Three repositories in the
> organisation have solved it three different ways. If the pattern here holds
> through session 4, it is worth petitioning Part 4 of the standard rather than
> leaving each project to rediscover it.

## The one that keeps going wrong

**Where an optimum is not unique, the check compares what every optimum shares, and the prose
teaches the tie. It never compares the solver's path.** Every serious finding in both reviews of
`teaching-code` was this same defect wearing different clothes — an assertion that held because the
solver is deterministic rather than because the answer is unique. The models here are larger
networks than anything in that library, so ties and degenerate duals are *more* likely, not less.

A related trap, already visible in the material: `texas_multi_city_buildout` asserts agreement to
`1e-9` on a network solve. A tolerance is two claims at once — about the implementations, and about
whether the computation is precise enough for the first claim to be testable. Solve at least as
tightly as you assert, or the check is testing determinism rather than equivalence.

## Environment

PyPSA 1.3 needs pandas 3, which the Anaconda base environment does not have, so this repository
has its own environment and its own kernel rather than a `PYTHONPATH`.

    python -m venv C:/Users/jonesec/dev/venvs/esm      # SHORT path: long-path limits bite
    C:/Users/jonesec/dev/venvs/esm/Scripts/pip install -r requirements.txt
    C:/Users/jonesec/dev/venvs/esm/Scripts/python -m ipykernel install --user --name esm \
        --display-name "Python (esm: pypsa)"

`requirements.txt` carries the ranges and `requirements-lock.txt` the resolved list that actually
produced the committed outputs — Python 3.13.9, PyPSA 1.3.0, pandas 3.0.5. Part 1 rule 3 wants
both: a range says what will install, only the lock says what ran.

**Do not use the `orteach-energy` kernel for this repository.** It works, and it lives under
`AppData/Local/Temp`, which is not a durable location — it belongs to `teaching-code` and may
vanish. `esm` is this repository's.

    python tools/execute_notebooks.py            # dry run, reports what breaks
    python tools/execute_notebooks.py --inplace  # and commits the outputs

### The solver is the thing that breaks for students, not for you

There is a full academic Gurobi licence on this machine, expiring 2026-12-04. **A student has
neither that nor a WLS key**, so what they get from `pip install gurobipy` is the restricted
licence: **2,000 variables and 2,000 constraints**. Two notebooks are past it and both now default
to HiGHS for that reason, which costs nothing — `texas_multi_city_buildout` measured HiGHS and
Gurobi agreeing to sixteen significant figures on every model it builds.

    model_boundary            312 variables    fits
    model_diversity           426              fits
    facility_decision         312              fits
    texas_multi_city_buildout 2,613            OVER  -> defaults to HiGHS
    real_network_import       16,080           OVER  -> defaults to HiGHS

**This class of defect cannot be found by running the notebooks here.** Three of them defaulted to
Gurobi and never installed `gurobipy`; they passed locally because this machine has it. That is
what CI on a clean machine is for, and why `.github/workflows/checks.yml` exists.

The `WLS = {}` placeholder carries no key and must never be filled in in a committed file. The
Gurobi WLS key in the older course copies has **not** been rotated — do not reuse any key found
there.

## Conventions inherited from `teaching-code`, to apply as notebooks are brought up

Named here so session 3 does not re-derive them; the standard is the authority for why.

- One setup cell in every notebook, and one licence cell in every notebook that solves. Patch them
  everywhere or nowhere.
- Tolerances named in one module and nowhere else; every hand-built model applies them.
- Tables live in `data/raw/` and both sides read them. A knob the prose names is passed to the
  package, not typed twice.
- Alt text is written in the same cell as the plot, at the moment the plot is written — not added
  before shipping. Accessibility is a Title II obligation with a date on it, not a courtesy.
- The commit message carries the defect record: which source was wrong, and what the notebook does
  now.
