# -*- coding: utf-8 -*-
"""build_m0_energy_arithmetic_notebook.py -> `notebooks/p1_foundations/02_energy_arithmetic.ipynb`.

WHERE THIS COPY CAME FROM, AND WHAT CHANGED ON THE WAY
Brought from the course folder's `Tools/` on 2026-10-22, as it stood after the
20 Oct Explore section.  The builder keeps the course's name so the two copies
can be compared; the notebook is named for its subject.  Changes here, each a
defect or a repository rule rather than a preference:
  * prose that pointed at course slides ("the Open Colab slide in Module 0",
    "Module 2") now points at the book's sections, which are what a reader of
    this repository has;
  * Part G's `levelized(cf, fixed=fixed, marginal=gas_mc)` captured its
    defaults when the cell ran - the standard's Part 6 "default-argument
    capture".  Edit `gas_fuel` in Part C, re-run Part G, and the curve did not
    move.  The arguments are now passed explicitly;
  * Part G carries the "Now the streamlined version" heading and its reason,
    because it is where the first function appears (Part 3);
  * every plotting cell carries ALT_TEXT describing what the figure shows;
  * an agreement cell against `esm.arithmetic` sits between Part F and Part G.
ANCHORED AT CHAPTER 2, though it serves sections 2.3, 9.1, 9.3, 9.4 and 12.4.
The placement rule anchors at the last chapter a notebook NEEDS; this one needs
none - it teaches the arithmetic those chapters assume - and it is run first,
before any model.  That is the plan's stated exception, the same one
`01_model_boundary` takes.

A CLASS WALKTHROUGH ("Class Walkthrough Plan.md").  Why it exists: an REE
student reported (Oct 2026) that REE 3302 names the same quantities 4301 uses
- kWh and kW, therms, heat rate, capacity factor - without the arithmetic 4301
assumes.  The REE 3302 review (18 Oct) agreed: 3302 defines them, 4301 computes
with them from Module 0 on.  This is the bridge: the arithmetic, once, at the
scale of one house and one plant, before Module 0's modeling slides need it.

SAME NUMBERS AS THE BOOK, so a student can read the section after class:
  A  energy vs power ............ Section 2.3  (dryer 2.6 kWh, meter 2.4 kW, 40 MW/160 MWh)
  B  one chain of conversions ... Section 2.3  (600 therms = ~17,600 kWh)
  C  heat rate, marginal cost ... Sections 9.3, Module 2 (gas $21.63, coal $25.74)
  D  emission rate, a CO2 price . Section 9.4  (0.338 and 1.050 t/MWh; $28.39, $46.74)
  E  capacity factor, sun, wind . Sections 9.1, 12.4  (306,600 MWh; 1,606 kWh/kW; 3.55 MW)
  F  capital: CRF and LCOE ...... Section 9.3, App B  ($108,500/MW-yr; $63 at 30%, $36 at 87%)
verify() asserts every one of those against the cell code itself, so a change
to a number here that drifts from the book fails the build.

DESIGN.  Jones's power-plant assignment is the model (CLAUDE.md section 1): a
ladder of one-rung arithmetic questions, placeholder values marked `# yours`
that the student replaces with a number they can cite.  Each part ends on a
question and stops.  Step-by-step at the top; the one function and the one
loop are in Part G at the bottom (Teaching Code Standard).  No data file, no
solver, nothing to install: it runs in Colab in seconds.

    python build_m0_energy_arithmetic_notebook.py          build (syntax check, verify)
    python build_m0_energy_arithmetic_notebook.py --run    also execute every cell
"""
import json
import math
import os
import sys

# tools/builders/<this file> -> tools/ -> the repository root.
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "notebooks", "p1_foundations", "02_energy_arithmetic.ipynb")

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


C = []
A = C.append

