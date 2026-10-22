# Part V — Storage and supply chains

Chapters 19–22. Storing energy when it is cheap, and the material and logistics
reality of building the things that do it.

| notebook | chapter | what it does |
|---|---|---|
| `19_battery_day.ipynb` | 19, §19.4 The State-of-Charge Constraint; §19.5 Does the Battery Pay for Itself? | the day `teaching-code` 12 builds, asked three new questions: what the battery is worth, what the cyclic rule is doing, and whether 8 hours saves twice what 4 does |
| `21_material_requirements.ipynb` | 21, §21.4 A Reference Build, in Tons | what a given buildout costs in materials rather than in dollars |
| `storage_duration_sizing.ipynb` | 20, §20.2 The Storage Comparison | **not yet written** — a multi-day wind lull sized twice, battery against hydrogen, splitting power from energy |

## Chapter 19 is shared with the method library, and split on purpose

> **The build is in
> [`teaching-code` notebook 12](https://github.com/sear-labs/teaching-code/tree/main/notebooks/12_energy_systems_pypsa)**
> — `dispatch_to_pypsa.ipynb`, Part E: the same day, the `StorageUnit`, every
> state-of-charge equation PyPSA writes, and the tie in which hours the battery
> charges. Read it first.

`19_battery_day` does not re-teach any of that. It builds the day in one cell and
spends itself on what the course's Module 4 adds: the battery as a value (the day
with and without it), the cyclic state-of-charge rule taken away, and longer
batteries. Its agreement assertion is against `esm.storage`, and it compares only
the day's cost, because the charging schedule is not unique on this instance.
Agreed with `teaching-code`'s maintainer on 2026-10-22, on exactly those terms.

## Chapter 22 is served from the method library instead

> **Chapter 22 and Case Study 5** — §22.1 The Transshipment Model — is
> [`teaching-code` notebook 13](https://github.com/sear-labs/teaching-code/tree/main/notebooks/13_supply_chain).

`21_material_requirements.ipynb` arrived here as the course's Module 4 supply-chain
notebook, and **its sourcing LP is the model that is already notebook 13**. Only
the material-intensity accounting belongs to this repository, as Chapter 21's
companion. Splitting the two is session 4's work in this part; until then the
notebook still carries both halves and the name runs ahead of the content.

`storage_duration_sizing` extends the battery already in notebook 12 rather than
rebuilding it — the power-versus-energy split is the part the method library does
not teach.
