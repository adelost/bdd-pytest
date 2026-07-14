"""Shared phase execution with error-tagging."""

from __future__ import annotations

from typing import Any, Callable


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
