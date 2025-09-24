from __future__ import annotations

import importlib
import logging
import sys
from types import ModuleType
from typing import Any, cast

import pytest


@pytest.mark.qt_noop
def test_gui_import_handles_missing_qt(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Import ``pdf_toolbox.gui`` when Qt libraries are unavailable."""
    original_gui = sys.modules.pop("pdf_toolbox.gui", None)

    stub_main_window = cast(Any, ModuleType("pdf_toolbox.gui.main_window"))

    class DummyMainWindow:
        pass

    stub_main_window.MainWindow = DummyMainWindow
    monkeypatch.setitem(sys.modules, "pdf_toolbox.gui.main_window", stub_main_window)

    fake_pyside = cast(Any, ModuleType("PySide6"))
    fake_pyside.__path__ = []
    monkeypatch.setitem(sys.modules, "PySide6", fake_pyside)
    monkeypatch.delitem(sys.modules, "PySide6.QtWidgets", raising=False)

    module: ModuleType | None = None

    caplog.clear()
    pdf_logger = logging.getLogger("pdf_toolbox")
    pdf_logger.addHandler(caplog.handler)
    caplog.set_level(logging.WARNING, logger="pdf_toolbox")
    try:
        module = importlib.import_module("pdf_toolbox.gui")
    finally:
        pdf_logger.removeHandler(caplog.handler)
        sys.modules.pop("pdf_toolbox.gui", None)
        if original_gui is not None:
            sys.modules["pdf_toolbox.gui"] = original_gui
        importlib.invalidate_caches()

    assert module is not None
    assert module.QT_AVAILABLE is False
    assert isinstance(module.QT_IMPORT_ERROR, Exception)
    assert "PySide6" in str(module.QT_IMPORT_ERROR)
    assert "Qt import failed" in caplog.text


@pytest.mark.qt_noop
def test_gui_import_logs_stub_failure(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Log a helpful warning when the stub fallback cannot be imported."""
    original_gui = sys.modules.pop("pdf_toolbox.gui", None)
    original_main_window = sys.modules.pop("pdf_toolbox.gui.main_window", None)

    fake_pyside = cast(Any, ModuleType("PySide6"))
    fake_pyside.__path__ = []
    monkeypatch.setitem(sys.modules, "PySide6", fake_pyside)
    monkeypatch.delitem(sys.modules, "PySide6.QtWidgets", raising=False)

    original_import_module = importlib.import_module

    def _fake_import(name: str, package: str | None = None) -> ModuleType:
        if name == "pdf_toolbox.gui.main_window":
            raise RuntimeError
        return original_import_module(name, package)

    monkeypatch.setattr(importlib, "import_module", _fake_import)

    module: ModuleType | None = None

    caplog.clear()
    pdf_logger = logging.getLogger("pdf_toolbox")
    pdf_logger.addHandler(caplog.handler)
    caplog.set_level(logging.WARNING, logger="pdf_toolbox")
    try:
        module = importlib.import_module("pdf_toolbox.gui")
    finally:
        pdf_logger.removeHandler(caplog.handler)
        sys.modules.pop("pdf_toolbox.gui", None)
        if original_gui is not None:
            sys.modules["pdf_toolbox.gui"] = original_gui
        if original_main_window is not None:
            sys.modules["pdf_toolbox.gui.main_window"] = original_main_window
        importlib.invalidate_caches()

    assert module is not None
    assert module.QT_AVAILABLE is False
    assert isinstance(module.QT_IMPORT_ERROR, Exception)
    assert module.MainWindow.__module__ == "pdf_toolbox.gui"
    assert "MainWindow stub import failed" in caplog.text
    assert any(record.exc_info for record in caplog.records)


def test_gui_main_uses_sys_argv(monkeypatch: pytest.MonkeyPatch) -> None:
    """Launch the GUI with stubbed Qt classes to cover the main entry point."""
    original_gui = sys.modules.pop("pdf_toolbox.gui", None)
    original_qtwidgets = sys.modules.pop("PySide6.QtWidgets", None)
    original_pyside = sys.modules.pop("PySide6", None)

    called: dict[str, Any] = {}

    stub_main_window = cast(Any, ModuleType("pdf_toolbox.gui.main_window"))

    class DummyMainWindow:
        def __init__(self) -> None:
            called["window"] = True

    stub_main_window.MainWindow = DummyMainWindow
    monkeypatch.setitem(sys.modules, "pdf_toolbox.gui.main_window", stub_main_window)

    class DummyApp:
        def __init__(self, argv: list[str]) -> None:
            called["argv"] = argv

        def exec(self) -> int:
            called["exec"] = True
            return 0

    qtwidgets = ModuleType("PySide6.QtWidgets")
    qtwidgets.QApplication = (  # type: ignore[attr-defined]  # pdf-toolbox: stub Qt module for tests | issue:-
        DummyApp
    )
    fake_pyside = ModuleType("PySide6")
    fake_pyside.__path__ = []
    fake_pyside.QtWidgets = qtwidgets  # type: ignore[attr-defined]  # pdf-toolbox: stub Qt module for tests | issue:-
    monkeypatch.setitem(sys.modules, "PySide6.QtWidgets", qtwidgets)
    monkeypatch.setitem(sys.modules, "PySide6", fake_pyside)

    module: ModuleType | None = None
    try:
        module = importlib.import_module("pdf_toolbox.gui")
        assert module.QT_AVAILABLE is True
        monkeypatch.setattr(module, "MainWindow", DummyMainWindow)
        monkeypatch.setattr(module, "QApplication", DummyApp)

        exit_called: dict[str, Any] = {}

        def fake_exit(code: int) -> None:
            exit_called["code"] = code

        monkeypatch.setattr(module.sys, "exit", fake_exit)

        module.main()

        assert exit_called["code"] == 0
        assert called["argv"] is module.sys.argv
        assert called["exec"] is True
        assert called["window"] is True
    finally:
        sys.modules.pop("pdf_toolbox.gui", None)
        if original_gui is not None:
            sys.modules["pdf_toolbox.gui"] = original_gui
        if original_qtwidgets is not None:
            sys.modules["PySide6.QtWidgets"] = original_qtwidgets
        else:
            sys.modules.pop("PySide6.QtWidgets", None)
        if original_pyside is not None:
            sys.modules["PySide6"] = original_pyside
        else:
            sys.modules.pop("PySide6", None)
        importlib.invalidate_caches()
