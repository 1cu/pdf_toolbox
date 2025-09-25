"""Tests for the pytest slow-test tracking helpers defined in ``conftest``."""

from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest

import conftest
from conftest import (
    _PROP_DURATION,
    _PROP_MARKED,
    STRICT_KEY,
    THRESHOLD_KEY,
    pytest_configure,
    pytest_runtest_call,
    pytest_sessionfinish,
)


class _StubConfig:
    def __init__(self) -> None:
        self.stash = pytest.Stash()

    def getini(self, name: str) -> str:
        if name == "slow_threshold":
            return "0.5"
        if name == "fail_on_unmarked_slow":
            return "true"
        raise KeyError(name)


class _StubItem:
    def __init__(
        self, config: _StubConfig, *, markers: list[object] | None = None
    ) -> None:
        self.config = config
        self.user_properties: list[tuple[str, object]] = []
        self._markers = list(markers or [])

    def iter_markers(self, name: str | None = None):
        if name == "slow":
            return iter(self._markers)
        return iter(())


class _FailingOutcome:
    def get_result(self) -> None:
        raise RuntimeError("boom")


class _InvalidThresholdConfig(_StubConfig):
    def getini(self, name: str) -> str:
        if name == "slow_threshold":
            return "invalid"
        if name == "fail_on_unmarked_slow":
            return "false"
        return super().getini(name)


def test_pytest_configure_defaults_on_invalid_threshold() -> None:
    config = _InvalidThresholdConfig()

    pytest_configure(cast(pytest.Config, config))

    assert config.stash[THRESHOLD_KEY] == 0.75
    assert config.stash[STRICT_KEY] is False

    session = SimpleNamespace(config=config)
    pytest_sessionfinish(cast(pytest.Session, session), exitstatus=0)
    assert conftest._CONTROLLER[0] is None


def test_pytest_runtest_call_records_metadata_when_test_errors() -> None:
    config = _StubConfig()
    pytest_configure(cast(pytest.Config, config))
    config.stash[THRESHOLD_KEY] = 0.0
    config.stash[STRICT_KEY] = True
    item = _StubItem(config)

    hook = pytest_runtest_call(item=cast(pytest.Item, item))
    next(hook)

    with pytest.raises(RuntimeError):
        hook.send(_FailingOutcome())

    durations = [value for key, value in item.user_properties if key == _PROP_DURATION]
    assert durations
    assert isinstance(durations[0], float)

    marked = [value for key, value in item.user_properties if key == _PROP_MARKED]
    assert marked == [False]

    session = SimpleNamespace(config=config)
    pytest_sessionfinish(cast(pytest.Session, session), exitstatus=0)
    assert conftest._CONTROLLER[0] is None
