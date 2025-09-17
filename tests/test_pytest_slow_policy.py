from __future__ import annotations

from pathlib import Path

import pytest

pytest_plugins = ("pytester",)

_PLUGIN_PATH = Path(__file__).resolve().parents[1] / "conftest.py"


def _activate_plugin(pytester: pytest.Pytester, ini: str) -> None:
    pytester.makeconftest(_PLUGIN_PATH.read_text(encoding="utf8"))
    pytester.makeini("[pytest]\n" + ini)


def _run(pytester: pytest.Pytester, *args: str):
    return pytester.runpytest("-p", "no:cov", *args)


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
    result = _run(pytester)
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
    result = _run(pytester)
    result.assert_outcomes(passed=1)
    assert result.ret == 0
    result.stdout.no_fnmatch_line("*UNMARKED*")


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
    result = _run(pytester)
    result.assert_outcomes(passed=1)
    assert result.ret == 0


def test_slow_policy_reports_without_failing_when_disabled(
    pytester: pytest.Pytester,
) -> None:
    _activate_plugin(
        pytester,
        "slow_threshold = 0.0\nfail_on_unmarked_slow = false\n",
    )
    pytester.makepyfile(
        """
        def test_unmarked():
            pass
        """
    )
    result = _run(pytester)
    result.assert_outcomes(passed=1)
    assert result.ret == 0
    result.stdout.fnmatch_lines(["*UNMARKED*test_unmarked*"])
