"""Custom Qt widgets and log handler (GUI-only)."""

from __future__ import annotations

import logging
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextDocument,
)
from PySide6.QtWidgets import QFileDialog, QLabel, QLineEdit, QPlainTextEdit

from pdf_toolbox.config import save_config
from pdf_toolbox.i18n import tr


class QtLogHandler(QObject, logging.Handler):
    """Send log records to a ``QPlainTextEdit`` widget."""

    message = Signal(logging.LogRecord)

    def __init__(self, widget: QPlainTextEdit, on_update: Callable[[], None]):
        """Initialize with target widget and update callback."""
        QObject.__init__(self)
        logging.Handler.__init__(self)
        self.widget = widget
        self.on_update = on_update
        self.message.connect(self._append)

    def emit(self, record: logging.LogRecord) -> None:
        """Forward a log record to the GUI thread."""
        self.message.emit(record)

    def _format_record_message(self, record: logging.LogRecord) -> str:
        """Return the log *record* message including exception details."""
        message = record.getMessage()
        formatter = self.formatter or logging.Formatter()
        exc_text = getattr(record, "exc_text", None)
        if record.exc_info and not exc_text:
            exc_text = formatter.formatException(record.exc_info)
        if exc_text:
            message = f"{message}\n{exc_text}" if message else exc_text
        if record.stack_info:
            stack_text = formatter.formatStack(record.stack_info)
            if stack_text:
                message = f"{message}\n{stack_text}" if message else stack_text
        return message

    def _append(self, record: logging.LogRecord) -> None:
        self.widget.setVisible(True)
        if isinstance(self.widget, LogDisplay):
            self.widget.add_entry(
                self._format_record_message(record),
                level=record.levelname,
                source=record.name,
                timestamp=datetime.fromtimestamp(record.created),
            )
            self.widget.scroll_to_bottom()
        else:
            self.widget.appendPlainText(self.format(record))
            self.widget.verticalScrollBar().setValue(self.widget.verticalScrollBar().maximum())
        self.on_update()


@dataclass(frozen=True)
class LogEntry:
    """Structured data for a single log row."""

    timestamp: datetime
    level: str
    source: str
    message: str


class _LogHighlighter(QSyntaxHighlighter):
    """Apply colour accents to log rows based on their severity."""

    _MIN_SEGMENTS = 3

    def __init__(self, parent: QPlainTextEdit | QTextDocument) -> None:
        super().__init__(parent)
        self._level_styles: dict[str, tuple[QTextCharFormat | None, QTextCharFormat]] = {}
        self._header_format = QTextCharFormat()
        self._header_format.setFontWeight(QFont.Weight.Bold)
        self._register_style("DEBUG", line_fg="#607D8B")
        self._register_style("INFO", level_fg="#1565C0", level_bold=True)
        self._register_style(
            "RESULT",
            line_bg="#E8F5E9",
            level_fg="#2E7D32",
            level_bold=True,
        )
        self._register_style(
            "WARNING",
            line_bg="#FFF3E0",
            level_fg="#E65100",
            level_bold=True,
        )
        self._register_style(
            "ERROR",
            line_bg="#FFEBEE",
            level_fg="#C62828",
            level_bold=True,
        )
        self._register_style(
            "CRITICAL",
            line_bg="#FFCDD2",
            level_fg="#B71C1C",
            level_bold=True,
        )

    def _register_style(
        self,
        level: str,
        *,
        line_fg: str | None = None,
        line_bg: str | None = None,
        level_fg: str | None = None,
        level_bold: bool = False,
    ) -> None:
        line_format: QTextCharFormat | None = None
        if line_fg or line_bg:
            line_format = QTextCharFormat()
            if line_fg:
                line_format.setForeground(QColor(line_fg))
            if line_bg:
                line_format.setBackground(QColor(line_bg))
        level_format = QTextCharFormat()
        if level_fg:
            level_format.setForeground(QColor(level_fg))
        if level_bold:
            level_format.setFontWeight(QFont.Weight.Bold)
        self._level_styles[level] = (line_format, level_format)

    def highlightBlock(self, text: str) -> None:  # noqa: N802  # pdf-toolbox: QSyntaxHighlighter requires camelCase hook name | issue:-
        if "│" not in text:
            return
        segments = text.split("│")
        if len(segments) < self._MIN_SEGMENTS:
            return
        if segments[1].strip() == tr("log_level"):
            self.setFormat(0, len(text), self._header_format)
            return
        level = segments[1].strip()
        style = self._level_styles.get(level)
        if not style:
            return
        line_format, level_format = style
        if line_format is not None:
            self.setFormat(0, len(text), line_format)
        start = text.index("│") + 1
        end = text.index("│", start + 1)
        self.setFormat(start + 1, end - start - 1, level_format)


