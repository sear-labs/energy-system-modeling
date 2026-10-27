# -*- coding: utf-8 -*-
"""build_sb3_notebook.py -> `notebooks/p3_generation/09_capital_and_lcoe.ipynb`.

DESIGN NOTE - why this is a chain of small questions rather than a lecture
An earlier version opened with the capital recovery factor and told the student
what each result meant ("this is the most common error in a first solar
business case"). Erick's note, 2 Sep: that is technically better and
pedagogically worse. It states the punchline, which spends the classroom
discussion before he gets to it, and it makes the assignment long enough to
crowd out the conversation it was supposed to start.

This version follows his original assignment's structure: a ladder of one-line
calculations, each with an obvious next question, where LCOE is ARRIVED AT
rather than introduced.

    how much electricity  ->  what is it worth at $10, at $50
    ->  how much fuel      ->  what does the fuel cost
    ->  compare            ->  where is break-even on fuel alone
    ->  now add capital    ->  what must you sell at

The numbers were chosen so the ladder lands somewhere: at $10/MWh the plant is
underwater on FUEL, before capital is mentioned. The student finds that, and it
is left for the room rather than announced here.

Prose rules this file follows, from that same note:
  * no "this is the graded part" - the rubric says what is graded
  * no stated punchlines; ask the question and stop
  * the facility thread is ONE soft prompt, not a bolded section

Run from Tools/:  python build_sb3_notebook.py
"""
import json
import sys
import os
import re

# tools/builders/<this file> -> tools/ -> the repository root.
# Three levels, not two: these builders used to live one level higher,
# in the course folder's Tools/.
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "notebooks", "p3_generation", "09_capital_and_lcoe.ipynb")

_N = [0]


def _id():
    _N[0] += 1
    return "cell-%02d" % _N[0]


def _escape_dollars(lines):
    # Colab and Jupyter read the text between two $ on a line as LaTeX, so
    # "$22 ... $90" rendered as garbled maths in class (Oct 2026).
    # Nothing in this notebook's markdown is meant as maths, so every $ is
    # escaped, except inside `code` and ``` fences, where a backslash would show.
    out, fence = [], False
    for l in lines:
        if l.lstrip().startswith("```"):
            fence = not fence
        elif not fence:
            l = "".join(p if p.startswith("`") else re.sub(r"(?<!\\)\$", r"\\$", p)
                        for p in re.split(r"(`[^`]*`)", l))
        out.append(l)
    return out


def md(*lines):
    return {"cell_type": "markdown", "id": _id(), "metadata": {},
            "source": _escape_dollars(lines)}


def code(*lines):
    return {"cell_type": "code", "id": _id(), "execution_count": None,
            "metadata": {}, "outputs": [], "source": list(lines)}


def L(s):
    return s + "\n"


C = []
A = C.append


def verify():
    mwh = 250 * 8760 * 30
    assert mwh == 65_700_000
    assert abs(mwh * 10 / 1e6 - 657) < 1
    assert abs(mwh * 50 / 1e6 - 3285) < 1
    # coal, mid heat rate, mid price
    mmbtu = mwh * 10000 / 1000.0
    tons = mmbtu / 13.0
    assert abs(tons / 1e6 - 50.5) < 0.1, tons / 1e6
    assert abs(tons * 20 / 1e6 - 1011) < 2
    assert abs(tons * 20 / mwh - 15.38) < 0.02
    # gas, mid
    mcf = (mwh * 7500 / 1000.0) / 1.036
    assert abs(mcf * 2.5 / mwh - 18.10) < 0.02
    print("arithmetic check: 65.7 TWh; $657M at $10/MWh, $3,285M at $50;")
    print("  coal mid burns 50.5 Mt costing $1,011M -> $15.38/MWh on fuel alone")
    print("  gas mid -> $18.10/MWh; so at $10/MWh the plant is under water")
    print("  on FUEL, before capital is mentioned.")


A(md(
L("# What does it cost to build a power plant?"),
L("## REE 4301 / IE 5300 - Energy Systems Modeling"),
L(""),
L("Work through this in order. Each step is one line of arithmetic, and each "
  "one sets up the next question."),
L(""),
L("Two plants, both **250 MW**, both assumed to last **30 years**: one coal, "
  "one gas."),
))

A(code(
L("import pandas as pd"),
))

