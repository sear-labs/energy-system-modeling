# -*- coding: utf-8 -*-
"""build_m1_smart_meter_notebook.py -> `notebooks/p2_demand/06_smart_meter_reading.ipynb`.

WHERE THIS COPY CAME FROM, AND THE ONE THING THAT COULD NOT COME WITH IT
Brought from the course folder's `Tools/` on 2026-10-22 (course notebook
M1_Smart_Meter_Walkthrough, 15 Oct).  The course runs it on the class file
`IntervalData.csv`, **one real household's Smart Meter Texas export**.  A year
of a home's 15-minute readings says when its occupants wake, leave, cook and
sleep; it is not this repository's to publish, so it is not here, the builder's
`--run` no longer reads it, and `.gitignore` refuses `IntervalData*.csv` with
that reason beside it.

So the notebook reads the student's OWN export if one is present, and
otherwise falls back to `esm.meter.synthetic_export()` - an invented house,
seeded, in the export's own column format - and says loudly that the fallback
is not an acceptable submission (the standard's Part 5: "fall back to
generated data, print loudly that it has done so").  Code written against the
synthetic file runs unchanged on a real export.

Other changes from the course copy:
  * Colab's `files.upload()` is gone from the default path.  It blocks "Run
    all", and it blocks a headless execution forever; the markdown says how to
    upload instead;
  * every plot carries ALT_TEXT, and the heat map's peak is printed as text;
  * an agreement cell against `esm.meter`, which computes the same summaries
    by numpy reshapes instead of pandas groupby/diff.

ANCHORED AT CHAPTER 6, section 6.2 (Smart Meters, Time Series, and Appliance
Signatures).  It sits beside `06_end_use_disaggregation`, which is the same
section at grid scale; this one is a single house.

THREE PARTS, EACH ENDING ON A QUESTION (unchanged from the course)
  A  read the meter: 15-minute kWh -> kW, one week, the base load
  B  the shape: weekday vs weekend by hour, month x hour heat map
  C  the spikes: the largest 15-minute steps - what could each one be?  (NILM;
     posed and not answered)

    python build_m1_smart_meter_notebook.py          build (syntax check)
    python build_m1_smart_meter_notebook.py --run    also execute, on the synthetic house
"""
import json
import os
import sys

# tools/builders/<this file> -> tools/ -> the repository root.
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "notebooks", "p2_demand", "06_smart_meter_reading.ipynb")

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

A(md(
L("# Reading a smart meter"),
L(""),
L("Section 6.2 of the book at the scale of one house: a year of 15-minute "
  "readings, what they say about the household's day, and the steps an "
  "appliance leaves when it switches on. In Colab, *File › Save a copy in Drive* "
  "first so your edits are kept."),
L(""),
L("**Before you look:** at what time of day does a house use the most "
  "electricity? And how much does it draw when nobody is doing anything?"),
))
A(code(
L("import pandas as pd"),
L("import matplotlib.pyplot as plt"),
))

A(md(
L("## The data: your own meter, or an invented one"),
L(""),
L("Download your own 15-minute interval export from **Smart Meter Texas** (or "
  "your utility's equivalent with the same columns) and put it where `MY_EXPORT` "
  "points. In Colab, drag it into the *Files* pane - it lands in `/content` - and "
  "set `MY_EXPORT = '/content/IntervalData.csv'`."),
L(""),
L("Your export identifies your home and its daily routine. Keep it out of any "
  "public repository; this one refuses files with that name."),
L(""),
L("With no export, the cell below builds an **invented** house so the notebook "
  "still runs, and says so."),
))
A(code(
L("from pathlib import Path"),
L("from esm.meter import synthetic_export"),
L(""),
L("MY_EXPORT = 'IntervalData.csv'            # yours: the path to your own export"),
L(""),
L("if Path(MY_EXPORT).exists():"),
L("    raw = pd.read_csv(MY_EXPORT)"),
L("    print(f'read your export: {MY_EXPORT}')"),
L("else:"),
L("    raw = synthetic_export(seed=4301)"),
L("    print('=' * 72)"),
L("    print(f'NO EXPORT AT {MY_EXPORT!r} - USING AN INVENTED HOUSE (seed 4301).')"),
L("    print('It is fine for following along. It is NOT an acceptable submission:')"),
L("    print('every number below describes a house that does not exist.')"),
L("    print('=' * 72)"),
L(""),
L("raw = raw.drop(columns=['ESIID'])         # identifies the meter; not needed"),
L("raw.head()"),
))

