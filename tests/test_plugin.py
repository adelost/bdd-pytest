"""Integration tests for the enforceable pytest contracts."""

from __future__ import annotations

import json
from xml.etree import ElementTree

import pytest

from bdd_pytest import BDD_RUN_SCHEMA_VERSION, component

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
def test_bdd_run_report_is_portable_and_versioned(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
):
    pytester.makepyfile(
        test_catalog="""
        import pytest
        from bdd_pytest import expect, scenario, unit, component

        @unit
        def test_applies_discount_over_500kr():
            scenario(
                "applies discount over 500kr",
                given=("a cart totaling 600kr", lambda: 600),
                when=("applying a ten percent discount", lambda total: total * 0.9),
                then=("the total is 540kr", lambda result, _: expect(result).to_be(540)),
            )

        @component
        @pytest.mark.skip(reason="sandbox unavailable")
        def test_documents_an_unavailable_payment_service():
            \"\"\"The unavailable payment service remains documented.\"\"\"
        """
    )
    output_file = pytester.path / "run.json"
    monkeypatch.setenv("BDD_REPORT_PROJECT", "checkout")
    monkeypatch.setenv("BDD_REPORT_REPOSITORY", "adelost/checkout")
    monkeypatch.setenv("BDD_REPORT_COMMIT_SHA", "0123456789abcdef")
    monkeypatch.setenv("BDD_REPORT_BRANCH", "main")

    result = pytester.runpytest(f"--bdd-report-json={output_file}")

    result.assert_outcomes(passed=1, skipped=1)
    report = json.loads(output_file.read_text())
    assert report["schemaVersion"] == BDD_RUN_SCHEMA_VERSION == "bdd.run.v1"
    assert report["run"] | {"frameworkVersion": "ignored"} == {
        "framework": "pytest",
        "frameworkVersion": "ignored",
        "project": "checkout",
        "repository": "adelost/checkout",
        "commitSha": "0123456789abcdef",
        "branch": "main",
        "startedAt": report["run"]["startedAt"],
        "finishedAt": report["run"]["finishedAt"],
        "durationMs": report["run"]["durationMs"],
        "status": "passed",
    }
    assert report["summary"] == {
        "total": 2,
        "passed": 1,
        "failed": 0,
        "skipped": 1,
        "pending": 0,
    }
    semantics = [
        (test["level"], test["documentation"], test["status"])
        for test in report["tests"]
    ]
    assert semantics == [
        ("unit", "scenario", "passed"),
        ("component", "docstring", "skipped"),
    ]
    assert all(test["file"] == "test_catalog.py" for test in report["tests"])
    assert all(test["id"].startswith("sha256:") for test in report["tests"])
    assert report["tests"][0]["scenarios"] == [
        {
            "documented": True,
            "name": "applies discount over 500kr",
            "phases": {
                "given": "a cart totaling 600kr",
                "when": "applying a ten percent discount",
                "then": "the total is 540kr",
            },
        }
    ]


@component
def test_bdd_run_report_records_failure_without_diagnostics(pytester: pytest.Pytester):
    pytester.makepyfile(
        test_failure="""
        from bdd_pytest import unit

        @unit
        def test_failed_behavior():
            \"\"\"The failed behavior remains documented.\"\"\"
            raise AssertionError("SENSITIVE_FAILURE_DETAIL")
        """
    )
    output_file = pytester.path / "failed-run.json"

    result = pytester.runpytest(f"--bdd-report-json={output_file}")

    result.assert_outcomes(failed=1)
    raw_report = output_file.read_text()
    report = json.loads(raw_report)
    assert report["run"]["status"] == "failed"
    assert report["summary"] == {
        "total": 1,
        "passed": 0,
        "failed": 1,
        "skipped": 0,
        "pending": 0,
    }
    assert report["tests"][0]["status"] == "failed"
    assert "SENSITIVE_FAILURE_DETAIL" not in raw_report


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
