# -*- coding: utf-8 -*-
"""build_sb2_notebook.py -> `2026 Fall/Notebooks/SB2_Representative_Days.ipynb`.

SB2 turns 8,760 metered hours into three representative days and then - the
part that is actually graded - shows that the three days reconcile back to the
year. A representative day is only honest when it reconciles, and the error is
the deliverable rather than something to hide.

DATA
Students bring their own interval export. As in 1N, the notebook falls back to
a synthetic profile so it runs before anyone has uploaded anything, and says
loudly that a synthetic profile is not an acceptable submission. Testing that
path means deleting the file and running the whole notebook, which the build
does below.

THE FACILITY HALF
SB2 is the module where the course is already working at facility scale and
never says so: an interval export IS metered facility demand, not a forecast.
The coda names that, then introduces ERCOT 4CP - a year of transmission charges
set by four fifteen-minute intervals - because it is the cleanest case of a
site needing to forecast THE GRID's peak rather than its own.

Run from Tools/:  python build_sb2_notebook.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "2026 Fall", "Notebooks",
                   "SB2_Representative_Days.ipynb")

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


def verify():
    """The reconciliation must actually close on the synthetic fallback."""
    import numpy as np
    import pandas as pd
    idx = pd.date_range("2025-01-01", periods=8760, freq="1h")
    hour = idx.hour.to_numpy()
    doy = idx.dayofyear.to_numpy()
    rng = np.random.default_rng(0)
    shape = (0.9 + 0.45 * np.exp(-((hour - 19) ** 2) / 6.0)
             + 0.20 * np.exp(-((hour - 7) ** 2) / 4.0))
    cooling = 1 + 0.55 * np.clip(np.sin(np.pi * (doy - 100) / 240), 0, 1)
    kw = 1.4 * shape * cooling * rng.normal(1.0, 0.05, len(idx))
    s = pd.Series(np.clip(kw, 0.15, None), index=idx)
    daily = s.resample("1D").sum()
    # three days by total, with weights that partition the year
    order = daily.sort_values()
    n = len(order)
    picks = [order.index[n // 6], order.index[n // 2], order.index[5 * n // 6]]
    weights = [n // 3, n - 2 * (n // 3), n // 3]
    est = sum(daily[d] * w for d, w in zip(picks, weights))
    err = est / daily.sum() - 1
    assert abs(err) < 0.05, err
    print("arithmetic check: synthetic year %.0f kWh, three weighted days "
          "reconcile to %.1f%%" % (daily.sum(), 100 * err))


A(md(
L("# From a smart meter to three representative days"),
L("## REE 4301 / IE 5300 - Energy Systems Modeling"),
L(""),
L("A model runs on 8,760 hours. You cannot reason about 8,760 hours and "
  "neither can a reader, so almost every study in this field compresses the "
  "year into a handful of representative days."),
L(""),
L("**That compression is a modelling assumption, and it is only honest when "
  "you show it reconciles.** Three days that miss the annual total by 30% are "
  "not representative of anything. The reconciliation is the deliverable here, "
  "not the plot."),
))

A(code(
L("import numpy as np"),
L("import pandas as pd"),
L("import matplotlib.pyplot as plt"),
L("import warnings"),
L("warnings.filterwarnings('ignore')"),
))

A(md(
L("---"),
L("## Step 1 - Load your own interval data"),
L(""),
L("Point `DEMAND_CSV_PATH` at your utility export - an ERCOT-style file with "
  "`USAGE_DATE`, `USAGE_START_TIME` and `USAGE_KWH` columns."),
L(""),
L("**If that file is not next to the notebook** - which it will not be the "
  "first time you open this - the cell falls back to a synthetic year so the "
  "rest runs. It will say so loudly. **A synthetic profile is not an "
  "acceptable submission**; upload your own export before you write anything "
  "up."),
))

A(code(
L("DEMAND_CSV_PATH = 'IntervalData.csv'   # <-- your own export"),
L(""),
L(""),
L("def load_interval(path):"),
L("    \"\"\"15-minute ERCOT-style export -> hourly mean kW on a real index.\"\"\""),
L("    raw = pd.read_csv(path)"),
L("    ts = pd.to_datetime(raw['USAGE_DATE'] + ' ' + raw['USAGE_START_TIME'],"),
L("                        format='%m/%d/%Y %H:%M')"),
L("    kwh15 = raw.set_index(ts)['USAGE_KWH']"),
L("    return kwh15.resample('1h').sum() * 4"),
L(""),
L(""),
L("def synthetic_year():"),
L("    \"\"\"Stand-in only: evening peak, morning bump, summer cooling.\"\"\""),
L("    idx = pd.date_range('2025-01-01', periods=8760, freq='1h')"),
L("    hour, doy = idx.hour.to_numpy(), idx.dayofyear.to_numpy()"),
L("    shape = (0.9 + 0.45 * np.exp(-((hour - 19) ** 2) / 6.0)"),
L("             + 0.20 * np.exp(-((hour - 7) ** 2) / 4.0))"),
L("    cooling = 1 + 0.55 * np.clip(np.sin(np.pi * (doy - 100) / 240), 0, 1)"),
L("    rng = np.random.default_rng(0)"),
L("    kw = 1.4 * shape * cooling * rng.normal(1.0, 0.05, len(idx))"),
L("    return pd.Series(np.clip(kw, 0.15, None), index=idx)"),
L(""),
L(""),
L("try:"),
L("    demand_kw = load_interval(DEMAND_CSV_PATH)"),
L("    IS_REAL = True"),
L("    print(f'loaded {DEMAND_CSV_PATH}: {len(demand_kw):,} hourly points')"),
L("except FileNotFoundError:"),
L("    demand_kw = synthetic_year()"),
L("    IS_REAL = False"),
L("    print('=' * 66)"),
L("    print(f'NO FILE NAMED {DEMAND_CSV_PATH} - using a SYNTHETIC year.')"),
L("    print('The notebook will run, but this is not your data and it is')"),
L("    print('not an acceptable submission. Upload your export and re-run.')"),
L("    print('=' * 66)"),
L(""),
L("print(f'{demand_kw.index[0]:%Y-%m-%d} to {demand_kw.index[-1]:%Y-%m-%d}')"),
L("print(f'peak {demand_kw.max():.2f} kW   mean {demand_kw.mean():.2f} kW')"),
))

A(md(
L("## Step 2 - Look at it before you compress it"),
L(""),
L("Plot the year, then plot one week. **Say in one sentence what shape it "
  "has and why** - occupancy, weather, a process schedule. If you cannot, you "
  "are not ready to choose representative days, because you do not yet know "
  "what they have to represent."),
))

A(code(
L("daily_kwh = demand_kw.resample('1D').sum()"),
L(""),
L("fig, ax = plt.subplots(2, 1, figsize=(10, 5))"),
L("daily_kwh.plot(ax=ax[0], title='daily energy across the year (kWh)')"),
L("demand_kw.iloc[24 * 180:24 * 187].plot("),
L("    ax=ax[1], title='one week in late June (kW)')"),
L("plt.tight_layout(); plt.show()"),
L(""),
L("print(f'annual total {daily_kwh.sum():,.0f} kWh')"),
L("print(f'highest day  {daily_kwh.max():,.0f} kWh on "
  "{daily_kwh.idxmax():%d %b}')"),
L("print(f'lowest day   {daily_kwh.min():,.0f} kWh on "
  "{daily_kwh.idxmin():%d %b}')"),
))

A(md(
L("---"),
L("## Step 3 - Choose three days, and say how you chose them"),
L(""),
L("Any defensible rule is acceptable **provided you state it**. The rule "
  "below sorts the year by daily energy and takes days at the one-sixth, "
  "one-half and five-sixths points - so each stands for a third of the year "
  "and none of them is an outlier."),
L(""),
L("Alternatives worth considering, and worth defending if you use them: peak "
  "/ average / minimum; one day per season; or a clustering on the hourly "
  "shape rather than the daily total."),
L(""),
L("**Every representative day needs a weight** - how many real days it stands "
  "for. Without weights you have three days, not a year."),
))

A(code(
L("order = daily_kwh.sort_values()"),
L("n = len(order)"),
L(""),
L("picks = [order.index[n // 6], order.index[n // 2], order.index[5 * n // 6]]"),
L("weights = [n // 3, n - 2 * (n // 3), n // 3]"),
L(""),
L("rep = pd.DataFrame({"),
L("    'date': [d.strftime('%d %b') for d in picks],"),
L("    'kWh that day': [round(daily_kwh[d]) for d in picks],"),
L("    'stands for (days)': weights,"),
L("})"),
L("print(rep.to_string(index=False))"),
L("print(f'\\nweights sum to {sum(weights)} days')"),
))

A(md(
L("---"),
L("## Step 4 - Reconcile. This is the graded part"),
L(""),
L("Multiply each representative day by its weight, add them up, and compare "
  "against the measured annual total."),
L(""),
L("**Predict first.** Will your three days over- or under-state the year, and "
  "why? The direction is more interesting than the magnitude."),
))

A(code(
L("estimate = sum(daily_kwh[d] * w for d, w in zip(picks, weights))"),
L("actual = daily_kwh.sum()"),
L("error = estimate / actual - 1"),
L(""),
L("print(f'three weighted days {estimate:>12,.0f} kWh')"),
L("print(f'measured year       {actual:>12,.0f} kWh')"),
L("print(f'error               {error:>12.1%}')"),
))

A(md(
L("**A few percent is normal and fine.** Say so and move on."),
L(""),
L("**Ten percent or more means the day selection is wrong**, not that the "
  "data is. The usual cause is that the chosen days miss a shape rather than "
  "a level - a facility with a sharp summer peak and a flat winter is badly "
  "served by three days picked on total energy alone, because two of them "
  "look identical."),
L(""),
L("> **Exercise 4.1.** Re-pick using peak / average / minimum instead. Does "
  "the error get better or worse, and does that tell you the rule is better "
  "or just luckier? Say how you would tell the difference."),
L(">"),
L("> **Exercise 4.2.** Report the error **and keep it in your write-up.** A "
  "representative-day study that does not state its reconciliation error is "
  "not a study, it is an assertion."),
))

A(md(
L("---"),
L("## Step 5 - Degree days"),
L(""),
L("Regress daily energy on heating and cooling degree days. The base "
  "temperature is a choice - state it and say how you chose it."),
L(""),
L("Without a weather file this step uses a proxy built from day of year. "
  "**Replace it with real degree days from NOAA for your own station** before "
  "you report anything; the proxy is here so the mechanics are visible."),
))

A(code(
L("# Proxy only. Substitute real HDD/CDD for your weather station."),
L("doy = daily_kwh.index.dayofyear.to_numpy()"),
L("temp_f = 62 + 22 * np.sin(np.pi * (doy - 110) / 182.5)"),
L(""),
L("BASE = 65.0     # degF. State yours and justify it."),
L("cdd = np.clip(temp_f - BASE, 0, None)"),
L("hdd = np.clip(BASE - temp_f, 0, None)"),
L(""),
L("X = np.column_stack([np.ones_like(cdd), cdd, hdd])"),
L("beta, *_ = np.linalg.lstsq(X, daily_kwh.values, rcond=None)"),
L("pred = X @ beta"),
L("ss_res = ((daily_kwh.values - pred) ** 2).sum()"),
L("ss_tot = ((daily_kwh.values - daily_kwh.mean()) ** 2).sum()"),
L(""),
L("print(f'base temperature     {BASE:.0f} F')"),
L("print(f'baseline load        {beta[0]:8.1f} kWh/day')"),
L("print(f'per cooling degree   {beta[1]:8.1f} kWh')"),
L("print(f'per heating degree   {beta[2]:8.1f} kWh')"),
L(f"print(f'R-squared            {{1 - ss_res / ss_tot:8.3f}}')"),
))

A(md(
L("> **Exercise 5.1.** State how much of the variation the regression "
  "explains, and name one thing driving the rest. Occupancy, a production "
  "schedule and day-of-week effects are the usual suspects - which applies to "
  "your site?"),
L(">"),
L("> **Exercise 5.2.** Try three base temperatures and report which fits "
  "best. The base temperature is not a physical constant; it is a property of "
  "the building."),
))

# The facility question is four source elements - rule, blank, the
# question, blank - because that is what the notebook carries. It was
# a bare string here once, which emitted no trailing newline and ran
# the question into the next heading. See Tools/check_builders.py.
A(md(
L("---"),
L(""),
L("*Before class: these representative days came from one site's meter. A region's load curve is far smoother. Which of your clusters would survive that smoothing, and which exists only because one building does one thing at a time?*"),
L(""),
))

A(code(
L("top4 = demand_kw.nlargest(4)"),
L("print('your four highest hours:')"),
L("for t, v in top4.items():"),
L("    print(f'   {t:%d %b %H:%M}   {v:.2f} kW')"),
L("print()"),
L("summer = top4.index.month.isin([6, 7, 8, 9]).sum()"),
L("print(f'{summer} of your 4 peak hours fall in June-September,')"),
L("print('which is when ERCOT sets 4CP. Would yours have coincided with the')"),
L("print('system peak, or only with your own?')"),
))

A(md(
L("> **Exercise 6.1.** Look up the actual 4CP intervals for the most recent "
  "year and check your load in them. If your peak and the system's do not "
  "coincide, you may already be paying less than you think - or have more "
  "headroom to shift than you think."),
L(""),
L("### Sources"),
L("- Your own utility interval export. In ERCOT territory: Smart Meter Texas."),
L("- NOAA / NCEI for real heating and cooling degree days at your station."),
L("- ERCOT and your utility's published 4CP guidance for the transmission "
  "charge mechanism."),
))


def syntax_check(cells):
    bad = 0
    for i, c in enumerate(cells):
        if c["cell_type"] != "code":
            continue
        src = "\n".join(l for l in "".join(c["source"]).splitlines()
                        if not l.strip().startswith("!"))
        try:
            compile(src, "<cell %d>" % i, "exec")
        except SyntaxError as e:
            bad += 1
            print("SYNTAX ERROR in cell %d: %s" % (i, e))
    if bad:
        raise SystemExit("%d cell(s) failed to compile" % bad)
    print("syntax check: %d code cells compile"
          % sum(1 for c in cells if c["cell_type"] == "code"))


NOTEBOOK = {"cells": C,
            "metadata": {"kernelspec": {"display_name": "Python 3",
                                        "language": "python", "name": "python3"},
                         "language_info": {"name": "python"},
                         "colab": {"provenance": []}},
            "nbformat": 4, "nbformat_minor": 5}

if __name__ == "__main__":
    verify()
    syntax_check(C)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(NOTEBOOK, f, indent=1, ensure_ascii=False)
    print("wrote", os.path.relpath(OUT, ROOT))
    print("cells: %d (%d code, %d markdown)"
          % (len(C), sum(1 for c in C if c["cell_type"] == "code"),
             sum(1 for c in C if c["cell_type"] == "markdown")))
