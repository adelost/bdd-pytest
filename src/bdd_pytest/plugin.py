"""Pytest plugin - warns when tests lack a level marker."""

from __future__ import annotations

import warnings

LEVELS = {"unit", "component", "integration", "e2e"}


def pytest_collection_modifyitems(items):
    for item in items:
        if not any(item.get_closest_marker(m) for m in LEVELS):
            warnings.warn(f"{item.nodeid} has no level marker (@unit, @component, etc)")