A(md(
L("# Energy arithmetic: the numbers a modeler computes with"),
L(""),
L("The arithmetic behind the book's section 2.3 and Chapter 9 - kW and kWh, "
  "heat rate, marginal cost, carbon per MWh, capacity factor, and the cost of "
  "building - once each, at the scale of one house and one plant. In Colab, "
  "*File › Save a copy in Drive* first so your edits are kept. There is no data "
  "file: every number is typed in, and the ones marked `# yours` are for you to "
  "replace with a number you can cite."),
L(""),
L("**Before you look:** a house's electricity bill says 1,000 kWh this month and "
  "its gas bill says 40 therms. Which is more energy?"),
))

A(md(
L("## Part A - Energy is an amount, power is a rate"),
L(""),
L("Power (kW, MW) is how fast. Energy (kWh, MWh) is how much: power × time."),
))
A(code(
L("dryer_kw = 3.5                  # the dryer's nameplate"),
L("dryer_hours = 45 / 60"),
L("dryer_kwh = dryer_kw * dryer_hours"),
L("print(f'one dryer load: {dryer_kwh:.2f} kWh')"),
L(""),
L("meter_kwh = 0.6                 # one 15-minute smart-meter reading"),
L("meter_kw = meter_kwh / 0.25     # energy / hours = average power"),
L("print(f'average draw over that quarter hour: {meter_kw:.1f} kW')"),
L(""),
L("battery_mw, battery_mwh = 40, 160"),
L("print(f'the battery runs {battery_mwh / battery_mw:.0f} hours at full power')"),
))
A(md(
L("> A phone charger draws about 5 W while it sits plugged in. Leave it there all "
  "year: how many kWh is that? How would you check your answer is not off by a "
  "factor of 1,000?"),
))

A(md(
L("## Part B - One chain of conversions"),
L(""),
L("Fuels are sold by heat (therms, gallons), electricity by the kWh. The bridge "
  "is **3,412 Btu per kWh**."),
))
A(code(
L("BTU_PER_KWH = 3412"),
L("BTU_PER_THERM = 100_000"),
L("BTU_PER_GALLON = 120_000        # gasoline, approximately (EIA)"),
L(""),
L("elec_kwh = 10_000               # yours: a year of electricity, from the bill"),
L("gas_therms = 600                # yours: a year of natural gas"),
L("gasoline_gal = 500              # yours: a year of gasoline"),
L(""),
L("gas_kwh = gas_therms * BTU_PER_THERM / BTU_PER_KWH"),
L("car_kwh = gasoline_gal * BTU_PER_GALLON / BTU_PER_KWH"),
L("print(f'electricity {elec_kwh:7,.0f} kWh')"),
L("print(f'gas         {gas_kwh:7,.0f} kWh')"),
L("print(f'gasoline    {car_kwh:7,.0f} kWh')"),
))
A(md(
L("> Put in your own household's numbers and say where each came from. Which of "
  "the three is largest? Then: the electricity line counts energy delivered to "
  "the house, the other two count heat in the fuel. Is it fair to add them?"),
))

A(md(
L("## Part C - Heat rate: what a MWh costs to make"),
L(""),
L("A plant's **heat rate** is the fuel heat it burns per MWh it sends out. A "
  "perfect plant would need 3.412 MMBtu per MWh."),
))
A(code(
L("gas_hr = 6.370                  # MMBtu/MWh: the Houston combined cycle, book 9.3-9.4"),
L("coal_hr = 10.745                # MMBtu/MWh: the coal plant beside it in book 9.4"),
L("print(f'gas plant efficiency  {3.412 / gas_hr:.1%}')"),
L("print(f'coal plant efficiency {3.412 / coal_hr:.1%}')"),
))
A(md(
L("**Marginal cost** is that heat rate times the fuel's price at the plant gate, plus variable O&M: what one more MWh costs to make."),
))
A(code(
L("gas_fuel = 2.65 / 1.033 + 0.50      # $/Mcf -> $/MMBtu, plus pipeline"),
L("coal_fuel = 18.76 / 15.97 + 0.75    # $/ton -> $/MMBtu, plus rail"),
L("gas_vom, coal_vom = 2.10, 5.06       # variable O&M, $/MWh"),
L("gas_mc = gas_hr * gas_fuel + gas_vom"),
L("coal_mc = coal_hr * coal_fuel + coal_vom"),
L("print(f'gas  ${gas_mc:.2f}/MWh')"),
L("print(f'coal ${coal_mc:.2f}/MWh')"),
))
A(md(
L("> Before you change anything: if the price of gas doubles, does the gas "
  "plant's marginal cost double? Predict, then edit `gas_fuel` and see."),
))

