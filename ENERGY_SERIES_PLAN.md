# The energy-system series: layout plan

The companion code for **Introduction to Energy System Modeling** by Erick C. Jones Jr., the CC BY
open textbook. Written 2026-09-06 against the manuscript, then checked against the chapter text.
**Moved into the repository it describes on 2026-09-07**, from `teaching-code`, where it was
written while that repository did not yet exist. Sessions 2-6 below are run from here.

> **The manuscript is the source of truth, not the Pressbooks site.** The published book at
> <https://uta.pressbooks.pub/energysystemmodeling> is the **1 September snapshot**, two chapters
> behind. Verified: the online contents match `CARES Book/Archive/2026-09-01 pre-Part-IV-expansion/`
> heading for heading. Build any mapping against `CARES Book/Manuscript/` and re-check when it moves.

**The book is the spine, not the semester.** Course codes (`M0`, `SB6`, `GRAD_N`) and term folders
(`2026 Fall`) name a delivery of the course rather than the subject.

---

## Two corrections this plan already absorbed

**Folders are not named for chapter numbers.** Part IV expanded from four chapters to six on
1 September, shifting every chapter from 14 up by two. Chapter-numbered folders would have meant
renaming ten directories and breaking every link into them for an edit that changed no subject
matter. Folders are named for their part and subject; **chapter numbers live in one mapping table
and nowhere else.** Parts have been stable across the expansion; chapter numbers have not.

**The map was then checked against the chapter text, not the titles**, and that check moved four
things. It is recorded below because a mapping built from titles looks finished and is not.

## Identity

| | |
|---|---|
| repository | `sear-labs/energy-system-modeling`, **private for now** (Jones, 2026-09-07); public when the notebooks are executed |
| package | `esm`, imported from `src/` by path, as `orteach` is here |
| code licence | MIT, matching `advopt-lithiumsc` and `code-standard` |
| prose licence | CC BY 4.0 on notebooks and text, matching the book |
| archetype | A + T: Parts 1–2 govern `src/`, Part 3 governs `notebooks/`, Part 4 the boundary |

## Layout

```
src/esm/                  the package
data/raw/                 authored instance tables, both sides read them
data/vendor/              third-party data, one sidecar per file
notebooks/
  p1_foundations/         model_boundary.ipynb
                          one_house_balance.ipynb
                          README.md  -> teaching-code 12 for the toy LP and PyPSA
  p2_demand/              representative_days.ipynb
                          end_use_disaggregation.ipynb
                          process_heat_electrification.ipynb          NEW
                          depot_charging.ipynb                        NEW
  p3_generation/          capital_and_lcoe.ipynb
                          screening_curves.ipynb                      NEW
  p4_networks/            feeder_hosting_capacity.ipynb               NEW
                          pipeline_pressure_and_n1.ipynb              NEW
                          cost_of_transit_by_mode.ipynb               NEW
                          pipeline_transport.ipynb
                          power_flow_and_lmp.ipynb
                          real_network_import.ipynb
  p5_storage_supply/      storage_duration_sizing.ipynb               NEW
                          material_requirements.ipynb
                          README.md  -> teaching-code 12 battery, 13 transshipment
  capstone/               texas_multi_city_buildout.ipynb
                          facility_decision.ipynb
  graduate/               model_diversity.ipynb
tests/  tools/  tools/builders/
```

## The mapping table

Twenty-two chapters, five case studies, one appendix. The only place chapter numbers appear.
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
| CS1 | §V Linear Programming Formulation | none yet, see below |
| CS2 | §V Linear Programming Formulation | none yet, see below |
| CS3 | Grid Evolution Data Benchmark | `screening_curves` supports it |
| CS4 | §II The LP Formulation; grad ext. DCOPF | `pipeline_transport`, `power_flow_and_lmp` |
| CS5 | §III The Transshipment Model | → teaching-code 13; `material_requirements` |
| App A | the four sector mini-projects integrated | `facility_decision`, `texas_multi_city_buildout` |

## What the chapter-text check moved

1. **Case Study 4 is not the Texas buildout.** Its text is the Permian and Eagle Ford crude-routing
   problem with a DCOPF graduate extension, which is exactly what `pipeline_transport` and
   `power_flow_and_lmp` already are. Chapter 17 even names the same five nodes those notebooks code.
   The Texas multi-city buildout has no case study; it is capstone integration, and Appendix A
   describes precisely that role, so it moves to `capstone/` beside `facility_decision`.
