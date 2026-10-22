# -*- coding: utf-8 -*-
"""A smart-meter export, read once so the notebook can be checked -- and a
synthetic one, so the notebook runs without anybody's real meter.

    from esm.meter import synthetic_export, to_kw, hourly_profile, biggest_steps
    raw = synthetic_export(seed=4301)
    kw = to_kw(raw)

WHY THERE IS A SYNTHETIC HOUSE AT ALL

`notebooks/p2_demand/06_smart_meter_reading.ipynb` teaches reading a 15-minute
Smart Meter Texas export: kWh to kW, the base load, the weekday and weekend
shapes, and the steps an appliance leaves when it switches on. The course runs
it on one real household's export. **That file never comes here** -- a year of
one home's 15-minute readings says when its occupants wake, leave and sleep, and
it is not this repository's to publish.

So the notebook reads the student's own export if they supply one, and
otherwise falls back to `synthetic_export()`, saying loudly that it has done so
and that the fallback is not an acceptable submission (the standard's Part 5).

WHAT THE SYNTHETIC HOUSE IS, AND IS NOT

A one-storey Texas house with no rooftop solar, built from appliances rather
than from a fitted curve, so that the steps in it have causes a student can
name: an always-on base, a refrigerator compressor, a central air conditioner
that cycles harder as the afternoon heats up, resistance heat strips on cold
mornings, a 4.5 kW water-heater element, an electric dryer two or three times a
week, a cooktop or oven most evenings, and lighting and plug load that follows
the household's day. **It is invented.** The sizes are typical nameplates, not a
survey, and nothing about it is a measurement of any real home.

It uses the export's own column names and formats, so the code a student writes
against it runs unchanged on their real export.

WHAT THE AGREEMENT ASSERTION COMPARES

The notebook builds its summaries with pandas `groupby` and `diff`. This module
builds the same ones with numpy reshapes over whole days, which is a different
route that has to land on the same numbers: total energy, the base load, the
24-hour weekday and weekend profiles, and the ten largest steps. Ties in the
largest steps are possible (two equal jumps), so the step SIZES are compared,
never which timestamp the sort happened to put first.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

#: The placeholder meter id. A real ESIID identifies a premise; this does not.
SYNTHETIC_ESIID = "SYNTHETIC-NOT-A-METER"
COLUMNS = ["ESIID", "USAGE_DATE", "REVISION_DATE", "USAGE_START_TIME",
           "USAGE_END_TIME", "USAGE_KWH", "ESTIMATED_ACTUAL",
           "CONSUMPTION_SURPLUSGENERATION"]
STEPS_PER_HOUR = 4                      # 15-minute readings


def _runs(rng, n_steps, start_lo, start_hi, length, prob):
    """A 0/1 array of one day's 15-minute steps with at most one run in it."""
    on = np.zeros(n_steps)
    if rng.random() < prob:
        s = int(rng.integers(start_lo, start_hi))
        on[s:s + length] = 1.0
    return on


