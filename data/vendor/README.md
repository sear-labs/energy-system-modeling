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
| MATPOWER cases | BSD-3 in practice, no SPDX detected | confirm before vendoring |
| Open-Meteo archive | CC BY 4.0 under their terms | an API; cache a snapshot |
| TU Berlin cloud time series | **none stated** | **replace, do not vendor** |

Two of these need saying plainly:

**The PyPSA cost tables are GPL-3.0.** That is a copyleft licence sitting inside an
MIT repository. Vendoring them means keeping their notice beside them and not
relicensing them — which `LICENSE-DATA` already provides for by giving this
directory its own terms.

**The TU Berlin series has no licence and is behind a personal share link.** No
stated licence is not permission, and a personal share link is not a source. It
gets replaced with something citable rather than vendored.
