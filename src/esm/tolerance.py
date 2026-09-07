# -*- coding: utf-8 -*-
"""Every tolerance in this repository, named once.

WHY THEY LIVE HERE AND NOWHERE ELSE

Part 4: "a threshold, tolerance or invariant is a value with copies, and the
duplicate is where the fix does not reach." A tolerance written into a notebook
and again into a test is two numbers nothing compares; correct one and the other
goes on being wrong with everything green.

So notebooks import these rather than typing a literal, and
`tools/check_notebooks.py` fails a notebook that writes `1e-9` inside an assert.

WHAT A TOLERANCE IS ACTUALLY CLAIMING

Two things at once, and only one of them is usually noticed:

    about the implementations   that they compute the same model
    about the computation       that it is precise enough for the first claim
                                to be testable at all

Get the second wrong and the check passes by coincidence. The standard records
the case: two notebooks solved a MILP at a 1e-3 and 1e-6 gap and then asserted
agreement to 1e-9 -- demanding agreement a thousand times finer than the solve
had been asked to deliver. It held for months on one machine because both sides
took the same path to the same vertex, and failed the first time it ran on Linux.

**Solve at least as tightly as you assert**, or the check is testing determinism
rather than equivalence.
"""

#: Relative tolerance for "the notebook and the package computed the same thing".
#:
#: 1e-9 is defensible for a linear program solved to optimality: the simplex
#: method terminates at a vertex, and both sides solve the same LP with the same
#: solver, so the objective agrees to solver precision rather than to the gap of
#: a branch-and-bound search.
#:
#: It would NOT be defensible for a MILP. Anything solved to a MIP gap must
#: assert no tighter than that gap -- see the module docstring.
AGREEMENT_RTOL = 1e-9

#: For a quantity that ought to be exactly conserved -- an energy balance, a
#: mass balance, flows summing to zero at a node. Floating point noise only.
CONSERVATION_ATOL = 1e-9

#: For a MILP compared against another MILP. Deliberately looser than
#: AGREEMENT_RTOL, and deliberately not used unless a solve actually involved
#: integers: two integer solutions can sit closer together than this, in which
#: case the answer is not unique and the assertion belongs on the invariant
#: rather than on the objective.
MILP_AGREEMENT_RTOL = 1e-6


def relative(a, b):
    """|a - b| / max(|a|, |b|, 1). The trailing 1 keeps it finite near zero."""
    return abs(a - b) / max(abs(a), abs(b), 1.0)


def agree(a, b, rtol=AGREEMENT_RTOL):
    """True if two scalars agree to `rtol`, relatively."""
    return relative(a, b) < rtol
