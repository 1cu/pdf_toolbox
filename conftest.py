"""Minimal pytest slow-test policy configured via ``pyproject.toml``."""

from __future__ import annotations

from numbers import Real
from time import perf_counter

import pytest

_PROP_DURATION = "duration"
_PROP_MARKED = "is_marked_slow"
_CONTROLLER: list[pytest.Config | None] = [None]


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
    config._slow_items = []  # type: ignore[attr-defined]
    try:
        threshold = float(config.getini("slow_threshold"))
    except Exception:
        threshold = 0.75
    config._slow_threshold = threshold  # type: ignore[attr-defined]
    config._fail_on_unmarked_slow = _as_bool(  # type: ignore[attr-defined]
        config.getini("fail_on_unmarked_slow")
    )
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
        threshold = getattr(item.config, "_slow_threshold", 0.75)
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

    threshold = getattr(controller, "_slow_threshold", 0.75)
    if duration is None or duration < threshold:
        return

    slow_items = getattr(controller, "_slow_items", [])
    slow_items.append((report.nodeid, duration, is_marked))


def pytest_terminal_summary(
    terminalreporter: pytest.TerminalReporter, exitstatus: int
) -> None:
    """Render the slow-test summary and enforce the policy."""
    del exitstatus
    config = terminalreporter.config
    slow_items = getattr(config, "_slow_items", [])
    if not slow_items:
        return

    threshold = getattr(config, "_slow_threshold", 0.75)
    terminalreporter.section(f"Slow tests (>= {threshold:.2f}s)")
    for nodeid, duration, is_marked in sorted(
        slow_items, key=lambda entry: entry[1], reverse=True
    ):
        tag = "slow" if is_marked else "UNMARKED"
        terminalreporter.write_line(f"{duration:6.2f}s  {tag:9}  {nodeid}")

    if getattr(config, "_fail_on_unmarked_slow", True) and any(
        not marked for _, _, marked in slow_items
    ):
        terminalreporter.write_line(
            f"\nUnmarked slow tests detected (>= {threshold:.2f}s). "
            "Mark with @pytest.mark.slow or speed them up."
        )
        session = getattr(terminalreporter, "_session", None)
        if session is not None:
            session.exitstatus = 1


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Clear controller reference after the session ends."""
    del exitstatus
    if hasattr(session.config, "workerinput"):
        return
    _CONTROLLER[0] = None
