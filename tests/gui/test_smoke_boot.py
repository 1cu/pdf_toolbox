"""Qt smoke tests that ensure the GUI starts without native dialogs."""

from __future__ import annotations

import os

os.environ.setdefault("QT_OPENGL", "software")

import pytest

from pdf_toolbox.gui.main_window import MainWindow
from pdf_toolbox.gui.widgets import LogDisplay

pytest_plugins = ("tests.gui.conftest_qt",)


@pytest.mark.gui
@pytest.mark.usefixtures("force_lang_en", "temp_config_dir", "no_file_dialogs")
def test_main_window_boots_and_exposes_core_widgets(qtbot):
    """Launch the main window and verify essential widgets are present."""
    window = MainWindow()
    qtbot.addWidget(window)

    window.show()
    qtbot.waitExposed(window, timeout=3000)
    assert window.isVisible()
    assert window.windowTitle().strip()
    assert window.tree.topLevelItemCount() > 0

    log_widgets = window.findChildren(LogDisplay)
    assert window.log in log_widgets
    assert not window.log.isVisible()
    assert window.action_about in window.settings_menu.actions()
    assert window.status_key == "ready"

    window.close()
