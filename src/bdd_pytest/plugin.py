"""Pytest plugin enforcing BDD level and documentation contracts."""

from __future__ import annotations

import inspect
import json
from typing import Literal, cast

import pytest

from ._contract import begin_test, end_test

LEVELS = ("unit", "component", "integration", "e2e")
Policy = Literal["off", "warn", "error"]
POLICIES = {"off", "warn", "error"}
LEVEL_TIMEOUT_LABELS = {
    "unit": "<100ms",
    "component": "<5s",
    "integration": "<30s",
    "e2e": "<120s",
}


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("bdd-pytest")
    group.addoption(
        "--bdd-level-policy",
        choices=sorted(POLICIES),
        default=None,
        help="Contract for exactly one level marker: off, warn, or error.",
    )
    group.addoption(
        "--bdd-documentation-policy",
        choices=sorted(POLICIES),
        default=None,
        help="Require a test docstring or scenario(): off, warn, or error.",
    )
    parser.addini(
        "bdd_level_policy",
        "Contract for exactly one BDD level marker (off, warn, error).",
        default="warn",
    )
    parser.addini(
        "bdd_documentation_policy",
        "Require a test docstring or scenario() call (off, warn, error).",
        default="off",
    )


def pytest_configure(config: pytest.Config) -> None:
    for level in LEVELS:
        timeout = LEVEL_TIMEOUT_LABELS[level]
        config.addinivalue_line("markers", f"{level}: bdd-pytest {level} test ({timeout})")
    for option, ini_name in (
        ("bdd_level_policy", "bdd_level_policy"),
        ("bdd_documentation_policy", "bdd_documentation_policy"),
    ):
        _policy(config, option, ini_name)


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    policy = _policy(config, "bdd_level_policy", "bdd_level_policy")
    if policy == "off":
        return

    violations: list[str] = []
    for item in items:
        marked = _level_markers(item)
        if len(marked) == 1:
            continue
        detail = (
            "no level marker" if not marked else f"multiple level markers: {', '.join(marked)}"
        )
        message = f"{item.nodeid}: {detail}; choose exactly one of {', '.join(LEVELS)}"
        if policy == "warn":
            item.warn(pytest.PytestWarning(message))
        else:
            violations.append(message)

    if violations:
        formatted = "\n  - ".join(violations)
        raise pytest.UsageError(f"bdd-pytest level contract failed:\n  - {formatted}")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item: pytest.Item):
    token = begin_test()
    outcome = yield
    scenarios = end_test(token)

    levels = _level_markers(item)
    documented_scenarios = [record for record in scenarios if record.documented]
    documentation = (
        "scenario"
        if documented_scenarios
        else "docstring"
        if _has_docstring(item)
        else "missing"
    )
    item.user_properties.append(("bdd.level", ",".join(levels)))
    item.user_properties.append(("bdd.documentation", documentation))
    if scenarios:
        serialized = json.dumps(
            [
                {
                    "name": record.name,
                    "phases": record.phases,
                    "documented": record.documented,
                }
                for record in scenarios
            ],
            separators=(",", ":"),
            sort_keys=True,
        )
        item.user_properties.append(("bdd.scenarios", serialized))

    policy = _policy(item.config, "bdd_documentation_policy", "bdd_documentation_policy")
    if policy == "off" or outcome.excinfo is not None:
        return
    if _has_docstring(item) or documented_scenarios:
        return

    message = (
        f"{item.nodeid}: documentation contract failed; add a non-empty test docstring "
        "or execute scenario()/scenario_outline()"
    )
    if policy == "warn":
        item.warn(pytest.PytestWarning(message))
    else:
        outcome.force_exception(pytest.fail.Exception(message, pytrace=False))


def _has_docstring(item: pytest.Item) -> bool:
    obj = getattr(item, "obj", None)
    return bool(obj and inspect.getdoc(obj))


def _level_markers(item: pytest.Item) -> list[str]:
    return [level for level in LEVELS if item.get_closest_marker(level)]


def _policy(config: pytest.Config, option: str, ini_name: str) -> Policy:
    cli_value = config.getoption(option, default=None)
    value = cli_value if cli_value is not None else config.getini(ini_name)
    if not isinstance(value, str) or value not in POLICIES:
        allowed = ", ".join(sorted(POLICIES))
        raise pytest.UsageError(f"{ini_name} must be one of: {allowed}; got {value!r}")
    return cast(Policy, value)
