# -*- coding: utf-8 -*-
"""Does `esm.sourcing` reproduce the cobalt sourcing instance?

Physics/economics tests on the package itself, mirroring test_transport.py's
shape: these check the model against the problem, not against the notebook, so
"they agree" cannot be satisfied by both being wrong the same way.

Needs scipy, which is a base dependency of `esm` (see pyproject.toml), so this
does NOT skip the way test_power_flow.py does for PyPSA.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from esm.sourcing import (  # noqa: E402
    SourcingInstance, assert_flows_are_unique, load_sourcing_instance,
    processor_utilisation, solve_sourcing,
)


@pytest.fixture(scope="module")
def solved():
    inst = load_sourcing_instance()
    return inst, solve_sourcing(inst)


def test_the_instance_is_the_one_the_notebook_describes(solved):
    inst, _ = solved
    assert inst.mines == {"DRC": 120.0, "Australia": 60.0, "Domestic": 40.0}
    assert inst.processors == {"China": 120.0, "Domestic": 120.0}
    assert inst.plants == {"Cell Plant A": 70.0, "Cell Plant B": 50.0}
    assert inst.ship[("DRC", "China")] == 2.0
    assert inst.deliver[("China", "Cell Plant A")] == 3.0


def test_the_domestic_name_collision_is_resolved_by_stage_not_by_origin():
    """The regression this module was written to catch.

    "Domestic" names both a mine and a processor. A loader that decides a
    route's stage from its origin alone files the Domestic PROCESSOR's
    deliveries as MINE shipments, producing a different LP.

    It is invisible on the base case: the unconstrained optimum never uses the
    Domestic processor, so the wrong model still returns $600 and still agrees
    with the notebook. Pin the classification directly rather than trusting a
    cost comparison to reveal it.
    """
    inst = load_sourcing_instance()
    # Domestic mine -> Domestic processor is a FIRST-stage leg
    assert ("Domestic", "Domestic") in inst.ship
    # Domestic processor -> plants are SECOND-stage legs, not shipments
    assert ("Domestic", "Cell Plant A") in inst.deliver
    assert ("Domestic", "Cell Plant B") in inst.deliver
    assert ("Domestic", "Cell Plant A") not in inst.ship
    assert ("Domestic", "Cell Plant B") not in inst.ship
    assert len(inst.ship) == 6 and len(inst.deliver) == 4


def test_least_cost_is_600_through_one_mine_and_one_processor(solved):
    _, r = solved
    assert abs(r.cost - 600.0) < 1e-6
    # the result that carries the module: 100% from a single mine
    assert abs(r.by_mine["DRC"] - 120.0) < 1e-6
    assert abs(r.by_mine["Australia"]) < 1e-6
    assert abs(r.by_mine["Domestic"]) < 1e-6


def test_every_plant_receives_exactly_its_requirement(solved):
    inst, r = solved
    for j, need in inst.plants.items():
        got = sum(v for k, v in r.flows.items()
                  if k in inst.deliver and k[1] == j)
        assert abs(got - need) < 1e-6


def test_each_processor_ships_exactly_what_it_received(solved):
    """Conservation -- the nodal balance in supply-chain clothing."""
    inst, r = solved
    for p in inst.processors:
        got = sum(v for k, v in r.flows.items()
                  if k in inst.ship and k[1] == p)
        out = sum(v for k, v in r.flows.items()
                  if k in inst.deliver and k[0] == p)
        assert abs(got - out) < 1e-6


def test_no_mine_or_processor_exceeds_capacity(solved):
    inst, r = solved
    for i, cap in inst.mines.items():
        assert r.by_mine[i] <= cap + 1e-6
    for p, cap in inst.processors.items():
        got = sum(v for k, v in r.flows.items()
                  if k in inst.ship and k[1] == p)
        assert got <= cap + 1e-6


def test_china_capacity_is_active_but_not_restrictive(solved):
    """The distinction the notebook's Exercise E.1 turns on.

    China runs at exactly 100% of its 120 kt cap, so the constraint is ACTIVE.
    The notebook's PyPSA formulation omits processor capacity entirely and still
    agrees -- because the constraint is not RESTRICTIVE, the cheapest route
    being capped at 120 by the DRC mine anyway. Agreement there is a
    coincidence, and this pins it so nobody rewrites the prose as "it does not
    bind".
    """
    inst, r = solved
    assert abs(processor_utilisation(inst, r)["China"] - 1.0) < 1e-9
    relaxed = SourcingInstance(
        mines=inst.mines,
        processors={**inst.processors, "China": 1e6},
        plants=inst.plants, ship=inst.ship, deliver=inst.deliver,
    )
    assert abs(solve_sourcing(relaxed).cost - r.cost) < 1e-6, (
        "removing the China cap changed the answer, so it IS restrictive and "
        "the notebook's PyPSA omission is no longer harmless"
    )


def test_the_resilience_price_curve(solved):
    """The module's headline result, asserted rather than only printed.

    Independently derived: the builder's verify() solves the same five points
    in gurobipy, this solves them through scipy.linprog. Both give these.
    """
    inst, base = solved
    for cap, want in ((0.75, 660.0), (0.60, 696.0), (0.50, 720.0), (0.40, 768.0)):
        got = solve_sourcing(inst, cap).cost
        assert abs(got - want) < 1e-6, (cap, got, want)
    # monotone: a tighter cap can never be cheaper
    costs = [solve_sourcing(inst, c).cost for c in (0.75, 0.60, 0.50, 0.40)]
    assert costs == sorted(costs)
    assert base.cost <= costs[0]


def test_a_cap_below_one_third_is_infeasible(solved):
    """Three mines cannot each supply under a third of demand."""
    inst, _ = solved
    with pytest.raises(RuntimeError, match="did not solve"):
        solve_sourcing(inst, 0.33)


def test_the_optimum_is_a_point_so_flows_may_be_compared(solved):
    """Part 6's precondition, checked rather than assumed.

    If a future edit to data/raw/ makes two routes tie, this fails with an
    explanation before the notebook's agreement assertion fails as a mismatch.
    """
    inst, _ = solved
    assert assert_flows_are_unique(inst) is True


def test_a_route_between_the_wrong_kinds_of_node_is_rejected(tmp_path):
    src = ROOT / "data" / "raw"
    for name in ("sourcing_mines.csv", "sourcing_processors.csv",
                 "sourcing_plants.csv", "sourcing_routes.csv"):
        (tmp_path / name).write_text((src / name).read_text(encoding="utf-8"),
                                     encoding="utf-8")
    # a mine shipping straight to a plant, skipping the processor stage
    p = tmp_path / "sourcing_routes.csv"
    p.write_text(p.read_text(encoding="utf-8") + "DRC,Cell Plant A,1.0\n",
                 encoding="utf-8")
    with pytest.raises(ValueError, match="neither a mine-to-processor"):
        load_sourcing_instance(source=tmp_path)


def test_a_local_edit_reaches_the_model(tmp_path):
    """The property Part 4 rests on: editing data/raw/ changes the answer both
    the notebook and the package see."""
    src = ROOT / "data" / "raw"
    for name in ("sourcing_mines.csv", "sourcing_processors.csv",
                 "sourcing_plants.csv", "sourcing_routes.csv"):
        (tmp_path / name).write_text((src / name).read_text(encoding="utf-8"),
                                     encoding="utf-8")

    # make the cheapest leg dearer; total cost must follow
    p = tmp_path / "sourcing_routes.csv"
    p.write_text(p.read_text(encoding="utf-8").replace("DRC,China,2.0",
                                                       "DRC,China,4.0"),
                 encoding="utf-8")

    base = solve_sourcing(load_sourcing_instance())
    edited = solve_sourcing(load_sourcing_instance(source=tmp_path))
    assert edited.cost > base.cost, (
        "editing data/raw/ changed nothing -- the loader is not reading the "
        "file the reader was told to edit"
    )
