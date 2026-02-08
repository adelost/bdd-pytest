"""Tests for the pytest plugin (missing level marker warning)."""

import warnings

from bdd_pytest import unit
from bdd_pytest.plugin import LEVELS, pytest_collection_modifyitems


class FakeItem:
    """Minimal pytest item stub for testing the plugin hook."""

    def __init__(self, nodeid: str, markers: set[str] | None = None):
        self.nodeid = nodeid
        self._markers = markers or set()

    def get_closest_marker(self, name: str):
        return name if name in self._markers else None


@unit
def test_warning_for_missing_level():
    items = [FakeItem("tests/test_foo.py::test_bar")]
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        pytest_collection_modifyitems(items)
    assert len(w) == 1
    assert "no level marker" in str(w[0].message)
    assert "test_bar" in str(w[0].message)


@unit
def test_no_warning_when_level_present():
    items = [FakeItem("tests/test_foo.py::test_bar", markers={"unit"})]
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        pytest_collection_modifyitems(items)
    assert len(w) == 0


@unit
def test_no_warning_for_any_level():
    for level in LEVELS:
        items = [FakeItem(f"test::{level}_test", markers={level})]
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            pytest_collection_modifyitems(items)
        assert len(w) == 0, f"Unexpected warning for level {level}"