A(md(
L("## Part A - Read the meter"),
L(""),
L("Each row is **energy** (kWh) over 15 minutes. Power (kW) is that energy "
  "divided by a quarter of an hour."),
))
A(code(
L("raw['time'] = pd.to_datetime(raw['USAGE_DATE'] + ' ' + raw['USAGE_START_TIME'],"),
L("                             format='%m/%d/%Y %H:%M')"),
L("is_export = raw['CONSUMPTION_SURPLUSGENERATION'].str.startswith('Surplus')"),
L(""),
L("use = raw[~is_export].set_index('time')['USAGE_KWH'].sort_index()"),
L("export = raw[is_export].set_index('time')['USAGE_KWH'].sort_index()"),
L("kw = use * 4                                # kWh per 15 min -> kW"),
L(""),
L("print(f'{use.index.min():%d %b %Y} to {use.index.max():%d %b %Y}, '"),
L("      f'{len(use):,} readings')"),
L("print(f'used {use.sum():,.0f} kWh, exported {export.sum():,.0f} kWh')   # exports: rooftop solar"),
))
A(md(
L("One week of it, every reading."),
))
A(code(
L("week = kw[kw.index >= kw.index.max() - pd.Timedelta(days=7)]"),
L("week.plot(figsize=(11, 3), ylabel='kW', title='The last week, every 15 minutes')"),
L("ALT_TEXT = (f'Line chart of the last week of 15-minute power readings. It sits '"),
L("            f'near {week.quantile(0.05):.2f} kW for long stretches and spikes to '"),
L("            f'as much as {week.max():.1f} kW; the average is {week.mean():.2f} kW.')"),
L("plt.show()"),
L("print(ALT_TEXT)"),
))
A(md(
L("> Look at the lowest points, around 3 a.m. What is this house drawing when "
  "nobody is doing anything, and what is always on?"),
))

A(md(
L("## Part B - The shape"),
))
A(code(
L("hourly = kw.groupby([kw.index.dayofweek >= 5, kw.index.hour]).mean().unstack(0)"),
L("hourly.columns = ['weekday', 'weekend']"),
L("ax = hourly.plot(figsize=(8, 3), xlabel='hour of day', ylabel='average kW',"),
L("                 style=['-', '--'])         # line style as well as colour"),
L("ALT_TEXT = (f'Two lines of average power by hour of day. Weekdays (solid) peak at '"),
L("            f'{hourly.weekday.max():.2f} kW at hour {hourly.weekday.idxmax()}; '"),
L("            f'weekends (dashed) peak at {hourly.weekend.max():.2f} kW at hour '"),
L("            f'{hourly.weekend.idxmax()}. Both are lowest overnight, near '"),
L("            f'{hourly.min().min():.2f} kW.')"),
L("plt.show()"),
L("print(ALT_TEXT)"),
))
A(md(
L("The same by month as well as by hour: each cell of the map is the average kW in that hour of that month."),
))
A(code(
L("grid = kw.groupby([kw.index.month, kw.index.hour]).mean().unstack()"),
L("plt.figure(figsize=(10, 3.5))"),
L("plt.imshow(grid, aspect='auto', cmap='viridis')"),
L("plt.colorbar(label='average kW')"),
L("plt.yticks(range(len(grid)), grid.index)"),
L("plt.xlabel('hour of day'); plt.ylabel('month')"),
L("month, hour = grid.stack().idxmax()"),
L("ALT_TEXT = (f'Heat map of average power, months down the side and hours of the '"),
L("            f'day across. The brightest cell is month {month} at hour {hour}, '"),
L("            f'{grid.loc[month, hour]:.2f} kW; the darkest is '"),
L("            f'{grid.min().min():.2f} kW.')"),
L("plt.show()"),
L("print(ALT_TEXT)"),
))
A(md(
L("> When is the peak, and does it move between summer and winter? Looking only "
  "at this picture, would rooftop solar cut this house's peak - or just its "
  "midday?"),
))

A(md(
L("## Part C - The spikes"),
L(""),
L("A big appliance switching on shows up as a **step**: the load jumps from one "
  "15-minute reading to the next."),
))
A(code(
L("steps = kw.diff()"),
L("biggest = steps.nlargest(10)"),
L("pd.DataFrame({'jump kW': biggest.round(2),"),
L("              'time of day': biggest.index.strftime('%a %H:%M'),"),
L("              'month': biggest.index.strftime('%b')})"),
))
A(md(
L("> Pick three of these steps. What appliance could each one be? Then the harder "
  "question: what in the data would tell a dryer from a water heater from an air "
  "conditioner? Several answers usually fit - say which evidence decides it."),
))

