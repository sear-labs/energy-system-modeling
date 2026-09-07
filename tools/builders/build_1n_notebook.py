# -*- coding: utf-8 -*-
"""build_1n_notebook.py - write `2026 Fall/Notebooks/1N_One_Node_Disaggregation.ipynb`,
the student-facing notebook for the 1N assignment (Assignment Catalog Part Four).

Part 0's PyPSA construction (cost loading, wind/solar/battery/hydrogen 1-node
model) is copied verbatim from the course's own working reference notebook,
`capacity-expansion-planning-single-node.ipynb` (Spring 2026, Class Collab
Code/Generation and PyPSA), wrapped in a reusable `build_1node_model()`
function so Parts 1-3 can call it repeatedly with a modified demand series.
Parts 2-3 are new: degree-day disaggregation (reusing the regression method
Module 1 already teaches, not a new one) and three demand-side technology
functions (weatherization, SEER/HSPF efficiency, heat-pump fuel switch).

Real figures embedded as worked defaults (all cited in the notebook itself,
not just here):
  - EIA RECS 2020: the three largest US residential electricity end uses are
    air conditioning 19%, space heating 12%, water heating 12% of site
    electricity consumption (eia.gov/energyexplained/use-of-energy/
    electricity-use-in-homes.php)
  - DOE Weatherization Assistance Program: ~30% average heating-cost
    reduction in cold-weather states (energy.gov, ACEEE WAP fact sheet)
  - Air-source heat pump seasonal COP: 2.4-3.3 typical range, using 2.8 as a
    representative default (NEEP Cold Climate ASHP Specification; COP ~=
    HSPF2 / 3.412)
  - Real worked demand data: `IntervalData.csv` (Spring 2026, Class Collab
    Code/Demand and Smart Meter Analysis) - real 15-minute ERCOT smart-meter
    data, the same class of data Module 1's own degree-day regression slide
    was built from
  - Real temperature data: fetched live from Open-Meteo's free historical
    archive API (archive-api.open-meteo.com), no API key required - verified
    working this session

Run from Tools/:  python build_1n_notebook.py
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "2026 Fall", "Notebooks", "1N_One_Node_Disaggregation.ipynb")
REF_DEMAND_CSV = os.path.join(
    ROOT, "2026 Spring (First Class)", "Google Drive", "Class Collab Code",
    "Demand and Smart Meter Analysis", "IntervalData.csv")


_ID_COUNTER = [0]


def _next_id():
    _ID_COUNTER[0] += 1
    return "cell-%02d" % _ID_COUNTER[0]


def md(*lines):
    return {"cell_type": "markdown", "id": _next_id(), "metadata": {},
            "source": list(lines)}


def code(*lines):
    return {"cell_type": "code", "id": _next_id(), "execution_count": None,
            "metadata": {}, "outputs": [], "source": list(lines)}


def L(s):
    """One source line, newline-terminated (nbformat convention)."""
    return s + "\n"


CELLS = []
A = CELLS.append

# ============================================================== Title
A(md(
L("# One-node disaggregation and demand-side technologies"),
L("## REE 4301 — Energy Systems Modeling"),
L("### Bridges Module 1 (Demand) into Module 2 (Generation)"),
L(""),
L("**Objective:** The 1-node capacity expansion model you already ran treats "
  "demand as one aggregate curve. Real demand-side technologies — "
  "weatherization, efficiency upgrades, heat pumps — don't act on the "
  "aggregate; they act on one end use at a time. In this assignment you will "
  "disaggregate your own demand profile into named end uses, apply a "
  "demand-side technology to one of them, and see how that changes the "
  "supply-side optimum the solver chooses."),
L(""),
L("**What You Will Learn:**"),
L("- How to separate weather-sensitive load (heating, cooling) from the "
  "weather-insensitive baseline using the same degree-day regression method "
  "from Mini-Project 1 — not a new method, the same one"),
L("- How to name and shape individual end uses within an aggregate profile"),
L("- How a demand-side choice (insulation, efficiency, fuel switching) "
  "changes what the generation-side solver builds"),
L("- Why you have to say what fuel an end use currently uses before you can "
  "talk about switching it"),
L(""),
L("**Builds on:** the 1-node baseline you already ran and replaced with your "
  "own demand profile. If you have not done that yet, Part 1 below is that "
  "step, unchanged."),
L(""),
L("**Standard submission requirements apply** — see Part One of the "
  "Assignment Catalogue: units on every number, cite your data source and "
  "its year, print to PDF with text cells intact, also submit the .ipynb."),
))

# ============================================================== Part 0 header

A(md(
L("---"),
L("## Part 0 — Setup & Baseline"),
L(""),
L("This is the **exact same 1-node model** from the reference notebook "
  "(`capacity-expansion-planning-single-node.ipynb`), wrapped in a function "
  "so Parts 1–3 can re-run it with different demand series. **Do not modify "
  "these cells** — everything you do happens from Part 1 onward."),
))

A(code(L("!pip install -q pypsa highspy requests gurobipy")))

A(code(
L("# General notebook settings"),
L("import logging"),
L("import warnings"),
L(""),
L("import pypsa"),
L("import pandas as pd"),
L("import numpy as np"),
L("import matplotlib.pyplot as plt"),
L("import requests"),
L("import io"),
L(""),
L("warnings.filterwarnings(\"ignore\")"),
L("logging.getLogger(\"gurobipy\").propagate = False"),
L("pypsa.options.params.optimize.log_to_console = False"),
L("pd.set_option(\"display.float_format\", \"{:,.2f}\".format)"),
))

A(md(
L('---\n'),
L('### Choosing a solver\n'),
L('\n'),
L('This notebook defaults to **Gurobi**. `pip install gurobipy` ships a restricted licence that needs no registration at all and solves models up to **2,000 variables and 2,000 constraints**.\n'),
L('\n'),
L('That ceiling arrives sooner than you would think. Measured sizes for the models in this course:\n'),
L('\n'),
L('| model | variables | constraints | restricted licence |\n'),
L('|---|---|---|---|\n'),
L('| 1-node, 24 hours | 123 | 291 | fits |\n'),
L('| SB6 Stage 1 | 766 | 1,837 | fits |\n'),
L('| SB6 Stage 2 | 886 | 2,172 | too big |\n'),
L('| SB6 Stage 3 | 2,614 | 6,444 | too big |\n'),
L('| TX-123BT, 24 hours | 16,080 | 38,304 | 19x over |\n'),
L('\n'),
L('When you exceed it, Gurobi returns *"Model too large for size-limited license"*. Two ways past it:\n'),
L('\n'),
L('**In class — switch to HiGHS.** Open source, no licence, no size limit. Uncomment the `SOLVER` line below. There is no accuracy cost: HiGHS and Gurobi agree to sixteen significant figures on every model here. The speed cost is real only when the problem is large — measured on a 1-node model, HiGHS is *marginally faster* at 24 hours, identical at one week, and about **12x slower** on a full 8,760-hour year (22 s against 1.8 s). On a mixed-integer unit-commitment problem with 2,880 binary variables the gap was only **1.8x**.\n'),
L('\n'),
L('**For homework — get an academic licence.** A free Web License Service (WLS) key from gurobi.com works in Colab with **no licence file**: paste the three values into `WLS` below. Build the environment **once** and reuse it — constructing a new one for every solve re-authenticates each time and will exhaust a WLS session partway through a scenario sweep.\n'),
))

A(code(
L("SOLVER = 'gurobi'\n"),
L("# SOLVER = 'highs'     # <-- uncomment: open source, no licence, no size cap\n"),
L('\n'),
L('# For homework: paste your academic Web License Service key here.\n'),
L('# Leave it empty and Gurobi falls back to its restricted licence.\n'),
L("WLS = {}   # {'WLSACCESSID': '...', 'WLSSECRET': '...', 'LICENSEID': 000000}\n"),
L('\n'),
L('ENV = None\n'),
L("if SOLVER == 'gurobi' and WLS:\n"),
L('    import gurobipy as gp\n'),
L('    ENV = gp.Env(params=WLS)     # ONE environment, reused by every solve\n'),
L('\n'),
L("print(f'solver: {SOLVER}'\n"),
L("      + ('  (academic WLS licence)' if ENV else '  (default licence)'))\n"),
))

A(md(L("### Techno-economic assumptions"),
     L("Same source as the reference notebook: the "
       "[technology-data](https://github.com/PyPSA/technology-data) "
       "repository.")))

A(code(
L("YEAR = 2030"),
L("url = f\"https://raw.githubusercontent.com/PyPSA/technology-data/master/outputs/costs_{YEAR}.csv\""),
L("costs = pd.read_csv(url, index_col=[0, 1])"),
L("costs.loc[costs.unit.str.contains(\"/kW\"), \"value\"] *= 1e3"),
L("costs = costs.value.unstack().fillna("),
L("    {\"discount rate\": 0.07, \"lifetime\": 20, \"FOM\": 0}"),
L(")"),
L("costs[\"marginal_cost\"] = costs[\"VOM\"] + costs[\"fuel\"] / costs[\"efficiency\"]"),
L(""),
L("def annuity(rate, n):"),
L("    \"\"\"Capital recovery factor for a given discount rate and lifetime "
  "- the same CRF from Module 2.\"\"\""),
L("    if rate == 0:"),
L("        return 1 / n"),
L("    return rate / (1 - (1 + rate) ** (-n))"),
L(""),
L("a = costs.apply(lambda x: annuity(x[\"discount rate\"], x[\"lifetime\"]), axis=1)"),
L("costs[\"capital_cost\"] = (a + costs[\"FOM\"] / 100) * costs[\"investment\"]"),
))

A(md(L("### Reference wind, solar and demand time series"),
     L("This is the same representative-year wind/solar capacity-factor "
       "series the reference notebook uses. Your own demand (Part 1) gets "
       "spliced onto this same calendar of hours.")))

A(code(
L("RESOLUTION = 3  # hours, matches the reference notebook"),
L("URL = \"https://tubcloud.tu-berlin.de/s/9toBssWEdaLgHzq/download/time-series.csv\""),
L(""),
L("# pandas reads a URL through urllib, which uses the SYSTEM certificate store."),
L("# This host serves an incomplete chain, so verification stops at \"unable to get"),
L("# local issuer certificate\" and the notebook dies on a stack trace. requests"),
L("# carries certifi's own bundle and completes the chain, so the download happens"),
L("# here and pandas is handed text."),
L("#"),
L("# The series is also on a personal share link with no stated licence, and is"),
L("# due to be replaced with a citable source - see data/vendor/README.md."),
L("try:"),
L("    _resp = requests.get(URL, timeout=60)"),
L("    _resp.raise_for_status()"),
L("except Exception as exc:"),
L("    raise RuntimeError("),
L("        f\"Could not download the reference time series.\\n\""),
L("        f\"  {type(exc).__name__}: {exc}\\n\""),
L("        \"This cell needs network access. The series carries wind_pu, pv_pu \""),
L("        \"and load_mw on an hourly calendar; data/vendor/README.md describes \""),
L("        \"the replacement that is due to remove this dependency.\""),
L("    ) from exc"),
L(""),
L("ts = pd.read_csv(io.StringIO(_resp.text), index_col=0,"),
L("                 parse_dates=True)[::RESOLUTION]"),
L("print(f\"{len(ts):,} snapshots at {RESOLUTION}h, \""),
L("      f\"{ts.index[0]:%Y-%m-%d} to {ts.index[-1]:%Y-%m-%d}\")"),
L("ts.head(3)"),
))

A(md(L("### `build_1node_model()` — the reusable model builder"),
     L("Identical construction to the reference notebook (electricity bus, "
       "load, load-shedding generator, wind, solar, 3-hour battery, "
       "hydrogen electrolysis/turbine/storage) — just wrapped in a function "
       "so you can call it again with a different `demand_mw` series "
       "without retyping it.")))

A(code(
L("def build_1node_model(demand_mw, label=\"model\"):"),
L("    \"\"\"demand_mw: a pandas Series indexed exactly like ts.index, in MW.\"\"\""),
L("    n = pypsa.Network()"),
L("    n.add(\"Bus\", \"electricity\", carrier=\"electricity\")"),
L("    n.set_snapshots(ts.index)"),
L("    n.snapshot_weightings.loc[:, :] = RESOLUTION"),
L(""),
L("    carriers = [\"wind\", \"solar\", \"hydrogen storage\", \"battery storage\","),
L("                \"load shedding\", \"electrolysis\", \"turbine\","),
L("                \"electricity\", \"hydrogen\"]"),
L("    colors = [\"dodgerblue\", \"gold\", \"black\", \"yellowgreen\", \"darkorange\","),
L("              \"magenta\", \"red\", \"grey\", \"grey\"]"),
L("    n.add(\"Carrier\", carriers, color=colors)"),
L(""),
L("    n.add(\"Load\", \"demand\", bus=\"electricity\", p_set=demand_mw)"),
L(""),
L("    n.add(\"Generator\", \"load shedding\", bus=\"electricity\","),
L("          carrier=\"load shedding\", marginal_cost=2000,"),
L("          p_nom=demand_mw.max())"),
L(""),
L("    n.add(\"Generator\", \"wind\", bus=\"electricity\", carrier=\"wind\","),
L("          p_max_pu=ts.wind_pu, capital_cost=costs.at[\"onwind\", \"capital_cost\"],"),
L("          marginal_cost=costs.at[\"onwind\", \"marginal_cost\"], p_nom_extendable=True)"),
L(""),
L("    n.add(\"Generator\", \"solar\", bus=\"electricity\", carrier=\"solar\","),
L("          p_max_pu=ts.pv_pu, capital_cost=costs.at[\"solar\", \"capital_cost\"],"),
L("          marginal_cost=costs.at[\"solar\", \"marginal_cost\"], p_nom_extendable=True)"),
L(""),
L("    n.add(\"StorageUnit\", \"battery storage\", bus=\"electricity\","),
L("          carrier=\"battery storage\", max_hours=3,"),
L("          capital_cost=costs.at[\"battery inverter\", \"capital_cost\"]"),
L("          + 3 * costs.at[\"battery storage\", \"capital_cost\"],"),
L("          efficiency_store=costs.at[\"battery inverter\", \"efficiency\"],"),
L("          efficiency_dispatch=costs.at[\"battery inverter\", \"efficiency\"],"),
L("          p_nom_extendable=True, cyclic_state_of_charge=True)"),
L(""),
L("    n.add(\"Bus\", \"hydrogen\", carrier=\"hydrogen\")"),
L("    n.add(\"Link\", \"electrolysis\", bus0=\"electricity\", bus1=\"hydrogen\","),
L("          carrier=\"electrolysis\", p_nom_extendable=True,"),
L("          efficiency=costs.at[\"electrolysis\", \"efficiency\"],"),
L("          capital_cost=costs.at[\"electrolysis\", \"capital_cost\"])"),
L("    n.add(\"Link\", \"turbine\", bus0=\"hydrogen\", bus1=\"electricity\","),
L("          carrier=\"turbine\", p_nom_extendable=True,"),
L("          efficiency=costs.at[\"OCGT\", \"efficiency\"],"),
L("          capital_cost=costs.at[\"OCGT\", \"capital_cost\"] / costs.at[\"OCGT\", \"efficiency\"])"),
L("    n.add(\"Store\", \"hydrogen storage\", bus=\"hydrogen\", carrier=\"hydrogen storage\","),
L("          capital_cost=costs.at[\"hydrogen storage underground\", \"capital_cost\"],"),
L("          e_nom_extendable=True, e_cyclic=True)"),
L(""),
L("    n.name = label"),
L("    return n"),
))

A(code(
L("def extract_results(n, label=\"\"):"),
L("    \"\"\"Pull the headline numbers out of a solved network.\"\"\""),
L("    cap = n.statistics.optimal_capacity().droplevel(0)"),
L("    bal = n.statistics.energy_balance(bus_carrier=\"electricity\").droplevel(0)"),
L("    served = n.loads_t.p_set[\"demand\"].sum() * RESOLUTION"),
L("    shed = n.generators_t.p[\"load shedding\"].sum() * RESOLUTION"),
L("    return {"),
L("        \"Scenario\": label,"),
L("        \"Total system cost ($M)\": n.objective / 1e6,"),
L("        \"Wind (MW)\": cap.get(\"wind\", 0.0),"),
L("        \"Solar (MW)\": cap.get(\"solar\", 0.0),"),
L("        \"Battery (MW)\": cap.get(\"battery storage\", 0.0),"),
L("        \"Total demand (MWh)\": served,"),
L("        \"Unserved energy (MWh)\": shed,"),
L("        \"Unserved (%)\": 100 * shed / served if served else 0.0,"),
L("    }"),
L(""),
L("def compare_scenarios(results_list):"),
L("    return pd.DataFrame(results_list).set_index(\"Scenario\").T"),
))

# ============================================================== Part 1
A(md(
L("---"),
L("## Part 1 — Baseline run and your own demand"),
L(""),
L("If you already completed the original 1-Node Assignment, this is the "
  "same step — reproduced here so this notebook stands on its own and so "
  "`r_reference` and `r_own` are available for the comparison table at the "
  "end of Part 3."),
))

A(code(
L("n_reference = build_1node_model(ts.load_mw, \"Reference demand\")"),
L("n_reference.optimize(solver_name=SOLVER, env=ENV)"),
L("r_reference = extract_results(n_reference, \"Reference demand\")"),
L("compare_scenarios([r_reference])"),
))

A(md(
L("### TODO — load your own demand profile"),
L(""),
L("Replace `DEMAND_CSV_PATH` with your own Mini-Project 1 / smart-meter "
  "export — an ERCOT-style 15-minute interval CSV with `USAGE_DATE`, "
  "`USAGE_START_TIME` and `USAGE_KWH` columns."),
L(""),
L("**If that file is not next to the notebook** — which it will not be the "
  "first time you open this in Colab — the cell below falls back to a "
  "synthetic residential profile so the rest of the notebook still runs. It "
  "will say loudly that it has done so. **A synthetic profile is not an "
  "acceptable submission**; upload your own export before you write anything "
  "up."),
L(""),
L("**State your assumption:** the reference wind/solar series and your own "
  "demand almost certainly come from different calendar years. This "
  "notebook aligns them by **day-of-year and hour-of-day**, not by exact "
  "date — i.e. it assumes your demand *shape* is representative regardless "
  "of which year it was metered in. Say so explicitly in your write-up; it "
  "is a real modelling assumption, not a bug."),
))

A(code(
L("DEMAND_CSV_PATH = \"IntervalData.csv\"  # <-- point this at your own export"),
L(""),
L("def load_own_demand(path):"),
L("    \"\"\"ERCOT-style 15-minute interval export -> hourly-mean kW, indexed "
  "by real timestamp.\"\"\""),
L("    raw = pd.read_csv(path)"),
L("    raw[\"ts\"] = pd.to_datetime("),
L("        raw[\"USAGE_DATE\"] + \" \" + raw[\"USAGE_START_TIME\"],"),
L("        format=\"%m/%d/%Y %H:%M\","),
L("    )"),
L("    kwh_15min = raw.set_index(\"ts\")[\"USAGE_KWH\"]"),
L("    kw_hourly = kwh_15min.resample(\"1h\").sum() * 4  # 15-min kWh -> hourly-avg kW"),
L("    return kw_hourly"),
L(""),
L(""),
L("def synthetic_demand(days=365):"),
L("    \"\"\"Stand-in profile: morning and evening peaks, warmer-month cooling."),
L("    Used ONLY when no interval file is present, so the notebook still runs."),
L("    \"\"\""),
L("    idx = pd.date_range('2024-01-01', periods=days * 24, freq='1h')"),
L("    hour = idx.hour.to_numpy()"),
L("    doy = idx.dayofyear.to_numpy()"),
L("    shape = (0.9"),
L("             + 0.45 * np.exp(-((hour - 19) ** 2) / 6.0)"),
L("             + 0.20 * np.exp(-((hour - 7) ** 2) / 4.0))"),
L("    cooling = 1 + 0.5 * np.clip(np.sin(np.pi * (doy - 100) / 240), 0, 1)"),
L("    rng = np.random.default_rng(0)"),
L("    kw = 1.4 * shape * cooling * rng.normal(1.0, 0.05, len(idx))"),
L("    return pd.Series(np.clip(kw, 0.15, None), index=idx)"),
L(""),
L("try:"),
L("    own_demand_kw = load_own_demand(DEMAND_CSV_PATH)"),
L("    DEMAND_IS_REAL = True"),
L("    print(f'loaded {DEMAND_CSV_PATH}: {len(own_demand_kw):,} hourly points')"),
L("except FileNotFoundError:"),
L("    own_demand_kw = synthetic_demand()"),
L("    DEMAND_IS_REAL = False"),
L("    print('=' * 66)"),
L("    print(f'NO FILE NAMED {DEMAND_CSV_PATH} FOUND - using a SYNTHETIC profile.')"),
L("    print('The rest of the notebook will run, but this is not your data')"),
L("    print('and it is not an acceptable submission. Upload your own')"),
L("    print('interval export and re-run from this cell.')"),
L("    print('=' * 66)"),
L(""),
L("title = ('Your metered demand (kW)' if DEMAND_IS_REAL"),
L("         else 'SYNTHETIC stand-in demand (kW) - replace with your own')"),
L("own_demand_kw.plot(figsize=(10, 2.5), title=title)"),
L("plt.tight_layout(); plt.show()"),
))

A(code(
L("def align_to_reference_calendar(series_kw, target_index, scale_to_mw=1e-3):"),
L("    \"\"\"Map a demand series onto the reference model's snapshot calendar "
  "by (month, day, hour) rather than exact date, since the two data sources "
  "are almost never the same year. Returns MW, indexed like target_index.\"\"\""),
L("    by_time = series_kw.groupby("),
L("        [series_kw.index.month, series_kw.index.day, series_kw.index.hour]"),
L("    ).mean()"),
L("    keys = list(zip(target_index.month, target_index.day, target_index.hour))"),
L("    mapped = pd.Series([by_time.get(k, np.nan) for k in keys], index=target_index)"),
L("    mapped = mapped.interpolate().bfill().ffill()  # cover any Feb 29 / missing hours"),
L("    return mapped * scale_to_mw"),
L(""),
L("one_premise_mw = align_to_reference_calendar(own_demand_kw, ts.index)"),
L(""),
L("print(f'one premise: peak {one_premise_mw.max()*1e3:,.1f} kW,'"),
L("      f'  annual {one_premise_mw.sum()*RESOLUTION*1e3:,.0f} kWh')"),
))

A(md(
L("### Your meter is the shape. It is not the scale."),
L(""),
L("**Read this before going further, because everything downstream depends "
  "on it.**"),
L(""),
L("What you just plotted is one metered premise — a house, or one building. "
  "The model it is about to enter builds wind farms and grid batteries. "
  "Solving a capacity expansion for a single house against that "
  "cost library is not wrong so much as **meaningless**: you would be "
  "asking what utility-scale fleet to build for a 20 kW load, and the "
  "answer would be dominated by rounding."),
L(""),
L("So use your meter for what it is genuinely good for — **the shape**. "
  "When load rises and falls, how it responds to weather, how peaky it is. "
  "That shape is real, it is yours, and it is the thing no textbook can "
  "give you."),
L(""),
L("Then **state a scale separately**, and defend it. You are modelling a "
  "development made of premises like yours: a neighbourhood, an apartment "
  "complex, a mixed-use block."),
))

A(code(
L("# ---------------- the shape is yours. the scale is a decision. -----------"),
L("N_PREMISES = 2_000     # <-- STATE AND DEFEND THIS"),
L(""),
L("DEVELOPMENT = ('a mixed-use development of roughly 2,000 premises like '"),
L("               'the metered one - call it 1,500 dwellings plus commercial '"),
L("               'and common-area load')"),
L("# -------------------------------------------------------------------------"),
L(""),
L("site_demand_mw = one_premise_mw * N_PREMISES"),
L(""),
L("print(DEVELOPMENT)"),
L("print()"),
L("print(f'  peak demand    {site_demand_mw.max():>8,.1f} MW')"),
L("print(f'  annual energy  {site_demand_mw.sum()*RESOLUTION/1e3:>8,.1f} GWh')"),
L("print(f'  load factor    {site_demand_mw.mean()/site_demand_mw.max():>8.2f}')"),
))

A(md(
L("Check that number against something you know before you use it. A real "
  "development lands in the **megawatts** — single digits for a "
  "residential block, a few tens for something the size of the Metroplex "
  "Industrial Park you meet in Module 0B, which is 50 MW. A peak of "
  "0.02 MW means you forgot to scale. A peak of 5,000 MW means you have "
  "accidentally built a city, and should either say so or reduce "
  "`N_PREMISES`."),
L(""),
L("The load factor is the other check. Somewhere near 0.5 is ordinary for "
  "a mixed residential load. Close to 1.0 means your profile is nearly "
  "flat, which is worth explaining before Part 3 — a flat load gives a "
  "demand-side measure very little expensive peak to bite into."),
L(""),
L("**Two things to state in your write-up, because both are assumptions "
  "and neither is free:**"),
L(""),
L("1. **Where `N_PREMISES` came from.** A dwelling count from a site plan, "
  "a floor area divided by an intensity, a real development you looked up. "
  "\"2,000 because it made the numbers look nice\" is not a defence."),
L("2. **That you assumed perfect coincidence.** Multiplying one profile by "
  "2,000 assumes every premise peaks *at the same instant*. Real "
  "developments do not: individual peaks scatter, so an actual aggregate "
  "peak is lower and flatter than this. Your model therefore **overstates "
  "peakiness**, which biases it toward peaking capacity and storage, and — "
  "importantly for Part 3 — **overstates what a demand-side measure is "
  "worth**, because it inflates the expensive hours the measure gets to "
  "displace."),
L(""),
L("If you want to correct for that rather than just declare it, the cell "
  "below shrinks the variation around the mean while holding total energy "
  "fixed. It is a crude stand-in for diversity, so say that it is one."),
))

A(code(
L("COINCIDENCE = 1.00   # 1.00 = no correction (and say so)."),
L("                     # ~0.6 is a common residential aggregate figure -"),
L("                     # cite one if you use it."),
L(""),
L("mean_mw = site_demand_mw.mean()"),
L("site_demand_mw = mean_mw + (site_demand_mw - mean_mw) * COINCIDENCE"),
L(""),
L("print(f'after a coincidence factor of {COINCIDENCE:.2f}:')"),
L("print(f'  peak demand    {site_demand_mw.max():>8,.1f} MW')"),
L("print(f'  annual energy  {site_demand_mw.sum()*RESOLUTION/1e3:>8,.1f} GWh'"),
L("      f'   (unchanged - the correction moves the peak, not the energy)')"),
L("print(f'  load factor    {site_demand_mw.mean()/site_demand_mw.max():>8.2f}')"),
))

A(md(
L("Now solve it. This is the same model as the reference run — only the "
  "demand series changed."),
))

A(code(
L("n_own = build_1node_model(site_demand_mw, \"Your development (Part 1)\")"),
L("n_own.optimize(solver_name=SOLVER, env=ENV)"),
L("r_own = extract_results(n_own, \"Your development (Part 1)\")"),
L("compare_scenarios([r_reference, r_own])"),
))

A(md(
L("**Report:** how does the optimal build (wind/solar/battery MW) and total "
  "system cost change between the reference demand and your own? State one "
  "reason your demand's *shape* — not just its total — drives that "
  "difference."),
))

# ============================================================== Part 2
A(md(
L("---"),
L("## Part 2 — Disaggregate the load"),
L(""),
L("The 1-node model treats demand as one curve. Every demand-side "
  "technology this course names — weatherization, efficiency upgrades, "
  "heat pumps — acts on one **end use**, not the aggregate. This part "
  "splits your own demand into named end uses using two steps:"),
L(""),
L("1. **Weather-sensitive vs. baseline split** — the same degree-day "
  "regression method from Mini-Project 1, applied to your own profile "
  "instead of a new method."),
L("2. **Named end-use split** — cited typical shares, applied to divide the "
  "regression's two components into the categories a technology can "
  "actually target."),
L(""),
L("**Cited reference shares** (state these in your write-up, or replace "
  "them with your own source): the three largest US residential "
  "electricity end uses are air conditioning (19%), space heating (12%), "
  "and water heating (12%) of site electricity consumption — EIA, "
  "*Residential Energy Consumption Survey* 2020 "
  "(eia.gov/energyexplained/use-of-energy/electricity-use-in-homes.php). "
  "The remainder (57%) is lighting, refrigeration, electronics and other "
  "plug loads — EIA does not break this remainder down further at the "
  "site-electricity level, so it is treated here as one **baseline** "
  "category. If you have access to a finer-grained source (NREL ResStock/"
  "ComStock, or your own utility's disaggregation), cite it and split "
  "baseline further."),
))

A(code(
L("# Real daily-mean temperature for your metering period, fetched live -"),
L("# no API key required. Update LAT/LON to your own city."),
L("LAT, LON = 32.7767, -96.7970  # Dallas, TX — change to your own location"),
L(""),
L("def fetch_daily_temp_f(start_date, end_date, lat=LAT, lon=LON):"),
L("    url = ("),
L("        \"https://archive-api.open-meteo.com/v1/archive\""),
L("        f\"?latitude={lat}&longitude={lon}\""),
L("        f\"&start_date={start_date}&end_date={end_date}\""),
L("        \"&daily=temperature_2m_mean&temperature_unit=fahrenheit&timezone=auto\""),
L("    )"),
L("    r = requests.get(url, timeout=30).json()[\"daily\"]"),
L("    return pd.Series(r[\"temperature_2m_mean\"],"),
L("                      index=pd.to_datetime(r[\"time\"]), name=\"temp_f\")"),
L(""),
L("daily_kwh = own_demand_kw.resample(\"1D\").sum()"),
L("start, end = daily_kwh.index.min().date(), daily_kwh.index.max().date()"),
L("temp_f = fetch_daily_temp_f(str(start), str(end))"),
L("temp_f = temp_f.reindex(daily_kwh.index).interpolate()"),
))

A(code(
L("BASE_TEMP_F = 65  # standard degree-day base, same as Module 1"),
L("hdd = (BASE_TEMP_F - temp_f).clip(lower=0)"),
L("cdd = (temp_f - BASE_TEMP_F).clip(lower=0)"),
L(""),
L("# Regress daily kWh on HDD and CDD - the same method Mini-Project 1 used."),
L("X = np.column_stack([np.ones(len(daily_kwh)), hdd.values, cdd.values])"),
L("beta, *_ = np.linalg.lstsq(X, daily_kwh.values, rcond=None)"),
L("baseline_kwh_per_day, heat_slope, cool_slope = beta"),
L(""),
L("pred = X @ beta"),
L("ss_res = ((daily_kwh.values - pred) ** 2).sum()"),
L("ss_tot = ((daily_kwh.values - daily_kwh.values.mean()) ** 2).sum()"),
L("r2 = 1 - ss_res / ss_tot"),
L("print(f\"Weather-insensitive baseline: {baseline_kwh_per_day:,.1f} kWh/day\")"),
L("print(f\"Heating slope: {heat_slope:,.2f} kWh per HDD\")"),
L("print(f\"Cooling slope: {cool_slope:,.2f} kWh per CDD\")"),
L("print(f\"R-squared: {r2:.2f}  (Module 1's own regression on real smart-meter \""),
L("      \"data got cooling R2=0.68, heating R2=0.21 - a weak heating fit is \""),
L("      \"common, not a sign you did it wrong)\")"),
))

A(code(
L("# Reconstruct daily end-use series that sum back to the metered total."),
L("heating_kwh = (heat_slope * hdd).clip(lower=0)"),
L("cooling_kwh = (cool_slope * cdd).clip(lower=0)"),
L("baseline_total_kwh = daily_kwh - heating_kwh - cooling_kwh"),
L(""),
L("n_negative_days = (baseline_total_kwh < 0).sum()"),
L("print(f\"{n_negative_days} of {len(baseline_total_kwh)} days have a \""),
L("      \"NEGATIVE implied baseline (fitted heating+cooling exceeds actual \""),
L("      \"usage that day).\")"),
L("print(\"This is a real, common artifact of a linear degree-day fit on \""),
L("      \"real data - not a bug, and not something to clip away. It \""),
L("      \"usually means those days had unusually low occupancy/usage \""),
L("      \"relative to the outdoor temperature. Report the count in your \""),
L("      \"write-up rather than silently fixing it; clipping it to zero \""),
L("      \"would break the reconciliation-to-total this course requires.\")"),
L(""),
L("# EIA RECS 2020 shares (cited above) split the weather-insensitive"),
L("# baseline into water heating vs. everything else."),
L("SHARE_WATER_HEATING_OF_BASELINE = 0.12 / (1 - 0.19 - 0.12)  # 12% of total,"),
L("                                                              # renormalized"),
L("                                                              # onto baseline"),
L("water_heating_kwh = baseline_total_kwh * SHARE_WATER_HEATING_OF_BASELINE"),
L("other_baseline_kwh = baseline_total_kwh - water_heating_kwh"),
L(""),
L("end_uses = pd.DataFrame({"),
L("    \"heating\": heating_kwh, \"cooling\": cooling_kwh,"),
L("    \"water_heating\": water_heating_kwh, \"other_baseline\": other_baseline_kwh,"),
L("})"),
L("assert np.allclose(end_uses.sum(axis=1), daily_kwh, atol=1e-6), \\"),
L("    \"end uses must reconcile back to the metered total\""),
L(""),
L("print(\"Annual share of each end use:\")"),
L("print((end_uses.sum() / end_uses.sum().sum() * 100).round(1).astype(str) + \"%\")"),
L("end_uses.plot.area(figsize=(10, 3), title=\"Disaggregated daily load (kWh)\")"),
L("plt.tight_layout(); plt.show()"),
))

A(md(
L("**Report:**"),
L("- Your own annual share for each end use, next to the EIA reference "
  "shares. Where do they agree or disagree, and what about your specific "
  "home/meter could explain a disagreement (climate, home size, heating "
  "fuel, occupancy)?"),
L("- The count of negative-implied-baseline days printed above, and one "
  "sentence on what it tells you about the limits of a linear degree-day "
  "fit."),
))

# ============================================================== Part 3
A(md(
L("---"),
L("## Part 3 — Add a demand-side technology"),
L(""),
L("There are two ways to put a demand-side measure into this model, and "
  "they answer **different questions**. You are going to do both, in that "
  "order, because the difference between them is the whole point of this "
  "part."),
L(""),
L("1. **Cut the demand series and re-solve.** Asks: *if demand were 30% "
  "lower, what would we build?*"),
L("2. **Offer the measure to the solver as something it may buy.** Asks: "
  "*is this measure worth building at all, and at what price does that "
  "stop being true?*"),
L(""),
L("The first assumes the answer to the second. Only the second is an "
  "investment decision, and only the second can tell you that a measure "
  "is **not** worth doing."),
))

# ---------------------------------------------------------- 3.1 exogenous cut
A(md(
L("### 3.1 First, the version that looks obvious"),
L(""),
L("Weatherization improves the building envelope, so it reduces the "
  "heating and cooling end uses. The direct way to model that is to "
  "multiply those two columns down and re-solve."),
L(""),
L("**Cite your cut factor.** The DOE Weatherization Assistance Program "
  "reports roughly a 30% average heating-cost reduction in cold-weather "
  "states (energy.gov; ACEEE WAP fact sheet). It is applied to cooling as "
  "well here, since the envelope affects both — say in your write-up if "
  "you think cooling deserves a different factor."),
))

A(code(
L("CUT_PCT = 0.30   # <-- your cut factor, cited"),
L(""),
L("cut_end_uses = end_uses.copy()"),
L("cut_end_uses['heating'] *= (1 - CUT_PCT)"),
L("cut_end_uses['cooling'] *= (1 - CUT_PCT)"),
L(""),
L("# Rescale each hour by that day's change in total, keeping the intraday"),
L("# shape. A full appliance-level reshape is out of scope - name that as a"),
L("# limitation in your write-up."),
L("daily_ratio = (cut_end_uses.sum(axis=1) / daily_kwh).reindex("),
L("    own_demand_kw.index.floor('D')).values"),
L("cut_demand_kw = pd.Series(own_demand_kw.values * daily_ratio,"),
L("                          index=own_demand_kw.index)"),
L("cut_demand_mw = align_to_reference_calendar(cut_demand_kw, ts.index) * N_PREMISES"),
L(""),
L("print(f'peak demand   before {site_demand_mw.max():,.1f} MW'"),
L("      f'   after {cut_demand_mw.max():,.1f} MW')"),
))

A(code(
L("n_cut = build_1node_model(cut_demand_mw, 'Demand cut exogenously')"),
L("n_cut.optimize(solver_name=SOLVER, env=ENV)"),
L("r_cut = extract_results(n_cut, 'Demand cut exogenously')"),
L(""),
L("compare_scenarios([r_reference, r_own, r_cut])"),
))

A(md(
L("Now say precisely what that told you."),
L(""),
L("It told you what the system builds **given** a 30% cut. It did not tell "
  "you whether the 30% cut was worth paying for, because nothing in the "
  "model knew what it cost. You supplied that answer as an input and the "
  "model priced everything else around it."),
L(""),
L("That is a legitimate scenario study. It is not an investment decision. "
  "Notice too that the measure could not decline gracefully: you got "
  "exactly 30%, in every hour, whether or not it was earning its keep in "
  "that hour."),
))

# ------------------------------------------------- 3.2 investable resource
A(md(
L("### 3.2 The same measure, as something the solver can buy"),
L(""),
L("Here is the reframe that matters. **To an optimizer, a negawatt and a "
  "megawatt are the same object.** A megawatt of wind and a megawatt of "
  "avoided heating load both help close `Bus-nodal_balance`; both cost "
  "money to build; both are only available at certain hours. So model the "
  "measure the way you already model a generator."),
L(""),
L("Every investable resource in this model is defined by exactly three "
  "things, and weatherization has all three:"),
L(""),
L("| | wind | weatherization |"),
L("|---|---|---|"),
L("| what it costs to build | `capital_cost` from technology-data | annualised cost of the retrofit |"),
L("| when it is available | `p_max_pu` = the wind profile | `p_max_pu` = the heating + cooling load shape |"),
L("| how much you can have | site and land limits | you cannot save more than the end use consumes |"),
L(""),
L("The availability profile is the part people get wrong. Weatherization "
  "cannot deliver a negawatt in a mild week — there is no heating load to "
  "avoid. Its output is capped, hour by hour, by the size of the end use "
  "it displaces."),
))

A(md(
L("A word on units. Everything from here is in **MW**, because you scaled "
  "your single premise up to a development in Part 1 — that is what made "
  "this model worth solving. If a number below comes out in the "
  "hundredths, check `N_PREMISES`: you are probably still modelling one "
  "building."),
L(""),
L("The costs stay in **$ per MW**, which is an intensive quantity: it does "
  "not depend on how big your development is. That is exactly why you can "
  "compare it against the wind and solar figures from technology-data, and "
  "why the threshold you find in 3.3 is a statement about the *measure* "
  "rather than about your `N_PREMISES`."),
))

A(code(
L("# The load this measure can act on: the heating + cooling share of each"),
L("# day, mapped onto the model's snapshots."),
L("hc_share = (end_uses['heating'] + end_uses['cooling']) / daily_kwh"),
L("saveable_kw = pd.Series("),
L("    own_demand_kw.values"),
L("    * hc_share.reindex(own_demand_kw.index.floor('D')).values,"),
L("    index=own_demand_kw.index)"),
L("saveable_mw = align_to_reference_calendar(saveable_kw, ts.index) * N_PREMISES"),
L(""),
L("peak_saveable = saveable_mw.max()"),
L("dsm_p_max_pu = (saveable_mw / peak_saveable).clip(0, 1)"),
L(""),
L("print(f'peak heating+cooling load  {peak_saveable:,.1f} MW')"),
L("print(f'availability profile       min {dsm_p_max_pu.min():.3f}'"),
L("      f'   mean {dsm_p_max_pu.mean():.3f}   max {dsm_p_max_pu.max():.3f}')"),
))

A(md(
L("The ceiling. You cannot weatherize away more than the measure "
  "physically reaches, so `CUT_PCT` comes back — but doing an entirely "
  "different job. In 3.1 it was an **imposed reduction**. Here it is a "
  "**limit on how much you may build**. Same number, opposite role."),
))

A(code(
L("dsm_p_nom_max = CUT_PCT * peak_saveable"),
L(""),
L("# 'Did the solver build any?' has to be judged RELATIVE to the ceiling."),
L("# An absolute cut-off in MW silently reads every small development as"),
L("# 'built nothing', and you would get a threshold that is really just the"),
L("# edge of your own search range."),
L("BUILT_TOL = 1e-4 * dsm_p_nom_max"),
L(""),
L("print(f'most weatherization you could ever build  {dsm_p_nom_max:,.1f} MW')"),
L("print(f'counting anything above {BUILT_TOL:,.6f} MW as built')"),
))

A(md(
L("The cost. Annualise it with **the same `annuity()`** that the wind and "
  "solar capital costs went through in Part 0 — that is what makes the "
  "comparison fair. A retrofit lasts decades, so it earns a long "
  "lifetime."),
L(""),
L("**`DSM_INVESTMENT` is yours to source and defend.** Divide the "
  "installed cost of the measure by the peak load it removes. The value "
  "below is a starting point, not a citation."),
))

A(code(
L("DSM_INVESTMENT = 3_000_000    # $ per MW of peak load removed  <-- CITE YOURS"),
L("DSM_LIFETIME   = 25           # years - envelope measures are long-lived"),
L("DSM_DISCOUNT   = 0.07         # same rate as the technology-data default"),
L(""),
L("dsm_capital_cost = annuity(DSM_DISCOUNT, DSM_LIFETIME) * DSM_INVESTMENT"),
L(""),
L("print(f'weatherization  ${dsm_capital_cost:>10,.0f} per MW-year')"),
L("print(f'onshore wind    ${costs.at[\"onwind\", \"capital_cost\"]:>10,.0f} per MW-year')"),
L("print(f'solar           ${costs.at[\"solar\", \"capital_cost\"]:>10,.0f} per MW-year')"),
))

A(md(
L("Now add it to the model. **`p_nom_extendable=True` is the line that "
  "carries this entire part** — it is the difference between telling the "
  "model there is 30% less demand and asking the model whether to buy the "
  "thing that would deliver it."),
L(""),
L("`marginal_cost=0` because once the envelope is improved the saving "
  "costs nothing to run. That is genuinely different from a fuelled "
  "generator, and it is why demand-side resources tend to displace "
  "*fuel* before they displace capacity."),
L(""),
L("### Predict before you run"),
L(""),
L("At $3M per MW, do you expect the solver to build any weatherization at "
  "all? Write a number down before running the next cell — including "
  "zero, if that is your prediction."),
))

A(code(
L("n_dsm = build_1node_model(site_demand_mw, 'Weatherization as a resource')"),
L("n_dsm.add('Carrier', 'demand-side resource', color='seagreen')"),
L(""),
L("n_dsm.add('Generator', 'weatherization',"),
L("          bus='electricity',"),
L("          carrier='demand-side resource',"),
L("          p_max_pu=dsm_p_max_pu,          # WHEN it can deliver"),
L("          p_nom_max=dsm_p_nom_max,        # HOW MUCH you may build"),
L("          capital_cost=dsm_capital_cost,  # WHAT it costs to build"),
L("          marginal_cost=0.0,              # free to run once built"),
L("          p_nom_extendable=True)          # <-- THE line: the solver decides"),
L(""),
L("n_dsm.optimize(solver_name=SOLVER, env=ENV)"),
L("built = n_dsm.generators.p_nom_opt['weatherization']"),
L(""),
L("print(f'weatherization built  {built:,.1f} MW'"),
L("      f'   of a possible {dsm_p_nom_max:,.1f} MW')"),
L(""),
L("r_dsm = extract_results(n_dsm, 'Weatherization as a resource')"),
L("compare_scenarios([r_own, r_cut, r_dsm])"),
))

# ------------------------------------------------------------- 3.3 the sweep
A(md(
L("### 3.3 Move the price until it enters and drops out"),
L(""),
L("One cost gives you one answer. The question worth asking is **at what "
  "price does this measure stop being worth building** — because that "
  "number is not an assumption. It is a result, and it tells you exactly "
  "what the measure is worth to this system."),
L(""),
L("This is the first loop in the notebook and it is a legitimate one: you "
  "built the resource by hand above, and this repeats that identical step "
  "at different prices."),
L(""),
L("### Predict before you run"),
L(""),
L("Sketch the curve first. As the price rises, does the capacity built "
  "fall smoothly to zero, or drop off a cliff?"),
))

A(code(
L("# Anchor the range on what the measure actually competes against: the"),
L("# investment that would make a MW of weatherization cost the same per"),
L("# year as a MW of onshore wind. Your system's threshold could be well"),
L("# above or below that - the point is to bracket it, not to guess it."),
L("crf = annuity(DSM_DISCOUNT, DSM_LIFETIME)"),
L("wind_equivalent = costs.at['onwind', 'capital_cost'] / crf"),
L("print(f'wind costs ${costs.at[\"onwind\", \"capital_cost\"]:,.0f}/MW-yr'"),
L("      f'  = ${wind_equivalent:,.0f}/MW at your CRF')"),
L(""),
L("sweep = []"),
L("for investment in wind_equivalent * np.array("),
L("        [0.05, 0.1, 0.2, 0.4, 0.6, 0.8, 1.0, 1.5, 2.0, 3.0, 5.0]):"),
L("    n_s = build_1node_model(site_demand_mw, 'sweep')"),
L("    n_s.add('Carrier', 'demand-side resource', color='seagreen')"),
L("    n_s.add('Generator', 'weatherization', bus='electricity',"),
L("            carrier='demand-side resource',"),
L("            p_max_pu=dsm_p_max_pu, p_nom_max=dsm_p_nom_max,"),
L("            capital_cost=annuity(DSM_DISCOUNT, DSM_LIFETIME) * investment,"),
L("            marginal_cost=0.0, p_nom_extendable=True)"),
L("    n_s.optimize(solver_name=SOLVER, env=ENV)"),
L("    sweep.append({'investment_musd_per_mw': investment / 1e6,"),
L("                  'built_mw': n_s.generators.p_nom_opt['weatherization'],"),
L("                  'system_cost_musd': n_s.objective / 1e6})"),
L(""),
L("sweep = pd.DataFrame(sweep)"),
L("sweep"),
))

A(code(
L("fig, ax = plt.subplots(figsize=(8, 3.5))"),
L("ax.plot(sweep.investment_musd_per_mw, sweep.built_mw, marker='o')"),
L("ax.axhline(dsm_p_nom_max, ls='--', lw=0.8, color='grey')"),
L("ax.text(sweep.investment_musd_per_mw.min(), dsm_p_nom_max, ' ceiling',"),
L("        va='bottom', fontsize=8, color='grey')"),
L("ax.set_xlabel('weatherization investment cost ($M per MW)')"),
L("ax.set_ylabel('MW built')"),
L("ax.set_title('When does the solver stop buying weatherization?')"),
L("plt.tight_layout(); plt.show()"),
))

A(md(
L("Read the three regions off that curve:"),
L(""),
L("- **Cheap** — the solver builds the ceiling. Every MW on offer is worth "
  "having."),
L("- **In between** — a declining segment, and this is the interesting "
  "one. The *first* negawatt displaces your most expensive hour; the last "
  "one displaces a cheap hour. Marginal value falls as you build more, so "
  "the resource retreats gradually rather than vanishing."),
L("- **Expensive** — nothing. The measure is worth less than it costs."),
L(""),
L("If your curve has no middle region, your ceiling is probably binding so "
  "hard that the measure never gets to be marginal. Say so — that is a "
  "finding, not a failure."),
L(""),
L("Now find the crossing by bisection rather than by squinting at the "
  "plot. **Bracket it from the sweep you already ran** — one price where "
  "it still builds, one where it does not — rather than from a guessed "
  "range."),
L(""),
L("That is not fussiness. A bisection whose bracket does not actually "
  "contain the answer will still return a number: the edge of your own "
  "bracket, looking exactly like a result. It is the same trap as a "
  "balance that closes to exactly zero in SB1 — an artifact of how you "
  "set the problem up, wearing the costume of a finding."),
L(""),
L("So the cell below refuses to guess. If your measure built at every "
  "price, or at none of them, it stops and tells you which way to move "
  "the range."),
))

A(code(
L("# Bracket from the sweep you just ran, rather than from a guessed range."),
L("built_rows = sweep[sweep.built_mw > BUILT_TOL]"),
L("empty_rows = sweep[sweep.built_mw <= BUILT_TOL]"),
L(""),
L("if built_rows.empty:"),
L("    raise ValueError("),
L("        'The solver built nothing at ANY price in your sweep, so there is '"),
L("        'no threshold inside it. Your measure is worth less than the '"),
L("        'cheapest price you tested - lower the multipliers above and '"),
L("        're-run. Do NOT report the bottom of the range as the threshold.')"),
L("if empty_rows.empty:"),
L("    raise ValueError("),
L("        'The solver built the measure at EVERY price in your sweep, so '"),
L("        'the threshold is above your range - raise the multipliers above '"),
L("        'and re-run. Do NOT report the top of the range as the threshold.')"),
L(""),
L("lo = built_rows.investment_musd_per_mw.max() * 1e6   # still builds here"),
L("hi = empty_rows.investment_musd_per_mw.min() * 1e6   # builds nothing here"),
L("print(f'threshold is between ${lo:,.0f} and ${hi:,.0f} per MW - refining')"),
L(""),
L("for _ in range(16):"),
L("    mid = (lo + hi) / 2"),
L("    n_b = build_1node_model(site_demand_mw, 'bisect')"),
L("    n_b.add('Carrier', 'demand-side resource', color='seagreen')"),
L("    n_b.add('Generator', 'weatherization', bus='electricity',"),
L("            carrier='demand-side resource',"),
L("            p_max_pu=dsm_p_max_pu, p_nom_max=dsm_p_nom_max,"),
L("            capital_cost=annuity(DSM_DISCOUNT, DSM_LIFETIME) * mid,"),
L("            marginal_cost=0.0, p_nom_extendable=True)"),
L("    n_b.optimize(solver_name=SOLVER, env=ENV)"),
L("    if n_b.generators.p_nom_opt['weatherization'] > BUILT_TOL:"),
L("        lo = mid"),
L("    else:"),
L("        hi = mid"),
L(""),
L("if abs(lo - built_rows.investment_musd_per_mw.max() * 1e6) < 1e-9:"),
L("    raise ValueError("),
L("        'The bisection never moved its lower bound, so this is the edge '"),
L("        'of your bracket rather than a converged threshold. That is the '"),
L("        'exact failure this section warns about - check BUILT_TOL against '"),
L("        'the size of your ceiling before trusting any number here.')"),
L(""),
L("print(f'weatherization drops out of the optimum at')"),
L("print(f'  ${lo:,.0f} per MW of installed cost')"),
L("print(f'  = ${annuity(DSM_DISCOUNT, DSM_LIFETIME) * lo:,.0f} per MW-year annualised')"),
))

A(md(
L("**That number is the answer to Part 3.** It is what one MW of avoided "
  "heating and cooling load is worth to this system: the capacity it lets "
  "you not build, plus the energy it lets you not generate, over the "
  "measure's life."),
L(""),
L("You did not assume it. The model computed it, and it would move if your "
  "demand shape, your weather, or your generation costs moved."),
L(""),
L("Now compare it against what the retrofit actually costs. If the real "
  "cost sits below that line the measure is worth doing — and your "
  "`DSM_INVESTMENT` should have built something back in 3.2. If it sits "
  "above, you have just quantified by how much the measure misses, which "
  "is a more useful sentence than \"weatherization is a good idea\"."),
))

# --------------------------------------------------- 3.4 choose your own
A(md(
L("### 3.4 Your technology — specify one of the three"),
L(""),
L("Everything above used weatherization. Your assignment is to specify "
  "**one** of the three as a resource. Each needs the same three numbers, "
  "and each takes them from a different place:"),
L(""),
L("| | displaces | ceiling | availability `p_max_pu` |"),
L("|---|---|---|---|"),
L("| **Weatherization** | heating + cooling | cut % × peak of those two | heating + cooling load |"),
L("| **Efficiency upgrade (SEER)** | cooling only | (1 − SEER_old/SEER_new) × peak cooling | cooling load |"),
L("| **Heat pump, replacing electric resistance** | heating only | (1 − 1/COP) × peak heating | heating load |"),
L(""),
L("**The heat pump has a fourth case, and it is not a resource at all.** "
  "If the building currently heats with *gas*, switching to a heat pump "
  "**adds** electric load rather than removing it. It is not a negawatt "
  "generator; it is a new `Load`. The saving happens in gas, which is "
  "outside this model's boundary entirely — so this model cannot see the "
  "benefit and will report the switch as pure cost."),
L(""),
L("If you choose that case, say so explicitly, and say what you would have "
  "to bring inside the boundary to evaluate it honestly. That is a "
  "full-marks answer, and it is Module 0B's question arriving early."),
))

A(code(
L("# --- specify ONE, then re-run 3.2 and 3.3 with it ---"),
L("# DSM_NAME, DSM_END_USES, DSM_CEILING_FRACTION = 'weatherization', ['heating', 'cooling'], 0.30"),
L("# DSM_NAME, DSM_END_USES, DSM_CEILING_FRACTION = 'seer upgrade',   ['cooling'], 1 - 10 / 15"),
L("# DSM_NAME, DSM_END_USES, DSM_CEILING_FRACTION = 'heat pump',      ['heating'], 1 - 1 / 2.8"),
L(""),
L("if 'DSM_NAME' not in globals():"),
L("    raise NameError("),
L("        'Uncomment exactly ONE of the three lines above. Part 3 asks you '"),
L("        'to choose a demand-side technology and defend the three numbers '"),
L("        'that define it - the notebook will not choose for you.')"),
L(""),
L("my_share = end_uses[DSM_END_USES].sum(axis=1) / daily_kwh"),
L("my_saveable_kw = pd.Series("),
L("    own_demand_kw.values"),
L("    * my_share.reindex(own_demand_kw.index.floor('D')).values,"),
L("    index=own_demand_kw.index)"),
L("my_saveable_mw = align_to_reference_calendar(my_saveable_kw, ts.index) * N_PREMISES"),
L(""),
L("my_p_max_pu = (my_saveable_mw / my_saveable_mw.max()).clip(0, 1)"),
L("my_p_nom_max = DSM_CEILING_FRACTION * my_saveable_mw.max()"),
L(""),
L("print(f'{DSM_NAME}: acts on {DSM_END_USES}')"),
L("print(f'  peak addressable load  {my_saveable_mw.max():,.1f} MW')"),
L("print(f'  ceiling                {my_p_nom_max:,.1f} MW')"),
L("print()"),
L("print('Re-run 3.2 and 3.3 with my_p_max_pu and my_p_nom_max, and report')"),
L("print('the price at which YOUR technology enters and drops out.')"),
))

A(md(
L("**Report:**"),
L("- The three numbers defining your resource — cost, availability, "
  "ceiling — each with a source."),
L("- The price at which it enters the optimum, and the price at which it "
  "drops out."),
L("- **What it displaced.** Compare the build in `r_own` against your DSM "
  "run: which technology got smaller, and does that make sense given "
  "*when* your measure is available?"),
L("- The difference between 3.1 and 3.2 in your own words — what question "
  "did each one answer?"),
L("- One demand-side technology you did **not** model, and what data you "
  "would need to add it (appliance-level submetering for a cooking-fuel "
  "switch, say, or an envelope audit for a deeper weatherization "
  "estimate)."),
))

# The facility question is four source elements - rule, blank, the
# question, blank - because that is what the notebook carries. It was
# a bare string here once, which emitted no trailing newline and ran
# the question into the next heading. See Tools/check_builders.py.
A(md(
L("---"),
L(""),
L("*Before class: this notebook worked from metered interval data rather than a forecast. What can you say about this building that you could not say about a region, and what did you give up to get it?*"),
L(""),
))

# ================================================================== write
NOTEBOOK = {
    "cells": CELLS,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "pygments_lexer": "ipython3"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(NOTEBOOK, f, indent=1, ensure_ascii=False)
    print("wrote", OUT)
    print("cells:", len(CELLS))
