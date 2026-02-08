"""Tests for scenario_outline() table-driven scenarios."""

import pytest

from bdd_pytest import expect, scenario_outline, unit


@unit
def test_basic_outline():
    scenario_outline(
        "computes area",
        [
            {"name": "unit square", "w": 1, "h": 1, "expected": 1},
            {"name": "rectangle", "w": 3, "h": 4, "expected": 12},
            {"name": "wide", "w": 10, "h": 2, "expected": 20},
        ],
        given=lambda row: (row["w"], row["h"]),
        when=lambda ctx, row: ctx[0] * ctx[1],
        then=lambda result, ctx, row: expect(result).to_be(row["expected"]),
    )


@unit
def test_outline_without_given():
    scenario_outline(
        "doubles a number",
        [
            {"name": "zero", "n": 0, "expected": 0},
            {"name": "positive", "n": 5, "expected": 10},
        ],
        when=lambda ctx, row: row["n"] * 2,
        then=lambda result, ctx, row: expect(result).to_be(row["expected"]),
    )


@unit
def test_outline_without_when():
    scenario_outline(
        "checks values",
        [
            {"name": "truthy", "val": 1},
            {"name": "also truthy", "val": "x"},
        ],
        given=lambda row: row["val"],
        then=lambda result, ctx, row: expect(ctx).to_be_truthy(),
    )


@unit
def test_outline_error_includes_row_name_and_phase():
    """Per-phase error tagging: [unit/then] prefix in outline errors."""
    with pytest.raises(AssertionError, match=r"\[unit/then\].*\[bad row\]"):
        scenario_outline(
            "fails on bad row",
            [
                {"name": "good row", "val": 1},
                {"name": "bad row", "val": 2},
            ],
            then=lambda result, ctx, row: expect(row["val"]).to_be(1),
        )


@unit
def test_outline_uses_row_index_when_no_name():
    with pytest.raises(AssertionError, match=r"\[row 1\]"):
        scenario_outline(
            "fails on row 1",
            [
                {"val": 1},
                {"val": 2},
            ],
            then=lambda result, ctx, row: expect(row["val"]).to_be(1),
        )


@unit
def test_outline_given_error_tagged():
    with pytest.raises(RuntimeError, match=r"\[unit/given\]"):
        scenario_outline(
            "given fails",
            [{"name": "boom"}],
            given=lambda row: (_ for _ in ()).throw(RuntimeError("setup broke")),
            then=lambda result, ctx, row: None,
        )


@unit
def test_outline_when_error_tagged():
    with pytest.raises(ValueError, match=r"\[unit/when\]"):
        scenario_outline(
            "when fails",
            [{"name": "boom"}],
            when=lambda ctx, row: (_ for _ in ()).throw(ValueError("action broke")),
            then=lambda result, ctx, row: None,
        )


@unit
def test_outline_cleanup_called():
    cleaned = []
    scenario_outline(
        "cleanup per row",
        [{"name": "a"}, {"name": "b"}],
        given=lambda row: row["name"],
        then=lambda result, ctx, row: None,
        cleanup=lambda ctx: cleaned.append(ctx),
    )
    expect(cleaned).to_be(["a", "b"])