A(md(
L("---"),
L("### Does the package agree?"),
L(""),
L("`esm.meter` reads the same export a different way - numpy reshapes over "
  "whole days instead of pandas `groupby` and `diff` - and has to land on the "
  "same numbers. The ten largest steps are compared as **sizes**: two equal jumps "
  "can sort either way round, so which timestamp came first is not a result."),
))
A(code(
L("import numpy as np"),
L("from esm.meter import biggest_steps, hourly_profile, to_kw"),
L("from esm.tolerance import AGREEMENT_RTOL, relative"),
L(""),
L("pkg_kw, pkg_export = to_kw(raw)"),
L("pkg_hourly = hourly_profile(pkg_kw)"),
L("checks = [('readings', len(kw), len(pkg_kw)),"),
L("          ('kWh used', use.sum(), pkg_kw.sum() / 4),"),
L("          ('kWh exported', export.sum(), pkg_export)]"),
L("checks += [(f'{d} hour {h}', hourly.at[h, d], pkg_hourly.at[h, d])"),
L("           for d in ('weekday', 'weekend') for h in range(24)]"),
L("checks += [(f'step {i + 1}', a, b)"),
L("           for i, (a, b) in enumerate(zip(biggest.to_numpy(), biggest_steps(pkg_kw)))]"),
L(""),
L("worst = max(relative(a, b) for _, a, b in checks)"),
L("print(f'{len(checks)} quantities compared; largest relative difference {worst:.1e}')"),
L("assert worst < AGREEMENT_RTOL, f'notebook and package disagree by {worst:.2e}'"),
L("print(f'notebook and package agree to {worst:.1e}')"),
))
A(md(
L("*Before class: one house's peak is a few kW. If you were sizing the service "
  "for a 200-home subdivision, would you add up 200 of these peaks - and if not, "
  "why not?*"),
L(""),
L("### Sources"),
L("- Smart Meter Texas interval export (15-minute kWh; consumption and surplus "
  "generation rows)."),
L("- The invented house: `esm.meter.synthetic_export`, built from typical "
  "appliance nameplates. It is not a measurement of any real home."),
))


def verify(cells):
    """The arithmetic the prose states, and the guard on the class file.

    The course builder read the real household's file from a Drive path. If
    any cell here ever names such a path again, the build stops: the only data
    this notebook may reach is the reader's own export or the invented house.
    """
    assert 0.6 * 4 == 2.4                      # 0.6 kWh in 15 minutes is 2.4 kW
    src = "\n".join("".join(c["source"]) for c in cells)
    for banned in ("G:/", ".shortcut-targets", "Class Collab Code", "files.upload("):
        assert banned not in src, "a cell names %r - see the module docstring" % banned
    print("verify: no cell reaches the class file; conversion holds")


def syntax_check(cells):
    bad = 0
    for i, c in enumerate(cells):
        if c["cell_type"] != "code":
            continue
        try:
            compile("".join(c["source"]), "<cell %d>" % i, "exec")
        except SyntaxError as e:
            bad += 1
            print("SYNTAX ERROR in cell %d: %s" % (i, e))
    if bad:
        raise SystemExit("%d cell(s) failed to compile" % bad)
    print("syntax check: %d code cells compile"
          % sum(1 for c in cells if c["cell_type"] == "code"))


def run(cells):
    """Execute on the synthetic house, from an empty folder so no export is found."""
    import contextlib, io, tempfile
    import matplotlib
    matplotlib.use("Agg")
    sys.path.insert(0, os.path.join(ROOT, "src"))
    here = os.getcwd()
    os.chdir(tempfile.mkdtemp())
    out = io.StringIO()
    try:
        ns = {}
        for i, c in enumerate(cells):
            if c["cell_type"] != "code":
                continue
            with contextlib.redirect_stdout(out):
                exec(compile("".join(c["source"]), "<cell %d>" % i, "exec"), ns)
    finally:
        os.chdir(here)
    text = out.getvalue()
    assert "USING AN INVENTED HOUSE" in text and "NOT an acceptable" in text
    assert "ESIID" not in ns["raw"].columns
    assert ns["use"].sum() > 0 and len(ns["hourly"]) == 24
    assert ns["grid"].shape == (12, 24) and ns["biggest"].iloc[0] > 0
    assert ns["worst"] < 1e-9
    print("run: %d readings, %.0f kWh used, biggest step %.1f kW, agreement %.1e"
          % (len(ns["use"]), ns["use"].sum(), ns["biggest"].iloc[0], ns["worst"]))


NOTEBOOK = {"cells": C,
            "metadata": {"kernelspec": {"display_name": "Python 3",
                                        "language": "python", "name": "python3"},
                         "language_info": {"name": "python"},
                         "colab": {"provenance": []}},
            "nbformat": 4, "nbformat_minor": 5}

if __name__ == "__main__":
    verify(C)
    syntax_check(C)
    if "--run" in sys.argv:
        run(C)
    words = sum(len("".join(c["source"]).split()) for c in C if c["cell_type"] == "markdown")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(NOTEBOOK, f, indent=1, ensure_ascii=False)
    print("wrote", os.path.relpath(OUT, ROOT))
    print("cells: %d (%d code, %d markdown), %d words of prose"
          % (len(C), sum(1 for c in C if c["cell_type"] == "code"),
             sum(1 for c in C if c["cell_type"] == "markdown"), words))
