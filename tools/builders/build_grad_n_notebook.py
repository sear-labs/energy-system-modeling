# -*- coding: utf-8 -*-
"""build_grad_n_notebook.py - write `2026 Fall/Notebooks/GRAD_N_Real_Network_Import.ipynb`,
the student-facing notebook for the GRAD-N assignment (Assignment Catalog Part Four,
IE 5300 / IE 6301 only).

Follows the standard set by `build_1n_notebook.py`: real data, and every
non-solver code path actually executed against it before shipping.  In this
case the solver paths were run too - the whole 123-bus DC OPF solves in about
two seconds with HiGHS, so there was no reason not to.

WHAT WAS ACTUALLY RUN (this session, PyPSA 1.3.0 + HiGHS 1.15.1):

  * The ranged-ZIP reader below really does pull the four TX-123BT
    configuration files out of the 544 MB Figshare archive using about 1.3 MB
    of HTTP range requests, in roughly seven seconds.  Verified.
  * The full import -> DC OPF -> LMP pipeline, on 15 February 2021 (day 46 of
    the 2021 profiles - Winter Storm Uri).  123 buses, 255 lines, 292
    generators, 24 snapshots; solves in ~2 s.
  * Both ACTIVSg imports in Part 6.

FIVE REAL DATA DEFECTS/TRAPS FOUND BY RUNNING IT, all of which the notebook
now makes students find rather than hiding:

  1. `Line_data.csv` header says
     `From Bus Latitude, From Bus Longitude, To Bus Latitude, To Bus Longitude`
     but the columns are actually ordered From-lat, TO-lat, From-lon, To-lon.
     Checked against `Bus_data.csv`: the corrected mapping matches to 0.0000
     mean absolute error, the labelled mapping is off by 128.85 degrees.
  2. The load profile is (24 hours x 123 buses) while the solar and wind
     profiles are (plants x 24 hours).  Opposite orientation, same folder.
  3. `Generator_data.xlsx` labels the no-load cost column `C0($/MWh)`; it is a
     $/h no-load cost, not a $/MWh energy cost.  `C1($/MWh)` is the real
     marginal cost.
  4. `import_from_pypower_ppc` carries MATPOWER's *solved dispatch* `Pg` into
     the static `generators.p_set` column, and PyPSA then writes a
     `Generator-p_set` equality constraint that pins every generator to it.
     The result is an over-determined problem that comes back `infeasible`
     with no useful message.  `n.generators["p_set"] = np.nan` releases it.
     This one cost real debugging time and is the single most useful thing in
     Part 6.
  5. `import_from_pypower_ppc` does not carry `gencost` across at all, so the
     objective is empty and PyPSA refuses to build a model until
     `marginal_cost` is set by hand.

ONE ERROR IN THE ASSIGNMENT CATALOG, found here and worth fixing there:
  ACTIVSg500 is a synthetic *South Carolina* system ("Synthetic South Carolina
  500-bus power system model", case header).  The Texas synthetic case is
  ACTIVSg2000.  The catalog's Stage 2 names ACTIVSg500 as the Texas follow-on,
  which loses the like-for-like comparison the stage is for.  This notebook
  offers ACTIVSg2000 as the Texas comparison and ACTIVSg500 as the smaller,
  faster option when scale alone is the point.

Run from Tools/:  python build_grad_n_notebook.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "2026 Fall", "Notebooks",
                   "GRAD_N_Real_Network_Import.ipynb")

_N = [0]


def _id():
    _N[0] += 1
    return "cell-%02d" % _N[0]


def md(*lines):
    return {"cell_type": "markdown", "id": _id(), "metadata": {},
            "source": list(lines)}


def code(*lines):
    return {"cell_type": "code", "id": _id(), "execution_count": None,
            "metadata": {}, "outputs": [], "source": list(lines)}


def L(s):
    return s + "\n"


C = []
A = C.append

# ================================================================== title
A(md(
L("# GRAD-N: Real Network Import — TX-123BT, then TAMU ACTIVSg"),
L("## REE 4301 / IE 5300 / IE 6301 — Energy Systems Modeling"),
L("### Graduate sections only. Individual work. After Mini-Project 3."),
L(""),
L("**The problem this assignment exists to solve.** Every network you have "
  "built in this course has between three and six nodes. You have reported "
  "binding constraints, congestion rents, and locational marginal prices from "
  "those models. None of them has ever been checked against a network that "
  "looks anything like the real thing."),
L(""),
L("Here you import **TX-123BT** — a synthetic 123-bus, 345 kV backbone that "
  "mirrors ERCOT's spatial and temporal characteristics, with five years of "
  "weather-driven hourly profiles — solve a DC optimal power flow on it, and "
  "compare what it says to what your own aggregated model said."),
L(""),
L("**What you will learn:**"),
L("- How to get a real network dataset into PyPSA, including the parts that "
  "do not import cleanly"),
L("- Why *validating* data you did not create is most of the work — this "
  "dataset has at least three defects you will find in Part 1"),
L("- How much of your Mini-Project 3 answer was an artefact of aggregation"),
L("- That spatial resolution is a modelling choice with a cost, not a detail"),
L(""),
L("**Stage 1 (Parts 0–5) is required. Stage 2 (Part 6) is an optional "
  "extension.**"),
L(""),
L("---"),
L("### The dataset"),
L(""),
L("Jin Lu, Xingpeng Li, Hongyi Li, Taher Chegini, Carlos Gamarra, Y. C. Ethan "
  "Yang, Margaret Cook, and Gavin Dillingham, *A Synthetic Texas Backbone "
  "Power System with Climate-Dependent Spatio-Temporal Correlated Profiles*. "
  "Dataset: DOI [10.6084/m9.figshare.22144616]"
  "(https://doi.org/10.6084/m9.figshare.22144616), CC BY 4.0. "
  "Landing page: <https://rpglab.github.io/resources/TX-123BT/>."),
L(""),
L("**Cite it in your report.** The licence requires attribution."),
))

# =================================================================== setup

A(md(
L("---"),
L("## Part 0 — Setup and data acquisition"),
L(""),
L("The complete TX-123BT release is a **544 MB ZIP** — five years of hourly "
  "climate, load, solar, wind and line-rating profiles. You need four small "
  "files out of it (about 67 KB total) plus one day of profiles."),
L(""),
L("Rather than download half a gigabyte, the cell below reads the archive's "
  "central directory over HTTP **range requests** and pulls out only the "
  "members it needs. This is worth knowing as a technique in its own right: "
  "it works on any static ZIP served by a host that honours "
  "`Range:` headers, and it turns a 544 MB download into about 1.3 MB."),
))

A(code(
L("!pip install -q pypsa highspy openpyxl"),
))

A(md(
L('---\n'),
L('### Choosing a solver\n'),
L('\n'),
L("This notebook defaults to **HiGHS**, which is open source, needs no licence, and has no size limit — because every model in it is well past what Gurobi's free licence allows. Gurobi is still the faster option if you have an academic key; see below.\n"),
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
L("SOLVER = 'highs'      # this notebook's models are far over the\n"),
L('                      # restricted-licence ceiling, so HiGHS is\n'),
L('                      # the default here\n'),
L("# SOLVER = 'gurobi'   # <-- faster, but needs a WLS key for models this size\n"),
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

A(code(
L("import io"),
L("import zipfile"),
L(""),
L("import numpy as np"),
L("import pandas as pd"),
L("import requests"),
L("import matplotlib.pyplot as plt"),
L(""),
L("pd.set_option('display.width', 120)"),
L(""),
L(""),
L("class HttpFile(io.RawIOBase):"),
L('    """A seekable read-only file over HTTP range requests.'),
L(""),
L("    Enough of the file protocol for `zipfile` to work with: it reads the"),
L("    end-of-central-directory record, then only the members you ask for."),
L('    """'),
L(""),
L("    def __init__(self, url, session=None):"),
L("        self.url = url"),
L("        self.s = session or requests.Session()"),
L("        self.pos = 0"),
L("        self.n_requests = 0"),
L("        self.n_bytes = 0"),
L("        r = self.s.get(url, headers={'Range': 'bytes=0-0'},"),
L("                       timeout=60, stream=True)"),
L("        r.raise_for_status()"),
L("        if 'Content-Range' not in r.headers:"),
L("            raise RuntimeError('server does not support range requests')"),
L("        self.size = int(r.headers['Content-Range'].split('/')[1])"),
L("        r.close()"),
L(""),
L("    def readable(self):"),
L("        return True"),
L(""),
L("    def seekable(self):"),
L("        return True"),
L(""),
L("    def tell(self):"),
L("        return self.pos"),
L(""),
L("    def seek(self, offset, whence=0):"),
L("        self.pos = (offset if whence == 0 else"),
L("                    self.pos + offset if whence == 1 else"),
L("                    self.size + offset)"),
L("        return self.pos"),
L(""),
L("    def read(self, n=-1):"),
L("        if n is None or n < 0:"),
L("            n = self.size - self.pos"),
L("        if n == 0 or self.pos >= self.size:"),
L("            return b''"),
L("        end = min(self.pos + n, self.size) - 1"),
L("        r = self.s.get(self.url,"),
L("                       headers={'Range': f'bytes={self.pos}-{end}'},"),
L("                       timeout=120)"),
L("        r.raise_for_status()"),
L("        data = r.content"),
L("        self.pos += len(data)"),
L("        self.n_requests += 1"),
L("        self.n_bytes += len(data)"),
L("        return data"),
L(""),
L(""),
L("TX123_ZIP = 'https://ndownloader.figshare.com/files/44942761'"),
L("remote = HttpFile(TX123_ZIP)"),
L("archive = zipfile.ZipFile(remote)"),
L("print(f'archive: {remote.size/1e6:.1f} MB, "
  "{len(archive.namelist()):,} members')"),
))