A(md(
L("## Part D - Carbon per MWh"),
L(""),
L("**Emission rate** = heat rate × the fuel's carbon content."),
))
A(code(
L("gas_kg, coal_kg = 53.06, 97.72      # kg CO2 per MMBtu of fuel (EPA)"),
L("gas_t = gas_hr * gas_kg / 1000      # tonnes CO2 per MWh"),
L("coal_t = coal_hr * coal_kg / 1000"),
L("print(f'gas {gas_t:.3f} t/MWh   coal {coal_t:.3f} t/MWh')"),
L(""),
L("co2_price = 20                      # $ per tonne"),
L("print(f'with ${co2_price}/t:  gas ${gas_mc + co2_price * gas_t:.2f}   '"),
L("      f'coal ${coal_mc + co2_price * coal_t:.2f}')"),
))
A(md(
L("> Coal emits about three times as much per MWh as gas, but its fuel carries "
  "less than twice the carbon per MMBtu. Where does the rest of the difference "
  "come from?"),
))

A(md(
L("## Part E - Capacity factor: from MW to MWh"),
L(""),
L("**Capacity factor** = what a plant produced ÷ what it would have produced at "
  "full output all year (8,760 hours)."),
))
A(code(
L("plant_mw, cf = 100, 0.35"),
L("print(f'{plant_mw * 8760 * cf:,.0f} MWh a year')"),
L(""),
L("ghi = 5.5                       # yours: kWh/m2/day of sun where you live (NREL)"),
L("performance = 0.80              # wiring, heat and inverter losses"),
L("solar_kwh_per_kw = ghi * performance * 365"),
L("print(f'solar: {solar_kwh_per_kw:,.0f} kWh per kW-year, '"),
L("      f'capacity factor {solar_kwh_per_kw / 8760:.1%}')"),
))
A(md(
L("Wind is different in kind: the power in it goes as the **cube** of its speed."),
))
A(code(
L("import math"),
L(""),
L("# power in the wind through a rotor: 1/2 x air density x swept area x speed cubed"),
L("rho = 1.225                     # kg/m3, air at sea level"),
L("rotor_m = 120                   # rotor diameter"),
L("area = math.pi * (rotor_m / 2) ** 2"),
L(""),
L("v = 8.0                         # m/s"),
L("wind_mw = 0.5 * rho * area * v ** 3 / 1e6"),
L("print(f'swept area {area:,.0f} m2;  power in the wind at {v} m/s: {wind_mw:.2f} MW')"),
L("print(f'the most any turbine can capture (Betz, 16/27): {wind_mw * 16 / 27:.2f} MW')"),
))
A(md(
L("> The wind at a site averages 8 m/s. Is the power in that wind the power at 8 "
  "m/s? Try a site that blows 4 m/s half the time and 12 m/s the other half, "
  "and compare."),
))

A(md(
L("## Part F - Building it: capital per MWh"),
L(""),
L("Capital is paid once; the **capital recovery factor** turns it into an equal "
  "yearly payment. Spread that over the year's MWh and add the marginal cost: "
  "the **levelized cost** (LCOE)."),
))
A(code(
L("rate, years = 0.07, 30"),
L("crf = rate * (1 + rate) ** years / ((1 + rate) ** years - 1)"),
L(""),
L("capex = 1_176_000               # $ per MW to build the Houston plant"),
L("fixed_om = 13_730               # $ per MW-year"),
L("fixed = capex * crf + fixed_om  # $ per MW-year"),
L(""),
L("cf_gas = 0.30"),
L("lcoe = fixed / (8760 * cf_gas) + gas_mc"),
L("print(f'CRF {crf:.4f}   fixed ${fixed:,.0f}/MW-yr   LCOE ${lcoe:.2f}/MWh')"),
))
A(md(
L("> Before you change `cf_gas` to 0.87: will the LCOE fall by more than half, "
  "or less? And which of the two numbers in this notebook - marginal cost or "
  "LCOE - would you use to decide which plant runs tonight?"),
))

