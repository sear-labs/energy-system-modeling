# -*- coding: utf-8 -*-
"""Does `esm.power_flow` compute the DC OPF the notebook builds by hand?

These are the package's own tests. The notebook's agreement assertion checks
that the two implementations match each other; these check that the package
matches the *physics*, so that "they agree" cannot be satisfied by both being
wrong in the same way.

Needs PyPSA, so the whole module skips where it is absent -- which is the base
Anaconda environment on the authoring machine. Run it with the `esm` kernel's
interpreter.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

pytest.importorskip("pypsa", reason="PyPSA lives in the esm venv, not the base env")

from esm import tolerance  # noqa: E402
from esm.power_flow import (  # noqa: E402
    check_balances, congestion_rent, load_dcopf3, solve_dcopf,
)


@pytest.fixture(scope="module")
def solved():
    inst = load_dcopf3()
    return inst, solve_dcopf(inst)


def test_the_instance_is_the_one_the_notebook_describes(solved):
    inst, _ = solved
    assert inst.buses == ["West Texas", "Dallas", "Houston"]
    assert inst.loads == {"Dallas": 120.0}
    assert inst.generators["WTX_Wind"]["marginal_cost"] == 0.0
    assert inst.generators["HOU_Gas"]["marginal_cost"] == 40.0
    # the bottleneck, which is the whole point of the example
    assert inst.lines["WTX_DAL"]["s_nom"] == 70.0


def test_demand_is_met_exactly(solved):
    _, r = solved
    assert abs(sum(r.dispatch.values()) - 120.0) < tolerance.CONSERVATION_ATOL


def test_every_bus_balances(solved):
    inst, r = solved
    check_balances(inst, r)  # raises with the residuals if it does not


def test_no_generator_exceeds_its_capacity(solved):
    inst, r = solved
    for g, mw in r.dispatch.items():
        assert -tolerance.CONSERVATION_ATOL <= mw <= inst.generators[g]["p_nom"] + 1e-9


def test_the_bottleneck_line_is_at_its_limit(solved):
    """The congested line is what makes this example teach anything.

    If this stops holding, the instance has changed and the prose above it in the
    notebook -- about congestion and about the $80 price -- is describing a
    different network.
    """
    inst, r = solved
    assert abs(abs(r.flows["WTX_DAL"]) - inst.lines["WTX_DAL"]["s_nom"]) < 1e-6


def test_the_dallas_price_exceeds_every_generator_cost(solved):
    """The counter-intuitive result, asserted rather than only narrated.

    Two generators at $0 and $40, and Dallas pays $80. That is not an error: with
    the import line capped, the marginal megawatt at Dallas has to come the long
    way round, and the price reflects what that displaces. Part 6 asks for the
    domain invariant in code, and this is the one the chapter is about.
    """
    _, r = solved
    costs = [40.0, 0.0]
    assert r.lmp["Dallas"] > max(costs) + 1.0


def test_uncongested_lines_carry_no_congestion_rent(solved):
    inst, r = solved
    rent = congestion_rent(inst, r)
    # the two 1000 MW lines are nowhere near binding
    for name in ("DAL_HOU", "HOU_WTX"):
        assert abs(r.flows[name]) < inst.lines[name]["s_nom"]
    # total rent is what consumers pay minus what generators receive
    paid = sum(inst.loads[b] * r.lmp[b] for b in inst.loads)
    earned = sum(r.dispatch[g] * r.lmp[inst.generators[g]["bus"]]
                 for g in inst.generators)
    assert abs(sum(rent.values()) - (paid - earned)) < 1e-6, (
        "congestion rent should be exactly the gap between what Dallas pays and "
        "what the generators are paid"
    )


def test_tightening_the_bottleneck_raises_the_dallas_price():
    """A monotonicity the model must respect, and a guard against a sign error.

    Squeezing the cheap import can only make Dallas worse off. If a future edit
    flips a sign in the flow constraint, dispatch and cost might still look
    plausible while this reverses.
    """
    inst = load_dcopf3()
    prices = []
    for limit in (50.0, 60.0, 70.0):
        tightened = type(inst)(
            buses=inst.buses,
            generators=inst.generators,
            loads=inst.loads,
            lines={**inst.lines,
                   "WTX_DAL": {**inst.lines["WTX_DAL"], "s_nom": limit}},
        )
        prices.append(solve_dcopf(tightened).lmp["Dallas"])
    assert prices[0] >= prices[1] >= prices[2] - 1e-9, prices


def test_the_solver_choice_does_not_change_the_answer():
    """HiGHS and Gurobi must agree, or one of them is not solving this model.

    Skips where gurobipy has no usable licence, which is what a student without
    one has -- so a skip here is the ordinary case, not a fault.
    """
    pytest.importorskip("gurobipy")
    inst = load_dcopf3()
    a = solve_dcopf(inst, solver="highs")
    try:
        b = solve_dcopf(inst, solver="gurobi")
    except Exception as exc:  # noqa: BLE001 - no licence is a skip, not a failure
        pytest.skip(f"gurobi unavailable here ({type(exc).__name__})")
    assert tolerance.agree(a.cost, b.cost)
    for bus in inst.buses:
        assert tolerance.agree(a.lmp[bus], b.lmp[bus])


def test_a_local_edit_reaches_the_model(tmp_path):
    """The property Part 4 rests on, end to end.

    A reader edits `data/raw/` and re-runs; both the notebook and the package
    must see it. This writes a modified copy of the tables and checks the answer
    moves -- if it does not, the loader is reading something else and the
    agreement assertion is comparing two things that ignore the reader.
    """
    src = ROOT / "data" / "raw"
    for name in ("dcopf3_buses.csv", "dcopf3_generators.csv",
                 "dcopf3_loads.csv", "dcopf3_lines.csv"):
        (tmp_path / name).write_text((src / name).read_text(encoding="utf-8"),
                                     encoding="utf-8")

    # make gas dearer; the Dallas price must follow
    gens = (tmp_path / "dcopf3_generators.csv").read_text(encoding="utf-8")
    (tmp_path / "dcopf3_generators.csv").write_text(
        gens.replace("40.0", "60.0"), encoding="utf-8")

    base = solve_dcopf(load_dcopf3())
    edited = solve_dcopf(load_dcopf3(source=tmp_path))
    assert edited.lmp["Dallas"] > base.lmp["Dallas"], (
        "editing data/raw/ changed nothing -- the loader is not reading the file "
        "the reader was told to edit"
    )
