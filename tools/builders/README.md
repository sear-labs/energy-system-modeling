# The notebook builders

**The builder is the source of truth; the notebook is a generated artifact.**
Editing a notebook directly without patching its builder means the next rebuild
silently reverts the change — which has happened here before. On 2 September 2026
seven of twelve builders had drifted from their own artifacts, invisibly: every
notebook was correct, every builder was wrong, and nothing was comparing them.
`../check_builders.py` is what compares them.

## These builders do not run in this repository yet

They were copied **verbatim**, so the scaffold commit is a move and nothing else.
Every one of them still computes its output path as

    ROOT / "2026 Fall" / "Notebooks" / <old course-code name>.ipynb

which is the layout of the private course folder they came from, not the layout
here. `../check_builders.py` looks for notebooks in the same place. So a builder
run right now writes into a path that does not exist in this repository, and the
checker finds nothing to check.

**This is known, not broken-by-accident.** Two reasons for leaving it:

1. The diagnostic pass (session 2) should measure the builders as they actually
   are, not as this session left them.
2. Repointing them is the same edit as reflecting the notebook renames, and both
   belong with the vertical slice (session 3), where the checker is ported
   alongside a `check_notebooks.py` from `teaching-code`.

## Which builder makes which notebook

The names are the course's, and the notebooks have been renamed for their subject.

| builder | notebook |
|---|---|
| `build_boundary_notebook.py` | `p1_foundations/model_boundary.ipynb` |
| `build_sb1_example_notebook.py` | `p1_foundations/one_house_balance.ipynb` |
| `build_sb2_notebook.py` | `p2_demand/representative_days.ipynb` |
| `build_1n_notebook.py` | `p2_demand/end_use_disaggregation.ipynb` |
| `build_sb3_notebook.py` | `p3_generation/capital_and_lcoe.ipynb` |
| `build_transport_notebook.py` | `p4_networks/pipeline_transport.ipynb` |
| `build_powerflow_notebook.py` | `p4_networks/power_flow_and_lmp.ipynb` |
| `build_grad_n_notebook.py` | `p4_networks/real_network_import.ipynb` |
| `build_supplychain_notebook.py` | `p5_storage_supply/material_requirements.ipynb` |
| `build_sb6_notebook.py` | `capstone/texas_multi_city_buildout.ipynb` |
| `build_m5_notebook.py` | `capstone/facility_decision.ipynb` |
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
