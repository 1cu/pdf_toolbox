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

import importlib
import sys
from collections.abc import Callable
from types import ModuleType
from typing import TYPE_CHECKING, Any, cast

import pdf_toolbox.config as _config
from pdf_toolbox.actions import Action, list_actions
from pdf_toolbox.utils import logger

ImportModule = Callable[..., ModuleType]


class _StubMainWindow:
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


def _load_qt(
    import_module: ImportModule = importlib.import_module,
) -> tuple[bool, Exception | None, type[Any] | None]:
    """Attempt to import Qt widgets and expose ``QApplication`` for runtime use."""
    try:
        qt_widgets = import_module("PySide6.QtWidgets")
    except (ImportError, OSError, RuntimeError) as exc:
        logger.warning("Qt import failed", exc_info=True)
        return False, exc, None

    qt_application = getattr(qt_widgets, "QApplication", None)
    if qt_application is None:
        message = "PySide6.QtWidgets.QApplication missing from Qt module"
        logger.warning(message)
        return False, RuntimeError(message), None

    return True, None, qt_application


def _load_main_window(
    import_module: ImportModule = importlib.import_module,
) -> type[Any]:
    """Resolve the GUI ``MainWindow`` class, falling back to a stub when Qt is missing."""
    try:
        module = import_module("pdf_toolbox.gui.main_window")
    except (ImportError, OSError, RuntimeError) as exc:
        logger.warning(
            "MainWindow stub import failed",
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return _StubMainWindow

    main_window_cls = getattr(module, "MainWindow", None)
    if isinstance(main_window_cls, type):
        return main_window_cls

    return _StubMainWindow


QT_AVAILABLE, QT_IMPORT_ERROR, _QApplication = _load_qt()
QApplication: type[Any] | None = cast(type[Any], _QApplication) if QT_AVAILABLE else None

if TYPE_CHECKING:
    from pdf_toolbox.gui.main_window import MainWindow
else:
    MainWindow: type[Any] = _load_main_window()


def main() -> None:
    """Launch the GUI application."""
    if not QT_AVAILABLE:
        raise QT_IMPORT_ERROR or RuntimeError("Qt libraries not available")

    qt_app = cast(type[Any], QApplication)
    app = qt_app(sys.argv)
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
