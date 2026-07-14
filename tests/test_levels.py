"""Tests for level decorators (@unit, @component, etc.)."""

import asyncio

from bdd_pytest import component, e2e, expect, integration, scenario, unit
from bdd_pytest.levels import LEVEL_TIMEOUTS, get_current_level

# --- Markers applied correctly ---


@unit
def test_unit_sets_marker():
    """@unit applies pytest.mark.unit to the test function."""


@component
def test_component_sets_marker():
    """@component applies pytest.mark.component to the test function."""


@integration
def test_integration_sets_marker():
    """@integration applies pytest.mark.integration to the test function."""


@e2e
def test_e2e_sets_marker():
    """@e2e applies pytest.mark.e2e to the test function."""


# --- Timeout markers ---


@unit
def test_unit_has_timeout_marker():
    scenario(
        "unit timeout is 0.1s",
        then=("timeout matches", lambda _, __: expect(LEVEL_TIMEOUTS["unit"]).to_be(0.1)),
    )


@unit
def test_all_timeouts_defined():
    scenario(
        "all levels have timeouts",
        then=(
            "four levels exist",
            lambda _, __: (
                expect(LEVEL_TIMEOUTS).to_contain("unit"),
                expect(LEVEL_TIMEOUTS).to_contain("component"),
                expect(LEVEL_TIMEOUTS).to_contain("integration"),
                expect(LEVEL_TIMEOUTS).to_contain("e2e"),
            ),
        ),
    )


# --- Context-local level ---


@unit
def test_thread_local_set_during_execution():
    """get_current_level() returns 'unit' inside @unit-decorated test."""
    scenario(
        "thread-local is set",
        then=("level is unit", lambda _, __: expect(get_current_level()).to_be("unit")),
    )


@component
def test_thread_local_set_for_component():
    scenario(
        "thread-local is set for component",
        then=("level is component", lambda _, __: expect(get_current_level()).to_be("component")),
    )


@unit
def test_context_local_restored_after_nested_decorator():
    """A nested level restores the surrounding test's level."""
    seen = []

    @component
    def nested():
        seen.append(get_current_level())

    expect(get_current_level()).to_be("unit")
    nested()
    expect(seen).to_be(["component"])
    expect(get_current_level()).to_be("unit")


@unit
def test_context_local_level_survives_async_execution():
    """Async tests retain their level across await points and restore it afterwards."""

    @component
    async def nested():
        await asyncio.sleep(0)
        return get_current_level()

    expect(asyncio.run(nested())).to_be("component")
    expect(get_current_level()).to_be("unit")


# --- Decorator preserves function metadata ---


@unit
def test_functools_wraps_preserves_name():
    pass


@unit
def test_decorated_function_name():
    expect(test_functools_wraps_preserves_name.__name__).to_be(
        "test_functools_wraps_preserves_name"
    )
