"""bdd-pytest - Enforced Given/When/Then for pytest.

No Gherkin, no .feature files, no step-definitions.
The scenario dict IS the test - inline, zero-config.
"""

from __future__ import annotations

from typing import Any, Callable

from ._contract import record_scenario
from ._phases import ScenarioCleanupError, raise_scenario_failures, run_phase
from .expect import Expectation, expect
from .levels import component, e2e, get_current_level, integration, unit
from .outline import cases, scenario_outline

__all__ = [
    "scenario",
    "catches",
    "expect",
    "Expectation",
    "ScenarioCleanupError",
    "scenario_outline",
    "cases",
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
    """Execute a validated Given/When/Then scenario inline."""
    scenario_name = _require_text("scenario name", name)
    given_phase = _validate_given(given)
    when_phase = _validate_phase("when", when) if when is not None else None
    then_phase = _validate_phase("then", then)
    if cleanup is not None and not callable(cleanup):
        raise TypeError(f"scenario {scenario_name!r}: cleanup must be callable")

    phase_docs = {"then": then_phase[0]}
    if given_phase is not None:
        phase_docs["given"] = given_phase if isinstance(given_phase, str) else given_phase[0]
    if when_phase is not None:
        phase_docs["when"] = when_phase[0]
    record_scenario(scenario_name, phase_docs)
    level = get_current_level()
    tag = f"{level}/" if level else ""
    ctx: Any = None
    result: Any = None

    primary_failure: BaseException | None = None
    try:
        if given_phase is not None and not isinstance(given_phase, str):
            ctx = run_phase("given", tag, scenario_name, given_phase[0], given_phase[1])

        if when_phase is not None:
            result = run_phase("when", tag, scenario_name, when_phase[0], when_phase[1], ctx)

        run_phase("then", tag, scenario_name, then_phase[0], then_phase[1], result, ctx)
    except BaseException as error:
        primary_failure = error

    cleanup_failure: BaseException | None = None
    if cleanup is not None:
        try:
            run_phase("cleanup", tag, scenario_name, "cleanup completes", cleanup, ctx)
        except BaseException as error:
            cleanup_failure = error

    raise_scenario_failures(scenario_name, primary_failure, cleanup_failure)


def catches(fn: Callable[[], Any]) -> Exception | None:
    """Call fn and return the exception if raised, else None.

    Usage:
        when=("doing risky thing", lambda _: catches(lambda: risky())),
        then=("error is ValueError", lambda err, _: expect(err).to_be_instance_of(ValueError)),
    """
    try:
        fn()
        return None
    except Exception as e:
        return e


def _require_text(field: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _validate_phase(
    phase: str, value: object
) -> tuple[str, Callable[..., Any]]:
    if not isinstance(value, tuple) or len(value) != 2:
        raise TypeError(f"{phase} must be a (description, callable) tuple")
    description, fn = value
    validated_description = _require_text(f"{phase} description", description)
    if not callable(fn):
        raise TypeError(f"{phase} callback must be callable")
    return validated_description, fn


def _validate_given(
    value: tuple[str, Callable[[], Any]] | str | None,
) -> tuple[str, Callable[[], Any]] | str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return _require_text("given description", value)
    description, fn = _validate_phase("given", value)
    return description, fn