A(md(
L("### Choose your day"),
L(""),
L("The profiles cover 2017–2021. The default below is **day 46 of 2021 — "
  "15 February 2021**, the second day of Winter Storm Uri, because it is the "
  "most interesting 24 hours in the dataset and it connects directly to "
  "Chapter 15 of the book."),
L(""),
L("You may pick a different day. If you do, say which and why in your report — "
  "the day you choose changes every number you will report."),
))

A(code(
L("YEAR = 2021"),
L("DAY = 46          # day-of-year, 1-365.  46 = 15 Feb 2021 (Winter Storm Uri)"),
L(""),
L("P = 'Data_public_5year/'"),
L("WANT = {"),
L("    'bus':    P + 'Bus_data.csv',"),
L("    'line':   P + 'Line_data.csv',"),
L("    'gen':    P + 'Generator_data.xlsx',"),
L("    'readme': P + 'Readme.txt',"),
L("    'load':   P + f'Load_5y/Load_annual_{YEAR}/load_annual_D{DAY}.txt',"),
L("    'solar':  P + f'Solar_5y/solar_{YEAR}/solar_annual_D{DAY}.txt',"),
L("    'wind':   P + f'Wind_5y/wind_{YEAR}/wind_annual_D{DAY}.txt',"),
L("    'rating': P + f'Daily_line_rating_5y/line_annual_{YEAR}.txt',"),
L("}"),
L(""),
L("raw = {}"),
L("for key, member in WANT.items():"),
L("    raw[key] = archive.read(member)"),
L("    print(f'  {len(raw[key]):>9,} bytes  {member}')"),
L(""),
L("print(f'\\ndownloaded {remote.n_bytes/1024:,.0f} KB in "
  "{remote.n_requests} range requests '"),
L("      f'instead of {remote.size/1e6:.0f} MB')"),
))

# ============================================================== validate
A(md(
L("---"),
L("## Part 1 — Validate before you trust"),
L(""),
L("You did not create this data and the people who did are not available to "
  "answer questions. Before any of it goes into a model, check that it says "
  "what its column headers claim it says."),
L(""),
L("This is not a formality. **There are at least three defects in the files "
  "you just downloaded.** Two of them are found below; the third is left for "
  "you in the exercise at the end of this Part."),
))

A(code(
L("bus = pd.read_csv(io.BytesIO(raw['bus']))"),
L("line = pd.read_csv(io.BytesIO(raw['line']))"),
L("gen = pd.read_excel(io.BytesIO(raw['gen']), sheet_name='Gen data')"),
L("solar_map = pd.read_excel(io.BytesIO(raw['gen']),"),
L("                          sheet_name='Solar Plant Number')"),
L("wind_map = pd.read_excel(io.BytesIO(raw['gen']),"),
L("                         sheet_name='Wind Plant Number')"),
L(""),
L("load = np.loadtxt(io.BytesIO(raw['load']))"),
L("solar = np.loadtxt(io.BytesIO(raw['solar']))"),
L("wind = np.loadtxt(io.BytesIO(raw['wind']))"),
L("daily_rating = np.loadtxt(io.BytesIO(raw['rating']))"),
L(""),
L("print('bus  ', bus.shape, list(bus.columns))"),
L("print('line ', line.shape)"),
L("print('gen  ', gen.shape, list(gen.columns))"),
L("print()"),
L("print('load  ', load.shape)"),
L("print('solar ', solar.shape)"),
L("print('wind  ', wind.shape)"),
L("print('rating', daily_rating.shape, '(lines x days)')"),
))

