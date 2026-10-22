# Energy System Modeling — companion code

The companion notebooks for **[*Introduction to Energy System Modeling*](https://uta.pressbooks.pub/energysystemmodeling)**
by Erick C. Jones, Jr. — the CC BY open textbook — and the code taught from it in
REE 4301 / IE 5300 / IE 6301 at UT Arlington.

**The book is the spine, not the semester.** Notebooks are named and filed for the
part and subject they serve, never for a course code or a term. `M0`, `SB6` and
`2026 Fall` name one delivery of a course; `power_flow_and_lmp` names a subject
that outlives it. **A notebook's path is meant to be linked from a chapter and
stay valid**, so paths do not move once published.

---

## Status

| | |
|---|---|
| notebooks | **17**, every one executed with its outputs committed |
| run clean end to end | 15 |
| stop at a deliberate blank, by design | 2 — `facility_decision` (cell 71) and `end_use_disaggregation` (cell 54) |
| **agreement assertion against the package** | **all 17** — each builds its model by hand and checks it against `src/esm/` |
| `src/esm/` | the package: one module per model, plus `data` and `tolerance` |
| `data/raw/` | the authored instance tables both halves read (CC0) |
| `data/vendor/` | third-party data, one sidecar each, under its own licence |
| release | **`v0.1.0`** — the tag `esm.data` fetches tables from when no local copy exists |

**Two notebooks stop partway on purpose.** Where the student must choose, the
notebook raises with an explanation rather than a bare `NameError`. They are
committed executed up to exactly that cell, with the student's cell clean — the
state you open them in, not an interrupted run.

**What the audit does not yet pass.** `python tools/check_notebooks.py` prints a
matrix of sixteen checks per notebook and exits 0 on purpose: several notebooks
still carry long cells, orphan code cells or prose numbers no output shows. It is
a map of remaining work, not a gate.

### Added 2026-10-22, from the course's Fall 2026 class walkthroughs

| notebook | from the course's | serves |
|---|---|---|
| `p1_foundations/02_energy_arithmetic` | `M0_Energy_Arithmetic` | §2.3; §9.1, §9.3, §9.4, §12.4 |
| `p2_demand/06_smart_meter_reading` | `M1_Smart_Meter_Walkthrough` | §6.2 |
| `p3_generation/10_dispatch_and_carbon` | `M2_Dispatch_Walkthrough` | §9.3–9.4, Chapter 10 |
| `p5_storage_supply/19_battery_day` | `M4_Storage_Walkthrough` | §19.4–19.5, beside `teaching-code` 12 |

`model_boundary` and `capital_and_lcoe` gained the course's **Explore** sections
(sliders and edit-and-run cells); `facility_decision`'s slide references follow
the course's current decks; and `material_requirements` no longer says Australia
enters the sourcing mix at a 50 percent cap — its own table shows it entering at
75. **The smart-meter notebook never uses a real household's data**: it reads the
reader's own export if they supply one and otherwise falls back, loudly, to an
invented house (`esm.meter.synthetic_export`).

**[ENERGY_SERIES_PLAN.md](ENERGY_SERIES_PLAN.md) is the specification** — the
chapter mapping, the layout, the notebooks still to write, the vendored-data
licences. Read it before changing anything structural.

---

## The mapping table

Twenty-three chapters, five case studies, nine appendices. **With the plan, the
only place chapter numbers appear.** Folders are named for part and subject
because chapter numbers have moved before (Part IV grew from four chapters to six
on 1 September 2026) and parts have not. Section numbers are the chapter's own,
from the manuscript, re-checked on 2026-10-22.

| ch | the section that wants it | companion |
|---|---|---|
| 1 | §1.4 Choosing the Boundary | `model_boundary` (motivating exception) |
| 2 | §2.2 Visualizing the System: Energy Balances | `one_house_balance` |
| 2 | §2.3 Energy, Power, and the Units a Modeler Uses; also §9.1, §9.3, §9.4, §12.4 | `energy_arithmetic` |
| 3 | §3.3 Temporal and Spatial Linking; §3.4 The Same Price, From Both Sides | → teaching-code 12; forward-refs `representative_days`, `model_boundary` |
| 4 | §4.6 Reference Models: 1-Node and 3-Node | → teaching-code 12 |
| 5 | §5.3 Grounding Models in Grid Data | `representative_days` |
| 6 | §6.2 Smart Meters, Time Series, and Appliance Signatures | `end_use_disaggregation` (grid scale); `smart_meter_reading` (one house) |
| 7 | §7.2 Process Heat: Low, Medium, and High Grade | `process_heat_electrification` NEW |
| 8 | §8.2 Charging Infrastructure and Policy | `depot_charging` NEW |
| 9 | §9.1 Core Generation Metrics | `capital_and_lcoe` |
| 9–10 | §9.3 Running Versus Building; §9.4 Carbon in the Model; Ch 10 Thermal Generation | `dispatch_and_carbon` |
| 10–12 | the three technology surveys | `screening_curves` NEW |
| 13 | §13.2–13.3 Moving Electrons, Molecules and Solids | `cost_of_transit_by_mode` NEW |
| 14 | §14.4 The Voltage Band and Hosting Capacity | `feeder_hosting_capacity` NEW |
| 15 | §15.2 The Weymouth Relation; §15.5 Winter Storm Uri | `pipeline_pressure_and_n1` NEW; `real_network_import` |
| 16 | §16.1 The Cost of Distance | `cost_of_transit_by_mode` NEW |
| 17 | §17.2 The LP Formulation; §17.4 Expansion Trade Study | `pipeline_transport` |
| 18 | §18.3 Congestion and LMP | `power_flow_and_lmp` |
| 18 | §18.1 The Rail Constraint: Discrete vs Continuous | → teaching-code 05 |
| 19 | §19.4 The State-of-Charge Constraint; §19.5 Does the Battery Pay for Itself? | → teaching-code 12 for the build; `battery_day` for its value, the cyclic rule, and duration |
| 20 | §20.2 The Storage Comparison | `storage_duration_sizing` NEW |
| 21 | §21.4 A Reference Build, in Tons | `material_requirements` |
| 22 | §22.1 The Transshipment Model | → teaching-code 13 |
| 23 | §23.1–23.6 The Facility Decision | `facility_decision`, `texas_multi_city_buildout` |
| CS1 | §V Linear Programming Formulation | none yet |
| CS2 | §V Linear Programming Formulation | none yet |
| CS3 | Grid Evolution Data Benchmark | `screening_curves` supports it |
| CS4 | §II The LP Formulation; grad ext. DCOPF | `pipeline_transport`, `power_flow_and_lmp` |
| CS5 | §III The Transshipment Model | → teaching-code 13; `material_requirements` |
| App A | Writing the Capstone Final Report | none; a writing guide |

`NEW` marks a notebook the plan specifies and nobody has written yet. The two
capstone notebooks still carry an `AppA_` prefix from when the facility decision
was Appendix A; they keep it so links already handed out keep working.

> **The manuscript is the source of truth, not the Pressbooks site.** The site can
> lag the manuscript. Re-check this table against the manuscript before trusting it.

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
| 19, battery and state of charge | `teaching-code` 12 builds it; `battery_day` here asks what it is worth |
| 22 and CS5, transshipment | `teaching-code` 13, REE Module 4's model |

---

## The notebooks

One click each. Each notebook's first cell installs what Colab lacks, clones this
repository so `data/` and `src/` are present, and moves into the notebook's folder.

<!-- NOTEBOOK-TABLE:START - generated by tools/add_colab_badges.py -->

| Notebook | Title | |
|---|---|---|
| **`capstone/`** | | |
| `AppA_facility_decision.ipynb` | Should this site build on-site generation? | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sear-labs/energy-system-modeling/blob/main/notebooks/capstone/AppA_facility_decision.ipynb) |
| `AppA_texas_multi_city_buildout.ipynb` | A multi-city Texas capacity buildout | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sear-labs/energy-system-modeling/blob/main/notebooks/capstone/AppA_texas_multi_city_buildout.ipynb) |
| **`graduate/`** | | |
| `model_diversity.ipynb` | Model diversity: the same system in a second tool | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sear-labs/energy-system-modeling/blob/main/notebooks/graduate/model_diversity.ipynb) |
| **`p0_start/`** | | |
| `00_start_here.ipynb` | Start here | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sear-labs/energy-system-modeling/blob/main/notebooks/p0_start/00_start_here.ipynb) |
| **`p1_foundations/`** | | |
| `01_model_boundary.ipynb` | Where do you draw the boundary? | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sear-labs/energy-system-modeling/blob/main/notebooks/p1_foundations/01_model_boundary.ipynb) |
| `02_energy_arithmetic.ipynb` | Energy arithmetic: the numbers a modeler computes with | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sear-labs/energy-system-modeling/blob/main/notebooks/p1_foundations/02_energy_arithmetic.ipynb) |
| `02_one_house_balance.ipynb` | An energy balance for one house | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sear-labs/energy-system-modeling/blob/main/notebooks/p1_foundations/02_one_house_balance.ipynb) |
| **`p2_demand/`** | | |
| `05_representative_days.ipynb` | From a smart meter to three representative days | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sear-labs/energy-system-modeling/blob/main/notebooks/p2_demand/05_representative_days.ipynb) |
| `06_end_use_disaggregation.ipynb` | One-node disaggregation and demand-side technologies | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sear-labs/energy-system-modeling/blob/main/notebooks/p2_demand/06_end_use_disaggregation.ipynb) |
| `06_smart_meter_reading.ipynb` | Reading a smart meter | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sear-labs/energy-system-modeling/blob/main/notebooks/p2_demand/06_smart_meter_reading.ipynb) |
| **`p3_generation/`** | | |
| `09_capital_and_lcoe.ipynb` | What does it cost to build a power plant? | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sear-labs/energy-system-modeling/blob/main/notebooks/p3_generation/09_capital_and_lcoe.ipynb) |
| `10_dispatch_and_carbon.ipynb` | Dispatch, then a price on carbon | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sear-labs/energy-system-modeling/blob/main/notebooks/p3_generation/10_dispatch_and_carbon.ipynb) |
| **`p4_networks/`** | | |
| `15_real_network_import.ipynb` | Real network import: TX-123BT, then TAMU ACTIVSg | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sear-labs/energy-system-modeling/blob/main/notebooks/p4_networks/15_real_network_import.ipynb) |
| `17_pipeline_transport.ipynb` | Energy transportation and network optimization | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sear-labs/energy-system-modeling/blob/main/notebooks/p4_networks/17_pipeline_transport.ipynb) |
| `18_power_flow_and_lmp.ipynb` | Power flow and locational marginal pricing | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sear-labs/energy-system-modeling/blob/main/notebooks/p4_networks/18_power_flow_and_lmp.ipynb) |
| **`p5_storage_supply/`** | | |
| `19_battery_day.ipynb` | What a battery is worth: one day, three questions | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sear-labs/energy-system-modeling/blob/main/notebooks/p5_storage_supply/19_battery_day.ipynb) |
| `21_material_requirements.ipynb` | Supply chains: sourcing and material reality | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sear-labs/energy-system-modeling/blob/main/notebooks/p5_storage_supply/21_material_requirements.ipynb) |

