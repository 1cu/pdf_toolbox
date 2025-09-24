from __future__ import annotations

import importlib
import logging
import sys
from types import ModuleType

import pytest


@pytest.mark.qt_noop
def test_gui_import_handles_missing_qt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Import ``pdf_toolbox.gui`` when Qt libraries are unavailable."""

    original_gui = sys.modules.pop("pdf_toolbox.gui", None)

    stub_main_window = ModuleType("pdf_toolbox.gui.main_window")

    class DummyMainWindow:
        pass

    setattr(stub_main_window, "MainWindow", DummyMainWindow)
    monkeypatch.setitem(sys.modules, "pdf_toolbox.gui.main_window", stub_main_window)

    fake_pyside = ModuleType("PySide6")
    setattr(fake_pyside, "__path__", [])
    monkeypatch.setitem(sys.modules, "PySide6", fake_pyside)
    monkeypatch.delitem(sys.modules, "PySide6.QtWidgets", raising=False)

    module = None
    captured: list[logging.LogRecord] = []

    class _Handler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured.append(record)

    handler = _Handler()
    target_logger = logging.getLogger("pdf_toolbox")
    target_logger.addHandler(handler)
    try:
        module = importlib.import_module("pdf_toolbox.gui")
    finally:
        target_logger.removeHandler(handler)
        sys.modules.pop("pdf_toolbox.gui", None)
        if original_gui is not None:
            sys.modules["pdf_toolbox.gui"] = original_gui
        importlib.invalidate_caches()

    assert module is not None
    assert module.QT_AVAILABLE is False
    assert isinstance(module.QT_IMPORT_ERROR, Exception)
    assert "PySide6" in str(module.QT_IMPORT_ERROR)
    assert any("Qt import failed" in record.getMessage() for record in captured)
