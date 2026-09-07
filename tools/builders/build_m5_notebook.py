# -*- coding: utf-8 -*-
"""build_m5_notebook.py - write `2026 Fall/Notebooks/M5_Facility_Decision.ipynb`.

WHY MODULE 5 EXISTS
Module 0 is an intro with no outro. This is the outro. It bookends M0B: that
notebook asked "where do you draw the boundary?" and answered it with two
sizes of one site. This one spends a whole session INSIDE the lower boundary,
on one facility and one question - should this site build on-site generation? -
and answers it by walking back through all five modules' tools.

THE DESIGN CONSTRAINT: ZERO NEW MACHINERY
Every component, argument and formula here has already appeared:
    Module 0   Bus / Generator / Load / p_nom_extendable / capital_cost
               (deck slides 40-43), and the boundary itself (M0B)
    Module 1   representative days (slides 13-16), load duration and peak,
               4CP (slide 23), the peak-shaving arithmetic (slide 24)
    Module 2   CRF (slide 22), LCOE (slide 23), avoided retail vs received
               wholesale (the facility coda, slide 81)
    Module 3   the interconnection as the whole network (facility coda, s86)
    Module 4   state of charge (slide 22), the battery's two revenue streams
               (slide 23 and Module 1 slide 24), single-source risk (s54)
The ONE thing that looks new is `n.snapshot_weightings.objective`, and it is
just Module 1's representative days written in PyPSA. It is called out as such
in the markdown rather than slipped in.

THE ARC, AND WHY IT IS THE ARC
    baseline bill                    $23.485 M/yr, 26% of it demand charges
    solar on energy value alone      FAILS by $16.03/MWh - a first-year
                                     analyst stops here and says no
    add the demand charge            +$36.72/MWh - it CLEARS, by $437k/yr
    add the battery                  $691k/yr, and the peak becomes firm
    set the demand charge to zero    the model builds NOTHING
The last line is the finding. The project exists because of a tariff
structure, not because of an energy price - which is the boundary lesson
arriving from the opposite direction.

VERIFIED (prototype, HiGHS, re-checked after the notebook was executed)
    peak 50.00 MW  ·  285.9 GWh/yr  ·  load factor 0.653
    bill $17.28 M volumetric + $6.20 M demand = $23.48 M/yr, $82.15/MWh
    roof 12.0 MW-dc  ·  CF 0.201  ·  LCOE $62.75/MWh
    wholesale $16.72 vs retail avoided $46.72 per MWh - a factor of 2.79
    solar shaves 50.00 -> 43.75 MW, worth $0.775 M/yr = $36.72/MWh
    LP: do-nothing $23.485 M (= the hand-built bill, asserted), solar-only
        $23.048 M, solar+battery $22.794 M with a 10.56 MW battery
    boundary check at 500 MW: 19 of 24 hours move, own-bill error 84.2%,
        hour 21 goes $90 -> $600 - identical to M0B Part D
    fixed $45/MWh tariff: solar survives at 12 MW, the battery falls to 3.65 MW

THE DELIBERATE BLANK
The final cell requires the student to set RECOMMENDATION and raises an
explanatory NameError if they have not. That is on purpose (Teaching Code
Standard, "deliberate blanks that crash"), so the notebook as shipped runs
clean top to bottom through Part 8 and stops with a message, not a traceback,
in Part 9. Do not "fix" it.

Run from Tools/:  python build_m5_notebook.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "2026 Fall", "Notebooks", "M5_Facility_Decision.ipynb")

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

# ---------------------------------------------------------------- constants
# Re-derived here so the builder aborts if the notebook's arithmetic and this
# docstring ever drift apart.
PEAK_MW = 50.0
ROOF_MW = 12.0
ICA_MW = 600.0
TRANS_4CP = 70.0
DIST_DEMAND = 4.50


def verify():
    crf25 = 0.07 * 1.07 ** 25 / (1.07 ** 25 - 1)
    crf15 = 0.07 * 1.07 ** 15 / (1.07 ** 15 - 1)
    assert abs(crf25 - 0.0858) < 5e-5, crf25
    assert abs(crf15 - 0.1098) < 5e-5, crf15
    assert abs(300.0 * 1000 * 2 * crf15 - 65874) < 5, "battery $/MW-yr drifted"
    demand = (TRANS_4CP + DIST_DEMAND * 12) * 1000.0
    assert demand == 124000.0, demand
    assert ROOF_MW < PEAK_MW < ICA_MW, "the roof must bind before the agreement"
    print("design check: CRF(7%%,25)=%.4f  CRF(7%%,15)=%.4f  demand charge "
          "${:,.0f}/MW-yr".format(demand) % (crf25, crf15))
    print("              battery ${:,.0f}/MW-yr - Module 1 slide 24 quotes "
          "$65,877 for 1 MW / 2 MWh".format(300.0 * 1000 * 2 * crf15))


# ================================================================== title
A(md(
L("# Should this site build on-site generation?"),
L("## REE 4301 / IE 5300 - Energy Systems Modeling"),
L("### The outro. Do this last."),
L(""),
L("Module 0 was an introduction. This is the other end of it."),
L(""),
L("In **M0B** you learned that choosing a boundary is the first modelling "
  "decision, and you saw one site - the Metroplex Industrial Park - answered "
  "two different ways at two different sizes. Then Modules 1 to 4 each closed "
  "with a short *At the Facility Scale* segment showing what that module's "
  "tools look like once the boundary drops."),
L(""),
L("This notebook is all of it at once. **One facility. One question.**"),
L(""),
L("> **Should the Metroplex Industrial Park build on-site generation?**"),
L(""),
L("### The design constraint: nothing new"),
L(""),
L("There is no new machinery in this notebook. Not one component, argument or "
  "formula that has not already appeared on a slide or in an earlier notebook. "
  "If you find yourself thinking *I have not seen this before*, you have - "
  "and the markdown will tell you where."),
L(""),
L("That is deliberate. The point of a capstone is not to teach you a sixth "
  "thing. It is to show you that the five things you already have are enough "
  "to answer a real question end to end - which is exactly what you will be "
  "asked to do in your first job, and exactly what you should be able to "
  "describe in an interview. **Part 9 makes you write that description.**"),
))

# ================================================================== setup
A(code("!pip install -q pypsa highspy"))

A(md(
L("We need three libraries and nothing else. `warnings` is silenced because "
  "PyPSA is noisy about pandas dtypes on import; nothing here depends on the "
  "warnings."),
))

A(code(
L("import numpy as np"),
L("import pandas as pd"),
L("import pypsa"),
L("import warnings"),
L("warnings.filterwarnings('ignore')"),
L(""),
L("SOLVER = 'highs'      # open source, no licence, no size cap"),
L("pd.set_option('display.width', 160)"),
L(""),
L("print('pypsa', pypsa.__version__, '· solver', SOLVER)"),
))

# ================================================================== Part 0
A(md(
L("---"),
L("# Part 0 - The boundary, stated before anything else"),
L(""),
L("Every model in this course had a boundary. Most of them had one you did "
  "not choose. This one you choose, and you state it first, because every "
  "number after this inherits it."),
L(""),
L("**Inside the boundary:** the Metroplex Industrial Park. Roughly 50 MW of "
  "warehousing, light manufacturing and a cold-storage tenant, north of "
  "Dallas. Its roof, its yard, its meter, its equipment, its bill."),
L(""),
L("**Outside the boundary:** ERCOT. The generation fleet. West Texas wind. "
  "What gets built in 2035. None of it is modelled here."),
L(""),
L("**Crossing the boundary,** and this is the list from M0B Part F:"),
L(""),
L("| channel | how it reaches this site |"),
L("|---|---|"),
L("| a price signal | a downloaded hourly series, plus the tariff wrapped "
  "around it |"),
L("| coincident-peak exposure | ERCOT 4CP - four intervals a year set the "
  "transmission charge |"),
L("| interconnection capacity | a 600 MW agreement the site has never come "
  "close to using |"),
L("| marginal emissions | nobody has promised 24/7 carbon-free energy here, "
  "so this channel is dormant |"),
L(""),
L("This is the site **before** the investors show up. In M0B it becomes a "
  "500 MW data centre; Part 7 re-asks today's question at that size, and "
  "gets a different answer for a reason worth understanding."),
))

A(md(
L("### The site, as data"),
L(""),
L("Everything a facility analyst is handed on day one: a tariff sheet, a "
  "roof survey, an interconnection agreement, and a quote. No forecasts, no "
  "scenarios - four documents."),
))

A(code(
L("# --- the site"),
L("ROOF_SQFT = 1_200_000.0    # usable roof and canopy area, from the survey"),
L("W_PER_SQFT = 10.0          # modern modules with row spacing on a flat roof"),
L("ICA_MW = 600.0             # the interconnection agreement, from M0B"),
L(""),
L("# --- the tariff, from the utility's large commercial schedule"),
L("ENERGY_ADDER = 12.0        # $/MWh   retail margin, ancillaries, losses"),
L("DELIVERY_VOL = 18.0        # $/MWh   volumetric delivery"),
L("TRANS_4CP = 70.0           # $/kW-yr transmission, set by the 4CP average"),
L("DIST_DEMAND = 4.50         # $/kW-month distribution, on the peak"),
L(""),
L("# --- the quotes"),
L("SOLAR_CAPEX = 1_100_000.0  # $/MW-dc installed, commercial rooftop"),
L("SOLAR_FOM = 16_000.0       # $/MW-yr"),
L("BATT_CAPEX_KWH = 300.0     # $/kWh - the same figure as Module 4 slide 23"),
L("BATT_HOURS = 2.0"),
L("RTE = 0.86                 # round trip, Module 4 slide 23"),
L(""),
L("ROOF_MW = ROOF_SQFT * W_PER_SQFT / 1e6"),
L("DEMAND_PER_MW_YR = (TRANS_4CP + DIST_DEMAND * 12) * 1000.0"),
L(""),
L("print(f'usable roof          {ROOF_MW:8.1f} MW-dc')"),
L("print(f'interconnection      {ICA_MW:8.0f} MW')"),
L("print(f'volumetric adders    ${ENERGY_ADDER + DELIVERY_VOL:8.2f} /MWh on "
  "top of the wholesale price')"),
L("print(f'demand charges       ${DEMAND_PER_MW_YR:8,.0f} /MW-yr on the peak')"),
))

A(md(
L("> **Note what that last line is.** `TRANS_4CP + DIST_DEMAND * 12` is a "
  "charge on your **highest single interval of the year**, not on your "
  "energy. It will turn out to be the entire reason this project happens. "
  "Watch it."),
))

# ================================================================== Part 1
A(md(
L("---"),
L("# Part 1 - What does the site pay now?"),
L("### Module 1's tools, at the facility scale"),
L(""),
L("Module 1 forecast demand for populations and regions. This site does not "
  "forecast its demand - it **measures** it. What follows is the interval "
  "meter, reduced to two **representative days** exactly the way Module 1 "
  "slides 13 to 16 described: a summer weekday and a winter weekday, weighted "
  "to add up to a year."),
L(""),
L("Two days is a screening model, not a study. A real analysis uses all "
  "8,760 hours. **Name that as an assumption in anything you hand in.**"),
))

A(code(
L("hours = np.arange(24)"),
L(""),
L("# summer weekday: cold storage and HVAC ride the afternoon; a day shift"),
L("park_summer = (28.0"),
L("               + 22.0 * np.exp(-((hours - 16) ** 2) / 22.0)"),
L("               + 4.0 * np.exp(-((hours - 8) ** 2) / 6.0))"),
L(""),
L("# winter weekday: flatter, and the peak moves to the morning"),
L("park_winter = (25.0"),
L("               + 9.0 * np.exp(-((hours - 10) ** 2) / 26.0)"),
L("               + 5.0 * np.exp(-((hours - 18) ** 2) / 12.0))"),
L(""),
L("W_SUMMER, W_WINTER = 165, 200      # days per year each one stands for"),
L("assert W_SUMMER + W_WINTER == 365"),
L(""),
L("print(pd.DataFrame({'summer MW': park_summer.round(1),"),
L("                    'winter MW': park_winter.round(1)}).T.to_string())"),
))

A(md(
L("### The three numbers that describe any facility's load"),
L(""),
L("Peak, energy, and the ratio between them. Module 1 called the last one the "
  "**load factor**, and it is the single most useful number about a site: it "
  "tells you how much of your bill is energy and how much is capacity."),
))

A(code(
L("peak = max(park_summer.max(), park_winter.max())"),
L("energy_yr = park_summer.sum() * W_SUMMER + park_winter.sum() * W_WINTER"),
L("load_factor = energy_yr / (peak * 8760)"),
L(""),
L("print(f'peak demand        {peak:9.2f} MW   (summer hour "
  "{int(park_summer.argmax())})')"),
L("print(f'annual energy      {energy_yr / 1000:9.1f} GWh')"),
L("print(f'load factor        {load_factor:9.3f}')"),
))

A(md(
L("### The price, which is an input"),
L(""),
L("Here is the whole of the boundary in one cell. **You are not going to "
  "compute this price.** It is a downloaded series - the day-ahead LMP at the "
  "site's node, as published."),
L(""),
L("It came out of the macro model in **M0B Part B**: someone ran a system "
  "model once, and the answer became a column in a file. That is called "
  "**soft-linking**, and it is the normal way a facility study gets its "
  "prices. From this cell until Part 7 the system model does not appear "
  "again."),
))

A(code(
L("# day-ahead LMP, $/MWh, as downloaded. M0B Part B produced these."),
L("lmp_summer = np.array(["),
L("    52., 52., 44., 37., 31., 26., 26., 22., 22., 22.,  0.,  0.,"),
L("    22., 22., 26., 31., 37., 44., 52., 62., 90., 90., 90., 90.])"),
L(""),
L("lmp_winter = np.array(["),
L("    37., 31., 26., 26., 22., 22., 22.,  0.,  0.,  0.,  0.,  0.,"),
L("     0.,  0.,  0., 22., 22., 26., 31., 37., 44., 44., 44., 52.])"),
L(""),
L("print(f'summer  min ${lmp_summer.min():6.0f}   mean "
  "${lmp_summer.mean():7.2f}   max ${lmp_summer.max():6.0f}')"),
L("print(f'winter  min ${lmp_winter.min():6.0f}   mean "
  "${lmp_winter.mean():7.2f}   max ${lmp_winter.max():6.0f}')"),
))

A(md(
L("### The tariff wrapped around it"),
L(""),
L("A site does not pay the LMP. It pays the LMP plus everything the utility "
  "bundles on top. Module 2's facility coda called this out: **the number a "
  "behind-the-meter generator avoids is the retail rate, not the wholesale "
  "price.** This cell is where the two part company."),
))

A(code(
L("retail_summer = lmp_summer + ENERGY_ADDER + DELIVERY_VOL"),
L("retail_winter = lmp_winter + ENERGY_ADDER + DELIVERY_VOL"),
L(""),
L("print(pd.DataFrame({'LMP summer': lmp_summer,"),
L("                    'retail summer': retail_summer,"),
L("                    'LMP winter': lmp_winter,"),
L("                    'retail winter': retail_winter}).T.to_string())"),
))

A(md(
L("> **Predict before you run the next cell.** The site draws about 50 MW at "
  "peak and around 286 GWh a year. Write down two guesses: what the annual "
  "bill is, and what fraction of it you think comes from the demand charges "
  "rather than the energy."),
))

A(code(
L("bill_energy = ((park_summer * retail_summer).sum() * W_SUMMER"),
L("               + (park_winter * retail_winter).sum() * W_WINTER)"),
L("bill_demand = peak * DEMAND_PER_MW_YR"),
L("bill_total = bill_energy + bill_demand"),
L(""),
L("print(f'volumetric charges   ${bill_energy / 1e6:9.2f} M/yr')"),
L("print(f'demand charges       ${bill_demand / 1e6:9.2f} M/yr   "
  "({bill_demand / bill_total * 100:.0f}% of the bill)')"),
L("print(f'                     {\"-\" * 22}')"),
L("print(f'TOTAL                ${bill_total / 1e6:9.2f} M/yr')"),
L("print(f'blended rate         ${bill_total / energy_yr:9.2f} /MWh')"),
))

A(md(
L("**That total is the number every later part of this notebook is measured "
  "against.** A facility study has one job: move it."),
L(""),
L("And look at the split. Roughly a quarter of the bill is bought with a "
  "single interval of demand, not with energy. A model that only counts "
  "$/MWh cannot see a quarter of the problem - which is exactly the mistake "
  "Part 2 is about to make on purpose."),
))

# ================================================================== Part 2
A(md(
L("---"),
L("# Part 2 - What would solar cost, and what is it worth?"),
L("### Module 2's tools, at the facility scale"),
L(""),
L("Module 2 asked what capacity a *system* should build. The facility "
  "question is narrower: should **this site** put generation behind its own "
  "meter?"),
L(""),
L("Start with what the site is physically allowed to build. Not a resource "
  "potential and not a land constraint - **roof area**, which is the "
  "constraint a system model has never once seen."),
))

A(code(
L("solar_max_mw = ROOF_MW"),
L("print(f'{ROOF_SQFT:,.0f} sq ft x {W_PER_SQFT:.0f} W/sq ft = "
  "{solar_max_mw:.1f} MW-dc')"),
))

A(md(
L("### The output, and the derate that stops it being a brochure number"),
L(""),
L("A clear-sky profile is an idealisation. Clouds, soiling, inverter losses "
  "and wiring take a bite out of every one of these hours, so the whole "
  "profile carries a derate. **That single factor moves the capacity factor "
  "from a number you could not defend to one you could.**"),
))

A(code(
L("DERATE = 0.88     # clouds, soiling, inverter and wiring losses"),
L(""),
L("solar_summer = (np.clip(np.sin(np.pi * (hours - 6.0) / 14.0), 0, 1) ** 1.15"),
L("                * 0.86 * DERATE)"),
L("solar_winter = (np.clip(np.sin(np.pi * (hours - 7.5) / 10.5), 0, 1) ** 1.15"),
L("                * 0.62 * DERATE)"),
L(""),
L("solar_per_mw = (solar_summer.sum() * W_SUMMER"),
L("                + solar_winter.sum() * W_WINTER)"),
L("capacity_factor = solar_per_mw / 8760"),
L(""),
L("print(pd.DataFrame({'summer p.u.': solar_summer.round(3),"),
L("                    'winter p.u.': solar_winter.round(3)}).T.to_string())"),
L("print()"),
L("print(f'output per MW-dc   {solar_per_mw:9,.0f} MWh/yr')"),
L("print(f'capacity factor    {capacity_factor:9.3f}')"),
))

A(md(
L("### Annualise the capital, then divide - Module 2 slide 22 and 23"),
L(""),
L("Identical arithmetic to the Houston CCGT, with two inputs changed: a "
  "25-year life instead of 30, and no fuel term at all."),
))

A(code(
L("CRF_SOLAR = 0.07 * 1.07 ** 25 / (1.07 ** 25 - 1)"),
L("solar_annual = SOLAR_CAPEX * CRF_SOLAR + SOLAR_FOM"),
L("lcoe = solar_annual / solar_per_mw"),
L(""),
L("print(f'CRF(7%, 25 yr)      {CRF_SOLAR:9.4f}')"),
L("print(f'CapEx x CRF        ${SOLAR_CAPEX * CRF_SOLAR:11,.0f} /MW-yr')"),
L("print(f'+ fixed O&M        ${solar_annual:11,.0f} /MW-yr')"),
L("print(f'/ {solar_per_mw:,.0f} MWh   ->  LCOE  ${lcoe:.2f} /MWh')"),
))

A(md(
L("### Now the question this whole module exists for"),
L(""),
L("You have a cost per MWh. **What do you compare it against?**"),
L(""),
L("There are two candidates and they are not close:"),
L(""),
L("- the **wholesale price** a merchant plant would *receive* for selling "
  "this energy into the market, and"),
L("- the **retail rate** this site *avoids paying* by not buying the energy "
  "at all."),
L(""),
L("Both have to be weighted by when the solar actually produces - a plant "
  "that generates at noon does not capture the 7 p.m. price. That weighting "
  "is why the next cell is longer than a simple average."),
L(""),
L("> **Predict:** how far apart are the two numbers? Within 20%? A factor of "
  "two? More?"),
))

A(code(
L("wholesale_value = ((lmp_summer * solar_summer).sum() * W_SUMMER"),
L("                   + (lmp_winter * solar_winter).sum() * W_WINTER"),
L("                   ) / solar_per_mw"),
L("retail_value = ((retail_summer * solar_summer).sum() * W_SUMMER"),
L("                + (retail_winter * solar_winter).sum() * W_WINTER"),
L("                ) / solar_per_mw"),
L(""),
L("print(f'LCOE, what it costs             ${lcoe:8.2f} /MWh')"),
L("print(f'wholesale, what a merchant gets ${wholesale_value:8.2f} /MWh')"),
L("print(f'retail, what this site avoids   ${retail_value:8.2f} /MWh')"),
L("print(f'ratio                            {retail_value / wholesale_value:8.2f} x')"),
L("print()"),
L("print(f'against wholesale   {lcoe - wholesale_value:+8.2f} /MWh   "
  "{\"FAILS\" if lcoe > wholesale_value else \"CLEARS\"}')"),
L("print(f'against retail      {lcoe - retail_value:+8.2f} /MWh   "
  "{\"FAILS\" if lcoe > retail_value else \"CLEARS\"}')"),
))

A(md(
L("**Two things happened there, and only one of them is the one you were "
  "expecting.**"),
L(""),
L("First, the retail rate is nearly three times the wholesale price. That is "
  "the distinction Module 2's facility coda said sinks more first-year solar "
  "business cases than any modelling error, and here it is worth $30/MWh. "
  "Using the wrong one would not have made the answer slightly wrong; it "
  "would have made it wrong by more than the whole margin."),
L(""),
L("Second - and this is the uncomfortable part - **the project still fails.** "
  "Even against the right price, the solar costs more per MWh than it saves."),
L(""),
L("A first-year analyst writes *\"rooftop solar is uneconomic at this site\"* "
  "and closes the file. That answer is defensible, well-reasoned, and wrong, "
  "and Part 4 is where you find out why. But you cannot skip to Part 4 - you "
  "have to know what the energy-only answer is before you can say what the "
  "demand charge is worth **on top of it**."),
))

# ================================================================== Part 3
A(md(
L("---"),
L("# Part 3 - Which limit actually binds?"),
L("### Module 3's tools, at the facility scale"),
L(""),
L("Module 3 built DCOPF, susceptances, loop flow and congestion rent. A "
  "facility uses almost none of it. It models **one element** of a network: "
  "the connection between itself and the system."),
L(""),
L("There are three candidate limits on how much solar this site can have. "
  "Only one of them binds, and the useful skill is finding out which."),
))

A(code(
L("import_headroom = ICA_MW - peak"),
L(""),
L("# the site may not export - a load interconnection agreement is not a"),
L("# generation one. So output can never exceed load in any lit hour."),
L("lit = np.concatenate([solar_summer, solar_winter]) > 1e-6"),
L("load_all = np.concatenate([park_summer, park_winter])[lit]"),
L("pu_all = np.concatenate([solar_summer, solar_winter])[lit]"),
L("no_export_mw = (load_all / pu_all).min()"),
L(""),
L("print(f'1. interconnection    {ICA_MW:8.0f} MW  -> {import_headroom:.0f} MW "
  "of import headroom')"),
L("print(f'2. roof area          {ROOF_MW:8.1f} MW-dc')"),
L("print(f'3. no export allowed  {no_export_mw:8.1f} MW-dc before the first "
  "spilled hour')"),
L("print()"),
L("print(f'binding limit: the ROOF, at {min(ROOF_MW, no_export_mw):.1f} MW-dc')"),
))

A(md(
L("### What over-building would cost, if the roof were bigger"),
L(""),
L("Worth computing even though it does not bind here, because it is the "
  "shape of the answer at every site that *does* have land."),
))

A(code(
L("rows = []"),
L("for mw in [12, 30, 45, 60, 75, 90]:"),
L("    gen_s, gen_w = solar_summer * mw, solar_winter * mw"),
L("    spilled = (np.maximum(gen_s - park_summer, 0).sum() * W_SUMMER"),
L("               + np.maximum(gen_w - park_winter, 0).sum() * W_WINTER)"),
L("    total = gen_s.sum() * W_SUMMER + gen_w.sum() * W_WINTER"),
L("    rows.append({'MW-dc': mw, 'spilled %': round(spilled / total * 100, 1),"),
L("                 'usable MWh/yr': round(total - spilled)})"),
L(""),
L("print(pd.DataFrame(rows).set_index('MW-dc').to_string())"),
))

A(md(
L("**The interconnection does not bind, and finding that out is the "
  "result.**"),
L(""),
L("That is worth saying plainly because it is the opposite of what students "
  "expect from a module about networks. The site has 550 MW of unused import "
  "headroom - the agreement was written for heavy industry that never "
  "arrived. For *this* question, at *this* size, the network is not the "
  "constraint and does not need to be modelled."),
L(""),
L("Two things follow, and they are both worth more than the calculation:"),
L(""),
L("1. **Check which limit binds before you build the model, not after.** A "
  "week spent modelling the interconnection here would have produced a "
  "correct answer to a question nobody asked."),
L("2. **Unused headroom is an asset.** Module 3's facility coda made this "
  "point and Part 7 collects on it: the reason investors buy this site is "
  "the 550 MW nobody is using."),
))

# ================================================================== Part 4
A(md(
L("---"),
L("# Part 4 - The charge the $/MWh comparison could not see"),
L("### Module 4's tools, at the facility scale"),
L(""),
L("Part 2 valued a MWh of solar at the retail rate it avoids, and the project "
  "failed. But a solar array does not only avoid energy. If it happens to be "
  "producing during the interval that sets the demand charge, it also "
  "**reduces the peak** - and the peak is a quarter of this site's bill."),
L(""),
L("That value does not appear anywhere in a $/MWh comparison. It has to be "
  "computed separately and added."),
L(""),
L("> **Predict:** the site peaks at 4 p.m. in summer. Solar at 4 p.m. is past "
  "its best but nowhere near done. How many of the 50 MW do you think 12 MW "
  "of rooftop solar takes off the peak - and does the peak stay at 4 p.m.?"),
))

A(code(
L("net_summer = park_summer - solar_summer * ROOF_MW"),
L("net_winter = park_winter - solar_winter * ROOF_MW"),
L("new_peak = max(net_summer.max(), net_winter.max())"),
L("shaved = peak - new_peak"),
L(""),
L("print(pd.DataFrame({'load': park_summer.round(1),"),
L("                    'solar': (solar_summer * ROOF_MW).round(1),"),
L("                    'net': net_summer.round(1)}).T.to_string())"),
L("print()"),
L("print(f'peak before   {peak:8.2f} MW at hour {int(park_summer.argmax())}')"),
L("print(f'peak after    {new_peak:8.2f} MW at hour "
  "{int(net_summer.argmax())}')"),
L("print(f'shaved        {shaved:8.2f} MW')"),
))

A(md(
L("**The peak moved.** It was at hour 16 and it is now at hour 17, because "
  "solar falls off faster than the load does. That is not a curiosity - it is "
  "why you cannot estimate peak reduction as *\"solar output at the old "
  "peak\"*. The system re-peaks somewhere else, and the second peak is what "
  "you actually pay for."),
L(""),
L("Now put a price on it and stack the two streams. This is the same "
  "two-stream structure as Module 1 slide 24 and Module 4 slide 23 - the "
  "asset earns in more than one way and neither stream alone is the answer."),
))

A(code(
L("solar_energy = solar_per_mw * ROOF_MW"),
L("value_energy = solar_energy * retail_value"),
L("value_peak = shaved * DEMAND_PER_MW_YR"),
L("cost_solar = ROOF_MW * solar_annual"),
L(""),
L("print(f'energy avoided       ${value_energy / 1e6:8.3f} M/yr   "
  "(${retail_value:.2f}/MWh x {solar_energy:,.0f} MWh)')"),
L("print(f'demand charge avoided${value_peak / 1e6:8.3f} M/yr   "
  "({shaved:.2f} MW x ${DEMAND_PER_MW_YR:,.0f}/MW-yr)')"),
L("print(f'annual cost          ${cost_solar / 1e6:8.3f} M/yr')"),
L("print(f'{\"-\" * 46}')"),
L("print(f'NET on energy alone  ${(value_energy - cost_solar) / 1e6:8.3f} M/yr')"),
L("print(f'NET with both        "
  "${(value_energy + value_peak - cost_solar) / 1e6:8.3f} M/yr')"),
L("print()"),
L("print(f'the demand charge is worth "
  "${value_peak / solar_energy:.2f}/MWh of solar output,')"),
L("print(f'nearly as much again as the energy itself "
  "(${retail_value:.2f}) - and none of it')"),
L("print('appears anywhere in a levelised cost comparison.')"),
))

A(md(
L("**The sign flipped.** Same array, same cost, same weather. The project "
  "went from losing money to making it, and nothing changed except that the "
  "model started counting a charge that was always on the bill."),
L(""),
L("This is the whole argument for the facility boundary. At system scale "
  "there is no demand charge - it is a cost-allocation artefact, not a "
  "physical quantity, and a macro model does not have one. At facility scale "
  "it is a quarter of the bill and the entire economics of the project."),
))

A(md(
L("### And now the problem the battery exists to solve"),
L(""),
L("Everything above assumed the solar is producing during the interval that "
  "sets the peak. Look at what that assumption is actually worth."),
))

A(code(
L("print('solar output in the hours that could set the peak:')"),
L("for h in (15, 16, 17, 18):"),
L("    print(f'   hour {h}:  {solar_summer[h]:.3f} p.u.  ->  "
  "{solar_summer[h] * ROOF_MW:5.2f} MW on a clear day,  0.00 MW under cloud')"),
L("print()"),
L("print(f'one cloudy afternoon in the wrong hour and the whole '"),
L("      f'${value_peak / 1e6:.3f} M/yr is gone,')"),
L("print('because the demand charge is set by a single interval and billed '"),
L("      'for twelve months.')"),
))

A(md(
L("Module 1 slide 23 put it this way: *you cannot shave a peak you did not "
  "see coming.* A solar array cannot promise to be there in a particular "
  "fifteen-minute interval four months from now. A battery can."),
L(""),
L("Which is why the battery in this notebook is **not** an arbitrage "
  "battery. Module 4 slide 23's 100 MW unit lives on the price spread. This "
  "one is bought for **duration and availability in one interval** - a "
  "completely different machine sized by a completely different number, "
  "which is exactly what Module 4's facility coda said."),
))

# ================================================================== Part 5
A(md(
L("---"),
L("# Part 5 - What it takes to actually get the equipment"),
L("### Module 4's second half, at the facility scale"),
L(""),
L("Module 4 allocated material flows across a whole industry. This site sits "
  "at one node of that network and buys from it. The question is not where "
  "capacity should be built - it is what a delivered module costs at this "
  "dock, when it arrives, and what happens if the supplier fails."),
L(""),
L("Two quotes are on the desk. One is cheaper and comes from a single "
  "country; the other costs more and is diversified. The site's procurement "
  "policy caps any one supplier at 60% of a critical input - Chapter 22's "
  "single-source risk constraint, imposed by someone who has to keep a "
  "project on schedule rather than by a planner who likes diversity."),
))

A(code(
L("MODULE_W = 550.0           # watts per module"),
L("MODULE_SHARE = 0.30        # modules as a share of installed cost"),
L("A_PRICE, A_LEAD = 0.26, 20    # $/W ex-works, weeks, one country"),
L("B_PRICE, B_LEAD = 0.34, 8     # $/W ex-works, weeks, diversified"),
L("SINGLE_SOURCE_CAP = 0.60"),
L(""),
L("n_modules = ROOF_MW * 1e6 / MODULE_W"),
L("blended = SINGLE_SOURCE_CAP * A_PRICE + (1 - SINGLE_SOURCE_CAP) * B_PRICE"),
L("capex_uplift = (blended - A_PRICE) * 1e6      # $/MW"),
L(""),
L("print(f'modules needed        {n_modules:10,.0f} at {MODULE_W:.0f} W')"),
L("print(f'cheapest single source ${A_PRICE:9.3f} /W, {A_LEAD} weeks')"),
L("print(f'under the 60% cap      ${blended:9.3f} /W   "
  "(+${blended - A_PRICE:.3f}/W)')"),
))

A(md(
L("### Feed it back into the LCOE"),
L(""),
L("This is the step that gets skipped. A procurement constraint is not a "
  "footnote - it changes the capital cost, which changes the annualised cost, "
  "which changes the number the whole decision turned on in Part 2."),
))

A(code(
L("capex_with_cap = SOLAR_CAPEX + capex_uplift"),
L("annual_with_cap = capex_with_cap * CRF_SOLAR + SOLAR_FOM"),
L("lcoe_with_cap = annual_with_cap / solar_per_mw"),
L(""),
L("print(f'CapEx    ${SOLAR_CAPEX / 1e6:6.3f} -> ${capex_with_cap / 1e6:.3f} /W"
  "   ({capex_with_cap / SOLAR_CAPEX - 1:+.1%})')"),
L("print(f'LCOE     ${lcoe:6.2f} -> ${lcoe_with_cap:.2f} /MWh')"),
L("print(f'still below the retail value it avoids? "
  "{lcoe_with_cap < retail_value + value_peak / solar_energy}')"),
L("print()"),
L("print(f'and the schedule: {A_LEAD} weeks gates "
  "{SINGLE_SOURCE_CAP:.0%} of the modules,')"),
L("print(f'so the array energises in phases, not on one day.')"),
))

A(md(
L("A 2.9% capital uplift does not change this answer - the margin from Part 4 "
  "is far bigger than that. **Say so explicitly in a report.** \"We tested it "
  "and it does not bind\" is a finding; silence is an omission a reviewer will "
  "find."),
L(""),
L("The lead time is the part that actually costs something, and it does not "
  "appear in any of the arithmetic above. It decides whether the array is "
  "earning during next summer's 4CP intervals or the ones after. **A year of "
  "the benefit you just computed is riding on a procurement decision, not on "
  "a modelling one.** Most graduates of this course will make that decision "
  "long before they make a modelling one."),
))

# ================================================================== Part 6
A(md(
L("---"),
L("# Part 6 - Now the streamlined version"),
L(""),
L("Everything up to here was built one step at a time so you could see each "
  "decision. From this point the notebook wraps that construction in a "
  "function, and the rule about when you are allowed to do that applies: "
  "**you have already built every one of these components by hand, and we are "
  "about to run the same model four times** at different configurations. That "
  "is the reason, and it is the only acceptable one."),
L(""),
L("The model is Module 0's anatomy with nothing added:"),
L(""),
L("| component | what it is here |"),
L("|---|---|"),
L("| `Bus` | the site, behind the meter |"),
L("| `Load` | the metered profile from Part 1 |"),
L("| `Generator` \"grid\" | the utility supply, priced at the retail tariff |"),
L("| `Generator` \"solar\" | the rooftop array, capped at the roof |"),
L("| `StorageUnit` | the battery, `max_hours=2` |"),
L(""),
L("**Two arguments carry the whole model, and both are from Module 0 slides "
  "40 to 43:**"),
L(""),
L("- `p_nom_extendable=True` on solar and the battery turns this from a "
  "dispatch model into an investment model. That is Module 2's capacity "
  "expansion, applied to a roof."),
L("- `capital_cost` on the **grid** generator is the trick worth "
  "remembering. The demand charge is a cost on your *highest* import, and an "
  "extendable generator's `p_nom` is exactly that: the largest value it ever "
  "has to supply. Put the demand charge in `capital_cost` and the solver "
  "prices your peak for you. No new machinery - a component you have used a "
  "dozen times, pointed at a different quantity."),
L(""),
L("`snapshot_weightings.objective` is Part 1's representative days, written "
  "in PyPSA: it tells the solver each summer hour stands for 165 days and "
  "each winter hour for 200."),
))

A(code(
L("index = pd.Index([f'S{h:02d}' for h in hours] + [f'W{h:02d}' for h in hours])"),
L("load_series = np.concatenate([park_summer, park_winter])"),
L("solar_series = np.concatenate([solar_summer, solar_winter])"),
L("retail_series = np.concatenate([retail_summer, retail_winter])"),
L("weights = np.array([W_SUMMER] * 24 + [W_WINTER] * 24, dtype=float)"),
L(""),
L(""),
L("def site_model(solar_max, batt_max, demand_charge=None, retail=None,"),
L("               capex_solar=None, load=None, ica=None):"),
L("    \"\"\"The facility model. Every line appeared in Parts 0-5.\"\"\""),
L("    demand_charge = DEMAND_PER_MW_YR if demand_charge is None else demand_charge"),
L("    retail = retail_series if retail is None else retail"),
L("    capex_solar = solar_annual if capex_solar is None else capex_solar"),
L("    load = load_series if load is None else load"),
L("    ica = ICA_MW if ica is None else ica"),
L(""),
L("    n = pypsa.Network()"),
L("    n.set_snapshots(index)"),
L("    n.snapshot_weightings.objective = weights   # representative days"),
L(""),
L("    n.add('Bus', 'Site')"),
L("    n.add('Load', 'park', bus='Site', p_set=pd.Series(load, index=index))"),
L(""),
L("    # the utility supply. capital_cost here IS the demand charge."),
L("    n.add('Generator', 'grid', bus='Site', p_nom_extendable=True,"),
L("          p_nom_max=ica, capital_cost=demand_charge,"),
L("          marginal_cost=pd.Series(retail, index=index))"),
L(""),
L("    if solar_max > 0:"),
L("        n.add('Generator', 'solar', bus='Site', p_nom_extendable=True,"),
L("              p_nom_max=solar_max, capital_cost=capex_solar,"),
L("              marginal_cost=0.0,"),
L("              p_max_pu=pd.Series(solar_series, index=index))"),
L(""),
L("    if batt_max > 0:"),
L("        n.add('StorageUnit', 'battery', bus='Site', p_nom_extendable=True,"),
L("              p_nom_max=batt_max, capital_cost=BATT_ANNUAL,"),
L("              max_hours=BATT_HOURS,"),
L("              efficiency_store=RTE ** 0.5,"),
L("              efficiency_dispatch=RTE ** 0.5,"),
L("              cyclic_state_of_charge=True)"),
L(""),
L("    n.optimize(solver_name=SOLVER, log_to_console=False)"),
L("    return n"),
L(""),
L(""),
L("CRF_BATT = 0.07 * 1.07 ** 15 / (1.07 ** 15 - 1)"),
L("BATT_ANNUAL = BATT_CAPEX_KWH * 1000.0 * BATT_HOURS * CRF_BATT"),
L("print(f'CRF(7%, 15 yr) {CRF_BATT:.4f}   battery ${BATT_ANNUAL:,.0f} /MW-yr')"),
L("print('Module 1 slide 24 quotes $65,877/yr for 1 MW / 2 MWh. Same number.')"),
))

A(md(
L("### The check that earns the wrapper"),
L(""),
L("Before trusting the function with anything, make it reproduce a number you "
  "already computed by hand. Run it with no solar and no battery: it should "
  "return exactly the bill from Part 1."),
L(""),
L("This is not ceremony. It is how you find out that the convenient version "
  "and the version you understand have quietly diverged."),
))

A(code(
L("do_nothing = site_model(0, 0)"),
L(""),
L("print(f'solver objective   ${do_nothing.objective / 1e6:10.4f} M/yr')"),
L("print(f'hand-built bill    ${bill_total / 1e6:10.4f} M/yr')"),
L("print(f'peak it chose      {do_nothing.generators.p_nom_opt[\"grid\"]:10.2f} "
  "MW  (hand: {peak:.2f})')"),
L(""),
L("rel = abs(do_nothing.objective - bill_total) / bill_total"),
L("assert rel < 1e-6, f'the wrapper does not reproduce the hand-built bill "
  "({rel:.2e})'"),
L("print()"),
L("print('the wrapper reproduces the hand-built bill exactly.')"),
))

A(md(
L("> **Predict before the next cell.** You know from Part 4 that solar alone "
  "clears by about $0.44 M/yr once the demand charge is counted. How much "
  "battery do you think the solver buys, and does the total saving roughly "
  "double, or something less?"),
))

A(code(
L("solar_only = site_model(ROOF_MW, 0)"),
L("both = site_model(ROOF_MW, 20.0)"),
L(""),
L("out = []"),
L("for name, n in [('do nothing', do_nothing), ('solar only', solar_only),"),
L("                ('solar + battery', both)]:"),
L("    out.append({"),
L("        'case': name,"),
L("        'bill $M/yr': round(n.objective / 1e6, 3),"),
L("        'solar MW': round(n.generators.p_nom_opt.get('solar', 0.0), 2),"),
L("        'battery MW': round(n.storage_units.p_nom_opt.get('battery', 0.0)"),
L("                            if len(n.storage_units) else 0.0, 2),"),
L("        'peak MW': round(n.generators.p_nom_opt['grid'], 2),"),
L("        'saved $M/yr': round((do_nothing.objective - n.objective) / 1e6, 3)})"),
L(""),
L("print(pd.DataFrame(out).set_index('case').to_string())"),
))

A(md(
L("Compare the `solar only` saving against the $0.437 M/yr you stacked by "
  "hand in Part 4. They agree, which means the hand calculation and the LP "
  "are the same model - one of them is just easier to explain to a client."),
L(""),
L("The battery adds about $0.25 M/yr on top - less than the solar did, and "
  "for a different reason. The array is buying energy it no longer has to "
  "purchase. The battery is buying **certainty about one interval**, which is "
  "worth something precisely because the array cannot promise it. Neither "
  "asset would clear on the other's argument."),
))

A(md(
L("### The finding"),
L(""),
L("One more run, and it is the one to put on the last slide of a presentation. "
  "Set the demand charge to zero - keep everything else identical, including "
  "the energy prices - and ask the solver what it wants to build."),
L(""),
L("> **Predict.** Less solar, or none?"),
))

A(code(
L("no_demand_charge = site_model(ROOF_MW, 20.0, demand_charge=0.0)"),
L(""),
L("print(f'with the demand charge:  solar "
  "{both.generators.p_nom_opt[\"solar\"]:5.2f} MW,  battery "
  "{both.storage_units.p_nom_opt[\"battery\"]:5.2f} MW')"),
L("print(f'with NO demand charge:   solar "
  "{no_demand_charge.generators.p_nom_opt[\"solar\"]:5.2f} MW,  battery "
  "{no_demand_charge.storage_units.p_nom_opt[\"battery\"]:5.2f} MW')"),
))

A(md(
L("**Nothing. It builds nothing.**"),
L(""),
L("Every megawatt of this project exists because of a line on a tariff sheet "
  "- a cost-allocation mechanism that has no counterpart anywhere in a "
  "macro model. The energy price never justified it and still does not."),
L(""),
L("Sit with that for a moment, because it is the whole course arriving from "
  "the other direction. In Module 0 you learned that lowering the boundary "
  "turns price from an output into an input. What Part 6 shows is the "
  "stronger version: **lowering the boundary also changes which quantities "
  "exist at all.** A demand charge is not a small term a macro model leaves "
  "out for tractability. It is not in there, because at system scale there is "
  "nothing for it to be."),
))

# ================================================================== Part 7
A(md(
L("---"),
L("# Part 7 - The boundary check"),
L("### Every number above rests on one assumption. Test it."),
L(""),
L("This whole notebook treated the price as exogenous. That was a "
  "**modelling assumption with an error bar**, not a fact, and M0B told you "
  "how to test it: put your load into a system model once and see whether the "
  "price moves."),
L(""),
L("At 50 MW it barely does - M0B measured a 3.6% own-bill error, which is "
  "smaller than the argument you would have about the weather year. But the "
  "investors are about to turn this site into a 500 MW data centre on the "
  "same interconnection, so re-run the test at the size that matters."),
L(""),
L("This is the one place the system model comes back. It is M0B Part B's "
  "network, rebuilt here rather than imported, so you can see that nothing "
  "was hidden."),
))

A(code(
L("# ---- the macro model from M0B Part B. Dallas node, wind, a merit order."),
L("metro = (4000"),
L("         + 1000 * np.exp(-((hours - 19) ** 2) / 12.0)"),
L("         + 400 * np.exp(-((hours - 8) ** 2) / 6.0))"),
L("wind_pu = np.clip(0.30 + 0.55 * np.sin(np.pi * (hours - 2) / 16), 0, 1)"),
L(""),
L("STACK = [(f'gas{i + 1:02d}', 600, c) for i, c in"),
L("         enumerate([22., 26., 31., 37., 44., 52., 62., 90.])]"),
L("STACK += [('peaker1', 300, 175.), ('peaker2', 300, 600.),"),
L("          ('scarcity', 300, 2000.)]"),
L(""),
L("grid = pypsa.Network()"),
L("grid.set_snapshots(hours)"),
L("grid.add('Bus', 'Dallas')"),
L("grid.add('Bus', 'Site')"),
L("grid.add('Generator', 'wind', bus='Dallas', p_nom=5000, marginal_cost=0,"),
L("         p_max_pu=pd.Series(wind_pu, index=hours))"),
L("for nm, mw, c in STACK:"),
L("    grid.add('Generator', nm, bus='Dallas', p_nom=mw, marginal_cost=c)"),
L("grid.add('Load', 'metro', bus='Dallas', p_set=pd.Series(metro, index=hours))"),
L("grid.add('Link', 'interconnection', bus0='Dallas', bus1='Site',"),
L("         p_nom=ICA_MW, efficiency=1.0)"),
L("grid.add('Load', 'site', bus='Site', p_set=0.0)"),
L(""),
L("grid.optimize(solver_name=SOLVER, log_to_console=False)"),
L("# '+ 0.0' turns the solver's -0.0 into 0.0. You will meet negative zero"),
L("# in solver output for the rest of your career; it means zero."),
L("lmp_base = grid.buses_t.marginal_price['Dallas'].values + 0.0"),
L(""),
L("# the series you 'downloaded' in Part 1 is this model's output. Prove it."),
L("assert np.allclose(lmp_base, lmp_summer), 'the downloaded series has drifted'"),
L("print(f'price with no site   min ${lmp_base.min():6.0f}   max "
  "${lmp_base.max():6.0f}')"),
L("print('and it matches the series Part 1 treated as downloaded data.')"),
))

A(md(
L("Now change **one number** - the site load - and re-solve. Nothing else "
  "about the network moves."),
))

A(code(
L("for site_mw in (50.0, 500.0):"),
L("    grid.loads.loc['site', 'p_set'] = site_mw"),
L("    grid.optimize(solver_name=SOLVER, log_to_console=False)"),
L("    lmp_now = grid.buses_t.marginal_price['Dallas'].values"),
L("    predicted = (lmp_base * site_mw).sum()"),
L("    actual = (lmp_now * site_mw).sum()"),
L("    moved = int((~np.isclose(lmp_now, lmp_base)).sum())"),
L("    print(f'{site_mw:6.0f} MW   price moved in {moved:2d} of 24 h   "
  "own-bill error {actual / predicted - 1:+7.1%}')"),
))

A(md(
L("**3.6% and 84%.** The same two numbers M0B reported, because it is the "
  "same test on the same model."),
L(""),
L("So: everything in Parts 1 to 6 is sound for the 50 MW park. The "
  "price-taker assumption holds, the retail tariff built on that price is "
  "real, and the recommendation stands."),
L(""),
L("**And none of it transfers to the data centre.** Not because the physics "
  "changed - the roof is the same roof - but because at 500 MW the price on "
  "which the entire tariff was built is a price this site would move. Three "
  "things break at once:"),
L(""),
L("| | at 50 MW | at 500 MW |"),
L("|---|---|---|"),
L("| the price series | downloaded, and correct within 3.6% | wrong by 84%, "
  "because the load changes it |"),
L("| the roof | 12 MW against a 50 MW peak - material | 12 MW against a "
  "500 MW peak - a rounding error |"),
L("| the interconnection | 550 MW of headroom, never binds | 100 MW of "
  "headroom, and it is the whole project |"),
L(""),
L("The honest answer for the data centre is not a different number. It is "
  "**\"this model does not apply; go back to M0B and hard-link.\"** Knowing "
  "when to say that is the difference between a defensible answer and a "
  "confident wrong one, and it is worth more in an interview than any "
  "result in this notebook."),
))

# ================================================================== Part 8
A(md(
L("---"),
L("# Part 8 - One sensitivity, because one assumption deserves it"),
L(""),
L("This site is on an **indexed** tariff: its energy charge passes the "
  "wholesale price straight through, which is why the battery had a $600/MWh "
  "evening to arbitrage against. Plenty of sites are on a fixed rate "
  "instead."),
L(""),
L("That matters here because the summer series has real shape to work "
  "against: it bottoms out at $0/MWh in the middle of the day, when West "
  "Texas wind is covering the metro load, and reaches $90 in the evening. "
  "A flat rate deletes that spread entirely."),
L(""),
L("It is a contract term, not a physical fact, and it is exactly the kind of "
  "assumption a reviewer will ask about. So test it: hold everything else "
  "constant and flatten the energy charge."),
))

A(code(
L("FIXED_RATE = 45.0     # $/MWh flat energy charge, in place of the index"),
L("retail_fixed = np.full(48, FIXED_RATE + DELIVERY_VOL)"),
L(""),
L("flat = site_model(ROOF_MW, 20.0, retail=retail_fixed)"),
L(""),
L("print(f'indexed tariff   solar "
  "{both.generators.p_nom_opt[\"solar\"]:5.2f} MW   battery "
  "{both.storage_units.p_nom_opt[\"battery\"]:5.2f} MW')"),
L("print(f'fixed ${FIXED_RATE:.0f}/MWh    solar "
  "{flat.generators.p_nom_opt[\"solar\"]:5.2f} MW   battery "
  "{flat.storage_units.p_nom_opt[\"battery\"]:5.2f} MW')"),
))

A(md(
L("**The solar recommendation survives; the battery recommendation does "
  "not.** The array is bought with the demand charge, which the contract term "
  "did not touch. Most of the battery was bought with the evening price "
  "spread, which the contract term deleted."),
L(""),
L("Report it that way. *\"Build the array regardless; revisit the battery when "
  "the supply contract is signed\"* is a recommendation someone can act on. "
  "*\"Build 12 MW of solar and 10.6 MW of storage\"* is a number that will be "
  "wrong the moment procurement renegotiates."),
))

# ================================================================== Part 9
A(md(
L("---"),
L("# Part 9 - The answer, written down"),
L(""),
L("You now have everything. Assemble it."),
L(""),
L("### The recommendation"),
L(""),
L("**Yes - build the rooftop array. Treat the battery as a separate decision "
  "gated on the supply contract.** The array clears not on the energy it "
  "generates but on the demand charge it avoids, and it clears with enough "
  "margin to absorb a 60% single-source procurement cap."),
L(""),
L("### The five assumptions a reviewer will go after, and what you say"),
L(""),
L("1. **Two representative days, not 8,760 hours.** A screening result. The "
  "direction is robust; the magnitude is not. Say so before they ask."),
L("2. **The demand charge is modelled on the annual peak,** not month by "
  "month. This overstates the charge in both the baseline and the solar case, "
  "so the *saving* is close to right even though neither *bill* is."),
L("3. **The model has perfect foresight of the peak interval. You do not.** "
  "This is the single largest optimism in the whole notebook. It is also the "
  "argument for the battery, so it cuts both ways - and Module 1 slide 23 "
  "already told you the mitigation is to curtail on every day that might "
  "contain a 4CP interval."),
L("4. **Price is exogenous.** Tested in Part 7 and sound at 50 MW."),
L("5. **The tariff is indexed.** Tested in Part 8; the solar answer survives "
  "and the battery answer does not."),
L(""),
L("### The interview version"),
L(""),
L("This is the point of Module 5. Somebody asks what you can do. You have "
  "ninety seconds. Here is the shape:"),
L(""),
L("> *\"I sized on-site generation for a 50 MW industrial site. The thing "
  "that made it interesting is that the array failed on energy value - it "
  "cost about $63 a megawatt-hour and only avoided about $47 - so on a "
  "straight LCOE comparison you'd walk away. But a quarter of that site's "
  "bill was demand charges, and the array happened to be producing through "
  "the interval that set them. Counting that, it cleared by about $440,000 "
  "a year. I checked the procurement constraint didn't eat the margin, and I "
  "checked that the site was small enough for the published price to still "
  "be valid - at ten times the load it wouldn't have been, and I'd have had "
  "to model the market instead of downloading it.\"*"),
L(""),
L("Every clause in that paragraph is a module. Nobody has to know that."),
))

A(md(
L("### Your turn"),
L(""),
L("Write your own version and put it in `RECOMMENDATION` below. Not a "
  "summary of this notebook - **your** site, or this one with a number you "
  "disagree with and can defend."),
L(""),
L("Three sentences. What you would do, what it is worth, and the one "
  "assumption that would change your mind."),
))

A(code(
L("# RECOMMENDATION = \"\"\""),
L("# ...three sentences..."),
L("# \"\"\""),
L(""),
L("if 'RECOMMENDATION' not in globals():"),
L("    raise NameError("),
L("        'Write your recommendation in the cell above and uncomment it.\\n'"),
L("        'Three sentences: what you would do, what it is worth, and the one\\n'"),
L("        'assumption that would change your mind. This notebook will not\\n'"),
L("        'write it for you - that sentence is the deliverable, and it is\\n'"),
L("        'the part a hiring manager will actually read.')"),
L(""),
L("words = len(RECOMMENDATION.split())"),
L("print(f'{words} words.')"),
L("print('Long enough.' if 25 <= words <= 140 else"),
L("      'Too short to be a recommendation.' if words < 25 else"),
L("      'Too long. A recommendation that needs 140 words is not one yet.')"),
))

A(md(
L("---"),
L("## What Module 5 was for"),
L(""),
L("1. **One question, answered end to end.** Not five exercises - one "
  "decision, with every module contributing a piece and none of them "
  "sufficient alone."),
L("2. **The answer came from the tariff, not the technology.** Set the "
  "demand charge to zero and the model builds nothing. The most important "
  "input in the whole study was a line on a bill."),
L("3. **A model that says no is doing its job.** Part 2's failure was not a "
  "wrong answer to be fixed. It was the right answer to a narrower question, "
  "and knowing it was narrower is the skill."),
L("4. **The boundary was checked, not assumed.** Part 7 is the difference "
  "between a defensible number and a confident wrong one, and it takes one "
  "extra solve."),
L("5. **Nothing new was needed.** Every component came from Modules 0 to 4. "
  "If that feels anticlimactic, notice what it means: you already have "
  "enough to do professional work, and have had for some weeks."),
L(""),
L("### Where this goes"),
L(""),
L("This notebook is the scaffold for the capstone. The capstone changes the "
  "site and the question; the structure - state the boundary, get the "
  "baseline, cost the option, find the binding limit, count every revenue "
  "stream, price the supply chain, hand it to the solver, test the "
  "assumption, write the paragraph - does not."),
L(""),
L("### Sources and notes"),
L("- The Metroplex Industrial Park, its investors and its 600 MW agreement "
  "are invented. The pattern of buying industrial sites for their existing "
  "interconnection is not."),
L("- The price series is M0B Part B's output, which is a teaching stand-in "
  "for ERCOT. Its *shape* - a long cheap base and a thin, very expensive "
  "tail - is the realistic feature that matters."),
L("- The 4CP transmission charge and the $300/kWh battery are the same "
  "figures used on Module 1 slide 24 and Module 4 slide 23; the tariff's "
  "other components are representative of a large commercial ERCOT schedule "
  "and should be replaced with your own site's rate sheet."),
L("- Solar capacity factor here comes from a clear-sky profile with a single "
  "derate. A real study uses NSRDB or PVWatts for the site's own coordinates."),
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
            print(src[:600])
    if bad:
        raise SystemExit("%d cell(s) failed to compile" % bad)
    print("syntax check: %d code cells compile"
          % sum(1 for c in cells if c["cell_type"] == "code"))


NOTEBOOK = {
    "cells": C,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python",
                       "name": "python3"},
        "language_info": {"name": "python"},
        "colab": {"provenance": []},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

if __name__ == "__main__":
    verify()
    syntax_check(C)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(NOTEBOOK, f, indent=1, ensure_ascii=False)
    print("wrote", OUT)
    print("cells: %d (%d code, %d markdown)"
          % (len(C),
             sum(1 for c in C if c["cell_type"] == "code"),
             sum(1 for c in C if c["cell_type"] == "markdown")))