A(md(
L("### Defect 1 — the profile arrays are not oriented the same way"),
L(""),
L("Look at the three shapes above. The load file is "
  "**(24 hours × 123 buses)**. The solar and wind files are "
  "**(plants × 24 hours)** — transposed relative to the load file, in the "
  "same release, documented correctly in `Readme.txt` and easy to miss."),
L(""),
L("Get this wrong and nothing raises an error; you simply model a different "
  "system. Assert the orientation rather than assuming it."),
))

A(code(
L("N_HOURS = 24"),
L("assert load.shape == (N_HOURS, len(bus)), \\"),
L("    f'expected load as (hours, buses), got {load.shape}'"),
L("assert solar.shape == (len(solar_map), N_HOURS), \\"),
L("    f'expected solar as (plants, hours), got {solar.shape}'"),
L("assert wind.shape == (len(wind_map), N_HOURS), \\"),
L("    f'expected wind as (plants, hours), got {wind.shape}'"),
L(""),
L("system_load = load.sum(axis=1)"),
L("print(f'system load: min {system_load.min():,.0f} MW  '"),
L("      f'peak {system_load.max():,.0f} MW  '"),
L("      f'energy {load.sum():,.0f} MWh')"),
L("print(f'wind fleet:  {wind.sum(axis=0).min():,.0f} - "
  "{wind.sum(axis=0).max():,.0f} MW')"),
L("print(f'solar fleet: peak {solar.sum(axis=0).max():,.0f} MW')"),
))

A(md(
L("### Defect 2 — `Line_data.csv`'s coordinate columns are mislabelled"),
L(""),
L("The header reads `From Bus Latitude, From Bus Longitude, To Bus Latitude, "
  "To Bus Longitude`. The values are ordered **From-latitude, To-latitude, "
  "From-longitude, To-longitude**: columns 8 and 9 are swapped relative to "
  "their labels."),
L(""),
L("You can prove this rather than guess it, because `Bus_data.csv` gives the "
  "true coordinate of every bus. Check each candidate mapping against it and "
  "keep the one with zero error."),
))

A(code(
L("coords = bus.set_index('Bus Number')"),
L("truth = {"),
L("    'from-lat': coords['Bus latitude'].loc[line['From Bus Number']].values,"),
L("    'to-lat':   coords['Bus latitude'].loc[line['To Bus Number']].values,"),
L("    'from-lon': coords['Bus longitude'].loc[line['From Bus Number']].values,"),
L("    'to-lon':   coords['Bus longitude'].loc[line['To Bus Number']].values,"),
L("}"),
L("cols = list(line.columns)"),
L("claimed = {7: 'from-lat', 8: 'from-lon', 9: 'to-lat', 10: 'to-lon'}"),
L(""),
L("print('mean absolute error against the true bus coordinates, in degrees:')"),
L("print(f\"{'col':>4}  {'header says':<22}{'error if believed':>18}"
  "  {'best match':<9}{'error':>9}\")"),
L("for j, says in claimed.items():"),
L("    v = line[cols[j]].values"),
L("    errs = {k: float(np.abs(v - t).mean()) for k, t in truth.items()}"),
L("    best = min(errs, key=errs.get)"),
L("    flag = '' if best == says else '   <-- MISLABELLED'"),
L("    print(f'{j:>4}  {cols[j]:<22}{errs[says]:>18.4f}  '"),
L("          f'{best:<9}{errs[best]:>9.4f}{flag}')"),
L(""),
L("print('\\nColumns 8 and 9 are swapped relative to their headers. '"),
L("      'True order: From-lat, To-lat, From-lon, To-lon.')"),
L("line = line.rename(columns={"),
L("    cols[7]: 'from_lat', cols[8]: 'to_lat',"),
L("    cols[9]: 'from_lon', cols[10]: 'to_lon'})"),
))

A(md(
L("### The sanity check that catches this without any arithmetic"),
L(""),
L("Plot the network. If the coordinates are wired up correctly it looks like "
  "Texas; if they are not, it looks like nothing. **Plot every network you "
  "import, before you solve it.**"),
))

A(code(
L("fig, ax = plt.subplots(figsize=(7.5, 8))"),
L("for _, r in line.iterrows():"),
L("    ax.plot([r['from_lon'], r['to_lon']], [r['from_lat'], r['to_lat']],"),
L("            color='0.7', lw=0.8, zorder=1)"),
L("gen_bus = set(gen['Bus Number'])"),
L("is_gen = bus['Bus Number'].isin(gen_bus)"),
L("ax.scatter(bus.loc[~is_gen, 'Bus longitude'], bus.loc[~is_gen, 'Bus latitude'],"),
L("           s=14, color='#0064B1', zorder=2, label='load-only bus')"),
L("ax.scatter(bus.loc[is_gen, 'Bus longitude'], bus.loc[is_gen, 'Bus latitude'],"),
L("           s=26, color='#DE6B1A', zorder=3, label='generator bus')"),
L("ax.set_title(f'TX-123BT: {len(bus)} buses, {len(line)} lines, 345 kV backbone')"),
L("ax.set_xlabel('longitude'); ax.set_ylabel('latitude')"),
L("ax.legend(frameon=False); ax.set_aspect(1.15)"),
L("plt.tight_layout(); plt.show()"),
))

A(md(
L("### The generator table"),
L(""),
L("Two things to notice, one of which is the third defect."),
L(""),
L("The **fuel mix** should look like ERCOT: gas-dominated, a lot of wind, a "
  "little coal and nuclear. Check that it does."),
L(""),
L("The **cost columns** are `C0($/MWh)` and `C1($/MWh)`. Both are labelled "
  "per-MWh. Look at the nuclear unit: `C0 = 0`, `C1 = 17.44`. Now look at a "
  "gas unit: `C0 = 597` on a 305 MW machine. A no-load cost of $597/MWh is "
  "not credible; a no-load cost of **$597 per hour** is. `C0` is a $/h "
  "no-load cost with a wrong unit label, and `C1` is the marginal cost you "
  "want. Using `C0` as an energy cost would inflate dispatch cost by two "
  "orders of magnitude on some units."),
))

A(code(
L("mix = gen.groupby('Fuel type')['Pmax (MW)'].agg(['count', 'sum'])"),
L("mix['share'] = 100 * mix['sum'] / mix['sum'].sum()"),
L("print(mix.round(1).to_string())"),
L("print(f\"\\ntotal installed {gen['Pmax (MW)'].sum():,.0f} MW \""),
L("      f'against a {system_load.max():,.0f} MW peak')"),
L("print()"),
L("print(gen.loc[gen['Fuel type'].isin(['Nuclear', 'Natural Gas']),"),
L("             ['Gen Number', 'Fuel type', 'Pmax (MW)', 'C0($/MWh)',"),
L("              'C1($/MWh)', 'Csu($)']].head(6).to_string(index=False))"),
))

