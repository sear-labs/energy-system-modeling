# Energy System Modeling — companion code

The companion notebooks for **[*Introduction to Energy System Modeling*](https://uta.pressbooks.pub/energysystemmodeling)**
by Erick C. Jones, Jr. — the CC BY open textbook — and the code taught from it in
REE 4301 / IE 5300 / IE 6301 at UT Arlington.

**The book is the spine, not the semester.** Notebooks are named and filed for the
part and subject they serve, never for a course code or a term. `M0`, `SB6` and
`2026 Fall` name one delivery of a course; `power_flow_and_lmp` names a subject
that outlives it.

---

## Status: this is the scaffold commit, and nothing here has been run

Read this before you trust a number in any notebook.

| | |
|---|---|
| notebooks present | 12 of the 19 the plan describes |
| **executed** | **none** — 190 code cells, zero outputs, measured on this tree 2026-09-06 |
| agreement assertions against the package | **none — there is no package yet** |
| `src/esm/` | not written; session 3 builds it |
| `data/raw/`, `data/vendor/` | empty; sessions 3 and 5 fill them |
| notebooks that carry no assertion at all | 5 of the 12 here |

The notebooks arrived from a private course folder exactly as they were, byte for
byte. They have never been executed end to end, which is precisely why they were
not published from that folder: a first commit of unexecuted notebooks fails the
standard's Part 5 (*ship it executed*), and this repository is honest about being
mid-build rather than pretending otherwise.

**[ENERGY_SERIES_PLAN.md](ENERGY_SERIES_PLAN.md) is the specification** — the
chapter mapping, the layout, the seven notebooks still to write, the vendored-data
licences, and the six-session sequence that gets from here to finished. Read it
before changing anything structural. This scaffold is its session 1.

### Why there are no Colab badges yet

Two reasons, and both lift at a known point. The repository is **private**, so a
badge would 404 for every student until it is made public. And the notebooks have
no setup cell yet — session 3 writes the clone-or-`../../src` opener and the
licence cell that every notebook then shares. Badges go in when both are true.

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

## Running anything

There is nothing to run yet — no package, no tests, no entry point. Session 2
builds a named kernel that can execute all twelve, and records how here. Until
then, the environment they will need is PyPSA, Gurobi, PuLP, NetworkX, SciPy,
Plotly and ipywidgets.

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
