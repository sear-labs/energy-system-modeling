# tx123bt_profiles_2021.csv — sidecar

    derived from    TX-123BT, Texas Synthetic Power System Test Case
    source URL      https://ndownloader.figshare.com/files/44942761
    DOI             10.6084/m9.figshare.22144616.v6
    authors         Jin Lu and Xingpeng Li
    licence         CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/
    retrieval date  2026-09-13
    sha256          124894bf1e574e8cd31821e1c7b2ad89511443691e72cd44ab4b79ef003f2b0f
    rows            8,760 hourly values for 2021

## What this is

A **derived work**: one compact annual table aggregated from TX-123BT's
per-day profile files. CC BY 4.0 permits derivatives with attribution, which
this sidecar supplies.

Regenerate it with:

    python tools/build_tx123bt_profiles.py --year 2021

## Columns, and what they assume

    load_mw    sum over all 123 buses, per hour. Real MW.
    wind_pu    total wind output that hour / the year's maximum total
    solar_pu   total solar output that hour / the year's maximum total

**The `_pu` columns are normalised realised OUTPUT, not availability.** The
archive publishes generation, so these understate availability in any hour that
was curtailed. For a teaching capacity-expansion model that is a conventional
proxy; it is stated here rather than left to be discovered.

Normalised by the annual maximum rather than by nameplate: nameplate is in
`Generator_data.xlsx` and would need a unit-to-bus mapping, while the annual
maximum is already in the data and yields a series peaking at exactly 1.0,
which is what a `p_max_pu` wants.

## Why the archive itself is not vendored

It is 544 MB. This table is the ~200 KB of it that the notebook reads. See
`README.md` in this directory.

## Citation

Jin Lu and Xingpeng Li, "Texas Synthetic Power System Test Case (TX-123BT)",
figshare, DOI 10.6084/m9.figshare.22144616.v6, CC BY 4.0.
