# -*- coding: utf-8 -*-
"""A household energy balance, written once so a notebook can be checked against it.

    from esm.balance import load_balance_instance, solve_balance
    inst = load_balance_instance()
    r = solve_balance(inst)
    r.total_in, r.useful, r.rejected

WHAT THIS IS FOR

`notebooks/p1_foundations/02_one_house_balance.ipynb` converts three utility
bills into one common unit, splits each into useful and rejected energy, and
checks the balance closes.

WHAT "AGREEMENT" CAN AND CANNOT MEAN FOR A NOTEBOOK WITH NO SOLVER

The other modules here re-solve an optimisation through a different library, so
agreement means two search procedures found the same optimum. There is no
search in this notebook. Re-implementing `billed x factor x efficiency` a
second way would produce a second copy of the same three multiplications, and
agreement between them would mean almost nothing -- a wrong conversion factor
would be in both.

So the checks that carry weight here are different in kind, and there are three:

**1. Conservation, exactly.** Useful plus rejected must equal input, per source
and in total. This is the one invariant the arithmetic cannot satisfy by
accident, and `conservation_residual()` reports it rather than asserting a
tolerance chosen in advance.

**2. Dimensional analysis against primary definitions.** The real risk in this
notebook is a unit conversion, so the second implementation attacks the units
rather than the arithmetic. `si_consistency()` rebuilds the therm factor from
what a therm IS -- 100,000 Btu, and the Btu is exactly defined -- and reports
the gap against the table.

**3. Order-independence.** Totals are accumulated in a different order here than
in the notebook's pandas column sums. That catches nothing on three rows and is
honest about it; it is documented so nobody mistakes it for a real check.

WHICH CONSTANTS CAN BE CHECKED, AND WHICH CANNOT

This distinction is the useful content of `si_consistency()` and is worth more
than the number it returns.

**The therm is definitional.** 1 therm = 100,000 Btu exactly, and 1 Btu (IT) =
1055.05585262 J exactly, so 1 therm = 29.30710702... kWh exactly. The table
says 29.3, which is low by 2.4e-4 relative. That is a rounding, deliberate and
conventional in teaching material, not an error -- but it is a real
discrepancy, so it is reported rather than hidden, and the tolerance it needs
is 5e-4 rather than AGREEMENT_RTOL.

**Gasoline is not.** There is no exact kWh per gallon: heating value is a
measured property that varies with blend, season and standard. EIA gives about
32.9 kWh/gal lower and 35.3 kWh/gal higher. The table's 33.7 sits between them
and matches neither, because 33.7 kWh/gal is the **EPA's gallon-equivalent used
for MPGe ratings**, a regulatory convention rather than a heating value. The
notebook's comment calls it a lower heating value.

`si_consistency()` therefore refuses to check gasoline and says why. Asserting a
tolerance against a "true" value that does not exist would be inventing
precision -- and picking one of EIA's two figures would silently change every
number in the notebook and the book figure drawn from it.
"""
from __future__ import annotations

from dataclasses import dataclass

from esm.data import table

#: 1 Btu (International Table), in joules. Exact by definition.
JOULES_PER_BTU = 1055.05585262

#: 1 kWh in joules. Exact.
JOULES_PER_KWH = 3.6e6

#: 1 therm = 100,000 Btu, by definition.
BTU_PER_THERM = 100_000

#: How far the table's rounded conversion factors may sit from their exact
#: definitions. NOT an agreement tolerance: this is the size of a deliberate
#: rounding in teaching material, three orders of magnitude looser than
#: AGREEMENT_RTOL, and it applies only to factors that HAVE an exact value.
ROUNDED_FACTOR_RTOL = 5e-4


@dataclass(frozen=True)
class BalanceInstance:
    """One household's bills, as billed."""
    sources: dict             # name -> {"as_billed", "unit", "kwh_per_unit",
                              #          "efficiency", "where_from"}


