"""Pytest slow-test policy hooks configured via ``pyproject.toml``."""

from __future__ import annotations

from collections.abc import Iterable
from time import perf_counter
from typing import Any, cast

import pytest

_CONTROLLER_CONFIG: pytest.Config | None = None


def _as_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _get_property(
    properties: Iterable[tuple[str, object]],
    key: str,
    default: Any | None = None,
) -> Any | None:
    for name, val in properties:
        if name == key:
            return val
    return default


def pytest_addoption(parser: pytest.Parser) -> None:
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
    try:
        threshold = float(config.getini("slow_threshold"))
    except (TypeError, ValueError):
        threshold = 0.75
    fail_policy = _as_bool(config.getini("fail_on_unmarked_slow"))

    config_state = cast(Any, config)
    config_state._slow_items = []
    config_state._slow_threshold = threshold
    config_state._fail_on_unmarked_slow = fail_policy

    if not hasattr(config, "workerinput"):
        global _CONTROLLER_CONFIG
        _CONTROLLER_CONFIG = config


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item: pytest.Item):
    start = perf_counter()
    outcome = yield
    duration = perf_counter() - start
    outcome.get_result()

    is_marked = any(marker.name == "slow" for marker in item.iter_markers())
    item.user_properties.append(("duration", duration))
    item.user_properties.append(("is_marked_slow", is_marked))


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    if report.when != "call":
        return

    config: pytest.Config | None = _CONTROLLER_CONFIG
    if config is None:
        session = getattr(report, "session", None)
        config = getattr(session, "config", None)
    if config is None:
        return

    config_state = cast(Any, config)
    threshold = getattr(config_state, "_slow_threshold", 0.75)
    duration = _get_property(
        report.user_properties, "duration", getattr(report, "duration", None)
    )
    try:
        recorded = float(duration)  # type: ignore[arg-type]
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


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    del exitstatus
    if hasattr(session.config, "workerinput"):
        return
    global _CONTROLLER_CONFIG
    _CONTROLLER_CONFIG = None
