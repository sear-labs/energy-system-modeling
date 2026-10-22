# -*- coding: utf-8 -*-
"""build_m2_dispatch_notebook.py -> `notebooks/p3_generation/10_dispatch_and_carbon.ipynb`.

WHERE THIS COPY CAME FROM, AND WHAT CHANGED ON THE WAY
Brought from the course folder's `Tools/` on 2026-10-22, after the 20 Oct
Explore section; agreed with teaching-code's owner as the Module 2 walkthrough
for `p3_generation`.  Anchored at Chapter 10, the last chapter whose material it
needs (gas and coal plants), and serving section 9.4, whose numbers it computes:
the $21.65/t flip price and the 500 t cap that puts about 551 MW on gas.
Changes, each a defect or a repository rule:
  * the bare `!pip install -q pypsa highspy` is gone - it was unpinned, and the
    generated setup cell installs the same with version bounds;
  * the CO2 contents (53.06, 97.72) were typed three times and the VOMs twice;
    they are named once (`gas_kg`, `coal_kg`, `gas_vom`, `coal_vom`) so the
    agreement cell can hand the package the notebook's own numbers - a reader
    who edits one sees it reach both sides;
  * each solve's result is kept (`out_b`, `price_b`, `out_c`, `out_cap`,
    `mu_cap`) because the network is re-solved in place three times and only
    the last answer survives to the bottom of the notebook;
  * an agreement cell against `esm.dispatch`, which solves the same hour in MW
    of electricity with no fuel buses and no Links;
  * prose that pointed at slides points at the book.

WHAT THIS IS - a CLASS WALKTHROUGH, not an assignment notebook
Jones, 15 Oct 2026: build the Module 2 walkthrough ("Class Walkthrough Plan.md",
decision 3).  It is opened in class from the "Open Colab: Dispatch, Then a Price
on Carbon" cue slide and run together.  Module 2's "The Same Math in PyPSA"
slide showed code that no student notebook contained; this is that code,
runnable, on the deck's own numbers.

THE NUMBERS ARE THE DECK'S, NOT A GRADED TASK'S
  Houston CCGT     6.370 MMBtu/MWh, gas $2.65/Mcf + $0.50 pipeline, VOM $2.10
  San Antonio coal 10.745 MMBtu/MWh, $18.76/ton + $0.75 rail,     VOM $5.06
from "Cheap Coal Loses to Gas"; emissions 0.338 and 1.050 t/MWh and the $21.65
flip price from the carbon slides.  MP2 asks students to find the carbon price
where THEIR merit order changes; Part C does it on these two plants, so the
method is shown and the graded answer is not.

THREE PARTS, ONE PER CUE
  A  the merit order by hand            ("What Decides Dispatch Order" .. "Merit Order")
  B  the same in PyPSA: fuel is a bus, the plant is a Link ("The Same Math in PyPSA")
  C  a price on carbon, then a cap, and the cap's dual (carbon slides; MP2)
Each Part ends on a question and stops (CLAUDE.md section 1).  verify() solves
every one of those questions so the numbers are right; the notebook does not
print the answers.

UNITS, because PyPSA does not know any: fuel buses are in MWh of heat.  A
fuel's price per MWh_th is $/MMBtu x 3.412; a Link's efficiency is 3.412 /
heat rate; its p_nom is in fuel units (MW_e / efficiency); its marginal_cost is
charged per MWh of fuel IN, so VOM x efficiency.  Then cost per MWh_e out is
heat rate x fuel price + VOM - the formula in Part A.  verify() checks it.

    python build_m2_dispatch_notebook.py          build (verify + syntax check)
    python build_m2_dispatch_notebook.py --run    also execute every cell
                                                  (needs pypsa + highspy on PYTHONPATH)
"""
import json
import os
import sys

# tools/builders/<this file> -> tools/ -> the repository root.
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "notebooks", "p3_generation", "10_dispatch_and_carbon.ipynb")

_N = [0]


def _id():
    _N[0] += 1
    return "cell-%02d" % _N[0]


def md(*lines):
    return {"cell_type": "markdown", "id": _id(), "metadata": {},
            "source": list(lines)}


def code(*lines):
    return {"cell_type": "code", "id": _id(), "execution_count": None,
            "metadata": {}, "outputs": [], "source": list(lines)}


