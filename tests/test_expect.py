"""Tests for expect() fluent assertions."""

import pytest

from bdd_pytest import expect, unit


def _raise(exc):
    """Raise in expression context (for lambdas)."""
    raise exc


# --- to_be ---


@unit
def test_to_be_pass():
    expect(42).to_be(42)


@unit
def test_to_be_fail():
    with pytest.raises(AssertionError, match="to be 99"):
        expect(42).to_be(99)


# --- to_be_none ---


@unit
def test_to_be_none_pass():
    expect(None).to_be_none()


@unit
def test_to_be_none_fail():
    with pytest.raises(AssertionError, match="to be None"):
        expect(42).to_be_none()


# --- to_be_truthy / to_be_falsy ---


@unit
def test_to_be_truthy_pass():
    expect(1).to_be_truthy()
    expect("hello").to_be_truthy()


@unit
def test_to_be_truthy_fail():
    with pytest.raises(AssertionError, match="to be truthy"):
        expect(0).to_be_truthy()


@unit
def test_to_be_falsy_pass():
    expect(0).to_be_falsy()
    expect("").to_be_falsy()
    expect(None).to_be_falsy()


@unit
def test_to_be_falsy_fail():
    with pytest.raises(AssertionError, match="to be falsy"):
        expect(1).to_be_falsy()


# --- to_contain ---


@unit
def test_to_contain_list():
    expect([1, 2, 3]).to_contain(2)


@unit
def test_to_contain_string():
    expect("hello world").to_contain("world")


@unit
def test_to_contain_fail():
    with pytest.raises(AssertionError, match="to contain 99"):
        expect([1, 2]).to_contain(99)


# --- to_be_instance_of ---


@unit
def test_to_be_instance_of_pass():
    expect(42).to_be_instance_of(int)
    expect("hello").to_be_instance_of(str)


@unit
def test_to_be_instance_of_fail():
    with pytest.raises(AssertionError, match="to be instance of str"):
        expect(42).to_be_instance_of(str)


# --- to_have_length ---


@unit
def test_to_have_length_pass():
    expect([1, 2, 3]).to_have_length(3)
    expect("abc").to_have_length(3)


@unit
def test_to_have_length_fail():
    with pytest.raises(AssertionError, match="to have length 5"):
        expect([1, 2]).to_have_length(5)


# --- to_be_close_to ---


@unit
def test_to_be_close_to_pass():
    expect(0.1 + 0.2).to_be_close_to(0.3)


@unit
def test_to_be_close_to_fail():
    with pytest.raises(AssertionError, match="to be close to"):
        expect(0.1).to_be_close_to(0.2)


@unit
def test_to_be_close_to_custom_places():
    expect(1.005).to_be_close_to(1.0, places=2)


@unit
def test_to_be_close_to_custom_places_fail():
    with pytest.raises(AssertionError, match="within 5 decimal places"):
        expect(1.00002).to_be_close_to(1.0, places=5)


@unit
def test_not_to_be_close_to():
    expect(0.1).not_.to_be_close_to(0.2)


# --- to_be_greater_than / to_be_less_than ---


@unit
def test_to_be_greater_than_pass():
    expect(10).to_be_greater_than(5)


@unit
def test_to_be_greater_than_fail():
    with pytest.raises(AssertionError, match="to be greater than"):
        expect(3).to_be_greater_than(5)


@unit
def test_to_be_less_than_pass():
    expect(3).to_be_less_than(5)


@unit
def test_to_be_less_than_fail():
    with pytest.raises(AssertionError, match="to be less than"):
        expect(10).to_be_less_than(5)


# --- to_match ---


@unit
def test_to_match_pass():
    expect("hello-world-123").to_match(r"world-\d+")


@unit
def test_to_match_fail():
    with pytest.raises(AssertionError, match="to match"):
        expect("hello").to_match(r"^\d+$")


# --- to_raise ---


@unit
def test_to_raise_pass():
    expect(lambda: _raise(ValueError("boom"))).to_raise(ValueError)


@unit
def test_to_raise_with_match():
    expect(lambda: _raise(ValueError("bad input"))).to_raise(
        ValueError, match="bad"
    )


@unit
def test_to_raise_nothing_raised():
    with pytest.raises(AssertionError, match="nothing was raised"):
        expect(lambda: 42).to_raise(ValueError)


@unit
def test_to_raise_wrong_type():
    with pytest.raises(AssertionError, match="TypeError was raised"):
        expect(lambda: _raise(TypeError("wrong"))).to_raise(ValueError)


@unit
def test_to_raise_match_fails():
    with pytest.raises(AssertionError, match="to match"):
        expect(lambda: _raise(ValueError("actual msg"))).to_raise(
            ValueError, match="expected msg"
        )


@unit
def test_to_raise_not_callable():
    with pytest.raises(TypeError, match="requires a callable"):
        expect(42).to_raise(ValueError)


# --- not_ negation ---


@unit
def test_not_to_be():
    expect(42).not_.to_be(99)


@unit
def test_not_to_be_fails():
    with pytest.raises(AssertionError, match="not.*to be"):
        expect(42).not_.to_be(42)


@unit
def test_not_to_contain():
    expect([1, 2]).not_.to_contain(99)


@unit
def test_not_to_be_none():
    expect(42).not_.to_be_none()


@unit
def test_not_to_raise():
    expect(lambda: 42).not_.to_raise(ValueError)


# --- chaining (returns self) ---


@unit
def test_chaining():
    result = expect(42).to_be(42)
    # Returns Expectation, can chain
    result.to_be_instance_of(int).to_be_greater_than(0)


# --- tuple trick for multiple assertions in lambda ---


@unit
def test_tuple_trick():
    # Simulates: lambda result, _: (expect(r).to_be(1), expect(r).to_be_truthy())
    r = 42
    _ = (
        expect(r).to_be(42),
        expect(r).to_be_truthy(),
        expect(r).to_be_instance_of(int),
    )