A(md(
L("> **Exercise 1.1 — find the third defect.** One of the two remaining "
  "quantities you are about to model has a documented meaning that does not "
  "match how a first reading of the file would suggest using it. Compare the "
  "static `Capacity (MW)` column in `Line_data.csv` against the daily values "
  "in `daily_rating` for your chosen day. State what the difference is, which "
  "one the dataset's own sample SCUC code uses, and why a **cold** day pushes "
  "the number in the direction it does. Part 4 turns this into an experiment; "
  "answer it here first, from the data."),
))

# ================================================================== build
A(md(
L("---"),
L("## Part 2 — Build the network in PyPSA"),
L(""),
L("Three unit conversions matter, and none of them is checked for you."),
L(""),
L("**Impedance.** `R, pu` and `X, pu` are per-unit on the system base. PyPSA "
  "wants ohms. With a 100 MVA base at 345 kV the base impedance is "
  "345² / 100 = 1,190.25 Ω, so `x_ohm = x_pu × 1190.25`. Get this wrong by a "
  "constant factor and the *relative* impedances stay right, so the flows "
  "look plausible and are wrong."),
L(""),
L("**Renewable output.** The solar and wind files give **MW produced**, not a "
  "capacity factor. PyPSA's `p_max_pu` is a fraction of `p_nom`, so divide by "
  "the plant's `Pmax` and clip to [0, 1]."),
L(""),
L("**Commitment.** Many units have `Pmin > 0`. That is a unit-commitment "
  "constraint and needs binary variables. This notebook solves the linear "
  "relaxation (`p_min_pu = 0`), which is what makes it run in seconds instead "
  "of minutes. **Say so in your report** — it is the single largest "
  "difference between this model and the SCUC the dataset ships."),
))

A(code(
L("import pypsa"),
L(""),
L("BASE_MVA = 100.0"),
L("V_NOM = 345.0"),
L("Z_BASE = V_NOM ** 2 / BASE_MVA          # 1190.25 ohm"),
L("VOLL = 9000.0                           # $/MWh value of lost load"),
L(""),
L(""),
L("def build_tx123(line_rating=None, voll=VOLL):"),
L('    """Assemble TX-123BT as a PyPSA network for one 24-hour day.'),
L(""),
L("    line_rating : None -> use the static `Capacity (MW)` column"),
L("                  array  -> per-line MW rating to use instead"),
L("    voll        : add a load-shedding generator at every bus at this price."),
L("                  Always do this on an imported network.  Without it an"),
L("                  over-constrained hour returns `infeasible` and tells you"),
L("                  nothing; with it you get MWh unserved, and where."),
L('    """'),
L("    n = pypsa.Network(name='TX-123BT')"),
L("    n.set_snapshots(pd.RangeIndex(N_HOURS, name='hour'))"),
L("    n.add('Carrier', 'AC')"),
L(""),
L("    n.add('Bus', ('B' + bus['Bus Number'].astype(str)).values,"),
L("          v_nom=V_NOM, carrier='AC',"),
L("          x=bus['Bus longitude'].values, y=bus['Bus latitude'].values)"),
L(""),
L("    s_nom = (line['Capacity (MW)'].values if line_rating is None"),
L("             else np.asarray(line_rating, dtype=float))"),
L("    n.add('Line', ('L' + line['line_num'].astype(str)).values,"),
L("          bus0=('B' + line['From Bus Number'].astype(str)).values,"),
L("          bus1=('B' + line['To Bus Number'].astype(str)).values,"),
L("          carrier='AC',"),
L("          r=line['R, pu'].values * Z_BASE,"),
L("          x=line['X, pu'].values * Z_BASE,"),
L("          s_nom=s_nom,"),
L("          length=line['Length (Mile)'].values * 1.60934)"),
L(""),
L("    for fuel in gen['Fuel type'].unique():"),
L("        n.add('Carrier', fuel)"),
L("    solar_of = dict(zip(solar_map['Generator Number'],"),
L("                        solar_map['Solar Plant Number']))"),
L("    wind_of = dict(zip(wind_map['Generator Number'],"),
L("                       wind_map['Wind Plant Number']))"),
L(""),
L("    for _, g in gen.iterrows():"),
L("        gid = int(g['Gen Number'])"),
L("        pmax = float(g['Pmax (MW)'])"),
L("        kw = dict(bus=f\"B{int(g['Bus Number'])}\", carrier=g['Fuel type'],"),
L("                  p_nom=pmax,"),
L("                  marginal_cost=float(g['C1($/MWh)']),   # NOT C0"),
L("                  p_min_pu=0.0)                          # LP relaxation"),
L("        if gid in solar_of and pmax > 0:"),
L("            kw['p_max_pu'] = pd.Series("),
L("                np.clip(solar[solar_of[gid] - 1] / pmax, 0, 1),"),
L("                index=n.snapshots)"),
L("        elif gid in wind_of and pmax > 0:"),
L("            kw['p_max_pu'] = pd.Series("),
L("                np.clip(wind[wind_of[gid] - 1] / pmax, 0, 1),"),
L("                index=n.snapshots)"),
L("        n.add('Generator',"),
L("              f\"G{gid}_{g['Fuel type'].replace(' ', '')}\", **kw)"),
L(""),
L("    if voll is not None:"),
L("        n.add('Carrier', 'load shedding')"),
L("    for j, b in enumerate(bus['Bus Number']):"),
L("        n.add('Load', f'D{b}', bus=f'B{b}',"),
L("              p_set=pd.Series(load[:, j], index=n.snapshots))"),
L("        if voll is not None:"),
L("            n.add('Generator', f'SHED{b}', bus=f'B{b}',"),
L("                  carrier='load shedding',"),
L("                  p_nom=float(load[:, j].max()) * 1.5 + 1.0,"),
L("                  marginal_cost=voll)"),
L("    return n"),
L(""),
L(""),
L("n = build_tx123()"),
L("print(f'{len(n.buses)} buses | {len(n.lines)} lines | '"),
L("      f'{len(n.generators)} generators | {len(n.loads)} loads | '"),
L("      f'{len(n.snapshots)} snapshots')"),
))

# ================================================================== solve
A(md(
L("---"),
L("## Part 3 — Solve the DC optimal power flow"),
L(""),
L("PyPSA writes the linearised power-flow constraints of Chapter 18 — "
  "Kirchhoff's voltage law around every independent loop, plus a nodal "
  "balance at every bus — and minimises dispatch cost subject to line "
  "thermal limits."),
))

A(code(
L("status, condition = n.optimize(solver_name=SOLVER, env=ENV)"),
L("print(status, condition)"),
))

