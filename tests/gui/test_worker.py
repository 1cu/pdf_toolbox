"""Unit tests for the GUI worker thread wrapper."""

from __future__ import annotations

import pytest

try:
    from pdf_toolbox.gui.worker import Worker
except (
    ImportError
):  # pragma: no cover  # pdf-toolbox: skip worker tests when PySide6 missing | issue:-
    pytest.skip("PySide6 is required for GUI tests", allow_module_level=True)

pytest_plugins = ("tests.gui.conftest_qt",)

pytestmark = [pytest.mark.gui]


def test_worker_emits_finished_on_success(qtbot) -> None:
    """Successful callables emit the finished signal with the result."""
    worker = Worker(lambda: "ok", {})
    with qtbot.waitSignal(worker.finished) as blocker:
        worker.run()
    assert blocker.args == ["ok"]


def test_worker_emits_error_on_exception(qtbot) -> None:
    """Exceptions propagate via the error signal."""

    def boom() -> None:
        raise ValueError("boom")

    worker = Worker(boom, {})
    with qtbot.waitSignal(worker.error) as blocker:
        worker.run()
    assert isinstance(blocker.args[0], ValueError)


def test_worker_respects_cancellation_flag() -> None:
    """Cancellation prevents the finished signal from firing."""
    seen = {}

    def sample(cancel) -> str:  # type: ignore[no-untyped-def]  # pdf-toolbox: Worker injects Event parameter dynamically | issue:-
        seen["cancel_set"] = cancel.is_set()
        return "done"

    worker = Worker(sample, {})
    captured: list[object] = []
    worker.finished.connect(captured.append)
    worker.cancel()
    worker.run()
    assert seen["cancel_set"] is True
    assert not captured
