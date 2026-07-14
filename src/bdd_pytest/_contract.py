"""Per-test state used by the pytest documentation contract."""

from __future__ import annotations

from contextvars import ContextVar, Token

_scenario_names: ContextVar[tuple[str, ...] | None] = ContextVar(
    "bdd_pytest_scenario_names", default=None
)


def begin_test() -> Token[tuple[str, ...] | None]:
    """Start tracking scenarios for the current pytest item."""
    return _scenario_names.set(())


def record_scenario(name: str) -> None:
    """Record a validated scenario without leaking state between tests."""
    current = _scenario_names.get()
    if current is not None:
        _scenario_names.set((*current, name))


def end_test(token: Token[tuple[str, ...] | None]) -> tuple[str, ...]:
    """Return scenarios recorded by this test and restore outer state."""
    names = _scenario_names.get() or ()
    _scenario_names.reset(token)
    return names