A(code(
L("def summarise(n, label=''):"),
L('    """Report the four things worth reporting from a solved network."""'),
L("    shed_cols = [c for c in n.generators_t.p.columns"),
L("                 if c.startswith('SHED')]"),
L("    shed = n.generators_t.p[shed_cols]"),
L("    unserved = shed.to_numpy().sum()"),
L("    lmp = n.buses_t.marginal_price"),
L("    util = n.lines_t.p0.abs().div(n.lines.s_nom, axis=1)"),
L("    binding = util.max()[util.max() > 0.999].sort_values(ascending=False)"),
L("    print(f'--- {label}')"),
L("    print(f'    daily cost        ${n.objective:,.0f}')"),
L("    print(f'    unserved energy   {unserved:,.1f} MWh')"),
L("    print(f'    LMP               ${lmp.to_numpy().min():,.2f} .. '"),
L("          f'${lmp.to_numpy().max():,.2f} /MWh '"),
L("          f'(mean ${lmp.to_numpy().mean():,.2f})')"),
L("    print(f'    binding lines     {len(binding)}')"),
L("    return binding, unserved"),
L(""),
L(""),
L("binding, unserved = summarise(n, "),
L("                              f'static Capacity column, day {DAY} of {YEAR}')"),
))

A(code(
L("names = bus.set_index('Bus Number')['Bus Name']"),
L(""),
L(""),
L("def congestion_table(n, top=8):"),
L('    """Which corridors bind, for how many hours, and between where."""'),
L("    util = n.lines_t.p0.abs().div(n.lines.s_nom, axis=1)"),
L("    rows = []"),
L("    for ln in util.max().sort_values(ascending=False).head(top).index:"),
L("        b0 = int(n.lines.at[ln, 'bus0'][1:])"),
L("        b1 = int(n.lines.at[ln, 'bus1'][1:])"),
L("        rows.append({"),
L("            'line': ln,"),
L("            'from': names[b0], 'to': names[b1],"),
L("            'rating MW': round(n.lines.at[ln, 's_nom'], 0),"),
L("            'peak use %': round(100 * util[ln].max(), 1),"),
L("            'hours binding': int((util[ln] > 0.999).sum()),"),
L("        })"),
L("    return pd.DataFrame(rows)"),
L(""),
L(""),
L("print(congestion_table(n).to_string(index=False))"),
))

A(code(
L("gen_mix = (n.generators_t.p.T.groupby(n.generators.carrier).sum().sum(axis=1)"),
L("           .sort_values(ascending=False))"),
L("gen_mix = gen_mix[gen_mix > 0.5]"),
L("print('generation over the day (MWh):')"),
L("for carrier, mwh in gen_mix.items():"),
L("    print(f'  {carrier:16s} {mwh:12,.0f}   {100*mwh/gen_mix.sum():5.1f}%')"),
L(""),
L("fig, ax = plt.subplots(1, 2, figsize=(13, 4))"),
L("(n.generators_t.p.T.groupby(n.generators.carrier).sum().T"),
L(" .loc[:, gen_mix.index].plot.area(ax=ax[0], lw=0, alpha=0.85))"),
L("n.loads_t.p_set.sum(axis=1).plot(ax=ax[0], color='k', lw=1.6, label='load')"),
L("ax[0].set_title('Dispatch by carrier'); ax[0].set_ylabel('MW')"),
L("ax[0].set_xlabel('hour'); ax[0].legend(fontsize=8, ncol=2)"),
L(""),
L("lmp = n.buses_t.marginal_price"),
L("ax[1].fill_between(lmp.index, lmp.min(axis=1), lmp.max(axis=1),"),
L("                   alpha=0.3, color='#0064B1', label='min-max across buses')"),
L("ax[1].plot(lmp.index, lmp.mean(axis=1), color='#0064B1', lw=2, label='mean')"),
L("ax[1].set_title('Locational marginal price'); ax[1].set_ylabel('$/MWh')"),
L("ax[1].set_xlabel('hour'); ax[1].legend(fontsize=8)"),
L("plt.tight_layout(); plt.show()"),
))

A(md(
L("> **Exercise 3.1.** The LMP band above is the spatial price spread the "
  "network creates. In your Mini-Project 3 or SB6 model, how many distinct "
  "prices could there possibly be? Here there are up to 123 per hour. State "
  "what your aggregated model can and cannot say about locational value as a "
  "result."),
))

# =========================================================== the experiment
A(md(
L("---"),
L("## Part 4 — The line-rating experiment"),
L(""),
L("This is the part of the assignment that is really about data assumptions "
  "rather than about Texas."),
L(""),
L("`Line_data.csv` gives one static `Capacity (MW)` per line. The release "
  "*also* ships `Daily_line_rating_5y`, a rating for every line on every day, "
  "computed from the weather — a **dynamic line rating**. Conductors sag when "
  "hot and can carry more current when the air is cold, so on a February "
  "morning in Texas the dynamic rating is well above the static one."),
L(""),
L("Solve the same day twice and compare."),
))

A(code(
L("dlr = daily_rating[:, DAY - 1]"),
L("static = line['Capacity (MW)'].values"),
L("print(f'static  rating: {static.min():,.0f} / {np.median(static):,.0f} / "
  "{static.max():,.0f} MW  (min/median/max)')"),
L("print(f'dynamic rating: {dlr.min():,.0f} / {np.median(dlr):,.0f} / "
  "{dlr.max():,.0f} MW')"),
L("print(f'dynamic is {np.median(dlr/static):.2f}x the static rating "
  "on the median line')"),
L(""),
L("results = {}"),
L("for label, rating in [('static Capacity column', None),"),
L("                      (f'dynamic rating, day {DAY}', dlr)]:"),
L("    m = build_tx123(line_rating=rating)"),
L("    m.optimize(solver_name=SOLVER, env=ENV, log_to_console=False)"),
L("    results[label] = m"),
L("    b, u = summarise(m, label)"),
L("    print()"),
))

A(code(
L("a, b = results.values()"),
L("la, lb = results.keys()"),
L("shed_a = a.generators_t.p[[c for c in a.generators_t.p.columns"),
L("                           if c.startswith('SHED')]].to_numpy().sum()"),
L("shed_b = b.generators_t.p[[c for c in b.generators_t.p.columns"),
L("                           if c.startswith('SHED')]].to_numpy().sum()"),
L("print(f'{la:28s} ${a.objective:>14,.0f}   {shed_a:>8,.1f} MWh unserved')"),
L("print(f'{lb:28s} ${b.objective:>14,.0f}   {shed_b:>8,.1f} MWh unserved')"),
L("print(f'{\"difference\":28s} ${a.objective-b.objective:>14,.0f}   '"),
L("      f'{shed_a-shed_b:>8,.1f} MWh')"),
L(""),
L("print('\\nwhere the unserved energy lands under the static rating:')"),
L("s = a.generators_t.p[[c for c in a.generators_t.p.columns"),
L("                      if c.startswith('SHED')]].sum()"),
L("s = s[s > 0.01].sort_values(ascending=False)"),
L("for k, v in s.items():"),
L("    print(f'  {names[int(k[4:])]:32s} {v:8,.1f} MWh')"),
))

