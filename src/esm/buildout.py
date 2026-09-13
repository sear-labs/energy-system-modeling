# -*- coding: utf-8 -*-
"""Checks for the Texas multi-hub buildout, written so a notebook can verify itself.

    from esm.buildout import load_buildout_instance, corridor_distances
    inst = load_buildout_instance()
    corridor_distances(inst)

WHAT THIS IS, AND WHAT IT IS NOT

`notebooks/capstone/AppA_texas_multi_city_buildout.ipynb` builds a multi-period,
five-hub capacity expansion model with storage, transmission, fuel networks and
a generation-transmission constraint. **This module does not re-solve it, and
does not pretend to.**

The reason is the one set out in `esm.facility`, only more so. A second
implementation would have to reproduce PyPSA's conventions for `StorageUnit`
state of charge, multi-period investment, line expansion and snapshot
weighting. Those conventions are what the second implementation would be
guessing at, so an agreement built on them would be testing a reading of the
PyPSA documentation rather than the model. A confident wrong answer is worse
than a stated gap.

**What this module does instead is attack the inputs and the invariants** --
the places where a spatial capacity-expansion study actually goes wrong, and
where an independent calculation is genuinely available:

  distances        recomputed by a DIFFERENT great-circle formula
  fuel costs       rebuilt from price, heat rate and VOM
  capital          annualised through the same CRF the rest of the package uses
  resource limits  built capacity checked against the stated maxima
  demand shares    checked to sum to one

WHY THE DISTANCE CHECK IS WORTH HAVING

The notebook uses the haversine formula. This module uses the spherical law of
cosines -- a different expression of the same geometry, not a reimplementation
of the same code. It catches the error that actually happens here: latitude and
longitude swapped in one hub's tuple, or a radius in miles. Both produce
plausible-looking distances and a plausible-looking answer, and neither shows up
anywhere else in the model.

The two formulas agree to about 1e-13 on these corridors, and the largest
disagreement is on the SHORTEST one (Austin-San Antonio, 118 km). That is not
noise, it is the known weakness of the law of cosines at small angles, where
`arccos` of a number very near 1 loses precision -- which is the reason
haversine exists. It matters here only as a reminder that the two routes are
genuinely different calculations rather than one written twice.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from esm.data import table
from esm.lcoe import capital_recovery_factor

EARTH_RADIUS_KM = 6371.0


@dataclass(frozen=True)
class BuildoutInstance:
    hubs: dict                # hub -> {"lat", "lon", "demand_share",
                              #         "wind_max_mw", "solar_max_mw"}
    corridors: list           # [(hub_a, hub_b), ...]
    costs: dict               # parameter -> float


def load_buildout_instance(source=None):
    """The five-hub instance, from `data/raw/`."""
    h = table("buildout_hubs.csv", source=source, float_precision="round_trip")
    hubs = {}
    for _, r in h.iterrows():
        hubs[str(r["hub"])] = {
            "lat": float(r["lat"]), "lon": float(r["lon"]),
            "demand_share": float(r["demand_share"]),
            "wind_max_mw": float(r["wind_max_mw"]),
            "solar_max_mw": float(r["solar_max_mw"]),
        }

    c = table("buildout_corridors.csv", source=source)
    corridors = [(str(a), str(b)) for a, b in zip(c["hub_a"], c["hub_b"])]
    for a, b in corridors:
        if a not in hubs or b not in hubs:
            raise ValueError(
                f"corridor {a!r}-{b!r} names a hub that is not in "
                f"buildout_hubs.csv."
            )

    k = table("buildout_costs.csv", source=source,
              float_precision="round_trip")
    costs = dict(zip(k["parameter"], k["value"].astype(float)))

    return BuildoutInstance(hubs=hubs, corridors=corridors, costs=costs)


def great_circle_km(a, b):
    """Distance between two (lat, lon) points by the SPHERICAL LAW OF COSINES.

    Deliberately not haversine -- see the module docstring. `math` rather than
    numpy so this shares nothing at all with the notebook's implementation.
    """
    lat1, lat2 = math.radians(a[0]), math.radians(b[0])
    dlon = math.radians(b[1] - a[1])
    cos_d = (math.sin(lat1) * math.sin(lat2)
             + math.cos(lat1) * math.cos(lat2) * math.cos(dlon))
    return EARTH_RADIUS_KM * math.acos(min(1.0, max(-1.0, cos_d)))


def corridor_distances(inst):
    """Every corridor's length in km, by the independent formula."""
    out = {}
    for a, b in inst.corridors:
        pa = (inst.hubs[a]["lat"], inst.hubs[a]["lon"])
        pb = (inst.hubs[b]["lat"], inst.hubs[b]["lon"])
        out[(a, b)] = great_circle_km(pa, pb)
    return out