A(md(
L("---"),
L("## 1. How much electricity?"),
L(""),
L("If the unit ran flat out for its whole life, how many MWh would it "
  "produce? Work it out before you run the cell."),
))

A(code(
L("mw, hours, years = 250, 8760, 30"),
L("lifetime_mwh = mw * hours * years"),
L(""),
L("print(f'{lifetime_mwh:,} MWh   =  {lifetime_mwh / 1e6:.1f} TWh')"),
))

A(md(
L("## 2. What is that worth?"),
L(""),
L("Suppose you sell every MWh at a flat price. Compute the lifetime revenue "
  "at **$10/MWh** and at **$50/MWh**."),
L(""),
L("Both are prices you can find in a real market, in different hours."),
))

A(code(
L("for price in (10, 50):"),
L("    print(f'at ${price:>2}/MWh   ${lifetime_mwh * price / 1e6:>9,.0f} M')"),
))

A(md(
L("---"),
L("## 3. How much fuel does that take?"),
L(""),
L("Heat rate is how much fuel energy you burn per unit of electricity out, in "
  "Btu/kWh. A **lower** number is a more efficient plant."),
L(""),
L("Pick three that bracket what real units achieve - a good one, a middling "
  "one, and a tired one. The ones below are reasonable; substitute your own "
  "and cite them."),
L(""),
L("Then convert fuel energy into the unit the fuel is actually sold in: "
  "**tons** for coal, **thousand cubic feet** for gas. That conversion is the "
  "heat content."),
))

A(code(
L("# MMBtu of fuel per MWh of electricity  =  heat rate / 1000"),
L("coal_heat_rates = [8_800, 10_000, 11_500]     # Btu/kWh"),
L("gas_heat_rates = [6_400, 7_500, 9_000]"),
L(""),
L("COAL_HEAT_CONTENT = 13.0      # MMBtu per ton, Texas lignite"),
L("GAS_HEAT_CONTENT = 1.036      # MMBtu per Mcf"),
L(""),
L("rows = []"),
L("for hr in coal_heat_rates:"),
L("    mmbtu = lifetime_mwh * hr / 1000"),
L("    rows.append({'fuel': 'coal', 'heat rate': hr,"),
L("                 'MMBtu': round(mmbtu / 1e6, 1),"),
L("                 'fuel units': f'{mmbtu / COAL_HEAT_CONTENT / 1e6:,.1f} Mt'})"),
L("for hr in gas_heat_rates:"),
L("    mmbtu = lifetime_mwh * hr / 1000"),
L("    rows.append({'fuel': 'gas', 'heat rate': hr,"),
L("                 'MMBtu': round(mmbtu / 1e6, 1),"),
L("                 'fuel units': f'{mmbtu / GAS_HEAT_CONTENT / 1e6:,.0f} Bcf'})"),
L(""),
L("print(pd.DataFrame(rows).to_string(index=False))"),
L("print('\\nMMBtu column is in millions.')"),
))

A(md(
L("> Look at the coal tonnage for a moment. How many rail cars is that, and "
  "how often would one have to arrive?"),
))

A(md(
L("---"),
L("## 4. What does the fuel cost?"),
L(""),
L("Three prices each, low to high. Fuel prices move a great deal, so a single "
  "number would be a guess dressed up as an answer."),
))

A(code(
L("coal_prices = [15, 20, 30]          # $/ton"),
L("gas_prices = [2.00, 2.50, 4.00]     # $/Mcf"),
L(""),
L("def fuel_bill(hr, heat_content, price):"),
L("    units = (lifetime_mwh * hr / 1000) / heat_content"),
L("    return units * price"),
L(""),
L("coal = pd.DataFrame("),
L("    [[fuel_bill(hr, COAL_HEAT_CONTENT, p) / 1e6 for p in coal_prices]"),
L("     for hr in coal_heat_rates],"),
L("    index=[f'{hr} Btu/kWh' for hr in coal_heat_rates],"),
L("    columns=[f'${p}/ton' for p in coal_prices]).round(0)"),
L(""),
L("gas = pd.DataFrame("),
L("    [[fuel_bill(hr, GAS_HEAT_CONTENT, p) / 1e6 for p in gas_prices]"),
L("     for hr in gas_heat_rates],"),
L("    index=[f'{hr} Btu/kWh' for hr in gas_heat_rates],"),
L("    columns=[f'${p:.2f}/Mcf' for p in gas_prices]).round(0)"),
L(""),
L("print('lifetime fuel bill, $ millions\\n')"),
L("print('COAL'); print(coal.to_string()); print()"),
L("print('GAS');  print(gas.to_string())"),
))

