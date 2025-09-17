"""Minimal pytest slow-test policy configured via ``pyproject.toml``."""

from __future__ import annotations

from numbers import Real
from time import perf_counter
from typing import NamedTuple

import pytest

_PROP_DURATION = "duration"
_PROP_MARKED = "is_marked_slow"

SLOW_ITEMS_KEY: pytest.StashKey[list[_SlowRecord]] = pytest.StashKey()
THRESHOLD_KEY: pytest.StashKey[float] = pytest.StashKey()
STRICT_KEY: pytest.StashKey[bool] = pytest.StashKey()
_CONTROLLER: list[pytest.Config | None] = [None]


class _SlowRecord(NamedTuple):
    nodeid: str
    duration: float
    is_marked: bool


def _as_bool(value: str) -> bool:
    """Interpret ``value`` using common truthy tokens."""
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def pytest_addoption(parser: pytest.Parser) -> None:
    """Expose slow-policy ini options for configuration."""
    parser.addini(
        "slow_threshold",
        "Seconds from which a test is considered slow (float as string).",
        default="0.75",
    )
    parser.addini(
        "fail_on_unmarked_slow",
        "If true, session fails when tests over threshold lack @pytest.mark.slow.",
        default="true",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Initialise slow-test tracking on *config*."""
    config.stash[SLOW_ITEMS_KEY] = []
    try:
        threshold = float(config.getini("slow_threshold"))
    except Exception:
        threshold = 0.75
    config.stash[THRESHOLD_KEY] = threshold
    config.stash[STRICT_KEY] = _as_bool(config.getini("fail_on_unmarked_slow"))
    if not hasattr(config, "workerinput"):
        _CONTROLLER[0] = config


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item: pytest.Item):
    """Record call duration and marker metadata for *item*."""
    start = perf_counter()
    outcome = yield
    duration = perf_counter() - start
    error: Exception | None = None
    try:
        outcome.get_result()
    except Exception as exc:  # pragma: no cover  # pdf-toolbox: preserve test failures while recording duration | issue:-
        error = exc
    finally:
        item.user_properties.append((_PROP_DURATION, duration))
        threshold = item.config.stash.get(THRESHOLD_KEY, 0.75)
        if duration >= threshold:
            is_marked = any(True for _ in item.iter_markers(name="slow"))
            item.user_properties.append((_PROP_MARKED, is_marked))
    if error is not None:
        raise error


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """Aggregate slow items on the controller config."""
    if report.when != "call":
        return
    controller = _CONTROLLER[0]
    if controller is None:
        return

    duration: float | None = None
    is_marked = False
    for key, value in report.user_properties:
        if key == _PROP_DURATION:
            if isinstance(value, Real):
                duration = float(value)
            elif isinstance(value, str):
                try:
                    duration = float(value)
                except ValueError:
                    duration = None
            else:
                duration = None
        elif key == _PROP_MARKED:
            is_marked = bool(value)

    threshold = controller.stash.get(THRESHOLD_KEY, 0.75)
    if duration is None or duration < threshold:
        return

    records = controller.stash.get(SLOW_ITEMS_KEY, None)
    if records is None:
        records = []
        controller.stash[SLOW_ITEMS_KEY] = records
    records.append(_SlowRecord(report.nodeid, duration, is_marked))


def pytest_terminal_summary(
    terminalreporter: pytest.TerminalReporter, exitstatus: int
) -> None:
    """Render the slow-test summary and enforce the policy."""
    del exitstatus
    config = terminalreporter.config
    slow_items = config.stash.get(SLOW_ITEMS_KEY, [])
    if not slow_items:
        return

    threshold = config.stash.get(THRESHOLD_KEY, 0.75)
    terminalreporter.section(f"Slow tests (>= {threshold:.2f}s)")
    for record in sorted(slow_items, key=lambda entry: entry.duration, reverse=True):
        tag = "slow" if record.is_marked else "UNMARKED"
        terminalreporter.write_line(
            f"{record.duration:6.2f}s  {tag:9}  {record.nodeid}"
        )

    if config.stash.get(STRICT_KEY, True) and any(
        not record.is_marked for record in slow_items
    ):
        terminalreporter.write_line(
            f"\nUnmarked slow tests detected (>= {threshold:.2f}s). "
            "Mark with @pytest.mark.slow or speed them up."
        )
        session = getattr(terminalreporter, "_session", None)
        if session is not None:
            session.exitstatus = pytest.ExitCode.TESTS_FAILED


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Clear controller reference after the session ends."""
    del exitstatus
    if hasattr(session.config, "workerinput"):
        return
    _CONTROLLER[0] = None
