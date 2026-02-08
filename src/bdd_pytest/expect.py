"""Expression-based assertions for use in lambdas.

Solves: Python `assert` is a statement, can't be used in lambdas.
All methods return `self` so they work as expressions.
"""

from __future__ import annotations

import re
from typing import Any, Type


class Expectation:
    """Fluent assertion wrapper. All methods return self for expression use."""

    def __init__(self, value: Any, *, negated: bool = False) -> None:
        self._value = value
        self._negated = negated

    @property
    def not_(self) -> Expectation:
        return Expectation(self._value, negated=not self._negated)

    def _check(self, condition: bool, msg: str) -> Expectation:
        ok = (not condition) if self._negated else condition
        prefix = "not " if self._negated else ""
        if not ok:
            raise AssertionError(f"Expected {prefix}{msg}")
        return self

    def to_be(self, expected: Any) -> Expectation:
        return self._check(
            self._value == expected,
            f"{self._value!r} to be {expected!r}",
        )

    def to_be_none(self) -> Expectation:
        return self._check(
            self._value is None,
            f"{self._value!r} to be None",
        )

    def to_be_truthy(self) -> Expectation:
        return self._check(bool(self._value), f"{self._value!r} to be truthy")

    def to_be_falsy(self) -> Expectation:
        return self._check(not bool(self._value), f"{self._value!r} to be falsy")

    def to_contain(self, item: Any) -> Expectation:
        return self._check(
            item in self._value,
            f"{self._value!r} to contain {item!r}",
        )

    def to_be_instance_of(self, cls: Type) -> Expectation:
        return self._check(
            isinstance(self._value, cls),
            f"{self._value!r} to be instance of {cls.__name__}",
        )

    def to_have_length(self, n: int) -> Expectation:
        actual = len(self._value)
        return self._check(
            actual == n,
            f"{self._value!r} to have length {n} (got {actual})",
        )

    def to_be_close_to(self, expected: float, *, places: int = 7) -> Expectation:
        diff = abs(self._value - expected)
        threshold = 10 ** -places
        return self._check(
            diff < threshold,
            f"{self._value!r} to be close to {expected!r} (within {places} decimal places)",
        )

    def to_be_greater_than(self, n: Any) -> Expectation:
        return self._check(
            self._value > n,
            f"{self._value!r} to be greater than {n!r}",
        )

    def to_be_less_than(self, n: Any) -> Expectation:
        return self._check(
            self._value < n,
            f"{self._value!r} to be less than {n!r}",
        )

    def to_match(self, pattern: str) -> Expectation:
        return self._check(
            re.search(pattern, self._value) is not None,
            f"{self._value!r} to match {pattern!r}",
        )

    def to_raise(self, exc_type: Type[BaseException], *, match: str | None = None) -> Expectation:
        """Assert that self._value (a callable) raises exc_type."""
        if not callable(self._value):
            raise TypeError(f"to_raise requires a callable, got {type(self._value).__name__}")
        raised = None
        try:
            self._value()
        except BaseException as e:
            raised = e

        if self._negated:
            if raised is not None and isinstance(raised, exc_type):
                raise AssertionError(
                    f"Expected not to raise {exc_type.__name__}, but it was raised"
                )
            return self

        if raised is None:
            raise AssertionError(f"Expected to raise {exc_type.__name__}, but nothing was raised")
        if not isinstance(raised, exc_type):
            raise AssertionError(
                f"Expected to raise {exc_type.__name__}, "
                f"but {type(raised).__name__} was raised"
            )
        if match is not None and not re.search(match, str(raised)):
            raise AssertionError(
                f"Expected error message to match {match!r}, got {str(raised)!r}"
            )
        return self


def expect(value: Any) -> Expectation:
    """Create an Expectation for fluent assertions."""
    return Expectation(value)
