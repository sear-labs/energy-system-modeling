# Energy System Modeling — companion code

The companion notebooks for **[*Introduction to Energy System Modeling*](https://uta.pressbooks.pub/energysystemmodeling)**
by Erick C. Jones, Jr. — the CC BY open textbook — and the code taught from it in
REE 4301 / IE 5300 / IE 6301 at UT Arlington.

**The book is the spine, not the semester.** Notebooks are named and filed for the
part and subject they serve, never for a course code or a term. `M0`, `SB6` and
`2026 Fall` name one delivery of a course; `power_flow_and_lmp` names a subject
that outlives it.

---

## Status: every notebook runs; the package does not exist yet

Read this before you trust a number in any notebook.

| | |
|---|---|
| notebooks present | 12 of the 19 the plan describes |
| **executed, committed with outputs** | **all 12** |
| run clean end to end | 10 |
| stop at a deliberate blank, by design | 2 — `facility_decision` and `end_use_disaggregation` |
| Colab badge | all 12, resolving once this repository is public |
| **agreement assertions against the package** | **none — there is no package yet** |
| `src/esm/` | not written; session 3 builds it |
| `data/raw/`, `data/vendor/` | empty; sessions 3 and 5 fill them |

**What "runs" does and does not mean here.** Every notebook executes top to
bottom on a clean kernel and its committed outputs came from that run. That is
Part 5's *ship it executed*, and it is real. What is **not** yet true is Part 4:
no notebook checks itself against a package, because there is no package. Twelve
notebooks build models by hand with nothing comparing them to a second
implementation. `python tools/check_notebooks.py` prints that per notebook rather
than letting it pass quietly, along with the rest of the audit.

**Two notebooks stop partway on purpose.** Where the student must choose,
Part 5 says "run all" should not produce a bare `NameError` — so they raise with
an explanation instead. They are committed executed up to exactly that cell, with
the student's cell clean. That is the state you open them in, not an interrupted
run.

### What was found by running them, and fixed

The notebooks arrived from a private course folder byte for byte and had never
been executed. Ten of the twelve ran clean on the first attempt. The rest is the
gap between "runs here" and "runs for a student", which is the gap that matters:

- **Three could never have run on Colab.** They default to Gurobi, their own
  prose says `pip install gurobipy`, and their install cell installed everything
  except gurobipy. They passed locally because the authoring machine has it —
  the "works on my laptop" failure exactly. Fixed.
- **One defaulted to a solver its own table says cannot solve it.**
  `texas_multi_city_buildout` printed a size table marking two of its three
  stages "too big" for Gurobi's free 2,000-variable licence, then defaulted to
  Gurobi. It now defaults to HiGHS, which the notebook had already measured as
  agreeing to sixteen significant figures.
- **One download was never going to work**, for two reasons at once: pandas reads
  URLs through the system certificate store and that host serves an incomplete
  chain, and the source is an unlicensed personal share link that is due to be
  replaced anyway. The fetch is fixed; the source is not, and
  [`data/vendor/README.md`](data/vendor/README.md) says so.
- **A Gurobi licence id was in five notebooks' outputs.** Never committed — the
  audit caught it first — and now scrubbed on every run and guarded by a test.

**[ENERGY_SERIES_PLAN.md](ENERGY_SERIES_PLAN.md) is the specification** — the
chapter mapping, the layout, the seven notebooks still to write, the vendored-data
licences, and the six-session sequence that gets from here to finished. Read it
before changing anything structural. Sessions 1 and 2 are done; session 3 writes
the package.

### The Colab badges resolve only once this repository is public

Every notebook carries one, and `README.md` lists them all in the table below.
They point at `github.com/sear-labs/energy-system-modeling`, which is **private**,
so today they 404 for anyone who clicks them. Making the repository public is the
single switch that turns all twelve on.

They were added now rather than later because adding twelve at once and missing
one is the likelier mistake; `python tools/add_colab_badges.py --check` fails if
any badge, or the table below, points at a path that has moved.

What a student gets when they click is not yet the whole of Part 5's *one click,
no install*. Each notebook installs its own dependencies in its first cell, and
ten of the twelve then run end to end. What is missing is the package: session 3
writes `src/esm/` and the clone-or-`../../src` setup cell that reaches it.

---

## The mapping table

Twenty-two chapters, five case studies, one appendix. **The only place chapter
numbers appear.** Folders are named for part and subject because Part IV expanded
from four chapters to six on 1 September, shifting every chapter from 14 up by
two — chapter-numbered folders would have meant renaming ten directories and
breaking every link into them for an edit that changed no subject matter. Parts
have been stable across the expansion; chapter numbers have not.

Section numbers are the chapter's own, from the manuscript.

| ch | the section that wants it | companion |
|---|---|---|
| 1 | §1.4 Choosing the Boundary | `model_boundary` (motivating exception) |
| 2 | §2.2 Visualizing the System: Energy Balances | `one_house_balance` |
| 3 | §3.3 Temporal and Spatial Linking; §3.4 The Same Price, From Both Sides | → teaching-code 12; forward-refs `representative_days`, `model_boundary` |
| 4 | §4.6 Reference Models: 1-Node and 3-Node | → teaching-code 12 |
| 5 | §5.3 Grounding Models in Grid Data | `representative_days` |
| 6 | §6.2 Smart Meters, Time Series, Appliance Signatures (NILM) | `end_use_disaggregation` |
| 7 | §7.2 Process Heat: Low, Medium, High Grade | `process_heat_electrification` NEW |
| 8 | §8.2 Charging Infrastructure and Policy | `depot_charging` NEW |
| 9 | §9.1 Core Generation Metrics | `capital_and_lcoe` |
| 10–12 | the three technology surveys | `screening_curves` NEW |
| 13 | §13.2–13.3 Moving Electrons, Molecules and Solids | `cost_of_transit_by_mode` NEW |
| 14 | §14.4 The Voltage Band and Hosting Capacity | `feeder_hosting_capacity` NEW |
| 15 | §15.2 The Weymouth Relation; §15.5 Winter Storm Uri | `pipeline_pressure_and_n1` NEW; `real_network_import` |
| 16 | §16.1 The Cost of Distance | `cost_of_transit_by_mode` NEW |
| 17 | §17.2 The LP Formulation; §17.4 Expansion Trade Study | `pipeline_transport` |
| 18 | §18.3 Congestion and LMP | `power_flow_and_lmp` |
| 18 | §18.1 The Rail Constraint: Discrete vs Continuous | → teaching-code 05 |
| 19 | §19.4 State-of-Charge; §19.5 Does the Battery Pay for Itself | → teaching-code 12 |
| 20 | §20.2 The Storage Comparison | `storage_duration_sizing` NEW |
| 21 | §21.4 A Reference Build, in Tons | `material_requirements` |
| 22 | §22.1 The Transshipment Model | → teaching-code 13 |
| CS1 | §V Linear Programming Formulation | none yet |
| CS2 | §V Linear Programming Formulation | none yet |
| CS3 | Grid Evolution Data Benchmark | `screening_curves` supports it |
| CS4 | §II The LP Formulation; grad ext. DCOPF | `pipeline_transport`, `power_flow_and_lmp` |
| CS5 | §III The Transshipment Model | → teaching-code 13; `material_requirements` |
| App A | the four sector mini-projects integrated | `facility_decision`, `texas_multi_city_buildout` |

> **The manuscript is the source of truth, not the Pressbooks site.** The published
> book is the 1 September snapshot, two chapters behind. Re-check this table
> against the manuscript before trusting it, and expect the site to lag.

### Coverage: which chapters have a companion, and which do not

**A chapter does not need its own notebook.** Several notebooks are deliberately
one-to-many, and forcing a companion per chapter would produce twenty-two thin
ones instead of nineteen that each carry a method:

    screening_curves          chapters 10, 11 and 12, and Case Study 3 -- the three
                              technology surveys share one comparison
    cost_of_transit_by_mode   chapters 13 and 16 -- the modalities and their economics
                              are the same table read twice
    teaching-code 12          chapters 3, 4 and 19
    facility_decision +
      texas_multi_city_buildout   Appendix A, which is integration by design

Measured against the manuscript on 2026-09-07, with the chapter text read rather
than the titles:

| | chapters |
|---|---|
| **companion exists and runs** | 1, 2, 3, 4, 5, 6, 9, 17, 18, 19, 21, 22 — twelve |
| **companion exists, covers part of the chapter** | 15 — `real_network_import` is §15.5 Winter Storm Uri; §15.2 The Weymouth Relation has none |
| **specified, not yet written** | 7, 8, 10, 11, 12, 13, 14, 16, 20 — nine |

Case studies: **CS4** and **CS5** have companions; **CS3** waits on
`screening_curves`; **CS1** and **CS2** each carry their own "Section V — Linear
Programming Formulation" and are therefore genuine notebook openings, held back
pending one decision — the case studies ship with instructor solution keys, and
whether those keys are already public in the book decides whether a companion
notebook can be. **Appendix A** is covered.

So: **thirteen of twenty-two chapters have a companion today**, and the seven
unwritten notebooks close the remaining nine. Nothing in the book is uncovered
*by oversight* — every gap above is a notebook the plan already specifies.

One notebook maps to no chapter: `graduate/model_diversity`, which solves the
same system in a second tool. It is a method demonstration rather than a
chapter companion, and where it belongs is still open.

### Some chapters are served from the method library instead

An arrow to `teaching-code` above is not an omission. That library
([sear-labs/teaching-code](https://github.com/sear-labs/teaching-code)) is
organised by topic and teaches a *method* on a small self-contained instance;
this repository is a *series* and carries the method on a real one. Where the
method is already taught there, this repository points rather than copies.

| chapter | already at |
|---|---|
| 3 and 4 | `teaching-code` 12 — which **is** REE Module 0, executed and verified |
| 18, discrete flow | `teaching-code` 05, branch and bound |
| 19, battery and state of charge | `teaching-code` 12 |
| 22 and CS5, transshipment | `teaching-code` 13, REE Module 4's model |

---

## The notebooks

One click each, once the repository is public. Until then these resolve to a
404 — see *The Colab badges resolve only once this repository is public* above.

<!-- NOTEBOOK-TABLE:START - generated by tools/add_colab_badges.py -->

| Notebook | Title | |
|---|---|---|
| **`capstone/`** | | |
| `facility_decision.ipynb` | Should this site build on-site generation? | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sear-labs/energy-system-modeling/blob/main/notebooks/capstone/facility_decision.ipynb) |
| `texas_multi_city_buildout.ipynb` | A multi-city Texas capacity buildout | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sear-labs/energy-system-modeling/blob/main/notebooks/capstone/texas_multi_city_buildout.ipynb) |
| **`graduate/`** | | |
| `model_diversity.ipynb` | Model diversity: the same system in a second tool | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sear-labs/energy-system-modeling/blob/main/notebooks/graduate/model_diversity.ipynb) |
| **`p1_foundations/`** | | |
| `model_boundary.ipynb` | Where do you draw the boundary? | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sear-labs/energy-system-modeling/blob/main/notebooks/p1_foundations/model_boundary.ipynb) |
| `one_house_balance.ipynb` | An energy balance for one house | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sear-labs/energy-system-modeling/blob/main/notebooks/p1_foundations/one_house_balance.ipynb) |
| **`p2_demand/`** | | |
| `end_use_disaggregation.ipynb` | One-node disaggregation and demand-side technologies | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sear-labs/energy-system-modeling/blob/main/notebooks/p2_demand/end_use_disaggregation.ipynb) |
| `representative_days.ipynb` | From a smart meter to three representative days | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sear-labs/energy-system-modeling/blob/main/notebooks/p2_demand/representative_days.ipynb) |
| **`p3_generation/`** | | |
| `capital_and_lcoe.ipynb` | What does it cost to build a power plant? | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sear-labs/energy-system-modeling/blob/main/notebooks/p3_generation/capital_and_lcoe.ipynb) |
| **`p4_networks/`** | | |
| `pipeline_transport.ipynb` | Energy transportation and network optimization | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sear-labs/energy-system-modeling/blob/main/notebooks/p4_networks/pipeline_transport.ipynb) |
| `power_flow_and_lmp.ipynb` | Power flow and locational marginal pricing | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sear-labs/energy-system-modeling/blob/main/notebooks/p4_networks/power_flow_and_lmp.ipynb) |
| `real_network_import.ipynb` | Real network import: TX-123BT, then TAMU ACTIVSg | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sear-labs/energy-system-modeling/blob/main/notebooks/p4_networks/real_network_import.ipynb) |
| **`p5_storage_supply/`** | | |
| `material_requirements.ipynb` | Supply chains: sourcing and material reality | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sear-labs/energy-system-modeling/blob/main/notebooks/p5_storage_supply/material_requirements.ipynb) |

