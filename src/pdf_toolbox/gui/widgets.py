"""Custom Qt widgets and log handler (GUI-only)."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QFileDialog, QLabel, QLineEdit, QPlainTextEdit

from pdf_toolbox.config import save_config
from pdf_toolbox.i18n import tr


class QtLogHandler(
    QObject, logging.Handler
):  # pragma: no cover  # pdf-toolbox: GUI helper | issue:-
    """Send log records to a ``QPlainTextEdit`` widget."""

    message = Signal(str)

    def __init__(self, widget: QPlainTextEdit, on_update):
        """Initialize with target widget and update callback."""
        QObject.__init__(self)
        logging.Handler.__init__(self)
        self.widget = widget
        self.on_update = on_update
        self.message.connect(self._append)

    def _append(self, msg: str) -> None:
        self.widget.setVisible(True)
        self.widget.appendPlainText(msg)
        self.widget.verticalScrollBar().setValue(
            self.widget.verticalScrollBar().maximum()
        )
        self.on_update()

    def emit(self, record: logging.LogRecord) -> None:  # type: ignore[override]  # pragma: no cover  # pdf-toolbox: override signal emitter with broader type; GUI-only | issue:-
        """Forward a log record to the GUI thread."""
        self.message.emit(self.format(record))


class FileEdit(QLineEdit):  # pragma: no cover  # pdf-toolbox: GUI widget | issue:-
    """Widget for selecting files or directories."""

    def __init__(self, cfg: dict, directory: bool = False, multi: bool = False):
        """Initialize with config and selection mode flags."""
        super().__init__()
        self.cfg = cfg
        self.directory = directory
        self.multi = multi
        self.setAcceptDrops(True)

    def browse(self) -> None:
        """Open a file or directory selection dialog."""
        initial = self.cfg.get("last_open_dir", str(Path.home()))
        if self.directory:
            path = QFileDialog.getExistingDirectory(
                self, tr("select_directory"), initial
            )
            if path:
                self.setText(path)
                self.cfg["last_open_dir"] = path
                save_config(self.cfg)
        elif self.multi:
            paths, _ = QFileDialog.getOpenFileNames(self, tr("select_files"), initial)
            if paths:
                self.setText(";".join(paths))
                self.cfg["last_open_dir"] = str(Path(paths[0]).parent)
                save_config(self.cfg)
        else:
            path, _ = QFileDialog.getOpenFileName(self, tr("select_file"), initial)
            if path:
                self.setText(path)
                self.cfg["last_open_dir"] = str(Path(path).parent)
                save_config(self.cfg)

    def dragEnterEvent(self, e):  # noqa: N802  # pdf-toolbox: Qt requires camelCase event name | issue:-
        """Accept drag when it contains URLs."""
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):  # noqa: N802  # pdf-toolbox: Qt requires camelCase event name | issue:-
        """Handle dropped files to populate the edit field."""
        paths = [url.toLocalFile() for url in e.mimeData().urls()]
        if not paths:
            return
        if self.multi:
            self.setText(";".join(paths))
        else:
            self.setText(paths[0])
        self.cfg["last_open_dir"] = str(Path(paths[0]).parent)
        save_config(self.cfg)


class ClickableLabel(QLabel):  # pragma: no cover  # pdf-toolbox: GUI widget | issue:-
    """Label that emits a ``clicked`` signal when pressed."""

    clicked = Signal()

    def mousePressEvent(self, event):  # noqa: N802  # pdf-toolbox: Qt requires camelCase event name | issue:-
        """Emit the ``clicked`` signal and forward the event."""
        self.clicked.emit()
        super().mousePressEvent(event)
