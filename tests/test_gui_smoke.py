"""Smoke tests for the Qt GUI using pytest-qt."""

from __future__ import annotations

import pytest


@pytest.mark.gui
def test_main_window_shows_and_has_expected_state(qtbot):
    """Ensure the main window becomes visible and exposes basic UI elements."""
    from pdf_toolbox.gui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    qtbot.waitUntil(window.isVisible, timeout=1000)

    assert window.isVisible()
    assert window.windowTitle() == "PDF Toolbox"
    assert window.action_about in window.settings_menu.actions()
    assert window.status_key == "ready"
