"""Shared phase execution with error-tagging."""

from __future__ import annotations

from typing import Any, Callable


def run_phase(
    phase: str, tag: str, desc: str, fn: Callable[..., Any], *args: Any
) -> Any:
    """Execute a scenario phase, wrapping errors with [tag/phase] desc prefix."""
    try:
        return fn(*args)
    except Exception as e:
        msg = f"[{tag}{phase}] {desc}: {e}"
        try:
            raise type(e)(msg) from e
        except TypeError:
            # Some exceptions (e.g. UnicodeDecodeError) require multiple args
            raise RuntimeError(msg) from e