def L(s):
    return s + "\n"


# ------------------------------------------------------------------ numbers
MMBTU_PER_MWH = 3.412
GAS = dict(wellhead=2.65, mmbtu_per_mcf=1.033, adder=0.50, hr=6.370, vom=2.10,
           kg_per_mmbtu=53.06)
COAL = dict(minemouth=18.76, mmbtu_per_ton=15.97, adder=0.75, hr=10.745, vom=5.06,
            kg_per_mmbtu=97.72)
WIND_MW, PLANT_MW, LOAD_MW, CAP_T = 150.0, 600.0, 1000.0, 500.0


def verify():
    gas_gate = GAS["wellhead"] / GAS["mmbtu_per_mcf"] + GAS["adder"]
    coal_gate = COAL["minemouth"] / COAL["mmbtu_per_ton"] + COAL["adder"]
    gas_mc = GAS["hr"] * gas_gate + GAS["vom"]
    coal_mc = COAL["hr"] * coal_gate + COAL["vom"]
    assert round(gas_gate, 3) == 3.065 and round(coal_gate, 3) == 1.925
    assert round(gas_mc, 2) == 21.63 and round(coal_mc, 2) == 25.74   # the deck
    # the Link formulation gives the same cost per MWh electric
    eff = MMBTU_PER_MWH / GAS["hr"]
    link_cost = gas_gate * MMBTU_PER_MWH / eff + GAS["vom"] * eff / eff
    assert abs(link_cost - gas_mc) < 1e-9
    # Part B question: the wellhead gas price that ties the two plants
    tie = ((coal_mc - GAS["vom"]) / GAS["hr"] - GAS["adder"]) * GAS["mmbtu_per_mcf"]
    assert round(tie, 2) == 3.32
    # Part B dispatch: wind, then gas, coal sets the price
    assert LOAD_MW - WIND_MW - PLANT_MW == 250
    # emissions per MWh electric (the carbon slides)
    e_gas = GAS["hr"] * GAS["kg_per_mmbtu"] / 1000
    e_coal = COAL["hr"] * COAL["kg_per_mmbtu"] / 1000
    assert round(e_gas, 3) == 0.338 and round(e_coal, 3) == 1.050
    # Part C: gas at twice the plant-gate price puts coal first ...
    gas_mc2 = GAS["hr"] * 2 * gas_gate + GAS["vom"]
    assert gas_mc2 > coal_mc
    # ... and the carbon price that flips it back is the deck's $21.65
    tau = (gas_mc2 - coal_mc) / (e_coal - e_gas)
    assert round(tau, 2) == 21.65, tau
    for t, flipped in ((0, False), (20, False), (22, True)):
        assert (gas_mc2 + t * e_gas < coal_mc + t * e_coal) == flipped
    # the cap: emissions with g MW of gas and 850-g of coal = 892.5 - 0.712 g
    thermal = LOAD_MW - WIND_MW
    g_min = (thermal * e_coal - CAP_T) / (e_coal - e_gas)
    assert WIND_MW + thermal * 0 >= 0 and 0 < g_min < PLANT_MW
    assert round(g_min) == 551
    # ... and its shadow price is the same tau: every cap has a price
    print("verify: gas $%.2f, coal $%.2f /MWh; tie at $%.2f/Mcf; flip at "
          "$%.2f/t; a %.0f t cap needs %.0f MW of gas and is priced at $%.2f/t"
          % (gas_mc, coal_mc, tie, tau, CAP_T, g_min, tau))
    return dict(tau=tau, g_min=g_min, coal_mc=coal_mc, gas_mc2=gas_mc2)


C = []
A = C.append

# ===================================================================== open
A(md(
L("# Dispatch, then a price on carbon"),
L(""),
L("The two plants of the book's sections 9.3 and 9.4 - the **Houston CCGT** and "
  "a **coal plant**, called *San Antonio coal* below - plus 150 MW of wind, "
  "serving 1,000 MW for one hour. In Colab, *File › Save a copy in Drive* first "
  "so your edits are kept."),
L(""),
L("**Before you run anything:** coal fuel is about 37% cheaper per MMBtu than "
  "gas at the plant gate. Which plant runs first? Write it down."),
))
A(code(
L("import pypsa"),
))

