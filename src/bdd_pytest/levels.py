"""Level decorators - @unit, @component, @integration, @e2e.

Each decorator does three things:
1. @pytest.mark.timeout(X) - enforces timeout
2. @pytest.mark.<level> - filterable marker
3. Sets thread-local _current_level.name at runtime for error-tagging
"""

from __future__ import annotations

import functools
import threading

import pytest

LEVEL_TIMEOUTS = {
    "unit": 0.1,
    "component": 5,
    "integration": 30,
    "e2e": 120,
}

_current_level = threading.local()


def _make_level(name: str):
    timeout = LEVEL_TIMEOUTS[name]

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            _current_level.name = name
            try:
                return fn(*args, **kwargs)
            finally:
                _current_level.name = None

        wrapper = pytest.mark.timeout(timeout)(wrapper)
        wrapper = getattr(pytest.mark, name)(wrapper)
        return wrapper

    return decorator


unit = _make_level("unit")
component = _make_level("component")
integration = _make_level("integration")
e2e = _make_level("e2e")


def get_current_level() -> str | None:
    return getattr(_current_level, "name", None)