2. **Case Studies 1 and 2 each carry a "Section V — Linear Programming Formulation."** They are not
   narrative exercises. Last draft dismissed CS2 as a scenario exercise; that was wrong. Both are
   genuine notebook openings, and CS1 is the transportation-demand case Chapter 8 needs.
3. **Chapter 3 has a claim on two notebooks it does not own.** Its learning objective is the
   representative-day abstraction and §3.4 is the price-from-both-sides argument, so it
   forward-references `representative_days` and `model_boundary` rather than anchoring them.
4. **Chapter 18 §18.1 is discrete rail flow**, which no energy notebook covers and
   `teaching-code` 05 already teaches as branch and bound. One more sideways pointer.

Also confirmed rather than assumed: §14.4 is literally "hosting capacity" and §15.2 is literally
"The Weymouth Relation", so both new notebooks proposed last turn match their chapters' own
sections. §15.1 is "What a Capacity Parameter Hides", the argument for splitting them from
`pipeline_transport`. And `real_network_import` loads day 46 of 2021, which is Winter Storm Uri,
the subject of §15.5.

## What does not move, because it is already published

| chapter | already at |
|---|---|
| 3 and 4 | `teaching-code` 12, which is REE Module 0 |
| 18, discrete flow | `teaching-code` 05, branch and bound |
| 19, battery and state of charge | `teaching-code` 12 |
| 22 and CS5, transshipment | `teaching-code` 13, REE Module 4's model |

This shrinks the Module 4 split to almost nothing: its sourcing LP is already notebook 13, so only
the material-intensity accounting moves across, as Chapter 21's companion.

## Placement rule

**Anchor at the last chapter whose material the notebook needs; forward-reference from the first
chapter that touches it.** A companion is only runnable once the reader has its prerequisites. One
deliberate exception: a notebook that raises the question the chapters then answer anchors at the
first chapter, as `model_boundary` does.

**Split when the halves have different methods and different prerequisites**, not merely because a
notebook touches two chapters.

## Vendored data

`data/vendor/`, never mixed with authored tables, one sidecar per file naming source URL, retrieval
date, licence and citation. **None of the current sources is MIT.**

| file | licence | note |
|---|---|---|
| TX-123BT, Lu and Li 2023 | CC BY 4.0 | DOI `10.6084/m9.figshare.22144616`, attribution required |
| PyPSA technology-data costs | **GPL-3.0** | keep its notice beside it, do not relicense |
| MATPOWER cases | BSD-3 in practice, no SPDX detected | confirm before vendoring |
| Open-Meteo archive | CC BY 4.0 under their terms | an API; cache a snapshot |
| TU Berlin cloud time series | **none stated** | replace, do not vendor |

## Seven new notebooks

**`screening_curves`, Ch 10–12.** Cost per MWh against capacity factor for gas, coal, nuclear, solar,
wind; the crossovers; the merit order falling out. No solver. The missing link between Chapter 9's
metrics and every capacity model later, and it supports Case Study 3's benchmark table.

**`cost_of_transit_by_mode`, Ch 13 and 16.** Dollars per MWh-mile for transmission, pipeline, LNG,
rail and truck, with energy density beside it. No solver. Gives Chapter 17's LP its motivation.

**`feeder_hosting_capacity`, Ch 14.** A radial feeder with load along it and rooftop solar added;
how much before voltage or transformer ratings bind. Matches §14.3 to §14.5 directly.

**`pipeline_pressure_and_n1`, Ch 15.** Flow follows the square root of a difference of squared
pressures. Model pressure as a variable, then remove a compressor. Shows what the capacity bound in
`pipeline_transport` hides, and the nonlinear relation needs lifting, so it reuses `teaching-code`
notebook 06 directly. The clearest case of the method library serving the case series.

**`depot_charging`, Ch 8.** A fleet returning at known times, a connection limit, a site demand
charge. The demand charge is a cost on the peak, needing an auxiliary variable bounding every hour.

**`process_heat_electrification`, Ch 7.** Boiler against heat pump against resistance at temperature,
with efficiency falling as the lift rises. §7.2's low, medium and high grade heat is the instance.

