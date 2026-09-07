# -*- coding: utf-8 -*-
"""Does `esm.data` resolve a table from the right place, in the right order?

WHY THIS MATTERS MORE THAN IT LOOKS

The resolution order is not a convenience: Part 4 hangs on it. A reader is told
to edit a value in `data/raw/` and re-run, and the agreement assertion is
supposed to stay green because both the notebook and the package picked up the
edit. If the published URL ever won over a local copy, editing the file would do
nothing at all -- silently -- and the notebook would keep reporting the numbers
on the published branch. Nothing would fail; the reader would simply be lied to.

So the test that matters here is `test_local_beats_the_url`.

The network is never touched. Every case below either finds a local file or
checks which path *would* be chosen, via `resolve()`.
"""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from esm import data as D  # noqa: E402


@pytest.fixture
def tables(tmp_path):
    """Two directories each holding a same-named table with different contents."""
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    (a / "t.csv").write_text("x\n1\n", encoding="utf-8")
    (b / "t.csv").write_text("x\n2\n", encoding="utf-8")
    return a, b


def test_explicit_source_wins(tables):
    a, b = tables
    assert D.resolve("t.csv", source=a) == a / "t.csv"
    assert D.table("t.csv", source=a)["x"].tolist() == [1]
    assert D.table("t.csv", source=b)["x"].tolist() == [2]


def test_env_var_is_used_when_no_source_given(tables, monkeypatch):
    a, _ = tables
    monkeypatch.setenv("ESM_DATA", str(a))
    assert D.resolve("t.csv") == a / "t.csv"


def test_explicit_source_beats_the_env_var(tables, monkeypatch):
    a, b = tables
    monkeypatch.setenv("ESM_DATA", str(a))
    assert D.resolve("t.csv", source=b) == b / "t.csv"


def test_local_beats_the_url(tables):
    """The one the agreement assertion depends on.

    A reader edits data/raw/ and re-runs; the package must see the edit.
    """
    a, _ = tables
    where = D.resolve("t.csv", source=a)
    assert isinstance(where, Path), (
        "a local copy exists but resolve() chose the published URL -- a reader "
        "editing data/raw/ would see no effect, and the agreement assertion "
        "would compare against the published branch instead of their edit"
    )


def test_url_is_the_fallback_when_nothing_local(monkeypatch, tmp_path):
    monkeypatch.delenv("ESM_DATA", raising=False)
    monkeypatch.chdir(tmp_path)
    where = D.resolve("definitely-not-a-real-table-xyz.csv")
    assert isinstance(where, str)
    assert where.startswith("https://raw.githubusercontent.com/")
    assert where.endswith("/data/raw/definitely-not-a-real-table-xyz.csv")


def test_the_url_names_a_ref_rather_than_floating(monkeypatch, tmp_path):
    """`main` moves. A published notebook must be able to pin a tag.

    This does not require DATA_REF to be a tag today -- it requires the ref to
    appear in the URL at all, so that pinning is a one-line change rather than a
    redesign.
    """
    assert D.DATA_REF, "DATA_REF is empty; the URL would be malformed"
    assert f"/{D.DATA_REF}/" in D.RAW_BASE


def test_failure_explains_itself(monkeypatch, tmp_path):
    """Part 5: a cell that cannot get its data fails with an explanation.

    Forces the URL branch and makes the fetch fail, then checks the message
    names the two things a reader would actually need to know.
    """
    monkeypatch.delenv("ESM_DATA", raising=False)
    monkeypatch.chdir(tmp_path)

    import requests

    def boom(*a, **k):
        raise requests.exceptions.ConnectionError("no network")

    monkeypatch.setattr(requests, "get", boom)

    with pytest.raises(RuntimeError) as exc:
        D.table("nope.csv")
    msg = str(exc.value)
    assert "nope.csv" in msg
    assert "private" in msg, "the message should name the 404-on-private case"
    assert "ESM_DATA" in msg, "the message should name the override that fixes it"


def test_last_source_is_recorded(tables):
    a, _ = tables
    D.table("t.csv", source=a)
    assert D.LAST_SOURCE == str(a / "t.csv"), (
        "a notebook should be able to print which copy its numbers came from"
    )
