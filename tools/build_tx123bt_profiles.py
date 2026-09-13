# -*- coding: utf-8 -*-
"""Derive one compact annual profile table from TX-123BT -> `data/vendor/`.

    python tools/build_tx123bt_profiles.py            # 2021, 1h
    python tools/build_tx123bt_profiles.py --year 2020

WHY A DERIVED TABLE RATHER THAN THE ARCHIVE

TX-123BT is 544 MB and stores its profiles as one file per day: for 2021 that
is 365 load files, 365 solar and 365 wind. `06_end_use_disaggregation` needs a single
annual series of hourly load, wind availability and solar availability, so
vendoring the archive would add half a gigabyte to every clone to deliver about
200 KB of what the notebook actually reads.

So this script pulls only the members it needs -- over HTTP range requests, the
same trick `15_real_network_import` teaches -- aggregates them, and writes one
CSV.

**And it is worth recording that the trick does not pay off at this scale.**
Measured on the 2021 run: 1,099 range requests moved 1,096 MB to extract 436 KB,
because a 1 MB buffered reader re-reads overlapping regions as `zipfile` seeks
between 1,095 members scattered through the archive. Downloading the 544 MB
archive once would have been half the bytes and one request.

Range requests win when you want a FEW members out of a large archive -- which
is exactly notebook 15's case, 1.5 MB in 27 requests -- and lose when you want
most of them. Left as it is because this runs once and needs no 544 MB of local
disk, but nobody should copy the pattern to a whole-archive extraction thinking
it is the efficient choice.

The CSV it writes is a DERIVED WORK of a CC BY 4.0 dataset, which the licence
permits with attribution; the attribution lives in the sidecar this script
writes beside it.

Re-runnable, so the derivation is reproducible rather than a thing that happened
once on somebody's laptop.

WHAT THE AGGREGATION ACTUALLY DOES, AND WHAT IT ASSUMES

    load_mw    sum over all 123 buses, per hour. Real MW.
    wind_pu    total wind output that hour / the year's maximum total
    solar_pu   total solar output that hour / the year's maximum total

**The two `_pu` columns are normalised REALISED output, not availability.** The
archive publishes generation, and generation is availability minus whatever was
curtailed, so a p.u. figure derived this way understates availability in any
hour where output was curtailed. For a teaching notebook driving a
capacity-expansion model that is an acceptable and conventional proxy, and it is
stated here rather than left for a reader to discover.

Normalising by the annual maximum rather than by nameplate capacity is the
second choice worth naming. Nameplate lives in `Generator_data.xlsx`, which
would need openpyxl and a mapping from units to buses; the annual maximum is in
the data already and gives a series that peaks at exactly 1.0, which is what a
`p_max_pu` wants. A reader who needs true capacity factors should go to the
generator table.
"""
import argparse
import hashlib
import io
import os
import zipfile

import numpy as np
import pandas as pd
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "data", "vendor")

ZIP_URL = "https://ndownloader.figshare.com/files/44942761"
DOI = "10.6084/m9.figshare.22144616.v6"
P = "Data_public_5year/"


class HttpFile(io.RawIOBase):
    """A seekable read-only file over HTTP range requests.

    The same device `15_real_network_import` builds and explains. Enough of the
    file protocol for `zipfile`: it reads the end-of-central-directory record,
    then only the members asked for.
    """

    def __init__(self, url):
        self.url = url
        self.s = requests.Session()
        self.pos = 0
        self.n_requests = 0
        self.n_bytes = 0
        r = self.s.get(url, headers={"Range": "bytes=0-0"}, timeout=60,
                       stream=True)
        r.raise_for_status()
        if "Content-Range" not in r.headers:
            raise RuntimeError("server does not support range requests")
        self.size = int(r.headers["Content-Range"].split("/")[1])
        r.close()

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        self.pos = (offset if whence == 0
                    else self.pos + offset if whence == 1
                    else self.size + offset)
        return self.pos

    def readinto(self, b):
        n = len(b)
        if n == 0 or self.pos >= self.size:
            return 0
        end = min(self.pos + n, self.size) - 1
        r = self.s.get(self.url,
                       headers={"Range": f"bytes={self.pos}-{end}"},
                       timeout=180)
        r.raise_for_status()
        data = r.content
        self.n_requests += 1
        self.n_bytes += len(data)
        b[:len(data)] = data
        self.pos += len(data)
        return len(data)


