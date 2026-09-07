# Part V — Storage and supply chains

Chapters 19–22. Storing energy when it is cheap, and the material and logistics
reality of building the things that do it.

| notebook | chapter | what it does |
|---|---|---|
| `21_material_requirements.ipynb` | 21, §21.4 A Reference Build, in Tons | what a given buildout costs in materials rather than in dollars |
| `storage_duration_sizing.ipynb` | 20, §20.2 The Storage Comparison | **not yet written** — a multi-day wind lull sized twice, battery against hydrogen, splitting power from energy |

## Two chapters are served from the method library instead

> **Chapter 19** — §19.4 State-of-Charge and §19.5 Does the Battery Pay for
> Itself — is
> [`teaching-code` notebook 12](https://github.com/sear-labs/teaching-code/tree/main/notebooks/12_energy_systems_pypsa),
> whose second half is exactly the day-with-a-battery model and its
> state-of-charge constraint.
>
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
