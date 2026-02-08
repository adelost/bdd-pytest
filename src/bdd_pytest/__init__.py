"""bdd-pytest - Enforced Given/When/Then for pytest.

No Gherkin, no .feature files, no step-definitions.
The scenario dict IS the test - inline, zero-config.
"""

from __future__ import annotations

from typing import Any, Callable

from ._phases import run_phase
from .expect import Expectation, expect
from .levels import component, e2e, get_current_level, integration, unit
from .outline import scenario_outline

__all__ = [
    "scenario",
    "catches",
    "expect",
    "Expectation",
    "scenario_outline",
    "unit",
    "component",
    "integration",
    "e2e",
]


def scenario(
    name: str,
    *,
    given: tuple[str, Callable[[], Any]] | str | None = None,
    when: tuple[str, Callable[..., Any]] | None = None,
    then: tuple[str, Callable[..., None]],
    cleanup: Callable[..., None] | None = None,
) -> None:
    """Execute a Given/When/Then scenario inline."""
    level = get_current_level()
    tag = f"{level}/" if level else ""
    ctx: Any = None
    result: Any = None

    try:
        if given is not None and not isinstance(given, str):
            ctx = run_phase("given", tag, given[0], given[1])

        if when is not None:
            result = run_phase("when", tag, when[0], when[1], ctx)

        result = run_phase("then", tag, then[0], then[1], result, ctx)
    finally:
        if cleanup is not None:
            cleanup(ctx)


def catches(fn: Callable[[], Any]) -> BaseException | None:
    """Call fn and return the exception if raised, else None.

    Usage:
        when=("doing risky thing", lambda _: catches(lambda: risky())),
        then=("error is ValueError", lambda err, _: expect(err).to_be_instance_of(ValueError)),
    """
    try:
        fn()
        return None
    except BaseException as e:
        return e