class LogDisplay(QPlainTextEdit):
    """Plain-text log viewer with aligned columns and colour highlights."""

    TIME_WIDTH = 8
    LEVEL_WIDTH = 8
    SOURCE_WIDTH = 20

    def __init__(self) -> None:
        """Initialise the log viewer with monospace formatting."""
        super().__init__()
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        self.setFont(font)
        self._entries: deque[LogEntry] = deque()
        self._max_entries = 200
        self._highlighter = _LogHighlighter(self.document())
        self._update_view()

    def set_maximum_entries(self, count: int) -> None:
        """Limit the number of stored log rows."""
        self._max_entries = max(1, count)
        self._trim_entries()
        self._update_view()

    def add_entry(
        self,
        message: str,
        *,
        level: str = "INFO",
        source: str | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        """Append a new structured entry to the display."""
        entry = LogEntry(
            timestamp or datetime.now(),
            level.upper(),
            (source or "").strip(),
            message,
        )
        self._entries.append(entry)
        self._trim_entries()
        self._update_view()
        self.scroll_to_bottom()

    def entries(self) -> list[LogEntry]:
        """Return a copy of the current log entries."""
        return list(self._entries)

    def has_entries(self) -> bool:
        """Return whether the viewer currently holds entries."""
        return bool(self._entries)

    def clear(self) -> None:
        """Remove all log entries."""
        self._entries.clear()
        super().clear()
        self._update_view()

    def scroll_to_bottom(self) -> None:
        """Scroll to the most recent entry."""
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    def _trim_entries(self) -> None:
        while len(self._entries) > self._max_entries:
            self._entries.popleft()

    def _format_source(self, source: str) -> str:
        if not source:
            return ""
        if len(source) <= self.SOURCE_WIDTH:
            return source
        return "…" + source[-(self.SOURCE_WIDTH - 1) :]

    def _render_entry(self, entry: LogEntry) -> list[str]:
        stamp = entry.timestamp.strftime("%H:%M:%S")
        source = self._format_source(entry.source)
        source_display = source.ljust(self.SOURCE_WIDTH)
        level = entry.level.ljust(self.LEVEL_WIDTH)
        message_lines = entry.message.splitlines() or [""]
        rows: list[str] = []
        for idx, line in enumerate(message_lines):
            if idx == 0:
                rows.append(f"{stamp} │ {level} │ {source_display} │ {line}")
            else:
                rows.append(
                    f"{' ' * self.TIME_WIDTH} │ {'':<{self.LEVEL_WIDTH}} │ {'':<{self.SOURCE_WIDTH}} │ {line}"
                )
        return rows

    def _header_row(self) -> str:
        time = tr("log_time").ljust(self.TIME_WIDTH)
        level = tr("log_level").ljust(self.LEVEL_WIDTH)
        source = tr("log_source").ljust(self.SOURCE_WIDTH)
        message = tr("log_message")
        return f"{time} │ {level} │ {source} │ {message}"

    def _update_view(self) -> None:
        lines: list[str] = []
        if self._entries:
            lines.append(self._header_row())
            for entry in self._entries:
                lines.extend(self._render_entry(entry))
        text = "\n".join(lines)
        super().setPlainText(text)


class FileEdit(QLineEdit):
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
            path = QFileDialog.getExistingDirectory(self, tr("select_directory"), initial)
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


class ClickableLabel(QLabel):
    """Label that emits a ``clicked`` signal when pressed."""

    clicked = Signal()

    def mousePressEvent(self, event):  # noqa: N802  # pdf-toolbox: Qt requires camelCase event name | issue:-
        """Emit the ``clicked`` signal and forward the event."""
        self.clicked.emit()
        super().mousePressEvent(event)
