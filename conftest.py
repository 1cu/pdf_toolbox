"""Pytest slow-test policy configured via ``pyproject.toml`` only."""

from __future__ import annotations

from collections.abc import Iterable
from time import perf_counter
from typing import Any

import pytest

_PROP_DURATION = "slow_policy_duration"
_PROP_MARKED = "slow_policy_is_marked"
_SLOW_ITEMS_KEY: pytest.StashKey[list[tuple[str, float, bool]]] = pytest.StashKey()
_THRESHOLD_KEY: pytest.StashKey[float] = pytest.StashKey()
_STRICT_KEY: pytest.StashKey[bool] = pytest.StashKey()
_CONTROLLER: list[pytest.Config | None] = [None]


def _as_bool(s: str) -> bool:
    """Return ``True`` when *s* is any common truthy string."""
    return str(s).strip().lower() in {"1", "true", "yes", "on"}


def _get_user_property(
    properties: Iterable[tuple[str, object]], key: str, default: Any | None = None
) -> Any | None:
    """Return the value stored under ``key`` in ``user_properties``."""
    for name, value in properties:
        if name == key:
            return value
    return default


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register slow-policy ini options."""
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
    """Initialise session-level slow-policy tracking on *config*."""
    slow_items: list[tuple[str, float, bool]] = []
    config.stash[_SLOW_ITEMS_KEY] = slow_items
    config._slow_items = slow_items  # type: ignore[attr-defined]  # pdf-toolbox: expose legacy attribute for pytest <8 plugins | issue:-
    try:
        threshold = float(config.getini("slow_threshold"))
    except Exception:
        threshold = 0.75
    config.stash[_THRESHOLD_KEY] = threshold
    config._slow_threshold = threshold  # type: ignore[attr-defined]  # pdf-toolbox: mirror legacy attribute for reporting hooks | issue:-
    strict = _as_bool(config.getini("fail_on_unmarked_slow"))
    config.stash[_STRICT_KEY] = strict
    config._fail_on_unmarked_slow = strict  # type: ignore[attr-defined]  # pdf-toolbox: maintain compatibility with existing tooling | issue:-
    if not hasattr(config, "workerinput"):
        _CONTROLLER[0] = config


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item: pytest.Item):
    """Measure call duration and flag slow markers on *item*."""
    start = perf_counter()
    outcome = yield
    duration = perf_counter() - start
    error: BaseException | None = None
    try:
        outcome.get_result()
    except BaseException as exc:  # pragma: no cover - handled by re-raise
        error = exc
    finally:
        threshold = item.config.stash.get(_THRESHOLD_KEY, 0.75)
        if duration >= threshold:
            is_marked = any(marker.name == "slow" for marker in item.iter_markers())
            item.user_properties.append((_PROP_DURATION, duration))
            item.user_properties.append((_PROP_MARKED, is_marked))
    if error is not None:
        raise error


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """Collect slow items from worker reports and aggregate them on the controller."""
    if report.when != "call":
        return
    config = _CONTROLLER[0]
    if config is None:
        return

    duration = _get_user_property(report.user_properties, _PROP_DURATION)
    try:
        recorded = float(duration)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return

    threshold = config.stash.get(_THRESHOLD_KEY, 0.75)
    if recorded < threshold:
        return

    is_marked = bool(_get_user_property(report.user_properties, _PROP_MARKED, False))
    config.stash[_SLOW_ITEMS_KEY].append((report.nodeid, recorded, is_marked))


def pytest_terminal_summary(
    terminalreporter: pytest.TerminalReporter, exitstatus: int
) -> None:
    """Render the slow-test summary and enforce the unmarked-slow policy."""
    del exitstatus
    config = terminalreporter.config
    slow_items = config.stash.get(_SLOW_ITEMS_KEY, [])
    if not slow_items:
        return

    threshold = config.stash.get(_THRESHOLD_KEY, 0.75)
    terminalreporter.section(f"Slow tests (>= {threshold:.2f}s)")
    for nodeid, duration, is_marked in sorted(
        slow_items, key=lambda entry: entry[1], reverse=True
    ):
        tag = "slow" if is_marked else "UNMARKED"
        terminalreporter.write_line(f"{duration:6.2f}s  {tag:9}  {nodeid}")

    strict = config.stash.get(_STRICT_KEY, True)
    if strict and any(not marked for _, _, marked in slow_items):
        terminalreporter.write_line(
            f"\nUnmarked slow tests detected (>= {threshold:.2f}s). "
            "Mark with @pytest.mark.slow or speed them up."
        )
        session = getattr(terminalreporter, "_session", None)
        if session is not None:
            session.exitstatus = 1


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Clear controller references once the session has ended."""
    del exitstatus
    if hasattr(session.config, "workerinput"):
        return
    _CONTROLLER[0] = None
