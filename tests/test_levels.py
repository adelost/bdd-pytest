"""Tests for level decorators (@unit, @component, etc.)."""

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


# --- Thread-local level ---


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


def test_thread_local_none_outside_decorator():
    """get_current_level() returns None when no decorator is active."""
    expect(get_current_level()).to_be_none()


# --- Decorator preserves function metadata ---


@unit
def test_functools_wraps_preserves_name():
    pass


@unit
def test_decorated_function_name():
    expect(test_functools_wraps_preserves_name.__name__).to_be(
        "test_functools_wraps_preserves_name"
    )
