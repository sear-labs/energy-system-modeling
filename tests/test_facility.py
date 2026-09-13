# -*- coding: utf-8 -*-
"""Does `esm.facility` reproduce the facility decision the capstone builds?

Note what these do NOT cover: the battery case. esm/facility.py's docstring
explains why reimplementing PyPSA's StorageUnit would test my reading of its
documentation rather than the model. What is tested instead is that the
objective can be rebuilt from a reported dispatch, which is what the notebook
uses to check the storage run.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from esm.facility import (  # noqa: E402
    annual_bill, battery_annual_per_mw, load_facility_instance,
    recompute_objective, solar_lcoe, solve_site,
)


@pytest.fixture(scope="module")
def inst():
    return load_facility_instance()


def test_the_instance_is_the_one_the_notebook_describes(inst):
    assert inst.roof_mw == 12.0
    assert inst.params["ica_mw"] == 600.0
    assert inst.demand_charge_per_mw_yr == 124_000.0
    assert len(inst.load) == 48
    assert sum(inst.weights[:24]) / 24 == 165.0
    assert abs(max(inst.load) - 50.0) < 0.1


def test_the_representative_days_tile_the_year(inst):
    """165 + 200 = 365. If they did not, every annual total would be wrong by
    the ratio, and nothing else in the notebook would look odd."""
    assert inst.weights[0] + inst.weights[24] == 365


def test_a_weighting_that_does_not_tile_the_year_is_refused(tmp_path):
    src = ROOT / "data" / "raw"
    for name in ("facility_system.csv", "facility_profiles.csv"):
        (tmp_path / name).write_text((src / name).read_text(encoding="utf-8"),
                                     encoding="utf-8")
    p = tmp_path / "facility_system.csv"
    p.write_text(p.read_text(encoding="utf-8").replace("days_winter,200.0",
                                                       "days_winter,100.0"),
                 encoding="utf-8")
    with pytest.raises(ValueError, match="365"):
        load_facility_instance(source=tmp_path)


def test_the_annual_bill_matches_the_notebook(inst):
    assert abs(annual_bill(inst) / 1e6 - 23.4847) < 0.0001


def test_the_solar_economics_match_the_notebook(inst):
    assert abs(inst.solar_annual_per_mw - 110_392) < 1.0
    assert abs(inst.solar_mwh_per_mw_yr - 1_759) < 1.0
    assert abs(solar_lcoe(inst) - 62.75) < 0.01


def test_the_battery_annuity_matches_module_4(inst):
    """$65,877/yr for 1 MW / 2 MWh -- the notebook cites the slide."""
    assert abs(battery_annual_per_mw(inst) - 65_877) < 1.0


def test_doing_nothing_costs_exactly_the_hand_stacked_bill(inst):
    """The property the notebook's own wrapper check rests on, from a third
    formulation: with no solar available the LP can only buy, so its optimum
    must be the bill computed without any optimisation at all."""
    r = solve_site(inst, solar_max=0.0)
    assert abs(r.cost - annual_bill(inst)) / annual_bill(inst) < 1e-12
    assert abs(r.grid_mw - max(inst.load)) < 1e-6


def test_solar_only_matches_the_notebook(inst):
    r = solve_site(inst, solar_max=inst.roof_mw)
    assert abs(r.cost / 1e6 - 23.0477) < 0.0005
    assert abs(r.solar_mw - 12.0) < 1e-6      # the roof bound binds
    assert abs(r.grid_mw - 43.75) < 0.01
    saving = annual_bill(inst) - r.cost
    assert abs(saving / 1e6 - 0.437) < 0.001


def test_solar_shaves_the_billed_peak(inst):
    """Why the array pays: not the energy, the demand charge."""
    base = solve_site(inst, solar_max=0.0)
    with_solar = solve_site(inst, solar_max=inst.roof_mw)
    assert with_solar.grid_mw < base.grid_mw


def test_without_the_demand_charge_no_solar_is_built(inst):
    """The notebook's finding, and the reason the whole capstone exists.

    At $62.75/MWh the array costs more than the energy it displaces. It clears
    only because it cuts the peak the demand charge is levied on -- so remove
    that charge and the recommendation reverses completely.
    """
    r = solve_site(inst, solar_max=inst.roof_mw, demand_charge=0.0)
    assert r.solar_mw < 1e-6


def test_a_flat_tariff_also_kills_it(inst):
    """Same array, same cost, different rate design."""
    flat = [45.0] * len(inst.load)
    r = solve_site(inst, solar_max=inst.roof_mw, retail=flat,
                   demand_charge=0.0)
    assert r.solar_mw < 1e-6


def test_more_roof_cannot_raise_the_cost(inst):
    """A larger bound can only relax the problem."""
    costs = [solve_site(inst, solar_max=m).cost for m in (0.0, 6.0, 12.0, 60.0)]
    assert costs == sorted(costs, reverse=True) or costs[-1] <= costs[0]
    for a, b in zip(costs, costs[1:]):
        assert b <= a + 1e-6


def test_recompute_objective_reproduces_a_solved_cost(inst):
    """The verifier must agree with the solver on a case the solver did solve,
    or its verdict on the battery case means nothing."""
    for m in (0.0, 12.0):
        r = solve_site(inst, solar_max=m)
        again = recompute_objective(inst, r.grid_dispatch, r.grid_mw,
                                    solar_mw=r.solar_mw)
        assert abs(again - r.cost) / r.cost < 1e-12


def test_recompute_objective_notices_a_misweighted_total(inst):
    """What the verifier is actually for.

    An objective built with the representative-day weighting left off is the
    realistic failure -- capacities still look sensible, the total is wrong by
    roughly the number of days. Feed it an unweighted energy total and it must
    not match.
    """
    r = solve_site(inst, solar_max=0.0)
    correct = recompute_objective(inst, r.grid_dispatch, r.grid_mw)
    unweighted = (sum(g * p for g, p in zip(r.grid_dispatch, inst.retail))
                  + r.grid_mw * inst.demand_charge_per_mw_yr)
    assert abs(unweighted - correct) / correct > 0.5


def test_a_dispatch_of_the_wrong_length_is_refused(inst):
    with pytest.raises(ValueError, match="snapshots"):
        recompute_objective(inst, [1.0, 2.0], 50.0)


def test_a_local_edit_reaches_the_model(tmp_path):
    src = ROOT / "data" / "raw"
    for name in ("facility_system.csv", "facility_profiles.csv"):
        (tmp_path / name).write_text((src / name).read_text(encoding="utf-8"),
                                     encoding="utf-8")
    p = tmp_path / "facility_system.csv"
    p.write_text(p.read_text(encoding="utf-8").replace("trans_4cp_per_kw_yr,70.0",
                                                       "trans_4cp_per_kw_yr,140.0"),
                 encoding="utf-8")
    base = load_facility_instance()
    edited = load_facility_instance(source=tmp_path)
    assert annual_bill(edited) > annual_bill(base)
