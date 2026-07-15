"""Portable ``bdd.run.v1`` report emitter for the pytest plugin."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import pytest

BDD_RUN_SCHEMA_VERSION = "bdd.run.v1"
Status = Literal["passed", "failed", "skipped", "pending"]


def _optional_text(value: str | None) -> str | None:
    normalized = value.strip() if value else ""
    return normalized or None


def _iso_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat().replace("+00:00", "Z")


def _test_id(file: str, full_name: str) -> str:
    normalized_file = unicodedata.normalize("NFC", file)
    normalized_name = unicodedata.normalize("NFC", full_name)
    identity = f"pytest\0{normalized_file}\0{normalized_name}"
    return f"sha256:{hashlib.sha256(identity.encode()).hexdigest()}"


@dataclass
class TestRecord:
    """Mutable accumulator projected into an immutable report record at write time."""

    id: str
    name: str
    full_name: str
    file: str
    line: int | None
    level: str | None
    documentation: str
    scenarios: list[dict[str, Any]] = field(default_factory=list)
    status: Status = "pending"
    duration_ms: float = 0
    retry_count: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "fullName": self.full_name,
            "file": self.file,
            "line": self.line,
            "level": self.level,
            "documentation": self.documentation,
            "scenarios": self.scenarios,
            "status": self.status,
            "durationMs": self.duration_ms,
            "retryCount": self.retry_count,
            "flaky": self.retry_count > 0 and self.status == "passed",
        }


class BddRunReporter:
    """Accumulate pytest lifecycle events and atomically emit one portable run."""

    def __init__(self, config: pytest.Config, output_file: Path):
        self.config = config
        self.output_file = output_file
        self.root = config.rootpath.resolve()
        self.started_at = time.time()
        self.records: dict[str, TestRecord] = {}

    def _portable_file(self, item: pytest.Item) -> str:
        path = Path(str(item.path)).resolve()
        try:
            portable = path.relative_to(self.root).as_posix()
        except ValueError:
            # Never expose an absolute local path when a plugin supplies an item
            # from outside the configured repository root.
            portable = path.name
        return portable

    def _ensure_item(self, item: pytest.Item) -> TestRecord:
        current = self.records.get(item.nodeid)
        if current is not None:
            return current
        file = self._portable_file(item)
        node_parts = item.nodeid.split("::")
        full_name = "::".join([file, *node_parts[1:]])
        levels = [
            level
            for level in ("unit", "component", "integration", "e2e")
            if item.get_closest_marker(level)
        ]
        documentation = "docstring" if _item_has_docstring(item) else "missing"
        line = item.location[1] + 1 if item.location and item.location[1] >= 0 else None
        record = TestRecord(
            id=_test_id(file, full_name),
            name=item.name,
            full_name=full_name,
            file=file,
            line=line,
            level=levels[0] if len(levels) == 1 else None,
            documentation=documentation,
        )
        self.records[item.nodeid] = record
        return record

    def pytest_collection_finish(self, session: pytest.Session) -> None:
        for item in session.items:
            self._ensure_item(item)

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        record = self.records.get(report.nodeid)
        if record is None:
            # Collection normally creates every record. A defensive fallback
            # keeps third-party dynamically-created items visible without paths.
            file = report.nodeid.split("::", 1)[0].replace(os.sep, "/").replace("\\", "/")
            if (
                file == ".."
                or file.startswith(("/", "../"))
                or re.match(r"^[A-Za-z]:/", file)
            ):
                file = file.rsplit("/", 1)[-1]
            name = report.nodeid.rsplit("::", 1)[-1]
            node_parts = report.nodeid.split("::")
            full_name = "::".join([file, *node_parts[1:]])
            record = TestRecord(
                id=_test_id(file, full_name),
                name=name,
                full_name=full_name,
                file=file,
                line=None,
                level=None,
                documentation="missing",
            )
            self.records[report.nodeid] = record

        record.duration_ms += max(0.0, float(report.duration) * 1000)
        rerun = getattr(report, "rerun", 0)
        if isinstance(rerun, int) and rerun > record.retry_count:
            record.retry_count = rerun

        properties = dict(report.user_properties)
        level = properties.get("bdd.level")
        if isinstance(level, str) and level in {"unit", "component", "integration", "e2e"}:
            record.level = level
        documentation = properties.get("bdd.documentation")
        if documentation in {"scenario", "docstring", "missing"}:
            record.documentation = documentation
        scenarios = properties.get("bdd.scenarios")
        if isinstance(scenarios, str):
            decoded = json.loads(scenarios)
            if isinstance(decoded, list):
                record.scenarios = decoded

        if report.failed:
            record.status = "failed"
        elif report.skipped and record.status != "failed":
            record.status = "skipped"
        elif report.when == "call" and report.passed and record.status == "pending":
            record.status = "passed"

    @pytest.hookimpl(trylast=True)
    def pytest_sessionfinish(
        self, session: pytest.Session, exitstatus: int | pytest.ExitCode
    ) -> None:
        finished_at = time.time()
        records = sorted(self.records.values(), key=lambda record: (record.file, record.full_name))
        counts = {
            status: sum(record.status == status for record in records)
            for status in ("passed", "failed", "skipped", "pending")
        }
        interrupted = int(exitstatus) == int(pytest.ExitCode.INTERRUPTED)
        failed = counts["failed"] > 0 or int(exitstatus) not in {
            int(pytest.ExitCode.OK),
            int(pytest.ExitCode.NO_TESTS_COLLECTED),
        }
        report = {
            "schemaVersion": BDD_RUN_SCHEMA_VERSION,
            "run": {
                "framework": "pytest",
                "frameworkVersion": pytest.__version__,
                "project": _optional_text(os.getenv("BDD_REPORT_PROJECT")),
                "repository": _optional_text(os.getenv("BDD_REPORT_REPOSITORY")),
                "commitSha": _optional_text(
                    os.getenv("BDD_REPORT_COMMIT_SHA") or os.getenv("GITHUB_SHA")
                ),
                "branch": _optional_text(
                    os.getenv("BDD_REPORT_BRANCH")
                    or os.getenv("GITHUB_HEAD_REF")
                    or os.getenv("GITHUB_REF_NAME")
                ),
                "startedAt": _iso_timestamp(self.started_at),
                "finishedAt": _iso_timestamp(finished_at),
                "durationMs": max(0.0, (finished_at - self.started_at) * 1000),
                "status": "interrupted" if interrupted else "failed" if failed else "passed",
            },
            "summary": {"total": len(records), **counts},
            "tests": [record.as_dict() for record in records],
        }
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.output_file.with_name(f"{self.output_file.name}.tmp-{os.getpid()}")
        temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, self.output_file)


def _item_has_docstring(item: pytest.Item) -> bool:
    obj = getattr(item, "obj", None)
    return bool(obj and getattr(obj, "__doc__", None) and obj.__doc__.strip())
