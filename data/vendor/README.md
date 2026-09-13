# Vendored third-party data

**Empty at the scaffold commit.** Session 5 fills it, and two notebooks
(`real_network_import` and `texas_multi_city_buildout`) download at run time until
it does — which is why they are expected among the diagnostic failures.

## The rule

Third-party data never mixes with the authored tables in `data/raw/`, and **every
file here carries a sidecar** — `<filename>.md` beside it — naming:

    source URL          where it actually came from, not the paper about it
    retrieval date      the data moves; a citation without a date is not reproducible
    licence             stated, never assumed
    citation            what to put in a bibliography

**None of the current sources is MIT**, and one has no stated licence at all.
`../../LICENSE-DATA` covers everything in this repository *except* this directory:
each file here keeps the licence it arrived with.

## What is planned, and what each costs

| file | licence | note |
|---|---|---|
| TX-123BT, Lu and Li 2023 | CC BY 4.0 | DOI `10.6084/m9.figshare.22144616`, attribution required |
| PyPSA technology-data costs | **GPL-3.0** | keep its notice beside it, do not relicense |
| MATPOWER cases | **NOT BSD-3 — confirmed 2026-09-13** | see below; do not vendor on MATPOWER's licence |
| Open-Meteo archive | CC BY 4.0 under their terms | an API; cache a snapshot |
| TU Berlin cloud time series | **none stated** | **replace, do not vendor** |

Three of these need saying plainly:

**The PyPSA cost tables are GPL-3.0.** That is a copyleft licence sitting inside an
MIT repository. Vendoring them means keeping their notice beside them and not
relicensing them — which `LICENSE-DATA` already provides for by giving this
directory its own terms.

**The TU Berlin series has no licence and is behind a personal share link.** No
stated licence is not permission, and a personal share link is not a source. It
gets replaced with something citable rather than vendored.

**The MATPOWER cases are NOT under MATPOWER's BSD licence, and the row above
used to say they were.** Confirmed 2026-09-13 by reading MATPOWER's own
`LICENSE`, which opens:

> The code in MATPOWER is distributed under the 3-clause BSD license below.
> **The MATPOWER case files distributed with MATPOWER are not covered by the
> BSD license.** In most cases, the data has either been included with
> permission or has been converted from data available from a public source.

So the licence that matters is the case's own. `15_real_network_import` uses
`case_ACTIVSg2000`, a synthetic Texas grid from Texas A&M's ARPA-E GRID DATA
programme, whose page states:

> This power system dataset is synthetic and does not represent any actual
> grid. It is provided by Texas A&M University researchers free for commercial
> or non-commercial use.

That is a clear grant to **use**. It is silent on **redistribution**, and the
repository asks downloaders to fill in a form, which is a reason to think they
would rather serve the file themselves than have it mirrored.

**Recommendation: do not vendor it.** Keep the run-time fetch, record the
provenance in a sidecar here, and cite Birchfield et al. If a vendored copy is
wanted later, the honest route is to ask Texas A&M for redistribution
permission in writing rather than to infer it — that is Jones's call, not a
session's.

Note this reverses the previous assumption in the direction that matters. "BSD-3
in practice" was a guess, and the guess was the permissive one.