def _grid(zf, name):
    """A whitespace-separated numeric file as a 2-D array."""
    text = zf.read(name).decode("utf-8", "replace")
    rows = [[float(x) for x in line.split()]
            for line in text.strip().splitlines() if line.strip()]
    return np.array(rows)


def build(year=2021):
    remote = HttpFile(ZIP_URL)
    zf = zipfile.ZipFile(io.BufferedReader(remote, buffer_size=1 << 20))
    names = set(zf.namelist())

    days = sorted(
        int(n.rsplit("_D", 1)[1].split(".")[0])
        for n in names
        if n.startswith(f"{P}Load_5y/Load_annual_{year}/load_annual_D"))
    if not days:
        raise SystemExit(f"no load files for {year} in the archive")
    print(f"{len(days)} days found for {year}")

    load, wind, solar = [], [], []
    for i, d in enumerate(days, 1):
        lo = _grid(zf, f"{P}Load_5y/Load_annual_{year}/load_annual_D{d}.txt")
        so = _grid(zf, f"{P}Solar_5y/solar_{year}/solar_annual_D{d}.txt")
        wi = _grid(zf, f"{P}Wind_5y/wind_{year}/wind_annual_D{d}.txt")

        # load is hours x buses; solar and wind are units x hours. Assert it
        # rather than trust it -- a transposed day would silently shift the
        # whole year by the wrong axis and still produce 24 plausible numbers.
        assert lo.shape[0] == 24, (d, "load", lo.shape)
        assert so.shape[1] == 24, (d, "solar", so.shape)
        assert wi.shape[1] == 24, (d, "wind", wi.shape)

        load.append(lo.sum(axis=1))
        solar.append(so.sum(axis=0))
        wind.append(wi.sum(axis=0))
        if i % 60 == 0 or i == len(days):
            print(f"  {i}/{len(days)} days  "
                  f"({remote.n_requests} range requests, "
                  f"{remote.n_bytes / 1024:,.0f} KB)")

    load = np.concatenate(load)
    solar = np.concatenate(solar)
    wind = np.concatenate(wind)
    assert load.shape == solar.shape == wind.shape, "ragged year"

    df = pd.DataFrame({
        "load_mw": load,
        "wind_pu": wind / wind.max(),
        "solar_pu": solar / solar.max(),
    })
    df.insert(0, "hour", range(len(df)))

    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, f"tx123bt_profiles_{year}.csv")
    # repr-precision floats, so the table round-trips exactly
    with io.open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("hour,load_mw,wind_pu,solar_pu\n")
        for _, r in df.iterrows():
            f.write("%d,%s,%s,%s\n" % (int(r["hour"]), repr(float(r["load_mw"])),
                                       repr(float(r["wind_pu"])),
                                       repr(float(r["solar_pu"]))))

    digest = hashlib.sha256(io.open(out, "rb").read()).hexdigest()
    print(f"\nwrote {os.path.relpath(out, ROOT)}")
    print(f"  {len(df):,} hours   sha256 {digest[:16]}...")
    print(f"  load  {df.load_mw.min():,.0f} - {df.load_mw.max():,.0f} MW")
    print(f"  wind  mean p.u. {df.wind_pu.mean():.3f}")
    print(f"  solar mean p.u. {df.solar_pu.mean():.3f}")
    print(f"  fetched {remote.n_bytes / 1024 / 1024:.1f} MB of a "
          f"{remote.size / 1e6:.0f} MB archive in "
          f"{remote.n_requests} range requests")
    return out, digest, len(df), remote


def write_sidecar(out, digest, hours, year):
    path = out + ".md"
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"""# tx123bt_profiles_{year}.csv — sidecar

    derived from    TX-123BT, Texas Synthetic Power System Test Case
    source URL      {ZIP_URL}
    DOI             {DOI}
    authors         Jin Lu and Xingpeng Li
    licence         CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/
    retrieval date  2026-09-13
    sha256          {digest}
    rows            {hours:,} hourly values for {year}

## What this is

A **derived work**: one compact annual table aggregated from TX-123BT's
per-day profile files. CC BY 4.0 permits derivatives with attribution, which
this sidecar supplies.

Regenerate it with:

    python tools/build_tx123bt_profiles.py --year {year}

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
figshare, DOI {DOI}, CC BY 4.0.
""")
    print(f"wrote {os.path.relpath(path, ROOT)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2021)
    a = ap.parse_args()
    out, digest, hours, _ = build(a.year)
    write_sidecar(out, digest, hours, a.year)