A(md(
L("## 5. Compare"),
L(""),
L("Put the two tables next to your revenue figures from step 2."),
L(""),
L("At **$50/MWh**, how many of those fuel bills can you cover?"),
L(""),
L("At **$10/MWh**, how many?"),
))

A(md(
L("---"),
L("## 6. Where do you break even on fuel alone?"),
L(""),
L("Divide the lifetime fuel bill by the lifetime MWh. That gives the price "
  "below which the plant would rather not run at all - roughly the number it "
  "would bid into an energy-only market."),
))

A(code(
L("rows = []"),
L("for hr, p in zip(coal_heat_rates, coal_prices):"),
L("    rows.append({'plant': f'coal {hr} Btu/kWh @ ${p}/ton',"),
L("                 '$/MWh': round(fuel_bill(hr, COAL_HEAT_CONTENT, p)"),
L("                                / lifetime_mwh, 2)})"),
L("for hr, p in zip(gas_heat_rates, gas_prices):"),
L("    rows.append({'plant': f'gas {hr} Btu/kWh @ ${p:.2f}/Mcf',"),
L("                 '$/MWh': round(fuel_bill(hr, GAS_HEAT_CONTENT, p)"),
L("                                / lifetime_mwh, 2)})"),
L(""),
L("print(pd.DataFrame(rows).to_string(index=False))"),
))

A(md(
L("> The spread between the cheapest and dearest row is roughly a factor of "
  "three, and you produced all of it by choosing assumptions. Which of the "
  "two - heat rate or fuel price - moved it more?"),
L(""),
L("> And you have not paid for the plant yet."),
))

A(md(
L("---"),
L("## 7. Now add the plant itself"),
L(""),
L("Look up overnight capital cost and fixed O&M for each technology in the "
  "**NREL Annual Technology Baseline**. Cite the year you used."),
L(""),
L("Spread the capital over the lifetime with a capital recovery factor - a "
  "mortgage payment on the plant:"),
L(""),
L("&nbsp;&nbsp;&nbsp;&nbsp;CRF = *r*(1+*r*)<sup>*n*</sup> / "
  "((1+*r*)<sup>*n*</sup> − 1)"),
L(""),
L("Then put the three pieces over the same denominator:"),
L(""),
L("&nbsp;&nbsp;&nbsp;&nbsp;(capital + fixed O&M + fuel) / total MWh&nbsp;&nbsp; "
  "= &nbsp;$/MWh"),
L(""),
L("**Tell me what number I have to sell electricity at to get my money back "
  "on each plant.**"),
))

A(code(
L("# Fill these in from the ATB you cite. The values below are placeholders"),
L("# so the cell runs - replace them and say which edition they came from."),
L("overnight = {'coal': 3_800_000.0, 'gas': 1_050_000.0}    # $/MW"),
L("fom = {'coal': 45_000.0, 'gas': 15_300.0}                # $/MW-yr"),
L("rate, life = 0.07, 30"),
L(""),
L("crf = rate * (1 + rate) ** life / ((1 + rate) ** life - 1)"),
L("print(f'CRF = {crf:.4f}\\n')"),
L(""),
L("chosen = {'coal': (10_000, COAL_HEAT_CONTENT, 20),"),
L("          'gas': (7_500, GAS_HEAT_CONTENT, 2.50)}"),
L(""),
L("rows = []"),
L("for tech, (hr, hc, price) in chosen.items():"),
L("    cap = overnight[tech] * crf * mw * years"),
L("    fixed = fom[tech] * mw * years"),
L("    fuel = fuel_bill(hr, hc, price)"),
L("    rows.append({'plant': tech,"),
L("                 'capital $M': round(cap / 1e6),"),
L("                 'FOM $M': round(fixed / 1e6),"),
L("                 'fuel $M': round(fuel / 1e6),"),
L("                 'break-even $/MWh':"),
L("                     round((cap + fixed + fuel) / lifetime_mwh, 2)})"),
L(""),
L("print(pd.DataFrame(rows).to_string(index=False))"),
))

A(md(
L("> Compare those two numbers against the fuel-only figures from step 6, and "
  "against the $10 and $50 prices you started with."),
L(""),
L("> One of these plants has most of its cost before it burns anything, and "
  "the other has most of its cost afterwards. Which is which, and what would "
  "that mean for how often each one wants to run?"),
))

