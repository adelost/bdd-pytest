"""Tests for scenario(), feature(), rule(), catches()."""

import pytest

from bdd_pytest import catches, expect, scenario, unit


def _raise(exc):
    """Raise in expression context (for lambdas)."""
    raise exc


# --- scenario() variants ---


@unit
def test_full_given_when_then():
    scenario(
        "adds two numbers",
        given=("two numbers", lambda: (2, 3)),
        when=("adding them", lambda ctx: ctx[0] + ctx[1]),
        then=("result is 5", lambda result, _: expect(result).to_be(5)),
    )


@unit
def test_given_then_only():
    scenario(
        "list starts empty",
        given=("an empty list", lambda: []),
        then=("length is 0", lambda _, ctx: expect(ctx).to_have_length(0)),
    )


@unit
def test_when_then_only():
    scenario(
        "computes without setup",
        when=("multiplying", lambda _: 6 * 7),
        then=("result is 42", lambda result, _: expect(result).to_be(42)),
    )


@unit
def test_then_only():
    scenario(
        "pure assertion",
        then=("true is truthy", lambda _, __: expect(True).to_be_truthy()),
    )


@unit
def test_given_string_description():
    scenario(
        "string-only given",
        given="some context description",
        when=("doing something", lambda _: 42),
        then=("result is 42", lambda result, _: expect(result).to_be(42)),
    )


# --- Error tagging ---


@unit
def test_error_in_given_tagged():
    with pytest.raises(RuntimeError, match=r"\[unit/given\]"):
        scenario(
            "given fails",
            given=("broken setup", lambda: _raise(RuntimeError("boom"))),
            then=("never reached", lambda r, c: None),
        )


@unit
def test_error_in_when_tagged():
    with pytest.raises(ValueError, match=r"\[unit/when\]"):
        scenario(
            "when fails",
            when=("broken action", lambda _: _raise(ValueError("oops"))),
            then=("never reached", lambda r, c: None),
        )


@unit
def test_error_in_then_tagged():
    with pytest.raises(AssertionError, match=r"\[unit/then\]"):
        scenario(
            "then fails",
            then=("wrong result", lambda _, __: expect(1).to_be(2)),
        )


# --- given() context flows to when() and then() ---


@unit
def test_context_flows_through():
    scenario(
        "context preserved",
        given=("a dict", lambda: {"key": "value"}),
        when=("reading key", lambda ctx: ctx["key"]),
        then=("got value", lambda result, ctx: (
            expect(result).to_be("value"),
            expect(ctx).to_contain("key"),
        )),
    )


# --- given+then: result is None, ctx is from given ---


@unit
def test_given_then_result_is_none():
    scenario(
        "no when means result is None",
        given=("a value", lambda: 42),
        then=("result is None, ctx is 42", lambda result, ctx: (
            expect(result).to_be_none(),
            expect(ctx).to_be(42),
        )),
    )


# --- cleanup ---


@unit
def test_cleanup_called_on_success():
    cleaned = []
    scenario(
        "cleanup runs after success",
        given=("a resource", lambda: "resource"),
        then=("it exists", lambda _, ctx: expect(ctx).to_be("resource")),
        cleanup=lambda ctx: cleaned.append(ctx),
    )
    expect(cleaned).to_be(["resource"])


@unit
def test_cleanup_called_on_failure():
    cleaned = []
    with pytest.raises(AssertionError):
        scenario(
            "cleanup runs after failure",
            given=("a resource", lambda: "resource"),
            then=("fails", lambda _, __: expect(1).to_be(2)),
            cleanup=lambda ctx: cleaned.append(ctx),
        )
    expect(cleaned).to_be(["resource"])


# --- catches() ---


@unit
def test_catches_returns_exception():
    err = catches(lambda: _raise(ValueError("test")))
    expect(err).to_be_instance_of(ValueError)
    expect(str(err)).to_contain("test")


@unit
def test_catches_returns_none_on_success():
    result = catches(lambda: 42)
    expect(result).to_be_none()


@unit
def test_catches_in_scenario():
    scenario(
        "catches integrates with scenario",
        when=("raising ValueError", lambda _: catches(lambda: _raise(ValueError("bad")))),
        then=("error is ValueError", lambda err, _: (
            expect(err).to_be_instance_of(ValueError),
            expect(str(err)).to_contain("bad"),
        )),
    )


