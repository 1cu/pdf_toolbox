"""Tests for GUI entry points and bootstrapping."""

from __future__ import annotations

import runpy

import pytest

from pdf_toolbox import gui

pytest_plugins = ("tests.gui.conftest_qt",)

pytestmark = [pytest.mark.gui]


def test_gui_main_launches_application(monkeypatch: pytest.MonkeyPatch) -> None:
    """``gui.main()`` instantiates both the app and main window."""
    monkeypatch.setattr(gui, "QT_AVAILABLE", True)

    created: dict[str, object] = {}

    class DummyApp:
        def __init__(self, args: list[str]):
            created["args"] = args

        def exec(self) -> int:
            created["exec_called"] = True
            return 0

    class DummyWindow:
        def __init__(self) -> None:
            created["window_created"] = True

    exit_codes: list[int] = []
    monkeypatch.setattr(gui, "QApplication", DummyApp)
    monkeypatch.setattr(gui, "MainWindow", DummyWindow)
    monkeypatch.setattr(gui.sys, "exit", exit_codes.append)

    gui.main()

    assert created["args"] == gui.sys.argv
    assert created["window_created"] is True
    assert created["exec_called"] is True
    assert exit_codes == [0]


def test_gui_dunder_main_invokes_main(monkeypatch: pytest.MonkeyPatch) -> None:
    """Running ``pdf_toolbox.gui`` as a module calls ``main()``."""
    called: list[bool] = []
    monkeypatch.setattr(gui, "main", lambda: called.append(True))

    runpy.run_module("pdf_toolbox.gui.__main__", run_name="__main__")

    assert called == [True]