# =================================================================== part A
A(md(
L("## Part A - The merit order, by hand"),
L(""),
L("A plant's marginal cost is **heat rate × fuel price at the plant gate + "
  "variable O&M**. Capital cost is not in it."),
))
A(code(
L("import warnings"),
L("warnings.filterwarnings('ignore', category=FutureWarning)  # PyPSA's notices about its next version"),
L(""),
L("MMBTU_PER_MWH = 3.412               # 1 MWh of electricity = 3.412 MMBtu of heat"),
L(""),
L("# fuel price at the plant gate, $/MMBtu"),
L("gas_gate  = 2.65 / 1.033 + 0.50     # $/Mcf -> $/MMBtu, plus pipeline"),
L("coal_gate = 18.76 / 15.97 + 0.75    # $/ton -> $/MMBtu, plus rail"),
L("print(f'gas  ${gas_gate:.3f}/MMBtu    coal ${coal_gate:.3f}/MMBtu')"),
))
A(md(
L("Then the marginal cost, in $/MWh of electricity."),
))
A(code(
L("gas_hr,  gas_vom  = 6.370, 2.10     # MMBtu/MWh, $/MWh"),
L("coal_hr, coal_vom = 10.745, 5.06"),
L(""),
L("gas_mc  = gas_hr  * gas_gate  + gas_vom"),
L("coal_mc = coal_hr * coal_gate + coal_vom"),
L("print(f'gas  ${gas_mc:.2f}/MWh    coal ${coal_mc:.2f}/MWh')"),
))
A(md(
L("> Coal's fuel was the cheaper one. Which number in the formula outweighed it? "
  "Was your prediction right?"),
))

# =================================================================== part B
A(md(
L("## Part B - The same thing in PyPSA"),
L(""),
L("The solver never sees the words *gas* or *coal*. Each fuel gets its own bus, "
  "measured in MWh of heat, and each plant is a **Link** that turns heat into "
  "electricity at `efficiency = 3.412 / heat rate`."),
))
A(code(
L("# Step 1 - buses: one for electricity, one per fuel"),
L("gas_kg, coal_kg = 53.06, 97.72      # kg CO2 per MMBtu of fuel (EIA)"),
L(""),
L("n = pypsa.Network()"),
L("n.add('Carrier', 'gas',  co2_emissions=gas_kg * MMBTU_PER_MWH / 1000)   # t CO2 per MWh of heat"),
L("n.add('Carrier', 'coal', co2_emissions=coal_kg * MMBTU_PER_MWH / 1000)  # used in Part C"),
L("n.add('Bus', 'Houston')"),
L("n.add('Bus', 'gas fuel',  carrier='gas')"),
L("n.add('Bus', 'coal fuel', carrier='coal')"),
))
A(md(
L("**Step 2 - supply:** fuel at its plant-gate price per MWh of heat, and wind."),
))
A(code(
L("n.add('Generator', 'gas supply',  bus='gas fuel',  carrier='gas',"),
L("      p_nom=10_000, marginal_cost=gas_gate * MMBTU_PER_MWH)"),
L("n.add('Generator', 'coal supply', bus='coal fuel', carrier='coal',"),
L("      p_nom=10_000, marginal_cost=coal_gate * MMBTU_PER_MWH)"),
L("n.add('Generator', 'wind', bus='Houston', p_nom=150, marginal_cost=0)"),
))
A(md(
L("**Step 3 - the plants are Links:** heat in at `bus0`, electricity out at `bus1`."),
))
A(code(
L("gas_eff, coal_eff = MMBTU_PER_MWH / gas_hr, MMBTU_PER_MWH / coal_hr"),
L(""),
L("n.add('Link', 'Houston CCGT', bus0='gas fuel', bus1='Houston',"),
L("      efficiency=gas_eff, p_nom=600 / gas_eff,        # p_nom is heat IN"),
L("      marginal_cost=gas_vom * gas_eff)                 # charged per MWh of heat IN"),
L("n.add('Link', 'San Antonio coal', bus0='coal fuel', bus1='Houston',"),
L("      efficiency=coal_eff, p_nom=600 / coal_eff,"),
L("      marginal_cost=coal_vom * coal_eff)"),
))
A(md(
L("**Step 4 - one hour of demand, and solve.**"),
))
A(code(
L("n.add('Load', 'demand', bus='Houston', p_set=1000)"),
L("n.optimize(solver_name='highs')"),
))
A(md(
L("**Step 5 - who ran, and what the last MWh cost.**"),
))
A(code(
L("out_b = -n.links_t.p1.iloc[0]                   # MW of electricity from each plant"),
L("price_b = n.buses_t.marginal_price['Houston'].iloc[0]"),
L("print(out_b.round(1).to_string())"),
L("print('wind', round(n.generators_t.p['wind'].iloc[0], 1))"),
L("print(f'price at Houston ${price_b:.2f}/MWh')"),
))
A(md(
L("> Compare the price to Part A. Which plant set it, and why that one?"),
L(">"),
L("> Now change one number. What wellhead gas price would put coal first? Work "
  "it out from Part A's formula **before** you edit `gas_gate` and re-run."),
))

