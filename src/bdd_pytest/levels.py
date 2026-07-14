"""Level decorators - @unit, @component, @integration, @e2e.

Each decorator does three things:
1. @pytest.mark.timeout(X) - enforces timeout
2. @pytest.mark.<level> - filterable marker
3. Sets a context-local current level at runtime for error-tagging
"""

from __future__ import annotations

import functools
import inspect
from contextvars import ContextVar
from typing import Any, Callable, TypeVar, cast

import pytest

LEVEL_TIMEOUTS = {
    "unit": 0.1,
    "component": 5,
    "integration": 30,
    "e2e": 120,
}

_current_level: ContextVar[str | None] = ContextVar("bdd_pytest_level", default=None)
F = TypeVar("F", bound=Callable[..., Any])


def _make_level(name: str) -> Callable[[F], F]:
    timeout = LEVEL_TIMEOUTS[name]

    def decorator(fn: F) -> F:
        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                token = _current_level.set(name)
                try:
                    return await fn(*args, **kwargs)
                finally:
                    _current_level.reset(token)

        else:

            @functools.wraps(fn)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                token = _current_level.set(name)
                try:
                    return fn(*args, **kwargs)
                finally:
                    _current_level.reset(token)

        wrapper = pytest.mark.timeout(timeout)(wrapper)
        wrapper = getattr(pytest.mark, name)(wrapper)
        return cast(F, wrapper)

    return decorator


unit = _make_level("unit")
component = _make_level("component")
integration = _make_level("integration")
e2e = _make_level("e2e")


def get_current_level() -> str | None:
    return _current_level.get()
