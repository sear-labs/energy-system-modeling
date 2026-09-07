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
- **No executed outputs.** Nothing here has been run. Part 5 says *ship it executed*, and this
  repository does not yet satisfy it; the README says so at the top rather than leaving a reader to
  discover it.

## The builders still point at the folder they came from

Every `tools/builders/build_*.py` computes its output path as
`ROOT/"2026 Fall"/"Notebooks"/<old name>.ipynb`, and `tools/check_builders.py` looks for notebooks
there too. **They were copied verbatim and not repaired**, so that the scaffold commit is a move and
nothing else, and so the diagnostic pass measures the builders as they actually are rather than as
this session left them. Session 3 repoints them, which is also where the notebook renames get
reflected. Until then a builder run writes into a path that does not exist here.

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

PyPSA 1.3 needs pandas 3, which the Anaconda base environment does not have. A working kernel
already exists on this machine as `orteach-energy` (PyPSA 1.3.0, linopy 0.9.1, highspy, gurobipy
13.0.3) — but **it lives under `AppData/Local/Temp`**, which is not a durable location. Session 2
builds this repository its own named kernel and records how; do not depend on the Temp one.

There is a full academic Gurobi licence on this machine (expires 2026-12-04). Students have neither
that nor the WLS trio, so **HiGHS is the path that must work without a licence**, and the free-tier
switch belongs on by default. The `WLS = {}` placeholder in the notebooks carries no key and must
never be filled in in a committed file. The Gurobi WLS key in the older course copies has **not**
been rotated — do not reuse any key found there.

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