A(md(
L("---"),
L("### Before class"),
L(""),
L("*You priced this as a plant that sells into a market. If the same 250 MW "
  "sat behind one customer's meter and never sold a thing, which number in "
  "your tables would change, and by how much?*"),
))

A(md(
L("---"),
L("### Does the package agree?"),
L(""),
L("`esm.lcoe` recomputes everything above from `data/raw/`. There is no "
  "solver here, so agreement cannot mean two searches found the same "
  "optimum - but there *is* a genuinely different second route, and it is "
  "the one worth your attention."),
L(""),
L("**What you did above** was annualise the capital with a CRF, add fuel and "
  "fixed costs, and divide the nominal total by the nominal lifetime energy. "
  "**The definition of LCOE** is not that. It is discounted cost over "
  "discounted energy:"),
L(""),
L("$$\text{LCOE} = \frac{\sum_t C_t/(1+r)^t}{\sum_t E_t/(1+r)^t}$$"),
L(""),
L("Those are different calculations. They agree here **only because the "
  "annual energy is constant over the life** - both sums pick up the same "
  "annuity factor and it cancels. That cancellation is the whole "
  "justification for the shortcut every screening study uses, and it is "
  "almost always assumed rather than shown."),
L(""),
L("> **Predict before you run it.** A solar array that loses half a percent "
  "of its output every year breaks that cancellation. Before you look: does "
  "the true LCOE come out above or below what the shortcut reports, and "
  "roughly by how much over thirty years?"),
))

A(code(
L("from esm.lcoe import (capital_recovery_factor, lcoe_by_crf, lcoe_by_dcf,"),
L("                     load_lcoe_instance, screening_table)"),
L("from esm.tolerance import AGREEMENT_RTOL, relative"),
L(""),
L("inst = load_lcoe_instance()"),
L("pkg_screen = screening_table(inst)"),
L(""),
L("checks = [('CRF', crf, capital_recovery_factor(rate, life))]"),
L("checks += [(f'{f} {hr} $/MWh',"),
L("            fuel_bill(hr, COAL_HEAT_CONTENT if f == 'coal'"),
L("                      else GAS_HEAT_CONTENT, p) / lifetime_mwh,"),
L("            pkg_screen[(f, hr)])"),
L("           for f, hr, p in"),
L("           [('coal', h, q) for h, q in zip(coal_heat_rates, coal_prices)]"),
L("           + [('gas', h, q) for h, q in zip(gas_heat_rates, gas_prices)]]"),
L("# the notebook's OWN computed values, not the 2-dp figures it printed:"),
L("# a displayed number is rounded, and AGREEMENT_RTOL is 1e-9."),
L("nb_breakeven = {t: ((overnight[t] * crf * mw * years"),
L("                    + fom[t] * mw * years"),
L("                    + fuel_bill(*chosen[t])) / lifetime_mwh)"),
L("                for t in chosen}"),
L("checks += [(f'{t} break-even', nb_breakeven[t],"),
L("            lcoe_by_crf(inst, inst.plants[(t, chosen[t][0])]))"),
L("           for t in chosen]"),
L(""),
L("print(f'{\"quantity\":24s} {\"notebook\":>12s} {\"package\":>12s} {\"rel diff\":>10s}')"),
L("for label, hand, pkg in checks:"),
L("    print(f'{label:24s} {hand:12.4f} {pkg:12.4f} {relative(hand, pkg):10.1e}')"),
L(""),
L("worst = max(relative(a, b) for _, a, b in checks)"),
L("assert worst < AGREEMENT_RTOL, ("),
L("    f'notebook and package disagree by {worst:.2e}, '"),
L("    f'which is worse than {AGREEMENT_RTOL:.0e}')"),
L("print()"),
L("print(f'notebook and package agree to {worst:.1e}')"),
))

A(md(
L("Now the part that is not a restatement."),
))

