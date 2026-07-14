"""Table-driven scenarios."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Callable, TypeVar, cast

import pytest

from ._contract import record_scenario
from ._phases import raise_scenario_failures, run_phase
from .levels import get_current_level

F = TypeVar("F", bound=Callable[..., Any])


def cases(table: Sequence[Mapping[str, Any]]) -> Callable[[F], F]:
    """Parametrize a ``row`` argument so every example is a pytest test item.

    Rows may include a non-empty ``name`` field, which becomes the pytest case id.
    This is the preferred table-driven API because one bad row does not hide later rows.
    """
    rows = _validate_table(table, require_names=True)
    ids = [_row_name(row, index) for index, row in enumerate(rows)]
    return cast(Callable[[F], F], pytest.mark.parametrize("row", rows, ids=ids))


def scenario_outline(
    name: str,
    table: list[dict[str, Any]],
    *,
    given: tuple[str, Callable[[dict], Any]] | Callable[[dict], Any] | None = None,
    when: tuple[str, Callable[..., Any]] | Callable[..., Any] | None = None,
    then: tuple[str, Callable[..., None]] | Callable[..., None],
    cleanup: Callable[..., None] | None = None,
) -> None:
    """Run scenarios inline for compatibility.

    Prefer :func:`cases`, which creates a separately collected pytest item for
    every row. Described phase tuples satisfy the documentation contract;
    callable-only phases remain supported as a legacy form.

    Flow per row:
        given(row) -> ctx
        when(ctx, row) -> result
        then(result, ctx, row)
    """
    scenario_name = _require_text("scenario name", name)
    rows = _validate_table(table)
    provided_phases = [phase for phase in (given, when, then) if phase is not None]
    tuple_flags = [isinstance(phase, tuple) for phase in provided_phases]
    if any(tuple_flags) and not all(tuple_flags):
        raise TypeError("scenario_outline must describe all phases or use callable-only phases")
    documented = all(tuple_flags)
    given_desc, given_fn = _resolve_phase("given", given, "setup completes", documented)
    when_desc, when_fn = _resolve_phase("when", when, "action completes", documented)
    then_desc, then_fn = _resolve_phase("then", then, "expectations hold", documented)
    assert then_desc is not None and then_fn is not None
    if cleanup is not None and not callable(cleanup):
        raise TypeError("cleanup callback must be callable")

    level = get_current_level()
    tag = f"{level}/" if level else ""

    for i, row in enumerate(rows):
        row_name = _row_name(row, i)
        label = f"{scenario_name} [{row_name}]"
        phase_docs = {"then": then_desc}
        if given_desc is not None:
            phase_docs["given"] = given_desc
        if when_desc is not None:
            phase_docs["when"] = when_desc
        record_scenario(label, phase_docs, documented=documented)
        ctx = None
        primary_failure: BaseException | None = None
        try:
            if given_fn is not None:
                ctx = run_phase("given", tag, label, given_desc, given_fn, row)

            if when_fn is not None:
                result = run_phase("when", tag, label, when_desc, when_fn, ctx, row)
            else:
                result = ctx

            run_phase("then", tag, label, then_desc, then_fn, result, ctx, row)
        except BaseException as error:
            primary_failure = error

        cleanup_failure: BaseException | None = None
        if cleanup is not None:
            try:
                run_phase("cleanup", tag, label, "cleanup completes", cleanup, ctx)
            except BaseException as error:
                cleanup_failure = error

        raise_scenario_failures(label, primary_failure, cleanup_failure)


def _validate_table(
    table: Sequence[Mapping[str, Any]],
    *,
    require_names: bool = False,
) -> list[dict[str, Any]]:
    if isinstance(table, (str, bytes)) or not isinstance(table, Sequence):
        raise TypeError("table must be a sequence of mappings")
    if not table:
        raise ValueError("table must contain at least one row")
    rows: list[dict[str, Any]] = []
    names: set[str] = set()
    for index, row in enumerate(table):
        if not isinstance(row, Mapping):
            raise TypeError(f"table row {index} must be a mapping")
        copied = dict(row)
        if require_names and "name" not in copied:
            raise ValueError(f"table row {index} requires a non-empty name")
        name = _row_name(copied, index)
        if name in names:
            raise ValueError(f"table row names must be unique: {name!r}")
        names.add(name)
        rows.append(copied)
    return rows


def _resolve_phase(
    label: str,
    value: tuple[str, Callable[..., Any]] | Callable[..., Any] | None,
    legacy_description: str,
    documented: bool,
) -> tuple[str | None, Callable[..., Any] | None]:
    if value is None:
        return None, None
    if documented:
        if not isinstance(value, tuple) or len(value) != 2:
            raise TypeError(f"{label} must be a (description, callable) tuple")
        description, fn = value
        validated_description = _require_text(f"{label} description", description)
        if not callable(fn):
            raise TypeError(f"{label} callback must be callable")
        return validated_description, fn
    if not callable(value):
        raise TypeError(f"{label} callback must be callable")
    return legacy_description, value


def _row_name(row: Mapping[str, Any], index: int) -> str:
    value = row.get("name", f"row {index}")
    return _require_text(f"table row {index} name", value)


def _require_text(field: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()