<!-- NOTEBOOK-TABLE:END -->

## Layout

```
src/esm/                  the package                        (session 3)
data/raw/                 authored instance tables, both sides read them
data/vendor/              third-party data, one sidecar per file
notebooks/
  p1_foundations/         model_boundary
                          one_house_balance
  p2_demand/              representative_days
                          end_use_disaggregation
  p3_generation/          capital_and_lcoe
  p4_networks/            pipeline_transport
                          power_flow_and_lmp
                          real_network_import
  p5_storage_supply/      material_requirements
  capstone/               texas_multi_city_buildout
                          facility_decision
  graduate/               model_diversity
tests/                    (session 3)
tools/                    check_builders.py
tools/builders/           the twelve notebook generators
```

Seven more notebooks are specified in the plan and not yet written:
`process_heat_electrification`, `depot_charging`, `screening_curves`,
`cost_of_transit_by_mode`, `feeder_hosting_capacity`, `pipeline_pressure_and_n1`,
`storage_duration_sizing`.

## Where the notebooks came from, and what was left behind

Fresh history, deliberately — **not** a filter or a push of the course folder's
51 commits, measured 2026-09-06. That folder tracks live exam banks in text and QTI form, a Canvas
backup carrying full quiz question content, and 94 files of an in-progress
manuscript. Git history is permanent, so filtering a working tree would not have
helped: the material is in the commits. Nothing but the notebooks and their
generators crossed, and `.gitignore` states each exclusion with its reason beside
it rather than relying on the copy having been careful.

