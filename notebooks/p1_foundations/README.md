# Part I — Foundations

Chapters 1–4. What a model is, where you draw its boundary, and what the tool is
doing when you stop writing the linear program yourself.

| notebook | chapter | what it does |
|---|---|---|
| `01_model_boundary.ipynb` | 1, §1.4 Choosing the Boundary | the motivating exception: it anchors at the *first* chapter because it raises the question the rest of Part I answers |
| `02_one_house_balance.ipynb` | 2, §2.2 Visualizing the System: Energy Balances | one house, at the reader's own scale, where the therm and gallon conversions stay visible instead of vanishing into quads |

## The toy LP and the PyPSA introduction are not here, on purpose

Chapters 3 and 4 — §3.3 Temporal and Spatial Linking, §3.4 The Same Price From
Both Sides, and §4.6 Reference Models: 1-Node and 3-Node — are served by

> **[`teaching-code` notebook 12](https://github.com/sear-labs/teaching-code/tree/main/notebooks/12_energy_systems_pypsa)**
> — `dispatch_to_pypsa.ipynb`

which **is** this course's Module 0: one hour of dispatch solved on paper, then in
gurobipy, then in PyPSA, all three agreeing; then a day with a battery; then
capacity as a decision.

**It is already executed and verified there**, which is the point. That library is
organised by topic and teaches a method on a small self-contained instance; this
repository is a series and carries the method on a real one. Where the method is
already taught there, this repository points at it rather than keeping a second
copy that nothing compares.

So a reader working through Part I goes: `model_boundary` → `one_house_balance` →
`teaching-code` 12 → Part II. Chapter 3 also forward-references
`representative_days` (Part II) and `model_boundary`, which it discusses but does
not anchor.

Its generator, `build_toy_lp_notebook.py`, likewise stayed in the course folder.
