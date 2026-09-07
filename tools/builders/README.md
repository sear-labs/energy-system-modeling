# The notebook builders

**The builder is the source of truth; the notebook is a generated artifact.**
Editing a notebook directly without patching its builder means the next rebuild
silently reverts the change — which has happened here before. On 2 September 2026
seven of twelve builders had drifted from their own artifacts, invisibly: every
notebook was correct, every builder was wrong, and nothing was comparing them.
`../check_builders.py` is what compares them.

## The builders run here now

Repointed 2026-09-07. Each writes to `notebooks/<part>/<NN_subject>.ipynb`, and
`ROOT` climbs three levels rather than two, because these used to live one level
higher in the course folder's `Tools/`. `../check_builders.py` looks under
`notebooks/` recursively and globs the builders out of this folder.

**Verified by running one**: `build_sb3_notebook.py` regenerates
`p3_generation/09_capital_and_lcoe.ipynb` in place, and the documented sequence
below puts back everything a rebuild strips.

**Expect a diff even when nothing changed.** The builders mint a fresh random
cell id on every run, so a rebuild always shows as modified. That is the
generator's behaviour, not a change to the notebook, and it is worth knowing
before somebody chases it.

## Three things are applied to notebooks AFTER a rebuild, not by the builders

A rebuild regenerates a notebook from its builder, which means it drops anything
the builder does not emit. Three things are deliberately not in the builders, and
each has its own idempotent tool — so the sequence after any rebuild is:

    python tools/builders/build_<x>_notebook.py     # regenerate
    python tools/sync_setup_cells.py                # re-apply the setup cell
    python tools/add_colab_badges.py                # re-apply the badge
    python tools/execute_notebooks.py --inplace     # re-execute

**The Colab badge** is generated from each notebook's own path, so putting it in
twelve builders would mean twelve copies of a URL that changes when a notebook
moves. `tools/add_colab_badges.py --check` fails if any badge is missing or
points at the wrong path, which is the guard that makes the separation safe.

**The executed outputs.** Part 5 says ship it executed; a builder emits source.

**The setup cell**, for the same reason as the badge: it contains this
notebook's own folder and a dependency list derived from what the notebook
imports, so twelve hand-maintained copies would drift the moment one changed.
`tools/sync_setup_cells.py --check` fails if any is missing or stale, and it
also removes the bare `!pip install` cell the builders still emit -- that cell
is unpinned, and the generated one installs the same things with version bounds.

Everything else — including the fix to the time-series download in
`build_1n_notebook.py` — **is** in the builder, patched in the same edit as the
notebook, because that is the rule this folder exists to enforce.

## Which builder makes which notebook

The names are the course's, and the notebooks have been renamed for their subject.

| builder | notebook |
|---|---|
| `build_boundary_notebook.py` | `p1_foundations/01_model_boundary.ipynb` |
| `build_sb1_example_notebook.py` | `p1_foundations/02_one_house_balance.ipynb` |
| `build_sb2_notebook.py` | `p2_demand/05_representative_days.ipynb` |
| `build_1n_notebook.py` | `p2_demand/06_end_use_disaggregation.ipynb` |
| `build_sb3_notebook.py` | `p3_generation/09_capital_and_lcoe.ipynb` |
| `build_transport_notebook.py` | `p4_networks/17_pipeline_transport.ipynb` |
| `build_powerflow_notebook.py` | `p4_networks/18_power_flow_and_lmp.ipynb` |
| `build_grad_n_notebook.py` | `p4_networks/15_real_network_import.ipynb` |
| `build_supplychain_notebook.py` | `p5_storage_supply/21_material_requirements.ipynb` |
| `build_sb6_notebook.py` | `capstone/AppA_texas_multi_city_buildout.ipynb` |
| `build_m5_notebook.py` | `capstone/AppA_facility_decision.ipynb` |
| `build_grad_m_notebook.py` | `graduate/model_diversity.ipynb` |

Twelve builders, twelve notebooks, one to one.

## The deck builders are not here, and must not be brought over

The course folder's `Tools/` also holds `build_m0.py` through `build_m4.py` and
`build_m5_deck.py`. Those names look like they belong to this set and do not:
they build **PowerPoint decks**, and they import six local helpers (`searkit`,
`deckmerge`, `restyle`, `reductions`, `band_trims`, `fitpass`) that would drag
half of that folder across with them. Only `build_m5_notebook.py` from that name
family is a notebook builder.

The reliable test is the one `check_builders.py` already applies: it globs
`build_*notebook*.py`, which selects exactly these twelve and no deck builder.
Prefer that glob to reading the names.

## They are stdlib-only, which is why they travelled alone

Every builder here imports only the standard library, with one exception:
`build_supplychain_notebook.py` imports `gurobipy` inside its `verify()`, guarded.
Nothing here needs `searkit` or any other course-folder helper.

Each builder carries a `verify()` asserting its own arithmetic and a
`syntax_check()` over its generated code cells. Keep both working, and record
*why* a structural decision was made in the builder's module docstring rather
than only what it does.
