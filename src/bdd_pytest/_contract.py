"""Per-test state used by the pytest documentation contract."""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass


@dataclass(frozen=True)
class ScenarioRecord:
    """Machine-readable scenario documentation captured during a test."""

    name: str
    phases: dict[str, str]
    documented: bool


_scenario_records: ContextVar[tuple[ScenarioRecord, ...] | None] = ContextVar(
    "bdd_pytest_scenario_records", default=None
)


def begin_test() -> Token[tuple[ScenarioRecord, ...] | None]:
    """Start tracking scenarios for the current pytest item."""
    return _scenario_records.set(())


def record_scenario(name: str, phases: dict[str, str], *, documented: bool = True) -> None:
    """Record a validated scenario without leaking state between tests."""
    current = _scenario_records.get()
    if current is not None:
        _scenario_records.set(
            (*current, ScenarioRecord(name=name, phases=phases, documented=documented))
        )


def end_test(
    token: Token[tuple[ScenarioRecord, ...] | None],
) -> tuple[ScenarioRecord, ...]:
    """Return scenarios recorded by this test and restore outer state."""
    records = _scenario_records.get() or ()
    _scenario_records.reset(token)
    return records