**`storage_duration_sizing`, Ch 20.** A multi-day wind lull sized twice, battery against hydrogen.
The power-versus-energy split, extending the battery already in notebook 12.

**Two more are now open, not proposed.** Case Studies 1 and 2 each carry an LP formulation and would
each take a notebook. They are held back pending one decision: the case studies ship with instructor
solution keys, and whether those keys are already public in the book decides whether a companion
notebook can be.

## A discipline the book already has

`Tools/build_figures.py` re-derives the merit-order dispatch and re-solves the battery, then
**asserts both against the notebooks' published output before drawing**, so a figure cannot drift
from the code a student runs. That is an agreement assertion in all but name. Move it across and
extend it to every figure.

---

# How to start

Six sessions. Each is a fresh chat with the prompt below pasted in. **Run them in order**; each
assumes the previous one landed. Where to run each is the first line of its prompt.

## 1. Scaffold - DONE 2026-09-07

> Landed as this repository's first commit. Three departures from the prompt below, each
> recorded where somebody will meet it:
>
> - **Twelve notebooks crossed, not thirteen.** `M0_Toy_LP_to_PyPSA` has no slot in the layout
>   above because `teaching-code` 12 *is* it, already executed and verified. The prompt's
>   "thirteen" and this plan's own layout disagreed; the layout won. See
>   `notebooks/p1_foundations/README.md`.
> - **The `build_m*.py` glob in the prompt is wrong.** `build_m0.py` through `build_m4.py` and
>   `build_m5_deck.py` build PowerPoint and pull in six local helpers. Only
>   `build_m5_notebook.py` is a notebook builder. Use `build_*notebook*.py`, which is what
>   `check_builders.py` itself globs. See `tools/builders/README.md`.
> - **Private, not public.** Jones's call on 2026-09-07, superseding the Identity table above.
>   Colab badges wait for the flip.


Run in `C:\Users\jonesec\dev\repo\teaching\teaching-code`, because this plan and the source folder are both reachable from there.

```
Work in C:\Users\jonesec\dev\repo\teaching\teaching-code. Read ENERGY_SERIES_PLAN.md, then create the repository
it describes at C:\Users\jonesec\dev\repo\teaching\energy-system-modeling with FRESH history: git init, not a
clone or a filter of the REE folder.

Take only the thirteen notebooks from
"...\Classes\REE 4301 - Energy System Modeling\2026 Fall\Notebooks\" and their
notebook builders from that folder's Tools\ (the build_*_notebook.py, build_m*.py,
build_sb*.py, build_1n_*, build_grad_*, build_toy_lp_*, build_powerflow_*,
build_transport_*, build_supplychain_*, build_boundary_* set, plus
check_builders.py). Take NOTHING else: no exams, no rubrics, no Canvas tooling, no
book. Verify by search that none came along before the first commit.

Lay the folders out as the plan says, named for part and subject, not chapter
number. Add MIT LICENSE, a CC BY note for the notebooks, and a README carrying the
mapping table verbatim and linking the Pressbooks book. Do not execute or edit any
notebook yet. Create sear-labs/energy-system-modeling public and push.
```

## 2. Environment and diagnostic - DONE 2026-09-07

> The environment is the `esm` venv and kernel; `requirements.txt` and
> `requirements-lock.txt` record it. **Ten of twelve executed clean on the first pass**, so
> the diagnostic became a fix pass rather than a queue, and no `REVIEW_QUEUE.md` was written
> - the defect record is in the commit and the findings are closed rather than listed.
>
> What actually broke, and what it taught:
>
> - The TU Berlin series failed on an incomplete certificate chain, not on the network. It is
>   still unlicensed and still due for replacement in session 5, now for a second reason.
> - **Three notebooks could never have run on Colab** - they default to Gurobi and never
>   installed `gurobipy`, passing here only because this machine has it. A local run cannot
>   find that class of defect, which is why CI now runs on a clean machine.
> - `texas_multi_city_buildout` defaulted to a solver its own table says cannot solve two of
>   its three stages. It now defaults to HiGHS, as `real_network_import` already did.
> - A deliberate blank is Part 5 working *and* it collides with "ship it executed". Resolved
>   in the runner: executed up to the blank, blank cell clean.
>
> Session 3's prompt below still stands, minus the parts done here: `check_notebooks.py` is
> ported, and the Colab badges and setup are in.