A(md(
L("### Does the package agree?"),
L(""),
L("`esm.arithmetic` holds each formula above once, written from the formula "
  "rather than from these cells, and this cell hands it the same inputs. One "
  "comparison is more than a re-typing: the package computes the levelized "
  "cost from its **definition** - every year's cost and every year's energy, "
  "discounted, then divided - where Part F used the capital recovery factor. "
  "The two meet only because this plant makes the same MWh every year."),
))
A(code(
L("from esm import arithmetic as ea"),
L("from esm.lcoe import capital_recovery_factor"),
L("from esm.tolerance import AGREEMENT_RTOL, relative"),
L(""),
L("checks = ["),
L("    ('dryer kWh', dryer_kwh, ea.energy_kwh(dryer_kw, dryer_hours)),"),
L("    ('meter kW', meter_kw, ea.average_kw(meter_kwh, 0.25)),"),
L("    ('gas, kWh of heat', gas_kwh, ea.heat_to_kwh(gas_therms * BTU_PER_THERM)),"),
L("    ('gas $/MWh', gas_mc, ea.marginal_cost(gas_hr, gas_fuel, gas_vom)),"),
L("    ('coal $/MWh', coal_mc, ea.marginal_cost(coal_hr, coal_fuel, coal_vom)),"),
L("    ('gas t/MWh', gas_t, ea.emission_rate(gas_hr, gas_kg)),"),
L("    ('coal t/MWh', coal_t, ea.emission_rate(coal_hr, coal_kg)),"),
L("    ('MWh a year', plant_mw * 8760 * cf, ea.annual_mwh(plant_mw, cf)),"),
L("    ('solar kWh/kW', solar_kwh_per_kw, ea.solar_kwh_per_kw(ghi, performance)),"),
L("    ('wind MW', wind_mw, ea.wind_power_mw(rho, rotor_m, v)),"),
L("    ('CRF', crf, capital_recovery_factor(rate, years)),"),
L("    ('LCOE, CRF vs definition', lcoe,"),
L("     ea.levelized_cost_dcf(capex, fixed_om, gas_mc, rate, years, cf_gas)),"),
L("]"),
L("for label, hand, pkg in checks:"),
L("    print(f'{label:25s} {hand:14,.4f} {pkg:14,.4f}   {relative(hand, pkg):.1e}')"),
L(""),
L("worst = max(relative(a, b) for _, a, b in checks)"),
L("assert worst < AGREEMENT_RTOL, f'notebook and package disagree by {worst:.2e}'"),
L("print(f'\\nnotebook and package agree to {worst:.1e}')"),
))

A(md(
L("## Now the streamlined version: Part G, the same arithmetic as a function"),
L(""),
L("Every piece of Part F was built by hand above. It is wrapped now because the "
  "curve below needs the same line ninety-one times, once per capacity factor - "
  "and the first thing the cell does is check that the wrapper gives back Part "
  "F's number."),
))
A(code(
L("import matplotlib.pyplot as plt"),
L(""),
L("def levelized(cf, fixed, marginal):"),
L("    return fixed / (8760 * cf) + marginal"),
L(""),
L("assert relative(levelized(cf_gas, fixed, gas_mc), lcoe) < AGREEMENT_RTOL"),
L(""),
L("cfs = [c / 100 for c in range(5, 96)]"),
L("plt.figure(figsize=(7, 3.5))"),
L("plt.plot(cfs, [levelized(c, fixed, gas_mc) for c in cfs], label='LCOE')"),
L("plt.axhline(gas_mc, ls='--', color='grey', label='marginal cost')"),
L("plt.ylim(0, 200); plt.xlabel('capacity factor'); plt.ylabel('$/MWh')"),
L("plt.legend(); plt.title('One gas plant, two costs')"),
L("ALT_TEXT = (f'Line chart of levelized cost against capacity factor for the gas '"),
L("            f'plant. A solid curve falls steeply from about '"),
L("            f'${levelized(0.05, fixed, gas_mc):.0f}/MWh at a 5% capacity factor and '"),
L("            f'flattens towards ${levelized(0.95, fixed, gas_mc):.0f}/MWh at 95%; a '"),
L("            f'dashed horizontal line marks the ${gas_mc:.2f}/MWh marginal cost, which '"),
L("            f'the curve approaches but never reaches.')"),
L("plt.show()"),
L("print(ALT_TEXT)"),
))
A(md(
L("> A peaking plant runs a few hundred hours a year. Where on this curve does it "
  "sit, and why would anyone build one?"),
L(""),
L("*Before class: the industrial park of the book's section 1.4 draws 50 MW; the "
  "same site as a data center draws 500 MW, all year. How many of your Part B "
  "houses is each, in electricity alone - and is the plant in Part C the one "
  "that would serve it?*"),
L(""),
L("### Sources"),
L("- U.S. EIA, energy conversion factors (Btu per kWh, therm, gallon of gasoline; "
  "MMBtu per Mcf of natural gas)."),
L("- U.S. EPA, GHG emission factors hub (kg CO2 per MMBtu)."),
L("- NREL, National Solar Radiation Database (global horizontal irradiance)."),
L("- Plant data: the Houston combined cycle and the coal plant of the book's "
  "sections 9.3 and 9.4."),
))


