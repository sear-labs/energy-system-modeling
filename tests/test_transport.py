# -*- coding: utf-8 -*-
"""Does `esm.transport` reproduce the Texas crude-oil routing instance?

Physics/economics tests on the package itself, mirroring test_power_flow.py's
shape: these check the model against the problem, not against the notebook, so
"they agree" cannot be satisfied by both being wrong the same way.

Needs scipy, which is in the base dependency set (`esm.data` already requires
pandas), so this does NOT skip the way test_power_flow.py does for PyPSA.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from esm.transport import (  # noqa: E402
    binding_routes, load_transport_instance, solve_transport,
)


@pytest.fixture(scope="module")
def solved():
    inst = load_transport_instance()
    return inst, solve_transport(inst)


def test_the_instance_is_the_one_the_notebook_describes(solved):
    inst, _ = solved
    assert inst.supply == {"Permian": 100000.0, "Eagle Ford": 80000.0}
    assert inst.demand == {"Houston": 70000.0, "Corpus": 60000.0, "Beaumont": 50000.0}
    # the bottleneck the whole notebook is about
    assert inst.routes[("Eagle Ford", "Corpus")]["capacity"] == 50000.0
    assert inst.routes[("Eagle Ford", "Corpus")]["cost"] == 1.50


def test_supply_equals_demand_here(solved):
    """The instance is deliberately balanced; a future edit that unbalances it
    should fail loudly rather than solve to a silently wrong answer."""
    inst, _ = solved
    assert sum(inst.supply.values()) == sum(inst.demand.values())


def test_every_supply_node_ships_exactly_its_supply(solved):
    inst, r = solved
    for s in inst.supply_nodes:
        shipped = sum(v for (i, j), v in r.flows.items() if i == s)
        assert abs(shipped - inst.supply[s]) < 1e-6


def test_every_demand_node_receives_exactly_its_demand(solved):
    inst, r = solved
    for d in inst.demand_nodes:
        received = sum(v for (i, j), v in r.flows.items() if j == d)
        assert abs(received - inst.demand[d]) < 1e-6


def test_no_route_exceeds_its_capacity(solved):
    inst, r = solved
    for k, v in r.flows.items():
        assert v <= inst.routes[k]["capacity"] + 1e-6


def test_the_cheap_bottleneck_route_is_saturated(solved):
    """Eagle Ford -> Corpus is the cheapest route ($1.50) and capped at 50,000.
    An optimal solution MUST use all of it -- if this notebook's point (the
    kickback story) is going to land, the bottleneck has to actually bind."""
    inst, r = solved
    assert binding_routes(inst, r) == [("Eagle Ford", "Corpus")]
    assert abs(r.flows[("Eagle Ford", "Corpus")] - 50000.0) < 1e-6


def test_total_cost_is_490000_not_490_million():
    """The regression this module was written to catch.

    The notebook's own printed total was 1000x too large before this module
    existed: `n.objective * 1000`, where `n.objective` was already real
    dollars. $490,000/day, not $490,000,000/day -- pin the correct order of
    magnitude explicitly so nobody re-introduces the multiplier.
    """
    inst = load_transport_instance()
    r = solve_transport(inst)
    assert 480_000 < r.cost < 500_000, (
        f"cost {r.cost:,.0f} is not in the range a 6-route, ~180,000 bbl/d "
        f"instance with $1.50-4.50/bbl routes should produce -- check for a "
        f"reintroduced unit-scaling bug"
    )


def test_unbalanced_instance_is_rejected_rather_than_silently_wrong():
    from esm.transport import TransportInstance

    bad = TransportInstance(
        supply_nodes=["A"], demand_nodes=["B"],
        supply={"A": 100.0}, demand={"B": 90.0},
        routes={("A", "B"): {"cost": 1.0, "capacity": 1000.0}},
    )
    with pytest.raises(ValueError, match="unbalanced"):
        solve_transport(bad)


def test_a_local_edit_reaches_the_model(tmp_path):
    """The property Part 4 rests on: editing data/raw/ changes the answer both
    the notebook and the package see."""
    src = ROOT / "data" / "raw"
    for name in ("transport_supply.csv", "transport_demand.csv",
                 "transport_routes.csv"):
        (tmp_path / name).write_text((src / name).read_text(encoding="utf-8"),
                                     encoding="utf-8")

    routes = (tmp_path / "transport_routes.csv").read_text(encoding="utf-8")
    # tighten the bottleneck further: 50000 -> 40000
    (tmp_path / "transport_routes.csv").write_text(
        routes.replace("Eagle Ford,Corpus,1.50,50000",
                       "Eagle Ford,Corpus,1.50,40000"),
        encoding="utf-8")

    base = solve_transport(load_transport_instance())
    edited = solve_transport(load_transport_instance(source=tmp_path))
    assert edited.cost > base.cost, (
        "tightening the cheapest route's capacity should raise total cost, "
        "but editing data/raw/ changed nothing"
    )