A(code(
L("gas = inst.plants[('gas', 7500)]"),
L(""),
L("shortcut = lcoe_by_crf(inst, gas)"),
L("definition = lcoe_by_dcf(inst, gas)"),
L("degrading = lcoe_by_dcf(inst, gas, degradation=0.005)"),
L(""),
L("print(f'CRF shortcut, flat output      ${shortcut:6.2f}/MWh')"),
L("print(f'DCF definition, flat output    ${definition:6.2f}/MWh')"),
L("print(f'DCF definition, 0.5%/yr loss   ${degrading:6.2f}/MWh')"),
L("print()"),
L("print(f'the two routes agree to {relative(shortcut, definition):.1e}'"),
L("      f' on flat output,')"),
L("print(f'and diverge by {degrading / definition - 1:.1%} once it degrades.')"),
L("print()"),
L("print('The shortcut cannot see the degradation: it divides a nominal')"),
L("print('total by a nominal total, and both fell by the same factor.')"),
L("print('That is the limit of the method you just used - and the reason')"),
L('print("a real study discounts the ENERGY as well as the money.")'),
))


A(md(
L("### Bonus"),
L(""),
L("Use what you just computed to parameterise the three-node PyPSA example: "
  "replace its gas figures with your real ones, and add a coal plant with "
  "yours. Then see whether the solver builds the thing you would have."),
L(""),
L("### Sources"),
L("- NREL Annual Technology Baseline - overnight cost, fixed O&M, lifetimes. "
  "Cite the edition."),
L("- EIA for fuel prices and heat contents; both vary by region and year."),
))


# ================================================================== explore
# Jones, 20 Oct 2026: walked in class and used for a reflection - sliders plus
# a cell where students add a plant themselves.  The slider reads step 7's
# numbers (overnight, fom, chosen - the ones the student cited), so the
# assignment's own cells are unchanged.  Step 7 assumes the plant runs every
# hour; capacity factor is the one new dimension, and it is the one that
# separates the two plants.
A(md(
L("---"),
L("## Explore - for your reflection"),
L(""),
L("Nothing above changes. The slider reads the numbers you cited in step 7. "
  "Step 7 assumed both plants run every hour for 30 years; the slider lets you "
  "drop that. Answer the numbered questions in your reflection."),
L(""),
L("### Now the streamlined version"),
L(""),
L("Step 7 is wrapped into a function here, because a slider recomputes it every time it moves - and you have built every term of it by hand above. At a capacity factor of 1 it gives back step 7's break-even prices."),
L(""),
L("### Slide it: when the plant does not run all the time"),
))
A(code(
L("from ipywidgets import interact, FloatSlider"),
L("import matplotlib.pyplot as plt"),
L(""),
L("def breakeven(capacity_factor=1.0, rate=0.07, coal_price=20.0, gas_price=2.50):"),
L("    crf_here = rate * (1 + rate) ** life / ((1 + rate) ** life - 1)"),
L("    mwh = lifetime_mwh * capacity_factor"),
L("    prices = {'coal': coal_price, 'gas': gas_price}"),
L("    parts = {}"),
L("    for tech, (hr, hc, _) in chosen.items():"),
L("        parts[tech] = {"),
L("            'capital': overnight[tech] * crf_here * mw * years / mwh,"),
L("            'fixed O&M': fom[tech] * mw * years / mwh,"),
L("            'fuel': fuel_bill(hr, hc, prices[tech]) * capacity_factor / mwh}"),
L("    table = pd.DataFrame(parts).T"),
L("    table['break-even $/MWh'] = table.sum(axis=1)     # sum first, then round"),
L("    table = table.round(2)"),
L("    print(table.to_string())"),
L("    ax = table.drop(columns='break-even $/MWh').plot.barh(stacked=True, figsize=(7, 2.2))"),
L("    for bars, hatch in zip(ax.containers, ('//', '..', '')):   # not colour alone"),
L("        for bar in bars:"),
L("            bar.set_hatch(hatch)"),
L("    plt.xlim(0, 300); plt.xlabel('$/MWh')"),
L("    ALT_TEXT = ('Stacked horizontal bars of break-even cost, one per plant, split '"),
L("                'into capital, fixed O&M and fuel: ' + '; '.join("),
L("                    f'{t} ${row[\"break-even $/MWh\"]:.2f}/MWh' for t, row in table.iterrows())"),
L("                + f', at a {capacity_factor:.0%} capacity factor.')"),
L("    plt.show()"),
L(""),
L("interact(breakeven,"),
L("    capacity_factor=FloatSlider(min=0.05, max=1.0, step=0.05, value=1.0, description='capacity f.'),"),
L("    rate=FloatSlider(min=0.02, max=0.15, step=0.005, value=0.07, description='rate'),"),
L("    coal_price=FloatSlider(min=10, max=60, step=1, value=20, description='coal $/ton'),"),
L("    gas_price=FloatSlider(min=1, max=10, step=0.1, value=2.5, description='gas $/Mcf'));"),
))
A(md(
L("> **1.** Lower the capacity factor to 50 percent, then 20 percent. Which plant's "
  "break-even rises faster? Does that change your answer to step 7's last "
  "question?"),
L(">"),
L("> **2.** Move the discount rate from 7 to 12 percent. Which plant cares more? Why "
  "might a regulated utility and a merchant developer put different numbers "
  "here?"),
L(">"),
L("> **3.** At a 60 percent capacity factor, find the gas price at which the two "
  "plants break even at the same $/MWh. Is that a price you have seen?"),
L(""),
L("### Edit and run: add a solar plant"),
L(""),
L("Fill in the blanks from the ATB (cite the edition), then run. Solar has no "
  "fuel bill, and it runs only when the sun does."),
))
A(code(
L("solar_overnight = None      # ___ $/MW"),
L("solar_fom = None            # ___ $/MW-yr"),
L("solar_cf = 0.25             # share of the year at full output; replace with your site's"),
L(""),
L("if solar_overnight is None or solar_fom is None:"),
L("    print('fill in solar_overnight and solar_fom first')"),
L("else:"),
L("    solar_breakeven = (solar_overnight * crf + solar_fom) / (8760 * solar_cf)"),
L("    print(f'solar break-even ${solar_breakeven:.2f}/MWh')"),
))
A(md(
L("> **4.** What does solar's break-even depend on that neither thermal plant's "
  "does? If its capacity factor fell from 0.25 to 0.20, by what fraction would "
  "the break-even rise - and could you have said so before running it?"),
))