# ================================================================== explore
# Jones, 20 Oct 2026: the class run became a reflection assignment, so students
# need "the ability to change numbers and explore some leading questions", with
# sliders AND cells where they edit a number or write a line themselves.  These
# cells only READ the numbers above (Parts C-F stay exactly as walked in class),
# and the functions live here at the bottom (Teaching Code Standard).
A(md(
L("---"),
L("## Explore - for your reflection"),
L(""),
L("Nothing above changes. These cells read its numbers. Two kinds: **sliders** "
  "(move one, watch what follows) and **edit-and-run** cells (change a number "
  "or write a line yourself). Answer the numbered questions in your reflection."),
L(""),
L("### Slide it: which plant runs first?"),
))
A(code(
L("from ipywidgets import interact, FloatSlider"),
L(""),
L("def merit(gas_price_mcf=2.65, coal_price_ton=18.76, co2_price=0.0):"),
L("    gas = gas_hr * (gas_price_mcf / 1.033 + 0.50) + 2.10 + co2_price * gas_t"),
L("    coal = coal_hr * (coal_price_ton / 15.97 + 0.75) + 5.06 + co2_price * coal_t"),
L("    print(f'gas ${gas:.2f}/MWh   coal ${coal:.2f}/MWh   ->  '"),
L("          f'{\"gas\" if gas < coal else \"coal\"} runs first')"),
L("    plt.figure(figsize=(6, 2))"),
L("    plt.barh(['coal', 'gas'], [coal, gas], color=['#6b4f3a', '#1f77b4'])"),
L("    plt.xlim(0, 120); plt.xlabel('$/MWh')"),
L("    ALT_TEXT = (f'Two horizontal bars, labelled coal and gas: coal ${coal:.2f}/MWh, '"),
L("                f'gas ${gas:.2f}/MWh. The shorter bar runs first.')"),
L("    plt.show()"),
L(""),
L("interact(merit,"),
L("         gas_price_mcf=FloatSlider(min=1, max=10, step=0.05, value=2.65, description='gas $/Mcf'),"),
L("         coal_price_ton=FloatSlider(min=5, max=60, step=0.5, value=18.76, description='coal $/ton'),"),
L("         co2_price=FloatSlider(min=0, max=100, step=0.5, value=0, description='CO2 $/t'));"),
))
A(md(
L("> **1.** At today's fuel prices, raise the CO2 price from zero. Does the order "
  "ever change? Now set gas to about **$5.80/Mcf** - the plant-gate price "
  "doubled - and find the CO2 price where the two plants swap."),
L(">"),
L("> **2.** At the swap, the two bars are the same length. Write the equation "
  "that says so and solve it for the CO2 price by hand. Does it match the slider?"),
L(""),
L("### Slide it: what makes up the levelized cost?"),
))
A(code(
L("def lcoe_parts(capex_per_mw=1_176_000, capacity_factor=0.30, rate=0.07, years=30):"),
L("    crf_here = rate * (1 + rate) ** years / ((1 + rate) ** years - 1)"),
L("    mwh = 8760 * capacity_factor                 # per MW per year"),
L("    parts = {'capital': capex_per_mw * crf_here / mwh,"),
L("             'fixed O&M': 13_730 / mwh,"),
L("             'fuel + VOM': gas_mc}"),
L("    total = sum(parts.values())"),
L("    print(f'LCOE ${total:.2f}/MWh = ' +"),
L("          ' + '.join(f'{k} ${v:.2f}' for k, v in parts.items()))"),
L("    plt.figure(figsize=(6, 1.8))"),
L("    left = 0"),
L("    for (name, v), hatch in zip(parts.items(), ('//', '..', '')):   # not colour alone"),
L("        plt.barh(['LCOE'], [v], left=left, label=name, hatch=hatch)"),
L("        left += v"),
L("    plt.xlim(0, 250); plt.xlabel('$/MWh'); plt.legend(fontsize=8)"),
L("    ALT_TEXT = ('One stacked horizontal bar of the levelized cost, left to right: '"),
L("                + ', '.join(f'{k} ${v:.2f}' for k, v in parts.items())"),
L("                + f', totalling ${total:.2f}/MWh.')"),
L("    plt.show()"),
L(""),
L("interact(lcoe_parts,"),
L("         capex_per_mw=FloatSlider(min=300_000, max=4_000_000, step=25_000, value=1_176_000, description='capex $/MW'),"),
L("         capacity_factor=FloatSlider(min=0.05, max=0.95, step=0.01, value=0.30, description='capacity f.'),"),
L("         rate=FloatSlider(min=0.02, max=0.15, step=0.005, value=0.07, description='rate'),"),
L("         years=FloatSlider(min=10, max=40, step=1, value=30, description='years'));"),
))
A(md(
L("> **3.** Which slider moves the LCOE most for a small nudge? Is it the same "
  "slider at a 10 percent capacity factor as at 90 percent?"),
L(">"),
L("> **4.** Find the capacity factor at which capital is half the LCOE. A wind "
  "farm has no fuel bar at all and runs at about 40 percent: what would its "
  "capital cost have to be for its LCOE to match this plant's at 87 percent?"),
L(""),
L("### Slide it: the average wind is not the average power"),
))
A(code(
L("def windy_site(mean_speed=8.0, spread=0.0):"),
L("    lo, hi = max(mean_speed - spread, 0), mean_speed + spread"),
L("    p_lo = 0.5 * rho * area * lo ** 3 / 1e6"),
L("    p_hi = 0.5 * rho * area * hi ** 3 / 1e6"),
L("    p_mean = 0.5 * rho * area * mean_speed ** 3 / 1e6"),
L("    print(f'half the time {lo:.1f} m/s, half the time {hi:.1f} m/s')"),
L("    print(f'power at the average speed  {p_mean:6.2f} MW')"),
L("    print(f'average of the power        {(p_lo + p_hi) / 2:6.2f} MW')"),
L(""),
L("interact(windy_site,"),
L("         mean_speed=FloatSlider(min=3, max=12, step=0.5, value=8, description='mean m/s'),"),
L("         spread=FloatSlider(min=0, max=6, step=0.5, value=0, description='± m/s'));"),
))
A(md(
L("> **5.** Hold the mean at 8 m/s and widen the spread. Which line moves? What "
  "would you want to know about a site besides its average wind speed?"),
L(">"),
L("> **6.** Above about 12 m/s a real turbine stops producing more. Which of the "
  "two lines does that limit change, and in which direction?"),
L(""),
L("### Edit and run: a third plant"),
L(""),
L("Write the three missing lines yourself, using Parts C, D and F as the pattern. "
  "The inputs are round illustrative numbers; replace them with ones you can "
  "cite (NREL ATB, EIA)."),
))
A(code(
L("# a nuclear plant"),
L("nuc_hr = 10.4               # MMBtu of heat per MWh - fission heat counts the same way"),
L("nuc_fuel = 0.70             # $/MMBtu, enriched and fabricated fuel"),
L("nuc_vom = 2.40              # $/MWh"),
L("nuc_capex = 7_000_000       # $/MW"),
L("nuc_fixed_om = 130_000      # $/MW-year"),
L("nuc_cf = 0.93"),
L(""),
L("nuc_mc = None               # ___ marginal cost, $/MWh   (Part C)"),
L("nuc_t = None                # ___ tonnes CO2 per MWh     (Part D) - and why?"),
L("nuc_lcoe = None             # ___ levelized cost, $/MWh  (Part F: use crf)"),
L(""),
L("print('nuclear: marginal cost', nuc_mc, ' CO2', nuc_t, ' LCOE', nuc_lcoe)"),
))
A(md(
L("> **7.** Rank the three plants by marginal cost, then by LCOE. Do the two "
  "rankings agree? Now put a $50 a tonne CO2 price on gas and coal (the first "
  "slider shows what it does to them): does nuclear's place in either ranking "
  "move?"),
))


