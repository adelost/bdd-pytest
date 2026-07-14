"""Shared phase execution with error-tagging."""

from __future__ import annotations

from typing import Any, Callable


class ScenarioCleanupError(Exception):
    """A scenario and its cleanup both failed; both errors are retained."""

    def __init__(self, scenario_name: str, primary: Exception, cleanup: Exception):
        message = (
            f"{scenario_name}: scenario and cleanup both failed\n"
            f"- {primary}\n"
            f"- {cleanup}"
        )
        super().__init__(message)
        self.primary = primary
        self.cleanup = cleanup
        self.exceptions = (primary, cleanup)


def run_phase(
    phase: str,
    tag: str,
    scenario_name: str,
    desc: str,
    fn: Callable[..., Any],
    *args: Any,
) -> Any:
    """Execute a scenario phase with enough context to locate a failure."""
    try:
        return fn(*args)
    except Exception as e:
        msg = f"[{tag}{phase}] {scenario_name} > {desc}: {e}"
        try:
            wrapped = type(e)(msg)
        except Exception:
            # Some exceptions (e.g. UnicodeDecodeError) require multiple args
            raise RuntimeError(msg) from e
        raise wrapped from e


def raise_scenario_failures(
    scenario_name: str,
    primary: BaseException | None,
    cleanup: BaseException | None,
) -> None:
    """Raise one failure, or a stable aggregate when scenario and cleanup fail."""
    if primary is not None and cleanup is not None:
        if isinstance(primary, Exception) and isinstance(cleanup, Exception):
            raise ScenarioCleanupError(scenario_name, primary, cleanup) from primary
        if not isinstance(primary, Exception):
            raise primary from cleanup
        raise cleanup from primary
    if primary is not None:
        raise primary
    if cleanup is not None:
        raise cleanup