# =================================================================== part C
A(md(
L("## Part C - A price on carbon, then a cap"),
L(""),
L("A cold winter doubles the plant-gate gas price. Start there."),
))
A(code(
L("# emissions per MWh of electricity = heat rate x carbon content"),
L("gas_t  = gas_hr  * gas_kg / 1000     # t CO2 / MWh"),
L("coal_t = coal_hr * coal_kg / 1000"),
L("print(f'gas {gas_t:.3f} t/MWh    coal {coal_t:.3f} t/MWh')"),
L(""),
L("gas_gate_winter = 2 * gas_gate"),
))
A(md(
L("**The price form:** add tau × emissions to each fuel's cost, and re-solve."),
))
A(code(
L("tau = 0                              # $ per tonne CO2 - try 0, then 20"),
L(""),
L("n.generators.loc['gas supply', 'marginal_cost'] = ("),
L("    gas_gate_winter * MMBTU_PER_MWH + tau * n.carriers.at['gas', 'co2_emissions'])"),
L("n.generators.loc['coal supply', 'marginal_cost'] = ("),
L("    coal_gate * MMBTU_PER_MWH + tau * n.carriers.at['coal', 'co2_emissions'])"),
L("n.optimize(solver_name='highs')"),
L("out_c, tau_c = -n.links_t.p1.iloc[0], tau"),
L("print(out_c.round(1).to_string())"),
))
A(md(
L("> At \\$0 coal runs first. Does \\$20 flip it? Write the one-line equation for "
  "the carbon price where the two plants tie, solve it by hand, then set `tau` "
  "just above it and run."),
))
A(code(
L("# cap form: no price, a limit on tonnes - and read the limit's shadow price"),
L("tau = 0"),
L("n.generators.loc['gas supply', 'marginal_cost'] = gas_gate_winter * MMBTU_PER_MWH"),
L("n.generators.loc['coal supply', 'marginal_cost'] = coal_gate * MMBTU_PER_MWH"),
L(""),
L("cap_t = 500                            # tonnes of CO2 in the hour"),
L("n.add('GlobalConstraint', 'co2 cap', type='primary_energy',"),
L("      carrier_attribute='co2_emissions', sense='<=', constant=cap_t,"),
L("      overwrite=True)                    # safe to re-run this cell"),
L("n.optimize(solver_name='highs')"),
L("out_cap = -n.links_t.p1.iloc[0]"),
L("mu_cap = abs(n.global_constraints.at['co2 cap', 'mu'])"),
L("print(out_cap.round(1).to_string())"),
L("print(f'cap shadow price ${mu_cap:.2f}/t')"),
))
A(md(
L("> The cap's shadow price is a number you have already met in this notebook. "
  "Which one, and why should they agree?"),
L(""),
L("*Before class: a data center signs for 300 MW at the Houston bus. Which plant "
  "serves its last megawatt - and what would a \\$20 carbon price do to its "
  "bill?*"),
L(""),
L("### Sources"),
L("- Plant numbers: the book's sections 9.3 and 9.4 (Texas 2023 fuel prices; "
  "heat rates and VOM from NREL ATB 2024)."),
L("- CO2 content: EIA carbon dioxide emission coefficients (natural gas 53.06, "
  "lignite 97.72 kg/MMBtu)."),
))