def verify():
    """Every number the book prints for these examples, from the cells' own inputs."""
    def check(name, got, want, tol):
        assert abs(got - want) <= tol, "%s: %r, book says %r" % (name, got, want)
    check("A dryer kWh", 3.5 * 45 / 60, 2.6, 0.05)
    check("A meter kW", 0.6 / 0.25, 2.4, 1e-9)
    check("A battery hours", 160 / 40, 4, 1e-9)
    check("A charger kWh/yr", 5 * 8760 / 1000, 43.8, 1e-9)
    check("B gas kWh", 600 * 100_000 / 3412, 17_600, 50)
    check("B elec MMBtu", 10_000 * 3412 / 1e6, 34.1, 0.05)
    gas_mc = 6.370 * (2.65 / 1.033 + 0.50) + 2.10
    coal_mc = 10.745 * (18.76 / 15.97 + 0.75) + 5.06
    check("C gas MC", gas_mc, 21.63, 0.005)
    check("C coal MC", coal_mc, 25.74, 0.005)
    check("C doubled gas MC", 6.370 * 2 * (2.65 / 1.033 + 0.50) + 2.10, 41.15, 0.005)
    gt, ct = 6.370 * 53.06 / 1000, 10.745 * 97.72 / 1000
    check("D gas t/MWh", gt, 0.338, 0.0005)
    check("D coal t/MWh", ct, 1.050, 0.0005)
    check("D gas + $20", gas_mc + 20 * gt, 28.39, 0.005)
    check("D coal + $20", coal_mc + 20 * ct, 46.74, 0.005)
    assert ct / gt > 3 * 0.95 and 97.72 / 53.06 < 2       # the Part D question holds
    check("E MWh", 100 * 8760 * 0.35, 306_600, 1e-6)
    check("E solar kWh/kW", 5.5 * 0.8 * 365, 1606, 0.5)
    area = math.pi * 60 ** 2
    check("E area", area, 11_310, 1)
    check("E wind MW", 0.5 * 1.225 * area * 8 ** 3 / 1e6, 3.55, 0.005)
    check("E Betz MW", 0.5 * 1.225 * area * 8 ** 3 / 1e6 * 16 / 27, 2.10, 0.005)
    # the Part E question: mean of the cube exceeds the cube of the mean
    assert (4 ** 3 + 12 ** 3) / 2 > 8 ** 3
    crf = 0.07 * 1.07 ** 30 / (1.07 ** 30 - 1)
    fixed = 1_176_000 * crf + 13_730
    check("F fixed $/MW-yr", fixed, 108_500, 50)
    check("F LCOE at 30%", fixed / (8760 * 0.30) + gas_mc, 63, 0.5)
    check("F LCOE at 87%", fixed / (8760 * 0.87) + gas_mc, 36, 0.5)
    # the Part F question: from 30% to 87% the fixed share falls by more than half,
    # the LCOE (which carries the marginal cost) by less
    lo, hi = fixed / (8760 * 0.30) + gas_mc, fixed / (8760 * 0.87) + gas_mc
    assert hi > lo / 2
    # facility line: 50 MW and 500 MW sites in Part B houses
    check("park houses", 50 * 8760 * 1000 / 10_000, 43_800, 1e-6)
    print("verify: all book numbers match")


