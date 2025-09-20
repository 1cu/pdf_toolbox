"""Qt smoke tests ensuring the GUI boots without native dialogs."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
os.environ.setdefault("QT_OPENGL", "software")

import pytest
from PySide6.QtWidgets import QPlainTextEdit

from pdf_toolbox.gui.main_window import MainWindow

pytest_plugins = ("tests.gui.conftest_qt",)

pytestmark = [
    pytest.mark.gui,
    pytest.mark.usefixtures("force_lang_en", "temp_config_dir", "no_file_dialogs"),
]


def test_main_window_smoke(qtbot) -> None:
    """Launch the main window and verify essential widgets are present."""
    window = MainWindow()
    qtbot.addWidget(window)

    window.show()
    qtbot.waitExposed(window, timeout=3000)

    assert window.isVisible()
    assert window.windowTitle().strip()
    assert window.tree.topLevelItemCount() > 0
    assert isinstance(window.log, QPlainTextEdit)

    window.close()