A(md(
L("> **Exercise 4.1.** Two runs of the same network on the same day, "
  "differing only in which line-rating column you believe, give materially "
  "different answers — a different daily cost, a different number of binding "
  "corridors, and in one case load shed that the other does not have."),
L(">"),
L("> Neither column is wrong. State which one you would use for **(a)** a "
  "long-run capacity-expansion study and **(b)** a next-day operational study, "
  "and defend each choice in two sentences. Then say what this implies about "
  "reporting a single congestion result without stating the rating "
  "assumption behind it."),
L(""),
L("> **Exercise 4.2 — the connection to Chapter 15.** Your chosen day is in "
  "the middle of Winter Storm Uri. Compare the peak system load in this "
  "dataset for your day against a normal winter day (try day 20). Then answer: "
  "the real February 2021 failure was driven by generators freezing and by "
  "plants that could not get gas. **Can the model you just solved represent "
  "either of those?** Be specific about which component would have to carry "
  "the constraint."),
))

# ====================================================== compare to your own
A(md(
L("---"),
L("## Part 5 — Compare against your own aggregated model"),
L(""),
L("This is the deliverable. Everything above was setup."),
L(""),
L("Take the network you built for Mini-Project 3 or SB6 — three to six nodes, "
  "your own line capacities, your own demand — and put its results beside "
  "these. The comparison is not about which is *right*: TX-123BT is synthetic "
  "too. It is about which questions each one can answer."),
))

A(code(
L("# Fill these in from your own Mini-Project 3 / SB6 run."),
L("MY_MODEL = {"),
L("    'nodes': None,               # e.g. 4"),
L("    'lines': None,"),
L("    'binding_corridor': None,    # e.g. 'West Texas -> Dallas'"),
L("    'lmp_spread': None,          # max - min LMP in $/MWh"),
L("    'daily_cost': None,          # $ for a comparable day"),
L("}"),
L(""),
L("ref = results[f'dynamic rating, day {DAY}']"),
L("ref_lmp = ref.buses_t.marginal_price"),
L("comparison = pd.DataFrame({"),
L("    'your model': [MY_MODEL['nodes'], MY_MODEL['lines'],"),
L("                   MY_MODEL['binding_corridor'], MY_MODEL['lmp_spread'],"),
L("                   MY_MODEL['daily_cost']],"),
L("    'TX-123BT': [len(ref.buses), len(ref.lines),"),
L("                 congestion_table(ref, top=1)['line'].iat[0],"),
L("                 round((ref_lmp.max(axis=1) - ref_lmp.min(axis=1)).max(), 2),"),
L("                 round(ref.objective, 0)],"),
L("}, index=['nodes', 'lines', 'top binding corridor',"),
L("          'max LMP spread ($/MWh)', 'daily cost ($)'])"),
L("print(comparison.to_string())"),
))

A(md(
L("### What to hand in for Stage 1"),
L(""),
L("1. **The import, working.** The network plot from Part 1 and the "
  "congestion table from Part 3, for a day you chose and justified."),
L("2. **The three data defects.** Two are found in Part 1; the third is "
  "Exercise 1.1. For each, say how you detected it and what would have "
  "happened had you not."),
L("3. **The rating experiment.** The two-run comparison from Part 4 with "
  "Exercise 4.1 answered."),
L("4. **Two ways your own aggregated model over- or under-states the real "
  "system's constraints, and why.** This is the graded core of the "
  "assignment. Be specific — name the corridor, the price, or the "
  "constraint. \"It has fewer nodes\" is not an answer; \"my model reports a "
  "single system price, so it cannot show the $X/MWh separation that appears "
  "between the Houston buses and West Texas in hours 18–21\" is."),
L("5. **The commitment relaxation.** State that you solved the LP relaxation "
  "rather than a unit-commitment problem, and give one result you would "
  "expect to move if you had not."),
))

# =========================================================== stage 2
A(md(
L("---"),
L("## Part 6 — Stage 2 (optional): the TAMU ACTIVSg cases"),
L(""),
L("**Optional extension. Not required.** Flag it to the instructor before "
  "attempting a full multi-period run at this scale; a single-snapshot DC OPF "
  "is the realistic ceiling for a course-length assignment."),
L(""),
L("**Which case to use.** The catalog names ACTIVSg500. Note that "
  "**ACTIVSg500 is a synthetic *South Carolina* system** — the case header "
  "says so. The synthetic **Texas** case is **ACTIVSg2000**. If your point is "
  "the like-for-like comparison against TX-123BT, use ACTIVSg2000. If your "
  "point is only what changes with scale and solve time, ACTIVSg500 is "
  "smaller and faster, but say in your report that you have changed "
  "geography as well as size."),
L(""),
L("Both ship as MATPOWER `.m` files in the MATPOWER repository, which is a "
  "cleaner fetch than the TAMU site (which requires a registration click)."),
))