# ================================================================ agreement
A(md(
L("---"),
L("### Does the package agree?"),
L(""),
L("`esm.dispatch` solves the same three hours with `scipy`, written the way Part "
  "A thinks: one variable per plant in MW of electricity, priced at heat rate × "
  "fuel + VOM. No fuel buses, no Links, no efficiencies. So the two can agree "
  "only if every conversion in Part B is right - fuel per MWh of heat, `p_nom` "
  "in heat units, VOM charged per MWh of heat in. Each is a place to be wrong by "
  "a factor of 3.412 and still get a plausible dispatch."),
L(""),
L("A price is a dual, and a dual is determined only when enough plants sit "
  "strictly between empty and full - one for the energy balance, a second "
  "whenever the cap binds. `assert_prices_are_unique` checks that first, so an "
  "edit that lands the load exactly on a plant's limit stops with the reason "
  "instead of a mismatch."),
))
A(code(
L("from esm.dispatch import Thermal, assert_prices_are_unique, solve_hour"),
L("from esm.tolerance import AGREEMENT_RTOL, relative"),
L(""),
L("# everything handed over is read from this notebook, not typed again"),
L("wind_mw = n.generators.at['wind', 'p_nom']"),
L("load_mw = n.loads.at['demand', 'p_set']"),
L("gas_mw = n.links.at['Houston CCGT', 'p_nom'] * gas_eff"),
L("coal_mw = n.links.at['San Antonio coal', 'p_nom'] * coal_eff"),
L("coal = Thermal('San Antonio coal', coal_mw, coal_hr, coal_gate, coal_vom, coal_kg)"),
L("summer = [Thermal('Houston CCGT', gas_mw, gas_hr, gas_gate, gas_vom, gas_kg), coal]"),
L("winter = [Thermal('Houston CCGT', gas_mw, gas_hr, gas_gate_winter, gas_vom, gas_kg), coal]"),
L(""),
L("pkg_b = solve_hour(summer, load_mw, wind_mw)"),
L("pkg_c = solve_hour(winter, load_mw, wind_mw, co2_price=tau_c)"),
L("pkg_cap = solve_hour(winter, load_mw, wind_mw, co2_cap=cap_t)"),
L("for plants, r in ((summer, pkg_b), (winter, pkg_c), (winter, pkg_cap)):"),
L("    assert_prices_are_unique(plants, r, wind_mw)   # compare only what is determined"),
L(""),
L("checks = [('Part B price $/MWh', price_b, pkg_b.price)]"),
L("checks += [(f'Part B {p} MW', out_b[p], pkg_b.output[p]) for p in out_b.index]"),
L("checks += [(f'Part C {p} MW', out_c[p], pkg_c.output[p]) for p in out_c.index]"),
L("checks += [(f'cap {p} MW', out_cap[p], pkg_cap.output[p]) for p in out_cap.index]"),
L("checks += [('cap shadow price $/t', mu_cap, pkg_cap.cap_price)]"),
L("for label, hand, pkg in checks:"),
L("    print(f'{label:26s} {hand:10.3f} {pkg:10.3f}   {relative(hand, pkg):.1e}')"),
L(""),
L("worst = max(relative(a, b) for _, a, b in checks)"),
L("assert worst < AGREEMENT_RTOL, f'notebook and package disagree by {worst:.2e}'"),
L("print(f'\\nnotebook and package agree to {worst:.1e}')"),
))