def synthetic_export(seed=4301, year=2025):
    """One year of 15-minute readings in the Smart Meter Texas export format.

    Deterministic for a given seed: the same seed gives the same house, on
    every machine, because every draw comes from one numpy Generator.
    """
    rng = np.random.default_rng(seed)
    days = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")
    n = 24 * STEPS_PER_HOUR
    step_hour = np.arange(n) / STEPS_PER_HOUR
    kw_days = []
    for day in days:
        doy, weekend = day.dayofyear, day.dayofweek >= 5
        # outdoor temperature, F: a seasonal swing, a daily swing, a daily draw
        temp = (68 + 18 * np.cos(2 * np.pi * (doy - 200) / 365)
                + 9 * np.sin(2 * np.pi * (step_hour - 9) / 24)
                + rng.normal(0, 4))
        kw = np.full(n, 0.22)                                   # always on
        kw += 0.13 * (np.arange(n) % 3 == rng.integers(0, 3))   # fridge compressor
        # central AC, 3.6 kW when running; runs more of each quarter hour as it heats
        duty = np.clip((temp - 76) / 14, 0, 1)
        kw += 3.6 * (rng.random(n) < duty)
        # heat strips, 5 kW, on cold mornings only
        cold = (temp < 42) & (step_hour >= 5) & (step_hour < 9)
        kw += 5.0 * (cold & (rng.random(n) < 0.5))
        # water heater, 4.5 kW element: a morning run and an evening run
        kw += 4.5 * _runs(rng, n, 6 * 4, 8 * 4, int(rng.integers(1, 3)), 0.9)
        kw += 4.5 * _runs(rng, n, 19 * 4, 22 * 4, int(rng.integers(1, 3)), 0.8)
        # dryer, 3.4 kW for 45-60 minutes, more often at weekends
        kw += 3.4 * _runs(rng, n, (10 if weekend else 17) * 4, 20 * 4,
                          int(rng.integers(3, 5)), 0.6 if weekend else 0.2)
        # cooktop or oven, 2 kW, most evenings
        kw += 2.0 * _runs(rng, n, 17 * 4, 19 * 4, int(rng.integers(2, 5)), 0.75)
        # lighting and plug load: low overnight, up in the morning and evening
        awake = (np.exp(-((step_hour - 7.5) ** 2) / 2)
                 + 1.6 * np.exp(-((step_hour - 20.5) ** 2) / 5))
        if weekend:
            awake = awake + 0.6 * np.exp(-((step_hour - 13) ** 2) / 10)
        kw += 0.45 * awake + rng.normal(0, 0.03, n).clip(-0.05, 0.05)
        kw_days.append(kw.clip(0.05))

    kw = np.concatenate(kw_days)
    start = pd.date_range(f"{year}-01-01", periods=len(kw), freq="15min")
    end = start + pd.Timedelta(minutes=15)
    return pd.DataFrame({
        "ESIID": SYNTHETIC_ESIID,
        "USAGE_DATE": start.strftime("%m/%d/%Y"),
        "REVISION_DATE": "",
        "USAGE_START_TIME": start.strftime("%H:%M"),
        "USAGE_END_TIME": end.strftime("%H:%M"),
        "USAGE_KWH": np.round(kw / STEPS_PER_HOUR, 3),
        "ESTIMATED_ACTUAL": "A",
        "CONSUMPTION_SURPLUSGENERATION": "Consumption",
    }, columns=COLUMNS)


def to_kw(raw):
    """(consumption kW, exported kWh) from an export: 15-minute energy -> power.

    Read with numpy rather than the notebook's pandas indexing, on purpose; the
    rows are put in time order first, because an export is not guaranteed to be.
    """
    time = pd.to_datetime(raw["USAGE_DATE"] + " " + raw["USAGE_START_TIME"],
                          format="%m/%d/%Y %H:%M")
    export = raw["CONSUMPTION_SURPLUSGENERATION"].str.startswith("Surplus").to_numpy()
    kwh = raw["USAGE_KWH"].to_numpy(dtype=float)
    order = np.argsort(time.to_numpy()[~export], kind="stable")
    use_time = time.to_numpy()[~export][order]
    kw = pd.Series(kwh[~export][order] * STEPS_PER_HOUR, index=pd.DatetimeIndex(use_time))
    return kw, float(kwh[export].sum())


def hourly_profile(kw):
    """Average kW by hour of day, weekdays and weekends, by whole-day reshapes."""
    days = kw.index.normalize()
    out = {}
    for label, keep in (("weekday", days.dayofweek < 5), ("weekend", days.dayofweek >= 5)):
        block = kw.to_numpy()[keep]
        hours = kw.index.hour.to_numpy()[keep]
        sums = np.bincount(hours, weights=block, minlength=24)
        counts = np.bincount(hours, minlength=24)
        out[label] = sums / counts
    return pd.DataFrame(out)


def base_load(kw, quantile=0.05):
    """The level the house rarely drops below: a low quantile, not the minimum,
    so one odd reading does not decide it."""
    return float(np.quantile(kw.to_numpy(), quantile))


def biggest_steps(kw, n=10):
    """The n largest upward jumps between consecutive readings, kW, largest first."""
    jumps = np.diff(kw.to_numpy())
    return np.sort(jumps)[::-1][:n]
