# case_ACTIVSg2000.m — sidecar

    source URL       https://raw.githubusercontent.com/MATPOWER/matpower/master/data/case_ACTIVSg2000.m
    upstream origin  Texas A&M University Electric Grid Test Case Repository
                     https://electricgrids.engr.tamu.edu/electric-grid-test-cases/activsg2000/
    retrieval date   2026-09-13
    sha256           8d00618de8fd10bf35a599f59d2deebfecd0d86e28fcff73219ad7c4ebab860b
    size             659,546 bytes
    licence          see below — NOT a standard SPDX licence, read this section
    citation         A. B. Birchfield, T. Xu, K. M. Gegner, K. S. Shetye and
                     T. J. Overbye, "Grid Structural Characteristics as
                     Validation Criteria for Synthetic Networks," IEEE
                     Transactions on Power Systems, vol. 32, no. 4,
                     pp. 3258-3265, July 2017. doi:10.1109/TPWRS.2016.2616385

## What this is

A 2000-bus synthetic power system on the geographic footprint of Texas, built
by Texas A&M under ARPA-E's GRID DATA programme. It is **entirely synthetic**
and represents no actual grid; it is built from public information and
statistical analysis so that it has realistic structure without disclosing
anything about the real network.

`notebooks/p4_networks/15_real_network_import.ipynb` reads it.

## The licence position, in full, because it is not simple

**MATPOWER's BSD licence does not cover this file.** The file is fetched from
MATPOWER's repository, and MATPOWER's own `LICENSE` opens:

> The code in MATPOWER is distributed under the 3-clause BSD license below.
> **The MATPOWER case files distributed with MATPOWER are not covered by the
> BSD license.** In most cases, the data has either been included with
> permission or has been converted from data available from a public source.

So the licence that governs is the case's own, granted by Texas A&M. Their page
for this case states:

> This power system dataset is synthetic and does not represent any actual
> grid. It is provided by Texas A&M University researchers free for commercial
> or non-commercial use.

**That grant is explicit about USE and silent about REDISTRIBUTION.** The
repository also asks downloaders to complete a form and to cite the papers,
which suggests a preference for serving the file themselves.

## Why it is vendored here anyway, and who decided

Vendoring it is redistribution, which the grant does not expressly address.

Reviewed 2026-09-13. The evidence above was put to Erick Jones with a
recommendation NOT to vendor and to keep the run-time fetch instead. **He
decided to vendor it on the strength of the free-use grant.** That is recorded
here rather than in a commit message alone so that the reasoning travels with
the file.

The case for it: the grant is broad and unqualified in its own terms ("free for
commercial or non-commercial use"), the data is synthetic and was published
expressly for research and teaching, attribution is given, and the citation the
authors ask for is above.

The case against, which stands: "use" is not "redistribute", and this
repository's own rule in `../vendor/README.md` is that a licence is "stated,
never assumed".

**If Texas A&M objects, the fix is to delete this file and the sidecar and
restore the run-time fetch in the notebook's builder.** Nothing else depends on
it being local. A written permission from the repository would settle the
question properly and is worth asking for.

## Licence of this file within this repository

Not MIT. `../../LICENSE-DATA` gives `data/vendor/` its own terms: each file here
keeps whatever it arrived with. This one arrived with the Texas A&M grant quoted
above and nothing more.