# ================================================================== explore
# Jones, 20 Oct 2026: a reflection assignment - sliders plus cells where
# students edit a number or a line of model code themselves.  The functions
# rebuild the Part B network from scratch, so Parts A-C stay as walked in
# class; they sit here at the bottom (Teaching Code Standard).
A(md(
L("---"),
L("## Explore - for your reflection"),
L(""),
L("Nothing above changes. Each slider cell rebuilds the Part B network with "
  "your numbers and solves it when you press **Run Interact**. The "
  "**edit-and-run** cells ask you to change a number or write model code "
  "yourself. Answer the numbered questions in your reflection."),
L(""),
L("### Now the streamlined version"),
L(""),
L("Part B's network is wrapped into a function here, because a slider rebuilds and re-solves it every time it moves - and you have built every component of it by hand above. With the defaults it gives back Part B's dispatch and price."),
L(""),
L("### Slide it: dispatch"),
))
A(code(
L("from ipywidgets import interact_manual, FloatSlider"),
L("import logging, warnings"),
L("for name in ('pypsa', 'linopy'):"),
L("    logging.getLogger(name).setLevel(logging.ERROR)"),
L("warnings.filterwarnings('ignore', message='.*include_objective_constant')"),
L(""),
L("def dispatch(gas_wellhead=2.65, coal_mine=18.76, co2_price=0.0,"),
L("             load_mw=1000.0, wind_mw=150.0, coal_min=0.0, co2_cap=None):"),
L("    \"\"\"Part B's network with your numbers. coal_min: share of the coal unit"),
L("    that must stay on. co2_cap: tonnes, or None for no cap.\"\"\""),
L("    g_gate = gas_wellhead / 1.033 + 0.50"),
L("    c_gate = coal_mine / 15.97 + 0.75"),
L("    g_eff, c_eff = MMBTU_PER_MWH / gas_hr, MMBTU_PER_MWH / coal_hr"),
L("    k = pypsa.Network()"),
L("    k.add('Carrier', 'gas',  co2_emissions=53.06 * MMBTU_PER_MWH / 1000)"),
L("    k.add('Carrier', 'coal', co2_emissions=97.72 * MMBTU_PER_MWH / 1000)"),
L("    k.add('Bus', 'Houston')"),
L("    k.add('Bus', 'gas fuel',  carrier='gas')"),
L("    k.add('Bus', 'coal fuel', carrier='coal')"),
L("    k.add('Generator', 'gas supply', bus='gas fuel', carrier='gas', p_nom=10_000,"),
L("          marginal_cost=(g_gate * MMBTU_PER_MWH"),
L("                         + co2_price * k.carriers.at['gas', 'co2_emissions']))"),
L("    k.add('Generator', 'coal supply', bus='coal fuel', carrier='coal', p_nom=10_000,"),
L("          marginal_cost=(c_gate * MMBTU_PER_MWH"),
L("                         + co2_price * k.carriers.at['coal', 'co2_emissions']))"),
L("    k.add('Generator', 'wind', bus='Houston', p_nom=wind_mw, marginal_cost=0)"),
L("    k.add('Link', 'Houston CCGT', bus0='gas fuel', bus1='Houston', efficiency=g_eff,"),
L("          p_nom=600 / g_eff, marginal_cost=gas_vom * g_eff)"),
L("    k.add('Link', 'San Antonio coal', bus0='coal fuel', bus1='Houston',"),
L("          efficiency=c_eff, p_nom=600 / c_eff, marginal_cost=coal_vom * c_eff,"),
L("          p_min_pu=coal_min)"),
L("    k.add('Load', 'demand', bus='Houston', p_set=load_mw)"),
L("    if co2_cap is not None:"),
L("        k.add('GlobalConstraint', 'co2 cap', type='primary_energy',"),
L("              carrier_attribute='co2_emissions', sense='<=', constant=co2_cap)"),
L("    status, condition = k.optimize(solver_name='highs', log_to_console=False)"),
L("    if condition != 'optimal':"),
L("        print(f'no dispatch meets {load_mw:.0f} MW with these rules: the solver says \"{condition}\"')"),
L("        return"),
L("    gas = -k.links_t.p1['Houston CCGT'].iloc[0]"),
L("    coal = -k.links_t.p1['San Antonio coal'].iloc[0]"),
L("    wind = k.generators_t.p['wind'].iloc[0]"),
L("    tonnes = gas * gas_t + coal * coal_t"),
L("    print(f'wind {wind:5.0f} MW   gas {gas:5.0f} MW   coal {coal:5.0f} MW   '"),
L("          f'CO2 {tonnes:5.0f} t')"),
L("    print(f'price at Houston ${k.buses_t.marginal_price[\"Houston\"].iloc[0]:.2f}/MWh')"),
L("    if co2_cap is not None:"),
L("        print(f'cap shadow price ${abs(k.global_constraints.at[\"co2 cap\", \"mu\"]):.2f}/t')"),
L(""),
L("interact_manual(dispatch,"),
L("    gas_wellhead=FloatSlider(min=1, max=8, step=0.05, value=2.65, description='gas $/Mcf'),"),
L("    coal_mine=FloatSlider(min=5, max=60, step=0.5, value=18.76, description='coal $/ton'),"),
L("    co2_price=FloatSlider(min=0, max=60, step=0.5, value=0, description='CO2 $/t'),"),
L("    load_mw=FloatSlider(min=200, max=1500, step=50, value=1000, description='load MW'),"),
L("    wind_mw=FloatSlider(min=0, max=600, step=25, value=150, description='wind MW'),"),
L("    coal_min=FloatSlider(min=0, max=1, step=0.1, value=0, description='coal must-run'),"),
L("    co2_cap=FloatSlider(min=300, max=1000, step=25, value=1000, description='CO2 cap t'));"),
))
A(md(
L("> **1.** Find the wellhead gas price at which coal moves ahead of gas. Does it "
  "match what Part A's formula predicts?"),
L(">"),
L("> **2.** Slide the load from 400 to 1,500 MW in steps of 100. At which loads "
  "does the price jump, and which plant sets it at each step? What happens near "
  "the top of the range, and what is the solver telling you?"),
L(">"),
L("> **3.** Put gas at about $5.80/Mcf so coal runs first, then find the CO2 "
  "price that flips them. Now set wind to 0, then 600 MW. Does the flip price "
  "move? Why or why not?"),
L(">"),
L("> **4.** With winter gas and no CO2 price, tighten the cap from 1,000 t in "
  "steps of 50. Does its shadow price change smoothly, jump, or stay put? Find "
  "the smallest cap this fleet can meet at 1,000 MW, then check it by hand with "
  "Part C's emission rates."),
L(""),
L("### Edit and run: a must-run rule"),
L(""),
L("Change the number in the call, not the function."),
))
A(code(
L("# coal_min is the share of the coal unit that must stay on, whatever it costs."),
L("# Try 0.0, then 0.5, then 1.0, at 700 MW."),
L("dispatch(load_mw=700, coal_min=0.0)"),
))
A(md(
L("> **5.** What happens to gas, to the price and to the tonnes of CO2 as the "
  "rule tightens? Who asks for a rule like this in a real grid, and what are "
  "they protecting?"),
L(""),
L("### Edit and run: add a plant yourself"),
L(""),
L("Copy `dispatch` into the cell below, rename it `dispatch_with_peaker`, and add "
  "a **gas peaker** at Houston: heat rate 9.8 MMBtu/MWh, VOM $4.50/MWh, 200 MW. "
  "It is one more `k.add('Link', ...)` fed from `gas fuel`: follow the CCGT's "
  "pattern for `efficiency`, `p_nom` (heat in) and `marginal_cost`."),
))
A(code(
L("# def dispatch_with_peaker(...):"),
L("#     ..."),
L("#"),
L("# dispatch_with_peaker(load_mw=1300)"),
))
A(md(
L("> **6.** Before you run it: at 1,300 MW, which plant sets the price, and at "
  "what $/MWh? Then run it. If your number and the solver's differ, which line "
  "of your `add` is the likely culprit?"),
))


