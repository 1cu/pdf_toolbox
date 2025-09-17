"""Pytest slow-test policy hooks configured via ``pyproject.toml``."""

from __future__ import annotations

from collections.abc import Iterable
from time import perf_counter
from typing import Any

import pytest

_STATE: dict[str, pytest.Config | None] = {"controller": None}


def _as_bool(s: str) -> bool:
    """Return ``True`` for common truthy strings."""
    return str(s).strip().lower() in {"1", "true", "yes", "on"}


def _get_user_property(
    properties: Iterable[tuple[str, object]], key: str, default: Any | None = None
) -> Any | None:
    """Retrieve *key* from pytest ``user_properties`` tuples."""
    for name, value in properties:
        if name == key:
            return value
    return default


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register slow-policy configuration options."""
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
    """Initialise slow-policy attributes on the active config."""
    config._slow_items = []  # type: ignore[attr-defined]
    try:
        config._slow_threshold = float(config.getini("slow_threshold"))  # type: ignore[attr-defined]
    except Exception:
        config._slow_threshold = 0.75  # type: ignore[attr-defined]
    config._fail_on_unmarked_slow = _as_bool(  # type: ignore[attr-defined]
        config.getini("fail_on_unmarked_slow")
    )

    if not hasattr(config, "workerinput"):
        _STATE["controller"] = config


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item: pytest.Item):
    """Record call duration and mark state on the test item."""
    start = perf_counter()
    outcome = yield
    duration = perf_counter() - start
    outcome.get_result()

    is_marked = any(marker.name == "slow" for marker in item.iter_markers())
    item.user_properties.append(("duration", duration))
    item.user_properties.append(("is_marked_slow", is_marked))


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """Collect slow-call metadata from worker reports."""
    if report.when != "call":
        return

    config = _STATE["controller"]
    if config is None:
        return

    threshold = getattr(config, "_slow_threshold", 0.75)
    duration = _get_user_property(report.user_properties, "duration")
    try:
        recorded = float(duration)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return
    if recorded < threshold:
        return

    is_marked = bool(
        _get_user_property(report.user_properties, "is_marked_slow", False)
    )
    config._slow_items.append((report.nodeid, recorded, is_marked))  # type: ignore[attr-defined]


def pytest_terminal_summary(
    terminalreporter: pytest.TerminalReporter, exitstatus: int
) -> None:
    """Render the slow-test summary and fail on unmarked slow tests."""
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
    """Reset controller state after the session completes."""
    del exitstatus
    if hasattr(session.config, "workerinput"):
        return
    _STATE["controller"] = None
