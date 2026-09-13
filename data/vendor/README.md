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
| TX-123BT, Lu and Li 2023 | CC BY 4.0 | DOI `10.6084/m9.figshare.22144616.v6`; **deliberately NOT vendored** — see below |
| PyPSA technology-data costs | **GPL-3.0** | keep its notice beside it, do not relicense |
| `case_ACTIVSg2000.m` | **not MATPOWER's BSD** — Texas A&M free-use grant | **vendored 2026-09-13 on Jones's ruling**; see its sidecar |
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

**TX-123BT is licensed to vendor and is still not vendored, on purpose.** It is
CC BY 4.0, so there is no licence obstacle at all. The obstacle is size and
pedagogy: the archive is **544 MB**, and `15_real_network_import` pulls
**1,546 KB of it in 27 HTTP range requests**. That reader is the teaching
content of the cell -- the printed line is literally "downloaded 1,546 KB in 27
range requests instead of 544 MB". Vendoring the archive would add half a
gigabyte to every clone and delete the lesson at the same time.

If the network dependency ever has to go, the right move is to vendor the four
extracted members (about 1.5 MB) with their own sidecar, and keep the
range-request reader in the notebook as a demonstration against a small
example. Not the whole archive.

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

**Recommended against vendoring; Jones ruled to vendor it, 2026-09-13.** The
file is now here as `case_ACTIVSg2000.m`, with the full licence position, the
recommendation, and the decision recorded in its sidecar so the reasoning
travels with the file. Asking Texas A&M for written redistribution permission
would still settle it properly, and the sidecar says how to reverse the
decision if they object.

Note this reverses the previous assumption in the direction that matters. "BSD-3
in practice" was a guess, and the guess was the permissive one.