A(code(
L("import re"),
L(""),
L(""),
L("def parse_matpower(text):"),
L('    """Minimal MATPOWER .m -> PYPOWER ppc dict."""'),
L("    ppc = {'version': '2'}"),
L("    m = re.search(r'mpc\\.baseMVA\\s*=\\s*([0-9.eE+-]+)\\s*;', text)"),
L("    ppc['baseMVA'] = float(m.group(1)) if m else 100.0"),
L("    for field in ('bus', 'gen', 'branch', 'gencost'):"),
L("        m = re.search(r'mpc\\.%s\\s*=\\s*\\[(.*?)\\n\\s*\\];' % field,"),
L("                      text, re.S)"),
L("        if not m:"),
L("            continue"),
L("        rows = []"),
L("        for raw_line in m.group(1).splitlines():"),
L("            s = raw_line.split('%')[0].strip().rstrip(';').strip()"),
L("            if s:"),
L("                rows.append([float(x) for x in"),
L("                             s.replace(',', ' ').split()])"),
L("        w = max(len(r) for r in rows)"),
L("        ppc[field] = np.array([r + [0.0] * (w - len(r)) for r in rows])"),
L(""),
L("    # Cell-array fields:  mpc.genfuel = { 'ng'; 'wind'; ... };"),
L("    # BOTH standard converters drop these, and they are the only place the"),
L("    # case says what anything burns.  Without them you have 544 anonymous"),
L("    # machines and cannot report a generation mix at all."),
L("    for field in ('gentype', 'genfuel', 'bus_name'):"),
L("        m = re.search(r'mpc\\.%s\\s*=\\s*\\{(.*?)\\};' % field, text, re.S)"),
L("        if m:"),
L("            ppc[field] = re.findall(r\"'([^']*)'\", m.group(1))"),
L("    return ppc"),
L(""),
L(""),
L("def marginal_cost_from_gencost(ppc):"),
L('    """MATPOWER gencost -> $/MWh.'),
L(""),
L("    `import_from_pypower_ppc` does NOT carry gencost across, so without"),
L("    this the objective is empty and PyPSA refuses to build a model."),
L(""),
L("    STATED APPROXIMATION: model 2 is a quadratic c2*p^2 + c1*p + c0, and a"),
L("    PyPSA LP takes one constant marginal cost per generator, so this keeps"),
L("    c1 and discards the curvature.  On ACTIVSg2000 that understates the"),
L("    marginal cost at full output by a mean of $0.38/MWh (median $0.21, max"),
L("    $4.03); 50 of 544 units are off by more than $1/MWh.  Small, but it is"),
L("    an approximation and you should say so.  See Exercise 6.1."),
L('    """'),
L("    out = []"),
L("    for row in ppc['gencost']:"),
L("        model, ncost = int(row[0]), int(row[3])"),
L("        c = row[4:4 + ncost]"),
L("        if model == 2:                    # polynomial, descending powers"),
L("            out.append(float(c[-2]) if ncost >= 2 else 0.0)"),
L("        else:                             # piecewise linear x1,y1,x2,y2,..."),
L("            pts = c.reshape(-1, 2)"),
L("            dx = pts[1, 0] - pts[0, 0]"),
L("            out.append(float((pts[1, 1] - pts[0, 1]) / dx) if dx else 0.0)"),
L("    return out"),
L(""),
L(""),
L("# MATPOWER fuel codes -> readable carrier names"),
L("FUEL_NAMES = {'ng': 'natural gas', 'coal': 'coal', 'nuclear': 'nuclear',"),
L("              'hydro': 'hydro', 'wind': 'wind', 'solar': 'solar',"),
L("              'oil': 'oil', 'biomass': 'biomass',"),
L("              'geothermal': 'geothermal', 'other': 'other'}"),
L(""),
L(""),
L("CASE = 'case_ACTIVSg2000'      # Texas.  'case_ACTIVSg500' is South Carolina."),
L("url = ('https://raw.githubusercontent.com/MATPOWER/matpower/master/data/'"),
L("       f'{CASE}.m')"),
L("text = requests.get(url, timeout=120).text"),
L("ppc = parse_matpower(text)"),
L("print(CASE)"),
L("print('  numeric tables:',"),
L("      {k: v.shape for k, v in ppc.items() if hasattr(v, 'shape')})"),
L("print('  cell arrays:  ',"),
L("      {k: len(ppc[k]) for k in ('gentype', 'genfuel', 'bus_name')"),
L("       if k in ppc})"),
L("print(' ', text.splitlines()[0])"),
))

A(md(
L("### The three things that make this import fail silently"),
L(""),
L("`import_from_pypower_ppc` is a convenience, not a complete translation. "
  "Two of its gaps produce the same unhelpful symptom — `infeasible`, with no "
  "message saying why — and the third produces something worse, which is a "
  "result that looks fine and is missing half the information."),
L(""),
L("1. **`gencost` is not imported.** No costs, so no objective, and PyPSA "
  "raises before it solves."),
L("2. **`Pg` — MATPOWER's own *solved dispatch* — is imported into the static "
  "`generators.p_set` column.** PyPSA then writes a `Generator-p_set` "
  "equality constraint pinning every generator to that value. The problem is "
  "over-determined: 544 generation levels are fixed, so the nodal balance "
  "cannot also hold, and the solver returns infeasible. **You are not "
  "optimising anything.** Setting `p_set` to `NaN` releases it."),
L("3. **`mpc.genfuel`, `mpc.gentype` and `mpc.bus_name` are dropped entirely** "
  "— by `import_from_pypower_ppc` and by pandapower's converter alike, "
  "because they are MATLAB cell arrays rather than numeric matrices. They are "
  "the only place the case records what anything burns or what anything is "
  "called. Lose them and you have 544 anonymous machines: the model still "
  "solves, the dispatch is still right, and you cannot report a generation "
  "mix, tell wind from gas, or name a single congested corridor. The parser "
  "above reads them; the cell below attaches them."),
L(""),
L("If you take one habit away from this assignment, make it this: after any "
  "network import, look at what constraints the model actually contains "
  "(`n.optimize.create_model().constraints`) before believing a result — or "
  "before believing an infeasibility. And check what the source file held "
  "that your object no longer does."),
))

A(code(
L("m = pypsa.Network()"),
L("m.import_from_pypower_ppc(ppc)"),
L(""),
L("print('as imported:')"),
L("print(f'  {len(m.buses)} buses, {len(m.lines)} lines, '"),
L("      f'{len(m.transformers)} transformers, {len(m.generators)} generators, '"),
L("      f'{len(m.loads)} loads')"),
L("print(f'  generators.p_set is set on {int(m.generators.p_set.notna().sum())}'"),
L("      f' of {len(m.generators)} generators, summing to '"),
L("      f'{m.generators.p_set.sum():,.0f} MW against '"),
L("      f'{m.loads.p_set.sum():,.0f} MW of load')"),
L(""),
L("# look at what the model would contain before fixing anything"),
L("m.generators['marginal_cost'] = marginal_cost_from_gencost(ppc)"),
L("print('\\nconstraints PyPSA would build:')"),
L("for name, con in m.optimize.create_model().constraints.items():"),
L("    flag = '   <-- this one pins every generator' if 'p_set' in name else ''"),
L("    print(f'  {name:30s} {con.shape}{flag}')"),
))

A(code(
L("m.generators['p_set'] = np.nan     # release MATPOWER's solved dispatch"),
L("m.generators['p_min_pu'] = 0.0     # LP relaxation, as in Part 2"),
L(""),
L("# Put back what the converter dropped."),
L("carriers = [FUEL_NAMES.get(f, f) for f in ppc['genfuel']]"),
L("for carrier in sorted(set(carriers)):"),
L("    m.add('Carrier', carrier)"),
L("m.generators['carrier'] = carriers"),
L("m.buses['substation'] = list(ppc['bus_name'])"),
L(""),
L("fleet = (m.generators.groupby('carrier').p_nom"),
L("         .agg(['count', 'sum']).sort_values('sum', ascending=False))"),
L("print('installed capacity by fuel:')"),
L("for carrier, r in fleet.iterrows():"),
L("    print(f\"  {carrier:14s} {int(r['count']):4d} units  {r['sum']:10,.0f} MW\""),
L("          f\"  {100*r['sum']/fleet['sum'].sum():5.1f}%\")"),
))

