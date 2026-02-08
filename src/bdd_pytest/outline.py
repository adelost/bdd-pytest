"""Table-driven scenarios."""

from __future__ import annotations

from typing import Any, Callable

from ._phases import run_phase
from .levels import get_current_level


def scenario_outline(
    name: str,
    table: list[dict[str, Any]],
    *,
    given: Callable[[dict], Any] | None = None,
    when: Callable[..., Any] | None = None,
    then: Callable[..., None],
    cleanup: Callable[..., None] | None = None,
) -> None:
    """Run a scenario for each row in table.

    Flow per row:
        given(row) -> ctx
        when(ctx, row) -> result
        then(result, ctx, row)
    """
    level = get_current_level()
    tag = f"{level}/" if level else ""

    for i, row in enumerate(table):
        row_name = row.get("name", f"row {i}")
        label = f"{name} [{row_name}]"
        ctx = None
        try:
            if given is not None:
                ctx = run_phase("given", tag, label, given, row)

            if when is not None:
                result = run_phase("when", tag, label, when, ctx, row)
            else:
                result = ctx

            run_phase("then", tag, label, then, result, ctx, row)
        finally:
            if cleanup is not None:
                cleanup(ctx)
