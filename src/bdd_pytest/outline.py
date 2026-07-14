"""Table-driven scenarios."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Callable, TypeVar, cast

import pytest

from ._contract import record_scenario
from ._phases import run_phase
from .levels import get_current_level

F = TypeVar("F", bound=Callable[..., Any])


def cases(table: Sequence[Mapping[str, Any]]) -> Callable[[F], F]:
    """Parametrize a ``row`` argument so every example is a pytest test item.

    Rows may include a non-empty ``name`` field, which becomes the pytest case id.
    This is the preferred table-driven API because one bad row does not hide later rows.
    """
    rows = _validate_table(table)
    ids = [_row_name(row, index) for index, row in enumerate(rows)]
    return cast(Callable[[F], F], pytest.mark.parametrize("row", rows, ids=ids))


def scenario_outline(
    name: str,
    table: list[dict[str, Any]],
    *,
    given: Callable[[dict], Any] | None = None,
    when: Callable[..., Any] | None = None,
    then: Callable[..., None],
    cleanup: Callable[..., None] | None = None,
) -> None:
    """Run scenarios inline for compatibility.

    Prefer :func:`cases`, which creates a separately collected pytest item for
    every row.

    Flow per row:
        given(row) -> ctx
        when(ctx, row) -> result
        then(result, ctx, row)
    """
    scenario_name = _require_text("scenario name", name)
    rows = _validate_table(table)
    if given is not None and not callable(given):
        raise TypeError("given callback must be callable")
    if when is not None and not callable(when):
        raise TypeError("when callback must be callable")
    if not callable(then):
        raise TypeError("then callback must be callable")
    if cleanup is not None and not callable(cleanup):
        raise TypeError("cleanup callback must be callable")

    level = get_current_level()
    tag = f"{level}/" if level else ""

    for i, row in enumerate(rows):
        row_name = _row_name(row, i)
        label = f"{scenario_name} [{row_name}]"
        record_scenario(label)
        ctx = None
        try:
            if given is not None:
                ctx = run_phase("given", tag, label, "setup completes", given, row)

            if when is not None:
                result = run_phase("when", tag, label, "action completes", when, ctx, row)
            else:
                result = ctx

            run_phase("then", tag, label, "expectations hold", then, result, ctx, row)
        finally:
            if cleanup is not None:
                cleanup(ctx)


def _validate_table(table: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(table, (str, bytes)) or not isinstance(table, Sequence):
        raise TypeError("table must be a sequence of mappings")
    if not table:
        raise ValueError("table must contain at least one row")
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(table):
        if not isinstance(row, Mapping):
            raise TypeError(f"table row {index} must be a mapping")
        rows.append(dict(row))
    return rows


def _row_name(row: Mapping[str, Any], index: int) -> str:
    value = row.get("name", f"row {index}")
    return _require_text(f"table row {index} name", value)


def _require_text(field: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()