Run in `C:\Users\jonesec\dev\repo\teaching\energy-system-modeling` from here on.

```
Read ENERGY_SERIES_PLAN.md. Build an environment that can run all thirteen
notebooks: PyPSA, Gurobi, PuLP, NetworkX, SciPy, Plotly, ipywidgets. Record how, in
a README, as a named kernel rather than a loose PYTHONPATH.

Then execute all thirteen as they are and record what breaks in REVIEW_QUEUE.md,
one row per notebook. This is a DIAGNOSTIC pass: do not fix content, do not
restructure, do not add assertions. Two notebooks fetch data over the network and
are expected to be among the failures. Commit the queue.
```

## 3. Vertical slice - PARTLY DONE 2026-09-07

> Done already, so session 3 does not redo it: `check_notebooks.py` is ported (as a matrix
> rather than a gate, since every notebook fails the agreement check for a known reason);
> the setup and licence cells are generated by `tools/sync_setup_cells.py`; the Colab badges
> by `tools/add_colab_badges.py`; and **`esm.data` settles where an instance table comes
> from** - local copy first, published raw URL as the fallback, which is the question three
> repositories in the org had each answered differently.
>
> **What remains is the actual slice**: `power_flow_and_lmp`'s instance out into `data/raw/`
> as tables both sides read, an `esm` module built from what it builds by hand, and the
> first agreement assertion. Nothing has one yet.
>
> One correction to the prompt below: `check_builders.py` is not yet usable as a seed
> checker, because the builders' output paths still name `2026 Fall/Notebooks/`. Repointing
> them is part of this session.


```
Read ENERGY_SERIES_PLAN.md and REVIEW_QUEUE.md. Take power_flow_and_lmp end to end
as the pattern every other notebook will copy: instance data out into data/raw as
tables both sides read, an esm package module built from what the notebook builds
by hand, one agreement assertion, the setup and licence cells, predict prompts, and
the conventions pass. Port a check_notebooks.py from teaching-code and keep
check_builders.py as the seed checker.

Where an optimum is not unique, compare what every optimum shares and teach the tie
in the prose. Do not compare the solver's path. Commit with the defect record.
```

## 4. Fan out

One session per part; four of them, or fewer if they go quickly.

```
Read ENERGY_SERIES_PLAN.md, REVIEW_QUEUE.md, and the power_flow_and_lmp notebook,
which is the pattern. Bring notebooks/p<N>_<name>/ up to that pattern: tables,
package module, one agreement assertion each, conventions, executed in place. Run
pytest, check_notebooks.py and check_seeds.py before committing.

pipeline_transport needs a static capacity sweep before its sliders, because
widgets record nothing when executed headlessly.
```

## 5. Vendored data, then the new notebooks

```
Read ENERGY_SERIES_PLAN.md. First vendor the external data into data/vendor with a
sidecar each (source URL, retrieval date, licence, citation) and repoint the two
notebooks that download at run time. The TU Berlin time series is unlicensed and
behind a personal share link: replace it rather than vendor it. The PyPSA cost
tables are GPL-3.0 and keep their own notice.

Then write the two arithmetic newcomers, screening_curves and
cost_of_transit_by_mode. They need no solver and cover four chapters between them.
Then feeder_hosting_capacity and pipeline_pressure_and_n1, the two chapters the
Part IV expansion added.
```

## 6. Close out

```
Read ENERGY_SERIES_PLAN.md. Write the three remaining new notebooks
(depot_charging, process_heat_electrification, storage_duration_sizing), then move
tools/build_figures.py across from the REE folder and extend its
assert-against-published-output discipline to every figure.

Finally, in C:\Users\jonesec\dev\repo\teaching\teaching-code, repoint README.md and
notebooks/12_energy_systems_pypsa/README.md at the new repository URL instead of
the OneDrive path, and move this plan file into the new repository.
```

## Open, still

- Whether Case Studies 1 and 2 get notebooks, which turns on whether their instructor solution keys
  are already public in the book.
- Whether the graduate notebooks sit in `graduate/` or as advanced companions inside their part.
  `model_diversity` fits no chapter; `real_network_import` serves Chapters 15 and 18.
- The manuscript moves. Re-check the mapping table against `CARES Book/Manuscript/` before trusting
  it, and note that the Pressbooks site will lag it.
