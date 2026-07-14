"""Integration tests for the enforceable pytest contracts."""

from __future__ import annotations

import json
from xml.etree import ElementTree

import pytest

from bdd_pytest import component

pytest_plugins = ["pytester"]


@component
def test_level_contract_rejects_missing_marker(pytester: pytest.Pytester):
    pytester.makepyfile("def test_unclassified():\n    pass")

    result = pytester.runpytest("--bdd-level-policy=error")

    result.stderr.fnmatch_lines(
        ["*bdd-pytest level contract failed:*", "*test_unclassified: no level marker*"]
    )
    assert result.ret == pytest.ExitCode.USAGE_ERROR


@component
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


@component
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


@component
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


@component
def test_level_contract_ignores_deselected_items(pytester: pytest.Pytester):
    pytester.makeini("[pytest]\nmarkers = slow: deselected in this test")
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.unit
        def test_selected():
            pass

        @pytest.mark.slow
        def test_unclassified_but_deselected():
            pass
        """
    )

    result = pytester.runpytest("-m", "not slow", "--bdd-level-policy=error")

    result.assert_outcomes(passed=1, deselected=1)


@component
def test_junit_report_contains_machine_readable_bdd_metadata(pytester: pytest.Pytester):
    pytester.makepyfile(
        """
        from bdd_pytest import scenario, unit

        @unit
        def test_documented_behavior():
            scenario(
                "documents behavior",
                given="a known precondition",
                when=("the action runs", lambda _: 42),
                then=("the result is correct", lambda result, _: assert_result(result)),
            )

        def assert_result(result):
            assert result == 42
        """
    )

    report = pytester.path / "report.xml"
    result = pytester.runpytest(
        "--bdd-level-policy=error",
        "--bdd-documentation-policy=error",
        f"--junitxml={report}",
    )

    result.assert_outcomes(passed=1)
    properties = {
        element.attrib["name"]: element.attrib["value"]
        for element in ElementTree.parse(report).findall(".//property")
    }
    assert properties["bdd.level"] == "unit"
    assert properties["bdd.documentation"] == "scenario"
    scenarios = json.loads(properties["bdd.scenarios"])
    assert scenarios == [
        {
            "documented": True,
            "name": "documents behavior",
            "phases": {
                "given": "a known precondition",
                "then": "the result is correct",
                "when": "the action runs",
            },
        }
    ]


@component
def test_documentation_contract_requires_described_outline_phases(pytester: pytest.Pytester):
    pytester.makepyfile(
        """
        from bdd_pytest import scenario_outline, unit

        ROWS = [{"name": "one", "value": 1}]

        @unit
        def test_legacy_outline():
            scenario_outline(
                "legacy",
                ROWS,
                then=lambda result, ctx, row: None,
            )

        @unit
        def test_documented_outline():
            scenario_outline(
                "documented",
                ROWS,
                then=("the value is valid", lambda result, ctx, row: None),
            )
        """
    )

    result = pytester.runpytest(
        "--bdd-level-policy=error", "--bdd-documentation-policy=error"
    )

    result.assert_outcomes(passed=1, failed=1)
    result.stdout.fnmatch_lines(["*test_legacy_outline: documentation contract failed*"])