@dataclass(frozen=True)
class BalanceResult:
    kwh_in: dict              # source -> kWh
    useful: dict              # source -> kWh doing the job
    rejected: dict            # source -> kWh lost
    total_in: float
    total_useful: float
    total_rejected: float


def load_balance_instance(source=None):
    """The household instance, from `data/raw/house_energy.csv`.

    Read through `esm.data.table`. The notebook states these same numbers
    inline, since seeing the bills is the point there; the two are copies and
    the agreement assertion is what stops them drifting.
    """
    t = table("house_energy.csv", source=source)
    sources = {}
    for _, row in t.iterrows():
        eff = float(row["efficiency"])
        if not 0.0 < eff <= 1.0:
            raise ValueError(
                f"{row['source']!r} has efficiency {eff}, which is not a "
                f"fraction between 0 and 1. An efficiency above 1 would make "
                f"useful energy exceed input and break conservation."
            )
        sources[row["source"]] = {
            "as_billed": float(row["as_billed"]),
            "unit": str(row["unit"]),
            "kwh_per_unit": float(row["kwh_per_unit"]),
            "efficiency": eff,
            "where_from": str(row["where_from"]),
        }
    return BalanceInstance(sources=sources)


def solve_balance(inst):
    """Convert, split, and total -- accumulating in joules.

    Internally in joules rather than kWh so the conversion to a common unit
    happens once, at a named SI constant, instead of being implied by the
    per-source factors. The result is returned in kWh because that is the unit
    the notebook and the reader's bills are in.
    """
    kwh_in, useful, rejected = {}, {}, {}
    joules_in = joules_useful = 0.0

    for name, s in inst.sources.items():
        j = s["as_billed"] * s["kwh_per_unit"] * JOULES_PER_KWH
        ju = j * s["efficiency"]
        joules_in += j
        joules_useful += ju
        kwh_in[name] = j / JOULES_PER_KWH
        useful[name] = ju / JOULES_PER_KWH
        rejected[name] = (j - ju) / JOULES_PER_KWH

    return BalanceResult(
        kwh_in=kwh_in, useful=useful, rejected=rejected,
        total_in=joules_in / JOULES_PER_KWH,
        total_useful=joules_useful / JOULES_PER_KWH,
        total_rejected=(joules_in - joules_useful) / JOULES_PER_KWH,
    )


def conservation_residual(result):
    """Input minus (useful + rejected), per source and in total.

    The one invariant here that cannot be satisfied by accident. Returned
    rather than asserted so a caller can print it -- the notebook does, and a
    residual printed as zero is worth more to a reader than an assertion that
    quietly passed.
    """
    out = {name: result.kwh_in[name] - result.useful[name] - result.rejected[name]
           for name in result.kwh_in}
    out["total"] = (result.total_in - result.total_useful
                    - result.total_rejected)
    return out


def si_consistency(inst):
    """Rebuild each conversion factor from primary definitions where one exists.

    Returns `{source: (table_value, exact_value, relative_gap)}` for factors
    that are definitional, and omits the rest. Read the module docstring on why
    gasoline is absent -- it is not an oversight, and adding it would require
    inventing a true value that does not exist.
    """
    exact = {
        "therms": BTU_PER_THERM * JOULES_PER_BTU / JOULES_PER_KWH,
        "kWh": 1.0,
    }
    out = {}
    for name, s in inst.sources.items():
        if s["unit"] in exact:
            want = exact[s["unit"]]
            got = s["kwh_per_unit"]
            out[name] = (got, want, abs(got - want) / want)
    return out


def unverifiable_factors(inst):
    """Sources whose conversion factor has no exact value to check against.

    Named explicitly so "not checked" is a visible fact rather than a silent
    gap in `si_consistency()`.
    """
    return {name: s["unit"] for name, s in inst.sources.items()
            if s["unit"] not in ("therms", "kWh")}


def rejected_share(result):
    """Each source's share of all rejected energy, largest first."""
    total = result.total_rejected
    pairs = sorted(((n, v / total) for n, v in result.rejected.items()),
                   key=lambda t: -t[1])
    return dict(pairs)