def run(cells):
    """Execute every cell and check the slider against step 7."""
    import contextlib, io, re
    import matplotlib
    matplotlib.use("Agg")
    sys.path.insert(0, os.path.join(ROOT, "src"))      # the agreement cell imports esm
    ns = {}
    for i, c in enumerate(cells):
        if c["cell_type"] != "code":
            continue
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile("".join(c["source"]), "<cell %d>" % i, "exec"), ns)

    def said(**kw):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ns["breakeven"](**kw)
        return buf.getvalue()
    def be(text, tech):
        return float(re.search(r"^" + tech + r"\s.*\s([\d.]+)\s*$", text, re.M).group(1))
    full = said()
    for tech, (hr, hc, price) in ns["chosen"].items():
        cap = ns["overnight"][tech] * ns["crf"] * ns["mw"] * ns["years"]
        fixed = ns["fom"][tech] * ns["mw"] * ns["years"]
        step7 = (cap + fixed + ns["fuel_bill"](hr, hc, price)) / ns["lifetime_mwh"]
        # to the cent: the course copy summed parts AFTER rounding them, and
        # printed gas at $29.51 against step 7's $29.50
        assert abs(be(full, tech) - step7) < 0.005, (tech, be(full, tech), step7)
    # Q1: coal's break-even rises faster as the capacity factor falls
    half = said(capacity_factor=0.5)
    assert be(half, "coal") - be(full, "coal") > be(half, "gas") - be(full, "gas")
    # Q3: at 60% the two meet at a gas price inside the slider's range
    lo, hi = said(capacity_factor=0.6, gas_price=1.0), said(capacity_factor=0.6, gas_price=10.0)
    assert be(lo, "gas") < be(lo, "coal") and be(hi, "gas") > be(hi, "coal")
    print("run: slider at 100%% reproduces step 7 (coal $%.2f, gas $%.2f); Q1 and Q3 hold"
          % (be(full, "coal"), be(full, "gas")))


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


NOTEBOOK = {"cells": C,
            "metadata": {"kernelspec": {"display_name": "Python 3",
                                        "language": "python", "name": "python3"},
                         "language_info": {"name": "python"},
                         "colab": {"provenance": []}},
            "nbformat": 4, "nbformat_minor": 5}

if __name__ == "__main__":
    verify()
    syntax_check(C)
    if "--run" in sys.argv:
        run(C)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(NOTEBOOK, f, indent=1, ensure_ascii=False)
    print("wrote", os.path.relpath(OUT, ROOT))
    print("cells: %d (%d code, %d markdown)"
          % (len(C), sum(1 for c in C if c["cell_type"] == "code"),
             sum(1 for c in C if c["cell_type"] == "markdown")))
