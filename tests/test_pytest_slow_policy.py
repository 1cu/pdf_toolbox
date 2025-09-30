from __future__ import annotations

import os
from contextlib import suppress
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

import conftest as slow_policy

pytest_plugins = ("pytester",)

_PLUGIN_PATH = Path(__file__).resolve().parents[1] / "conftest.py"


class _DummyStash(dict[pytest.StashKey[Any], Any]):
    """Lightweight stand-in for pytest's stash container."""


class DummyConfig(SimpleNamespace):
    """Simple config stub that mimics the stash interface."""

    def __init__(
        self,
        *,
        threshold: float = 0.75,
        strict: bool = True,
        items: list[tuple[str, float, bool]] | None = None,
    ) -> None:
        """Populate the stash-backed config stub with slow-policy settings."""
        stash = _DummyStash()
        stash[slow_policy.THRESHOLD_KEY] = threshold
        stash[slow_policy.STRICT_KEY] = strict
        stash[slow_policy.SLOW_ITEMS_KEY] = [
            slow_policy._SlowRecord(*entry) for entry in (items or [])
        ]
        super().__init__(stash=stash)


class DummyReporter:
    """Minimal terminal reporter stub for exercising slow-policy summaries."""

    def __init__(self, config: DummyConfig, session: SimpleNamespace) -> None:
        """Store the provided config/session and capture emitted lines."""
        self.config = config
        self._session = session
        self.lines: list[str] = []

    def section(self, title: str) -> None:
        """Record the rendered section title."""
        self.lines.append(title)

    def write_line(self, text: str) -> None:
        """Record a summary line."""
        self.lines.append(text)


def test_terminal_summary_sets_exit_status_for_unmarked() -> None:
    config = DummyConfig(items=[("pkg::test", 1.2, False)])
    session = SimpleNamespace(exitstatus=0)
    reporter = DummyReporter(config, session)

    slow_policy.pytest_terminal_summary(
        cast(pytest.TerminalReporter, reporter),
        0,
    )

    assert session.exitstatus == 1
    assert any("UNMARKED" in line for line in reporter.lines)
    assert any(line.startswith("Slow tests") for line in reporter.lines)


def test_terminal_summary_respects_non_strict_policy() -> None:
    config = DummyConfig(strict=False, items=[("pkg::test", 1.2, False)])
    session = SimpleNamespace(exitstatus=0)
    reporter = DummyReporter(config, session)

    slow_policy.pytest_terminal_summary(
        cast(pytest.TerminalReporter, reporter),
        0,
    )

    assert session.exitstatus == 0
    assert any(line.startswith("Slow tests") for line in reporter.lines)


def test_logreport_collects_slow_items() -> None:
    config = DummyConfig()
    try:
        slow_policy._CONTROLLER[0] = cast(pytest.Config, config)
        report = SimpleNamespace(
            when="call",
            nodeid="pkg::test",
            user_properties=[
                (slow_policy._PROP_DURATION, 1.1),
                (slow_policy._PROP_MARKED, True),
            ],
        )
        slow_policy.pytest_runtest_logreport(cast(pytest.TestReport, report))
    finally:
        slow_policy._CONTROLLER[0] = None

    assert config.stash[slow_policy.SLOW_ITEMS_KEY] == [
        slow_policy._SlowRecord("pkg::test", 1.1, True)
    ]


def test_runtest_call_records_user_properties(monkeypatch: pytest.MonkeyPatch) -> None:
    config = DummyConfig(threshold=0.5)
    item = SimpleNamespace(
        config=config,
        user_properties=[],
        iter_markers=lambda *_, **__: [],
    )

    class FakePerfCounter:
        def __init__(self) -> None:
            self.values = [0.0, 1.0]
            self.index = 0
            self.last = 1.0

        def __call__(self) -> float:
            if self.index < len(self.values):
                self.last = self.values[self.index]
                self.index += 1
            return self.last

    monkeypatch.setattr(slow_policy, "perf_counter", FakePerfCounter())

    generator = slow_policy.pytest_runtest_call(cast(pytest.Item, item))
    assert generator is not None
    next(generator)

    class Outcome:
        def get_result(self) -> None:
            return None

    with suppress(StopIteration):
        generator.send(Outcome())

    assert item.user_properties == [
        (slow_policy._PROP_DURATION, 1.0),
        (slow_policy._PROP_MARKED, False),
    ]


def test_sessionfinish_clears_controller() -> None:
    config = DummyConfig()
    slow_policy._CONTROLLER[0] = cast(pytest.Config, config)
    session = SimpleNamespace(config=SimpleNamespace())

    slow_policy.pytest_sessionfinish(
        cast(pytest.Session, session),
        0,
    )

    assert slow_policy._CONTROLLER[0] is None


def _activate_plugin(pytester: pytest.Pytester, ini: str) -> None:
    plugin_src = _PLUGIN_PATH.read_text(encoding="utf8").replace("\r\n", "\n")
    pytester.makeconftest(plugin_src)
    pytester.makeini("[pytest]\n" + ini)


def _run(pytester: pytest.Pytester, *args: str) -> pytest.RunResult:
    previous = os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD")
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    try:
        return pytester.runpytest_inprocess(
            "--override-ini",
            # Drop ``-q`` from ``addopts`` so pytest still renders the terminal
            # outcome summary that ``RunResult.assert_outcomes`` relies on when
            # parsing results under pytest>=8.4.
            "addopts=--durations=0 --durations-min=0.75",
            "-p",
            "no:pytestqt",
            "-p",
            "no:cov",
            *args,
        )
    finally:
        if previous is None:
            os.environ.pop("PYTEST_DISABLE_PLUGIN_AUTOLOAD", None)
        else:
            os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = previous


@pytest.mark.slow
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


@pytest.mark.slow
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


@pytest.mark.slow
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


@pytest.mark.slow
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
