# -*- coding: utf-8 -*-
"""Does .gitignore still block what must never be published, and still allow
what this repository needs?

WHY THIS EXISTS

This repository was created with fresh history precisely because its source --
a private course folder -- tracks live exam banks, a Canvas quiz backup holding
full question content, and an in-progress book manuscript. Git history is
permanent, so the .gitignore is not a tidiness rule here; it is the guard that
makes a mistaken `git add .` recoverable instead of a rotation-and-rewrite
event.

A guard nobody exercises is a guard that has already failed, so this file
exercises it. The standard's Part 2c says to verify with `git check-ignore -v`
rather than assume the pattern matched, and Part 6 says a requirement living in
prose has already failed. This is that verification, written down once and run
by pytest thereafter.

THE FAILURE THAT MOTIVATED THE SECOND HALF

The first draft of .gitignore contained `*exam*`. That matches "example", and
it silently ignored `build_sb1_example_notebook.py` -- a builder this
repository needs. Nothing would have reported it: the file simply would not
have been committed, and the notebook it generates would have had no generator.

That is why `must_not_be_ignored` exists and is the longer of the two lists. A
pattern that is too broad fails silently and in the direction nobody checks.
"""
import subprocess
import pytest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def is_ignored(relpath):
    """True if git would ignore `relpath`. Uses check-ignore, so it tests the
    real matcher rather than a reimplementation of glob semantics."""
    r = subprocess.run(
        ["git", "check-ignore", "-q", "--no-index", "--", relpath],
        cwd=REPO, capture_output=True,
    )
    if r.returncode not in (0, 1):
        raise RuntimeError(
            f"git check-ignore failed ({r.returncode}) on {relpath!r}: "
            f"{r.stderr.decode('utf-8', 'replace')}"
        )
    return r.returncode == 0


# Paths that must NEVER reach a commit. Each entry names a real class of file
# from the course folder this material came from.
MUST_BE_IGNORED = [
    # exams and question banks -- live for a course being taught now
    "Exams/mini-exam-1-undergrad.txt",
    "Exams/REE4301_exam_bank.qti.zip",
    "exam_bank.md",
    "Mini-Exam 2 Graduate.docx",
    "question_bank.txt",
    "to_text2qti.py",
    # rubrics and grading instruments
    "Tools/build_rubrics.py",
    "Tools/export_to_canvas_rubrics.py",
    "rubrics.json",
    "Canvas Rubric Import/criteria.csv",
    # quizzes, including the Canvas backup with full question content
    "quiz_backup.json",
    "Quizzes/q1.txt",
    # the book manuscript
    "CARES Book/Manuscript/ch01.md",
    "Tools/build_book_edits.py",
    # anything about a student -- education-record adjacent even unnamed
    "roster.csv",
    "gradebook.xlsx",
    "Student Work/paper.docx",
    # Canvas tooling and anything it caches
    "Tools/canvas_probe.py",
    "Tools/canvas_dryrun.py",
    # credentials
    ".env",
    ".env.local",
    "gurobi.lic",
    "wls_key.txt",
    "my_token.json",
    # binaries git stores badly and carries forever
    "UTA Slides/Module 0.pptx",
    "Resources/textbook.pdf",
    "Fall Course Schedule.xlsx",
    # noise
    "__pycache__/x.pyc",
    ".ipynb_checkpoints/a.ipynb",
]

# Paths this repository needs. A pattern that swallows one of these is the
# failure mode that does not announce itself.
MUST_NOT_BE_IGNORED = [
    # the builder whose name contains "example", which `*exam*` would eat
    "tools/builders/build_sb1_example_notebook.py",
    "tools/builders/build_1n_notebook.py",
    "tools/builders/build_boundary_notebook.py",
    "tools/builders/build_grad_m_notebook.py",
    "tools/builders/build_grad_n_notebook.py",
    "tools/builders/build_m5_notebook.py",
    "tools/builders/build_powerflow_notebook.py",
    "tools/builders/build_sb2_notebook.py",
    "tools/builders/build_sb3_notebook.py",
    "tools/builders/build_sb6_notebook.py",
    "tools/builders/build_supplychain_notebook.py",
    "tools/builders/build_transport_notebook.py",
    "tools/check_builders.py",
    # every notebook
    "notebooks/p1_foundations/01_model_boundary.ipynb",
    "notebooks/p1_foundations/02_one_house_balance.ipynb",
    "notebooks/p2_demand/05_representative_days.ipynb",
    "notebooks/p2_demand/06_end_use_disaggregation.ipynb",
    "notebooks/p3_generation/09_capital_and_lcoe.ipynb",
    "notebooks/p4_networks/17_pipeline_transport.ipynb",
    "notebooks/p4_networks/18_power_flow_and_lmp.ipynb",
    "notebooks/p4_networks/15_real_network_import.ipynb",
    "notebooks/p5_storage_supply/21_material_requirements.ipynb",
    "notebooks/capstone/AppA_texas_multi_city_buildout.ipynb",
    "notebooks/capstone/AppA_facility_decision.ipynb",
    "notebooks/graduate/model_diversity.ipynb",
    # what sessions 3 and 5 will add
    "src/esm/__init__.py",
    "src/esm/power_flow.py",
    "data/raw/bus_load.csv",
    "data/vendor/tx123bt_load.csv",
    "data/vendor/tx123bt_load.csv.md",
    "tests/test_power_flow.py",
    "tools/check_notebooks.py",
    "pyproject.toml",
    "requirements-lock.txt",
    # repository documents
    "README.md",
    "LICENSE",
    "LICENSE-DATA",
    "CITATION.cff",
    "CLAUDE.md",
    "ENERGY_SERIES_PLAN.md",
    "notebooks/p1_foundations/README.md",
]


@pytest.mark.parametrize("relpath", MUST_BE_IGNORED)
def test_must_be_ignored(relpath):
    assert is_ignored(relpath), (
        f"{relpath!r} is NOT ignored. This class of file must never reach a "
        f"commit -- see .gitignore and CLAUDE.md Part 11."
    )


@pytest.mark.parametrize("relpath", MUST_NOT_BE_IGNORED)
def test_must_not_be_ignored(relpath):
    assert not is_ignored(relpath), (
        f"{relpath!r} IS ignored, and this repository needs it. A .gitignore "
        f"pattern is too broad; run `git check-ignore -v {relpath}` to see "
        f"which line matched."
    )


def test_the_example_trap_specifically():
    """The regression this file was written for.

    `*exam*` matches "example". Any future edit that reaches for the short
    pattern breaks the builder for `02_one_house_balance.ipynb`, and breaks it
    silently.
    """
    assert not is_ignored("tools/builders/build_sb1_example_notebook.py")
    assert is_ignored("exam_bank.md")
