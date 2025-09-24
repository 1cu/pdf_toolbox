"""Qt-based GUI for PDF Toolbox (package facade).

This package exposes a minimal, stable API for tests and callers:

- ``DEFAULT_CONFIG``, ``CONFIG_PATH``, ``load_config``, ``save_config``
- ``MainWindow``
- ``main()`` entry point
- ``QT_AVAILABLE`` and ``QT_IMPORT_ERROR`` flags

It also re-exports ``Action`` and ``list_actions`` so tests can monkeypatch
``gui.list_actions`` easily when constructing forms.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pdf_toolbox.config as _config
from pdf_toolbox.actions import Action, list_actions
from pdf_toolbox.utils import logger

if TYPE_CHECKING:  # pragma: no cover  # pdf-toolbox: typing-only import guard | issue:-
    from pdf_toolbox.gui.main_window import MainWindow
else:

    class MainWindow:  # pragma: no cover  # pdf-toolbox: runtime fallback for typing | issue:-
        """Placeholder replaced with the Qt-backed window at runtime."""

        ...


# Re-export config with indirection so tests can monkeypatch gui.CONFIG_PATH
CONFIG_PATH = _config.CONFIG_PATH
DEFAULT_CONFIG = _config.DEFAULT_CONFIG


def load_config() -> dict:
    """Load GUI configuration from the active `CONFIG_PATH`."""
    return _config.load_config_at(CONFIG_PATH)


def save_config(cfg: dict) -> None:
    """Save GUI configuration to the active `CONFIG_PATH`."""
    _config.save_config_at(CONFIG_PATH, cfg)


try:  # Detect Qt availability for headless error handling tests
    from PySide6.QtWidgets import QApplication

    QT_AVAILABLE = True
    QT_IMPORT_ERROR: Exception | None = None
except (ImportError, OSError, RuntimeError) as _qt_exc:
    QT_AVAILABLE = False
    QT_IMPORT_ERROR = _qt_exc
    logger.warning("Qt import failed", exc_info=True)

if not TYPE_CHECKING:
    if QT_AVAILABLE:
        from pdf_toolbox.gui.main_window import MainWindow as _LoadedMainWindow

        MainWindow = _LoadedMainWindow
    else:
        try:
            from pdf_toolbox.gui import main_window as _main_window_mod
        except (
            ImportError,
            OSError,
            RuntimeError,
        ):  # pragma: no cover  # pdf-toolbox: stub import fallback | issue:-
            pass
        else:
            stub_cls = getattr(_main_window_mod, "MainWindow", None)
            if isinstance(stub_cls, type):
                MainWindow = stub_cls


def main() -> None:
    """Launch the GUI application."""
    if not QT_AVAILABLE:
        raise QT_IMPORT_ERROR or RuntimeError("Qt libraries not available")

    app = QApplication(sys.argv)
    _win = MainWindow()
    sys.exit(app.exec())


__all__ = [
    "CONFIG_PATH",
    "DEFAULT_CONFIG",
    "QT_AVAILABLE",
    "QT_IMPORT_ERROR",
    "Action",
    "MainWindow",
    "list_actions",
    "load_config",
    "main",
    "save_config",
]