A(code(
L("status, condition = m.optimize(solver_name=SOLVER, env=ENV)"),
L("print(status, condition)"),
L("if condition == 'optimal':"),
L("    lmp = m.buses_t.marginal_price"),
L("    util = m.lines_t.p0.abs().div(m.lines.s_nom, axis=1).iloc[0]"),
L("    print(f'  hourly cost   ${m.objective:,.0f}')"),
L("    print(f'  LMP           ${lmp.to_numpy().min():,.2f} .. '"),
L("          f'${lmp.to_numpy().max():,.2f} /MWh')"),
L("    print(f'  binding lines {int((util > 0.999).sum())} of {len(util)}')"),
L(""),
L("    mix = (m.generators_t.p.T.groupby(m.generators.carrier).sum().sum(axis=1))"),
L("    mix = mix[mix > 0.5].sort_values(ascending=False)"),
L("    print('\\n  dispatch at this snapshot (MW):')"),
L("    for carrier, mw in mix.items():"),
L("        print(f'    {carrier:14s} {mw:10,.0f}  {100*mw/mix.sum():5.1f}%')"),
L(""),
L("    print('\\n  most-loaded corridors:')"),
L("    for ln, u in util.sort_values(ascending=False).head(4).items():"),
L("        b0, b1 = m.lines.at[ln, 'bus0'], m.lines.at[ln, 'bus1']"),
L("        print(f\"    {ln:8s} {100*u:5.1f}%   \""),
L("              f\"{m.buses.at[b0, 'substation']} -> \""),
L("              f\"{m.buses.at[b1, 'substation']}\")"),
))

A(md(
L("> **Exercise 6.1 — the approximation you just made.** "
  "`marginal_cost_from_gencost` keeps the linear term of MATPOWER's quadratic "
  "cost curve and throws away the curvature, because a PyPSA LP takes one "
  "constant marginal cost per generator. Quantify it: compute "
  "`c1 + 2*c2*Pmax` for every unit, compare against the `c1` you actually "
  "used, and report the mean and worst-case error in $/MWh. Then say whether "
  "it could plausibly change which units are marginal — and therefore the "
  "LMPs you just reported."),
L(""),
L("> **Exercise 6.2.** Compare the installed capacity mix above against "
  "ERCOT's actual fuel mix for the year the case represents (EIA-930 or "
  "ERCOT's own fact sheet). The generators in this case are **real** — "
  "locations, capacities and fuel types come from EIA-860. Say how close it "
  "is, and where it is not."),
))

A(md(
L("### What to hand in for Stage 2"),
L(""),
L("State **what changes going from 123 buses to 2,000 beyond \"more nodes\"**. "
  "Cover at least:"),
L(""),
L("- **Solve time**, measured, for a single snapshot — and extrapolate to the "
  "8,760 hours you would want."),
L("- **Data-cleaning effort.** You have now imported two real networks. "
  "Which import took longer, and was it proportional to the size?"),
L("- **Whether the same questions are even answerable.** TX-123BT ships "
  "five years of hourly weather-driven profiles. ACTIVSg2000 ships a single "
  "operating snapshot. Say what that costs you."),
L("- **Voltage levels.** TX-123BT is a single-voltage 345 kV backbone. "
  "ACTIVSg2000 has 500, 230, 161 and 115 kV, plus transformers. Say what the "
  "extra realism buys, and what it costs."),
))

A(md(
L("---"),
# The facility question is four source elements - rule, blank, the
# question, blank - because that is what the notebook carries. It was
# a bare string here once, which emitted no trailing newline and ran
# the question into the next heading. See Tools/check_builders.py.
L(""),
L("*Before class: you swapped an aggregated network for a real one. If your site sat at one of these buses, what could you now see about its price that the aggregated version hid?*"),
L(""),
L("### Sources"),
L("- **TX-123BT** — Jin Lu et al., *A Synthetic Texas Backbone Power System "
  "with Climate-Dependent Spatio-Temporal Correlated Profiles*. "
  "DOI 10.6084/m9.figshare.22144616, CC BY 4.0. "
  "rpglab.github.io/resources/TX-123BT"),
L("- **Sample SCUC code** — github.com/rpglab/SCUC_Dynamic_Line_Rating"),
L("- **ACTIVSg cases** — A. B. Birchfield et al., *Grid Structural "
  "Characteristics as Validation Criteria for Synthetic Networks*, IEEE "
  "Transactions on Power Systems. Distributed with MATPOWER "
  "(github.com/MATPOWER/matpower, `data/case_ACTIVSg*.m`) and at "
  "electricgrids.engr.tamu.edu"),
L("- **PyPSA** — pypsa.readthedocs.io. DC optimal power flow, "
  "`import_from_pypower_ppc`"),
L("- FERC/NERC/Regional Entity staff, *Final Report on the February 2021 Cold "
  "Weather Outages in Texas and the South Central United States*, November "
  "2021 — the source for the Chapter 15 material this notebook's default day "
  "connects to"),
))

NOTEBOOK = {
    "cells": C,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python",
                       "name": "python3"},
        "language_info": {"name": "python", "pygments_lexer": "ipython3"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

def syntax_check(cells):
    """Compile every code cell before writing.

    Cells are assembled from many small `L(...)` string literals, which makes
    it easy to split an f-string across lines and forget the closing quote on
    each fragment.  That produces a notebook whose cells look right and raise
    SyntaxError the moment a student runs them.  Six cells here did exactly
    that on the first build.
    """
    bad = 0
    idx = 0
    for c in cells:
        if c["cell_type"] != "code":
            continue
        idx += 1
        src = chr(10).join(l for l in "".join(c["source"]).splitlines()
                        if not l.strip().startswith("!"))
        try:
            compile(src, "<cell %d>" % idx, "exec")
        except SyntaxError as e:
            bad += 1
            print("cell %d line %s: %s" % (idx, e.lineno, e.msg))
            for j, l in enumerate(src.splitlines(), 1):
                if abs(j - (e.lineno or 0)) <= 1:
                    print("   %3d| %s" % (j, l))
    if bad:
        raise SystemExit("%d code cell(s) failed the syntax check" % bad)
    print("syntax check: %d code cells compile" % idx)


if __name__ == "__main__":
    syntax_check(C)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(NOTEBOOK, f, indent=1, ensure_ascii=False)
    print("wrote", OUT)
    print("cells:", len(C), "(%d code, %d markdown)" % (
        sum(1 for c in C if c["cell_type"] == "code"),
        sum(1 for c in C if c["cell_type"] == "markdown")))
