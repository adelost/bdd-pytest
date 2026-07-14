"""Integration tests for the enforceable pytest contracts."""

from __future__ import annotations

import pytest

from bdd_pytest import unit

pytest_plugins = ["pytester"]


@unit
def test_level_contract_rejects_missing_marker(pytester: pytest.Pytester):
    pytester.makepyfile("def test_unclassified():\n    pass")

    result = pytester.runpytest("--bdd-level-policy=error")

    result.stderr.fnmatch_lines(
        ["*bdd-pytest level contract failed:*", "*test_unclassified: no level marker*"]
    )
    assert result.ret == pytest.ExitCode.USAGE_ERROR


@unit
def test_level_contract_rejects_multiple_markers(pytester: pytest.Pytester):
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.unit
        @pytest.mark.component
        def test_ambiguous():
            pass
        """
    )

    result = pytester.runpytest("--bdd-level-policy=error")

    result.stderr.fnmatch_lines(["*multiple level markers: unit, component*"])
    assert result.ret == pytest.ExitCode.USAGE_ERROR


@unit
def test_documentation_contract_rejects_undocumented_test(pytester: pytest.Pytester):
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.unit
        def test_undocumented():
            assert True
        """
    )

    result = pytester.runpytest(
        "--bdd-level-policy=error", "--bdd-documentation-policy=error"
    )

    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*documentation contract failed*"])


@unit
def test_documentation_contract_accepts_docstring_and_scenario(pytester: pytest.Pytester):
    pytester.makepyfile(
        """
        from bdd_pytest import expect, scenario, unit

        @unit
        def test_with_docstring():
            \"\"\"The behavior is documented without the scenario DSL.\"\"\"
            assert True

        @unit
        def test_with_scenario():
            scenario(
                \"the behavior is documented as a scenario\",
                then=(\"the invariant holds\", lambda _, __: expect(True).to_be_truthy()),
            )
        """
    )

    result = pytester.runpytest(
        "--bdd-level-policy=error", "--bdd-documentation-policy=error"
    )

    result.assert_outcomes(passed=2)