def syntax_check(cells):
    bad = 0
    for i, c in enumerate(cells):
        if c["cell_type"] != "code":
            continue
        src = "\n".join(l for l in "".join(c["source"]).splitlines()
                        if not l.strip().startswith("!"))
        try:
            compile(src, "<cell %d>" % i, "exec")
        except SyntaxError as e:
            bad += 1
            print("SYNTAX ERROR in cell %d: %s" % (i, e))
    if bad:
        raise SystemExit("%d cell(s) failed to compile" % bad)
    print("syntax check: %d code cells compile"
          % sum(1 for c in cells if c["cell_type"] == "code"))


def run(cells, expect):
    """Execute every code cell in one namespace (pip lines skipped) and check
    the solver agrees with verify()."""
    import io, contextlib, logging
    logging.disable(logging.CRITICAL)
    sys.path.insert(0, os.path.join(ROOT, "src"))      # the agreement cell imports esm
    ns = {}
    disp = []
    explore = False
    for i, c in enumerate(cells):
        if c["cell_type"] == "markdown" and "## Explore" in "".join(c["source"]):
            explore = True
        if c["cell_type"] != "code":
            continue
        src = "\n".join(l for l in "".join(c["source"]).splitlines()
                        if not l.strip().startswith("!"))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exec(compile(src, "<cell %d>" % i, "exec"), ns)
        n = ns.get("n")
        if n is not None and "optimize(" in src and not explore:
            disp.append((i, (-n.links_t.p1).iloc[0].round(1).to_dict(),
                         float(n.buses_t.marginal_price["Houston"].iloc[0])))
    n = ns["n"]
    b_disp, b_price = disp[0][1], disp[0][2]
    assert b_disp == {"Houston CCGT": 600.0, "San Antonio coal": 250.0}, b_disp
    assert round(b_price, 2) == round(expect["coal_mc"], 2), b_price
    c0 = disp[1][1]
    assert c0 == {"Houston CCGT": 250.0, "San Antonio coal": 600.0}, c0
    gas_cap = disp[-1][1]["Houston CCGT"]
    assert abs(gas_cap - expect["g_min"]) < 0.5, gas_cap
    mu = abs(n.global_constraints.at["co2 cap", "mu"])
    assert abs(mu - expect["tau"]) < 0.01, mu
    assert ns["worst"] < 1e-9, ns["worst"]                     # the agreement cell ran
    print("run: Part B %s at $%.2f; Part C coal first at tau=0; cap -> %.1f MW gas, "
          "shadow price $%.2f/t" % (b_disp, b_price, gas_cap, mu))

    # explore: dispatch() at the values the questions name
    def said(**kw):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ns["dispatch"](**kw)
        return buf.getvalue()
    winter = (2 * (2.65 / 1.033 + 0.50) - 0.50) * 1.033          # "about $5.80"
    out = said()
    assert "gas   600" in out and "coal   250" in out and "$25.74" in out, out
    # Q1: the tie is at $3.32/Mcf (verify): just below gas still leads, just above coal does
    assert "gas   600" in said(gas_wellhead=3.30) and "coal   600" in said(gas_wellhead=3.35)
    # Q2: price steps - wind sets it below 150 MW... gas to 750, coal to 1350, then infeasible
    assert "$21.63" in said(load_mw=700) and "$25.74" in said(load_mw=1300)
    assert "no dispatch meets 1400 MW" in said(load_mw=1400)
    # Q3: the flip price does not depend on wind while both plants are on the margin
    import re
    def mw(text, plant):
        return float(re.search(plant + r"\s+(-?\d+) MW", text).group(1))
    for w in (0, 150, 600):
        lo = said(gas_wellhead=winter, co2_price=21.5, wind_mw=w, load_mw=1100)
        hi = said(gas_wellhead=winter, co2_price=21.8, wind_mw=w, load_mw=1100)
        assert mw(lo, "coal") > mw(lo, "gas") and mw(hi, "gas") > mw(hi, "coal"), (w, lo, hi)
    # Q4: cap shadow price is the $21.65 flip until the fleet cannot meet the cap
    e_gas, e_coal = 6.370 * 53.06 / 1000, 10.745 * 97.72 / 1000
    floor = 600 * e_gas + 250 * e_coal                             # all the gas it can, coal the rest
    c = said(gas_wellhead=winter, co2_cap=500)
    assert "$21.65/t" in c, c
    assert "no dispatch meets" in said(gas_wellhead=winter, co2_cap=floor - 5)
    assert "no dispatch" not in said(gas_wellhead=winter, co2_cap=floor + 5)
    # Q5: must-run coal at 700 MW pushes gas off
    assert "coal   600" in said(load_mw=700, coal_min=1.0)
    print("run: explore checked - tie, price steps, infeasible above 1,350 MW, flip "
          "independent of wind, cap floor %.0f t, must-run" % floor)


NOTEBOOK = {"cells": C,
            "metadata": {"kernelspec": {"display_name": "Python 3",
                                        "language": "python", "name": "python3"},
                         "language_info": {"name": "python"},
                         "colab": {"provenance": []}},
            "nbformat": 4, "nbformat_minor": 5}

if __name__ == "__main__":
    expect = verify()
    syntax_check(C)
    if "--run" in sys.argv:
        run(C, expect)
    words = sum(len("".join(c["source"]).split()) for c in C if c["cell_type"] == "markdown")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(NOTEBOOK, f, indent=1, ensure_ascii=False)
    print("wrote", os.path.relpath(OUT, ROOT))
    print("cells: %d (%d code, %d markdown), %d words of prose"
          % (len(C), sum(1 for c in C if c["cell_type"] == "code"),
             sum(1 for c in C if c["cell_type"] == "markdown"), words))
