"""GUI widget unit tests that keep coverage deterministic."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

pytest.importorskip("PySide6.QtWidgets")
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from pdf_toolbox.gui.widgets import (
    ClickableLabel,
    FileEdit,
    LogDisplay,
    LogEntry,
    QtLogHandler,
)

pytest_plugins = ("tests.gui.conftest_qt",)

pytestmark = [
    pytest.mark.gui,
    pytest.mark.usefixtures("force_lang_en", "temp_config_dir", "no_file_dialogs"),
]


def test_file_edit_browse_directory_updates_text_and_config(
    monkeypatch: pytest.MonkeyPatch, qtbot
) -> None:
    """Directory browse updates both the text field and config."""
    from pdf_toolbox.gui import widgets as widgets_mod

    cfg: dict[str, str] = {}
    saved: list[dict[str, str]] = []

    def record(data: dict[str, str]) -> None:
        saved.append(dict(data))

    monkeypatch.setattr(widgets_mod, "save_config", record)

    widget = FileEdit(cfg, directory=True)
    qtbot.addWidget(widget)

    widget.browse()

    assert Path(widget.text()).name == "chosen-dir"
    assert cfg["last_open_dir"] == widget.text()
    assert saved
    assert saved[-1]["last_open_dir"] == widget.text()


def test_file_edit_browse_multi_files_records_last_dir(
    monkeypatch: pytest.MonkeyPatch, qtbot
) -> None:
    """Multi-file browse joins selections and stores the folder."""
    from pdf_toolbox.gui import widgets as widgets_mod

    cfg: dict[str, str] = {}
    saved: list[dict[str, str]] = []

    def record(data: dict[str, str]) -> None:
        saved.append(dict(data))

    monkeypatch.setattr(widgets_mod, "save_config", record)

    widget = FileEdit(cfg, multi=True)
    qtbot.addWidget(widget)

    widget.browse()

    paths = widget.text().split(";")
    assert len(paths) == 1
    assert paths[0].endswith("multi.pdf")
    assert cfg["last_open_dir"].endswith("dialog-selection")
    assert saved
    assert saved[-1]["last_open_dir"].endswith("dialog-selection")


def test_file_edit_browse_single_file(monkeypatch: pytest.MonkeyPatch, qtbot) -> None:
    """Single file browse updates the text and config."""
    from pdf_toolbox.gui import widgets as widgets_mod

    cfg: dict[str, str] = {}
    saved: list[dict[str, str]] = []

    def record(data: dict[str, str]) -> None:
        saved.append(dict(data))

    monkeypatch.setattr(widgets_mod, "save_config", record)

    widget = FileEdit(cfg)
    qtbot.addWidget(widget)

    widget.browse()

    assert widget.text().endswith("chosen.pdf")
    assert cfg["last_open_dir"].endswith("dialog-selection")
    assert saved
    assert saved[-1]["last_open_dir"].endswith("dialog-selection")


def test_file_edit_drag_and_drop_updates_config(
    monkeypatch: pytest.MonkeyPatch, qtbot, tmp_path: Path
) -> None:
    """Dropping files populates the edit and persists the directory."""
    from pdf_toolbox.gui import widgets as widgets_mod

    cfg: dict[str, str] = {}
    saved: list[dict[str, str]] = []

    def record(data: dict[str, str]) -> None:
        saved.append(dict(data))

    monkeypatch.setattr(widgets_mod, "save_config", record)

    widget = FileEdit(cfg)
    qtbot.addWidget(widget)

    dropped = tmp_path / "document.pdf"
    dropped.write_text("dummy")

    class DummyUrl:
        def __init__(self, value: str) -> None:
            self.value = value

        def toLocalFile(self) -> str:  # noqa: N802  # pdf-toolbox: stub mirrors Qt URL API | issue:-
            return self.value

    class DummyMime:
        def __init__(self, urls: list[DummyUrl]) -> None:
            self._urls = urls

        def hasUrls(self) -> bool:  # noqa: N802  # pdf-toolbox: stub mirrors Qt MIME API | issue:-
            return True

        def urls(self) -> list[DummyUrl]:
            return self._urls

    class DummyEvent:
        def __init__(self, urls: list[DummyUrl]) -> None:
            self._mime = DummyMime(urls)
            self.accepted = False

        def mimeData(self) -> DummyMime:  # noqa: N802  # pdf-toolbox: stub mirrors Qt event API | issue:-
            return self._mime

        def acceptProposedAction(self) -> None:  # noqa: N802  # pdf-toolbox: stub mirrors Qt event API | issue:-
            self.accepted = True

    drag_event = DummyEvent([DummyUrl(str(dropped))])
    widget.dragEnterEvent(drag_event)
    assert drag_event.accepted

    drop_event = DummyEvent([DummyUrl(str(dropped))])
    widget.dropEvent(drop_event)

    assert widget.text() == str(dropped)
    assert cfg["last_open_dir"] == str(dropped.parent)
    assert saved
    assert saved[-1]["last_open_dir"] == str(dropped.parent)


def test_file_edit_drop_multi_joins_paths(
    monkeypatch: pytest.MonkeyPatch, qtbot, tmp_path: Path
) -> None:
    """Multi-file drops join paths with a semicolon."""
    from pdf_toolbox.gui import widgets as widgets_mod

    cfg: dict[str, str] = {}
    saved: list[dict[str, str]] = []

    def record(data: dict[str, str]) -> None:
        saved.append(dict(data))

    monkeypatch.setattr(widgets_mod, "save_config", record)

    widget = FileEdit(cfg, multi=True)
    qtbot.addWidget(widget)

    dropped_one = tmp_path / "first.pdf"
    dropped_one.write_text("dummy")
    dropped_two = tmp_path / "second.pdf"
    dropped_two.write_text("dummy")

    class DummyUrl:
        def __init__(self, value: str) -> None:
            self.value = value

        def toLocalFile(self) -> str:  # noqa: N802  # pdf-toolbox: stub mirrors Qt URL API | issue:-
            return self.value

    class DummyMime:
        def __init__(self, urls: list[DummyUrl]) -> None:
            self._urls = urls

        def hasUrls(self) -> bool:  # noqa: N802  # pdf-toolbox: stub mirrors Qt MIME API | issue:-
            return True

        def urls(self) -> list[DummyUrl]:
            return self._urls

    class DummyEvent:
        def __init__(self, urls: list[DummyUrl]) -> None:
            self._mime = DummyMime(urls)

        def mimeData(self) -> DummyMime:  # noqa: N802  # pdf-toolbox: stub mirrors Qt event API | issue:-
            return self._mime

    widget.dropEvent(
        DummyEvent([DummyUrl(str(dropped_one)), DummyUrl(str(dropped_two))])
    )

    assert widget.text() == ";".join([str(dropped_one), str(dropped_two)])
    assert saved
    assert saved[-1]["last_open_dir"] == str(dropped_one.parent)


def test_clickable_label_emits_signal(qtbot) -> None:
    """Clicking the label emits the ``clicked`` signal."""
    label = ClickableLabel("Click me")
    qtbot.addWidget(label)

    with qtbot.waitSignal(label.clicked):
        QTest.mouseClick(label, Qt.MouseButton.LeftButton)


def test_qt_log_handler_appends_and_calls_update(qtbot) -> None:
    """Log messages surface in the widget and trigger callbacks."""
    widget = LogDisplay()
    widget.setVisible(False)
    updates: list[list[LogEntry]] = []
    handler = QtLogHandler(widget, lambda: updates.append(widget.entries()))

    record = logging.makeLogRecord(
        {"msg": "Hello", "levelno": logging.INFO, "levelname": "INFO"}
    )
    handler.emit(record)

    qtbot.waitUntil(
        lambda: widget.entries() and widget.entries()[-1].message == "Hello"
    )

    assert widget.isVisible()
    assert updates
    assert widget.entries()[-1].message == "Hello"