def daily_capital(capex_per_mw, lifetime_years, discount_rate):
    """$/MW overnight -> $/MW/day, since a period here is one representative day.

    Mixing $/yr capital with $/day operating is the commonest way to get a
    capacity-expansion answer wrong by three orders of magnitude, which is why
    this is a named function rather than an inline division.
    """
    return (capex_per_mw * capital_recovery_factor(discount_rate,
                                                   int(lifetime_years))
            / 365.0)


def line_daily_capital(inst, km):
    """$/MW/day for a corridor of `km`, at the instance's line cost."""
    return daily_capital(inst.costs["line_capex_per_mw_km"] * km,
                         inst.costs["line_life_years"],
                         inst.costs["discount_rate"])


def fuel_cost_per_mwh(price_per_mmbtu, heat_rate_mmbtu_per_mwh, vom_per_mwh):
    """All-in variable cost of a thermal MWh."""
    return price_per_mmbtu * heat_rate_mmbtu_per_mwh + vom_per_mwh


def gas_cost_per_mwh(inst):
    price = inst.costs["gas_price_per_mcf"] / inst.costs["gas_mmbtu_per_mcf"]
    return fuel_cost_per_mwh(price, inst.costs["gas_heat_rate_mmbtu_per_mwh"],
                             inst.costs["gas_vom_per_mwh"])


def coal_cost_per_mwh(inst):
    price = inst.costs["coal_price_per_ton"] / inst.costs["coal_mmbtu_per_ton"]
    return fuel_cost_per_mwh(price, inst.costs["coal_heat_rate_mmbtu_per_mwh"],
                             inst.costs["coal_vom_per_mwh"])


def check_demand_shares(inst, tol=1e-9):
    """Hub demand shares must sum to one.

    If they do not, total demand is silently wrong by the shortfall and every
    capacity in the answer is wrong with it, while nothing looks out of place.
    """
    total = sum(h["demand_share"] for h in inst.hubs.values())
    if abs(total - 1.0) > tol:
        raise AssertionError(
            f"hub demand shares sum to {total:.6f}, not 1. Total system demand "
            f"is therefore {abs(1 - total):.1%} away from what the notebook "
            f"states, and every built capacity is wrong by about that much."
        )
    return True


def check_resource_limits(inst, built_wind_mw, built_solar_mw, tol=1e-6):
    """Built capacity must respect the stated resource maxima.

    Takes plain dicts rather than a PyPSA network, so the package keeps no
    dependency on the solver library it is checking.
    """
    bad = []
    for hub, mw in built_wind_mw.items():
        cap = inst.hubs.get(hub, {}).get("wind_max_mw", 0.0)
        if mw > cap + tol:
            bad.append(f"wind at {hub}: {mw:,.0f} MW built, {cap:,.0f} allowed")
    for hub, mw in built_solar_mw.items():
        cap = inst.hubs.get(hub, {}).get("solar_max_mw", 0.0)
        if mw > cap + tol:
            bad.append(f"solar at {hub}: {mw:,.0f} MW built, {cap:,.0f} allowed")
    if bad:
        raise AssertionError(
            "built capacity exceeds the resource limit -- the limits are not "
            "reaching the model: " + "; ".join(bad))
    return True