def syntax_check(cells):
    bad = 0
    for i, c in enumerate(cells):
        if c["cell_type"] != "code":
            continue
        try:
            compile("".join(c["source"]), "<cell %d>" % i, "exec")
        except SyntaxError as e:
            bad += 1
            print("SYNTAX ERROR in cell %d: %s" % (i, e))
    if bad:
        raise SystemExit("%d cell(s) failed to compile" % bad)
    print("syntax check: %d code cells compile"
          % sum(1 for c in cells if c["cell_type"] == "code"))


def run(cells):
    """Execute every cell in order and check the printed values are the book's."""
    import contextlib, io
    import matplotlib
    matplotlib.use("Agg")
    sys.path.insert(0, os.path.join(ROOT, "src"))      # the agreement cell imports esm
    ns, out = {}, io.StringIO()
    for i, c in enumerate(cells):
        if c["cell_type"] != "code":
            continue
        with contextlib.redirect_stdout(out):
            exec(compile("".join(c["source"]), "<cell %d>" % i, "exec"), ns)
    text = out.getvalue()
    for s in ("2.62 kWh", "2.4 kW", "4 hours", "17,585", "53.6%", "31.8%",
              "$21.63", "$25.74", "0.338", "1.050", "$28.39", "$46.74",
              "306,600 MWh", "1,606 kWh", "18.3%", "11,310 m2", "3.55 MW",
              "2.10 MW", "0.0806", "$108,500", "$62.9"):
        assert s in text, "run output lacks %r" % s
    assert abs(ns["levelized"](0.87, ns["fixed"], ns["gas_mc"]) - 35.87) < 0.01
    assert "notebook and package agree" in text
    # the default-argument capture, fixed: an edit to the marginal cost now
    # reaches the curve (it did not when `marginal=gas_mc` was a default)
    assert ns["levelized"](0.87, ns["fixed"], ns["gas_mc"] + 10) > 45
    # explore: the sliders' functions, at the values the questions name
    def said(fn, *a):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            fn(*a)
        return buf.getvalue()
    winter = (2 * (2.65 / 1.033 + 0.50) - 0.50) * 1.033       # wellhead, $/Mcf
    assert abs(winter - 5.80) < 0.02                            # "about $5.80"
    assert "coal runs first" in said(ns["merit"], winter, 18.76, 21.0)
    assert "gas runs first" in said(ns["merit"], winter, 18.76, 22.0)
    assert "gas runs first" in said(ns["merit"], 2.65, 18.76, 0.0)
    assert "LCOE $62.9" in said(ns["lcoe_parts"], 1_176_000, 0.30, 0.07, 30)
    w = said(ns["windy_site"], 8.0, 4.0)
    assert "3.55 MW" in w and "6.21 MW" in w, w
    assert ns["nuc_mc"] is None                                 # left for the student
    print("run: %d cells executed; printed values match the book; explore checked" %
          sum(1 for c in cells if c["cell_type"] == "code"))


NOTEBOOK = {"cells": C,
            "metadata": {"kernelspec": {"display_name": "Python 3",
                                        "language": "python", "name": "python3"},
                         "language_info": {"name": "python"},
                         "colab": {"provenance": []}},
            "nbformat": 4, "nbformat_minor": 5}

if __name__ == "__main__":
    syntax_check(C)
    verify()
    if "--run" in sys.argv:
        run(C)
    words = sum(len("".join(c["source"]).split()) for c in C if c["cell_type"] == "markdown")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(NOTEBOOK, f, indent=1, ensure_ascii=False)
    print("wrote", os.path.relpath(OUT, ROOT))
    print("cells: %d (%d code, %d markdown), %d words of prose"
          % (len(C), sum(1 for c in C if c["cell_type"] == "code"),
             sum(1 for c in C if c["cell_type"] == "markdown"), words))