Verified before the first commit, on the copied tree rather than on the source:
25 files, all byte-identical to their originals; only `.py` and `.ipynb` present;
no exam, rubric, Canvas, manuscript or student content; and every Gurobi mention
is the same empty `WLS = {}` placeholder, carrying no key.

## Running it yourself

**On Colab, click a badge** — once this repository is public. Each notebook
installs what it needs in its first cell.

**Locally**, the notebooks need PyPSA, which needs pandas 3, so they get their own
environment and their own kernel rather than a `PYTHONPATH`:

```bash
python -m venv ~/dev/venvs/esm
~/dev/venvs/esm/Scripts/pip install -r requirements.txt
~/dev/venvs/esm/Scripts/python -m ipykernel install --user --name esm --display-name "Python (esm: pypsa)"
```

`requirements.txt` is what the code tolerates; `requirements-lock.txt` is what
actually produced the committed outputs — Python 3.13.9, PyPSA 1.3.0, pandas
3.0.5. Part 1 rule 3 wants both, because a range says what will install and only
the lock says what ran.

Then, from the repository root:

```bash
python tools/execute_notebooks.py             # dry run: what breaks, one row each
python tools/execute_notebooks.py --inplace   # and write the outputs back
python tools/check_notebooks.py               # the audit matrix
python tools/add_colab_badges.py --check      # every badge points at a real path
python -m pytest tests/ -q                    # the ignore rules and the licence scrubber
```

**No solver licence is needed.** HiGHS is free, uncapped, and is what the two
largest notebooks default to. Gurobi's pip wheel adds a 2,000-variable
restricted licence that the smaller models fit inside; nothing here requires it.

There is no `run_all.py` yet, because there is no package for it to call. That
arrives with `src/esm/` in session 3.

## Licences

Code is MIT; prose, notebooks and figures are CC BY 4.0, matching the book;
authored tables are CC0; vendored data keeps its own licence. **Stated by path in
[LICENSE-DATA](LICENSE-DATA)**, which is the authority — `LICENSE` covers the code
alone.

## How to cite

No DOI yet: it is minted against the first tagged release, and there has not been
one. [CITATION.cff](CITATION.cff) carries the citation metadata in the meantime
and gets the concept DOI added once Zenodo issues it.

```bibtex
@software{jones_energy_system_modeling,
  author  = {Jones, Jr., Erick C.},
  title   = {Energy System Modeling: companion code},
  year    = {2026},
  url     = {https://github.com/sear-labs/energy-system-modeling}
}
```

To cite the book itself rather than the code, cite the book.