<!-- NOTEBOOK-TABLE:END -->

## Layout

```
src/esm/                  the package: one module per model, data loading, tolerances
data/raw/                 authored instance tables, both halves read them (CC0)
data/vendor/              third-party data, one sidecar per file
notebooks/
  p0_start/               start_here
  p1_foundations/         model_boundary, one_house_balance, energy_arithmetic
  p2_demand/              representative_days, end_use_disaggregation, smart_meter_reading
  p3_generation/          capital_and_lcoe, dispatch_and_carbon
  p4_networks/            real_network_import, pipeline_transport, power_flow_and_lmp
  p5_storage_supply/      battery_day, material_requirements
  capstone/               facility_decision, texas_multi_city_buildout
  graduate/               model_diversity
tests/                    the package, the ignore rules, the licence scrubber
tools/                    execute, audit, setup-cell and badge tools
tools/builders/           the notebook generators - the source of truth
```

Seven more notebooks are specified in the plan and not yet written:
`process_heat_electrification`, `depot_charging`, `screening_curves`,
`cost_of_transit_by_mode`, `feeder_hosting_capacity`, `pipeline_pressure_and_n1`,
`storage_duration_sizing`.

## Where the notebooks came from, and what was left behind

Fresh history, deliberately — **not** a filter or a push of the private course
folder. That folder tracks live exam banks, a Canvas backup carrying full quiz
question content, an in-progress manuscript, solution keys and one household's
smart-meter export. Git history is permanent, so filtering a working tree would
not have helped: the material is in the commits. Only notebooks, their
generators and authored tables cross, and `.gitignore` states each exclusion
with its reason beside it — tested in both directions by `tests/test_gitignore.py`.

## Running it yourself

**On Colab, click a badge.** Each notebook installs what it needs in its first cell.

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
python tools/sync_setup_cells.py --check      # every setup cell is current
python -m pytest tests/ -q                    # the package, ignore rules, scrubber
```

**No solver licence is needed.** HiGHS is free, uncapped, and is what the large
notebooks default to. Gurobi's pip wheel adds a 2,000-variable restricted licence
that the smaller models fit inside; nothing here requires it.

## Licences

Code is MIT; prose, notebooks and figures are CC BY 4.0, matching the book;
authored tables are CC0; vendored data keeps its own licence. **Stated by path in
[LICENSE-DATA](LICENSE-DATA)**, which is the authority — `LICENSE` covers the code
alone.

## How to cite

No DOI yet: one is minted when a release is deposited with Zenodo, and none has
been. [CITATION.cff](CITATION.cff) carries the citation metadata in the meantime
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
