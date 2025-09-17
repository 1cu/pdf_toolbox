from __future__ import annotations

import importlib.util
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

pytest_plugins = ("pytester",)

_PLUGIN_PATH = Path(__file__).resolve().parents[1] / "conftest.py"


def _load_plugin():
    module_name = f"_slow_policy_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, _PLUGIN_PATH)
    if spec is None or spec.loader is None:
        pytest.fail("Could not load slow policy plugin")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _activate_plugin(pytester: pytest.Pytester, ini: str) -> None:
    pytester.makeconftest(_PLUGIN_PATH.read_text())
    pytester.makeini("[pytest]\n" + ini)


def test_slow_policy_flags_unmarked(pytester: pytest.Pytester) -> None:
    _activate_plugin(
        pytester,
        "slow_threshold = 0.0\nfail_on_unmarked_slow = true\n",
    )
    pytester.makepyfile(
        """
        def test_unmarked():
            pass
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)
    assert result.ret == 1
    result.stdout.fnmatch_lines(
        [
            "*Slow tests (>= 0.00s)*",
            "*UNMARKED*test_unmarked*",
            "*Unmarked slow tests detected (>= 0.00s).*",
        ]
    )


def test_slow_policy_allows_marked(pytester: pytest.Pytester) -> None:
    _activate_plugin(
        pytester,
        "slow_threshold = 0.0\nfail_on_unmarked_slow = true\n",
    )
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.slow
        def test_marked():
            pass
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)
    assert result.ret == 0
    result.stdout.fnmatch_lines(["*test_marked*"])


def test_slow_policy_tolerates_invalid_threshold(pytester: pytest.Pytester) -> None:
    _activate_plugin(
        pytester,
        "slow_threshold = not-a-number\nfail_on_unmarked_slow = off\n",
    )
    pytester.makepyfile(
        """
        def test_fast():
            pass
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)
    assert result.ret == 0


def test_get_property_returns_default() -> None:
    plugin = _load_plugin()
    assert plugin._get_property([], "missing", "sentinel") == "sentinel"


def test_logreport_ignores_missing_duration() -> None:
    plugin = _load_plugin()
    plugin._STATE["controller_config"] = SimpleNamespace(
        _slow_items=[],
        _slow_threshold=0.75,
    )

    report = SimpleNamespace(
        when="call",
        user_properties=[],
        nodeid="pkg/test.py::test_case",
        duration=None,
    )

    plugin.pytest_runtest_logreport(cast(pytest.TestReport, report))
    controller = cast(SimpleNamespace, plugin._STATE["controller_config"])
    assert controller._slow_items == []


def test_logreport_skips_non_numeric_duration() -> None:
    plugin = _load_plugin()
    plugin._STATE["controller_config"] = SimpleNamespace(
        _slow_items=[],
        _slow_threshold=0.1,
    )

    report = SimpleNamespace(
        when="call",
        user_properties=[("duration", object())],
        nodeid="pkg/test.py::test_case",
        duration=None,
    )

    plugin.pytest_runtest_logreport(cast(pytest.TestReport, report))
    controller = cast(SimpleNamespace, plugin._STATE["controller_config"])
    assert controller._slow_items == []
