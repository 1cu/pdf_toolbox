"""Pytest slow-test policy hooks configured via ``pyproject.toml``."""

from __future__ import annotations

from collections.abc import Iterable
from time import perf_counter
from typing import Any, cast

import pytest

_STATE: dict[str, object] = {"config": None, "collect_via_logreport": False}


def _as_bool(value: str) -> bool:
    """Return ``True`` when a string matches a truthy toggle."""
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _get_property(
    properties: Iterable[tuple[str, object]],
    key: str,
    default: Any | None = None,
) -> Any | None:
    """Look up a key in ``pytest`` user properties."""
    for name, val in properties:
        if name == key:
            return val
    return default


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register ini options for the slow-test policy."""
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
    """Cache policy settings and prepare slow-item bookkeeping."""
    try:
        threshold = float(config.getini("slow_threshold"))
    except Exception:
        threshold = 0.75
    fail_policy = _as_bool(config.getini("fail_on_unmarked_slow"))
    option = getattr(config, "option", None)
    num_processes = getattr(option, "numprocesses", 0)
    collect_via_logreport = bool(num_processes)

    config_state = cast(Any, config)
    config_state._slow_items = []
    config_state._slow_threshold = threshold
    config_state._fail_on_unmarked_slow = fail_policy
    config_state._collect_via_logreport = collect_via_logreport

    if not hasattr(config, "workerinput"):
        _STATE["config"] = config
        _STATE["collect_via_logreport"] = collect_via_logreport


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item: pytest.Item):
    """Measure each test call and record slow entries for the main process."""
    start = perf_counter()
    outcome = yield
    duration = perf_counter() - start
    outcome.get_result()

    is_marked = any(marker.name == "slow" for marker in item.iter_markers())
    item.user_properties.append(("duration", duration))
    item.user_properties.append(("is_marked_slow", is_marked))

    threshold = getattr(item.config, "_slow_threshold", 0.75)
    if duration >= threshold and not getattr(
        item.config, "_collect_via_logreport", False
    ):
        slow_items = getattr(item.config, "_slow_items", None)
        if slow_items is not None:
            slow_items.append((item.nodeid, duration, is_marked))


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """Collect slow entries when xdist workers report back to the controller."""
    if report.when != "call":
        return

    if not bool(_STATE.get("collect_via_logreport", False)):
        return

    config = _STATE.get("config")
    if config is None:
        return

    config_state = cast(Any, config)
    threshold = getattr(config_state, "_slow_threshold", 0.75)
    duration = _get_property(
        report.user_properties, "duration", getattr(report, "duration", None)
    )
    if duration is None:
        return

    try:
        recorded = float(duration)
    except (TypeError, ValueError):
        return

    if recorded < threshold:
        return

    is_marked = bool(_get_property(report.user_properties, "is_marked_slow", False))
    slow_items = getattr(config_state, "_slow_items", None)
    if slow_items is not None:
        slow_items.append((report.nodeid, recorded, is_marked))


def pytest_terminal_summary(
    terminalreporter: pytest.TerminalReporter, exitstatus: int
) -> None:
    """Display slow tests and fail the session when policy rules are violated."""
    del exitstatus
    slow_items = getattr(terminalreporter.config, "_slow_items", [])
    if not slow_items:
        return

    threshold = getattr(terminalreporter.config, "_slow_threshold", 0.75)
    terminalreporter.section(f"Slow tests (>= {threshold:.2f}s)")
    for nodeid, duration, is_marked in sorted(
        slow_items, key=lambda entry: entry[1], reverse=True
    ):
        tag = "slow" if is_marked else "UNMARKED"
        terminalreporter.write_line(f"{duration:6.2f}s  {tag:9}  {nodeid}")

    strict = getattr(terminalreporter.config, "_fail_on_unmarked_slow", True)
    if strict and any(not marked for _, _, marked in slow_items):
        terminalreporter.write_line(
            f"\nUnmarked slow tests detected (>= {threshold:.2f}s). "
            "Mark with @pytest.mark.slow or speed them up."
        )
        session = getattr(terminalreporter, "_session", None)
        if session is not None:
            session.exitstatus = 1
