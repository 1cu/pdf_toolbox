"""Shared Qt fixtures for GUI smoke tests."""

from __future__ import annotations

import inspect
import os
import tempfile
from collections.abc import Callable, Iterator
from pathlib import Path
from threading import Event
from types import SimpleNamespace

os.environ.setdefault("QT_OPENGL", "software")

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox

from pdf_toolbox import config, gui, i18n, utils
from pdf_toolbox.gui import main_window as gui_main_window


@pytest.fixture
def force_lang_en() -> Iterator[None]:
    """Force the GUI language to English for deterministic assertions."""
    previous = getattr(i18n, "_STATE", {}).get("lang")
    i18n.set_language("en")
    try:
        yield
    finally:
        if previous is None:
            i18n.set_language(None)
        else:
            i18n.set_language(previous)


@pytest.fixture
def temp_config_dir(monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Redirect configuration reads and writes to a temporary directory."""
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        config_file = base / "pdf_toolbox_config.json"
        base.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(utils, "CONFIG_FILE", config_file)
        monkeypatch.setattr(config, "CONFIG_PATH", config_file)
        monkeypatch.setattr(gui, "CONFIG_PATH", config_file)
        monkeypatch.setattr(gui_main_window, "CONFIG_PATH", config_file)
        yield base


@pytest.fixture
def no_file_dialogs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Make file dialogs deterministic so tests avoid native UI prompts."""
    dialog_dir = tmp_path / "dialog-selection"
    dialog_dir.mkdir()
    selected_dir = dialog_dir / "chosen-dir"
    selected_dir.mkdir()
    selected_file = dialog_dir / "chosen.pdf"
    selected_file.write_text("dummy")
    multi_file = dialog_dir / "multi.pdf"
    multi_file.write_text("dummy")

    def fake_get_existing_directory(*_args, **_kwargs) -> str:
        return str(selected_dir)

    def fake_get_open_file_name(*_args, **_kwargs) -> tuple[str, str]:
        return str(selected_file), ""

    def fake_get_open_file_names(*_args, **_kwargs) -> tuple[list[str], str]:
        return ([str(multi_file)], "")

    monkeypatch.setattr(
        QFileDialog, "getExistingDirectory", fake_get_existing_directory
    )
    monkeypatch.setattr(QFileDialog, "getOpenFileName", fake_get_open_file_name)
    monkeypatch.setattr(QFileDialog, "getOpenFileNames", fake_get_open_file_names)


@pytest.fixture
def messagebox_stubs(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Replace ``QMessageBox`` with a controllable stub."""
    real_message_box = QMessageBox

    calls: dict[str, list[object]] = {
        "critical": [],
        "warning": [],
        "information": [],
        "question": [],
        "exec": [],
        "instances": [],
    }
    responses = {
        "critical": real_message_box.StandardButton.Ok,
        "warning": real_message_box.StandardButton.Ok,
        "information": real_message_box.StandardButton.Ok,
        "question": real_message_box.StandardButton.Ok,
        "exec": real_message_box.StandardButton.Ok,
    }

    class StubMessageBox:
        StandardButton = real_message_box.StandardButton

        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            self.window_title = ""
            self.text = ""
            self.informative_text = ""
            self.text_format = None
            self.text_flags = None
            self.buttons = None
            calls["instances"].append(self)

        def setWindowTitle(self, title: str) -> None:  # noqa: N802  # pdf-toolbox: stub preserves Qt camelCase API | issue:-
            self.window_title = title

        def setTextFormat(self, fmt) -> None:  # noqa: N802  # type: ignore[override]  # pdf-toolbox: stub preserves Qt camelCase API | issue:-
            self.text_format = fmt

        def setText(self, text: str) -> None:  # noqa: N802  # pdf-toolbox: stub preserves Qt camelCase API | issue:-
            self.text = text

        def setInformativeText(self, text: str) -> None:  # noqa: N802  # pdf-toolbox: stub preserves Qt camelCase API | issue:-
            self.informative_text = text

        def setStandardButtons(self, buttons) -> None:  # noqa: N802  # type: ignore[override]  # pdf-toolbox: stub preserves Qt camelCase API | issue:-
            self.buttons = buttons

        def setTextInteractionFlags(self, flags) -> None:  # noqa: N802  # type: ignore[override]  # pdf-toolbox: stub preserves Qt camelCase API | issue:-
            self.text_flags = flags

        def exec(self) -> QMessageBox.StandardButton:
            calls["exec"].append(self)
            return responses["exec"]

        @classmethod
        def critical(cls, parent, title: str, text: str) -> QMessageBox.StandardButton:
            calls["critical"].append((parent, title, text))
            return responses["critical"]

        @classmethod
        def warning(cls, parent, title: str, text: str) -> QMessageBox.StandardButton:
            calls["warning"].append((parent, title, text))
            return responses["warning"]

        @classmethod
        def information(
            cls, parent, title: str, text: str
        ) -> QMessageBox.StandardButton:
            calls["information"].append((parent, title, text))
            return responses["information"]

        @classmethod
        def question(cls, parent, title: str, text: str) -> QMessageBox.StandardButton:
            calls["question"].append((parent, title, text))
            return responses["question"]

    def set_response(kind: str, value: QMessageBox.StandardButton) -> None:
        responses[kind] = value

    monkeypatch.setattr(gui_main_window, "QMessageBox", StubMessageBox)
    return SimpleNamespace(calls=calls, set_response=set_response, responses=responses)


@pytest.fixture
def dialog_exec_stub(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Stub ``QDialog.exec`` so tests can control dialog outcomes."""
    callbacks: list[Callable[[QDialog], None]] = []
    results: dict[str, QDialog.DialogCode | int] = {
        "return": QDialog.DialogCode.Accepted
    }
    calls: list[QDialog] = []

    def set_result(value: QDialog.DialogCode | int) -> None:
        results["return"] = value

    def set_callback(callback: Callable[[QDialog], None] | None) -> None:
        callbacks.clear()
        if callback is not None:
            callbacks.append(callback)

    def fake_exec(self: QDialog) -> int:
        calls.append(self)
        if callbacks:
            callbacks[0](self)
        return int(results["return"])

    monkeypatch.setattr(QDialog, "exec", fake_exec)
    return SimpleNamespace(
        calls=calls, set_result=set_result, set_callback=set_callback
    )


@pytest.fixture
def stub_worker(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Patch the GUI worker with a deterministic, synchronous variant."""
    created = []
    cancels = []
    waits: list[int | None] = []
    terminates = []
    starts = []

    class ImmediateWorker(QObject):
        finished = Signal(object)
        error = Signal(object)

        def __init__(self, func, kwargs: dict[str, object]):
            super().__init__()
            self.func = func
            self.kwargs = dict(kwargs)
            self._cancel = Event()
            self._running = False
            created.append(self)

        def isRunning(self) -> bool:  # noqa: N802  # pdf-toolbox: method name follows Qt worker API | issue:-
            return self._running

        def cancel(self) -> None:
            cancels.append(self)
            self._cancel.set()
            self._running = False

        def wait(self, timeout: int | None = None) -> bool:
            waits.append(timeout)
            return True

        def terminate(self) -> None:
            terminates.append(self)
            self._running = False

        def start(self) -> None:
            self._running = True
            starts.append(self)
            try:
                if "cancel" in inspect.signature(self.func).parameters:
                    self.kwargs.setdefault("cancel", self._cancel)
                result = self.func(**self.kwargs)
                if not self._cancel.is_set():
                    self.finished.emit(result)
            except Exception as exc:
                if not self._cancel.is_set():
                    self.error.emit(exc)
            finally:
                self._running = False

    monkeypatch.setattr(gui_main_window, "Worker", ImmediateWorker)
    return SimpleNamespace(
        cls=ImmediateWorker,
        created=created,
        cancels=cancels,
        waits=waits,
        terminates=terminates,
        starts=starts,
    )


@pytest.fixture(autouse=True)
def _disable_author_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Skip the author metadata prompt during GUI initialisation."""
    original = gui_main_window.MainWindow.__dict__["check_author"]
    monkeypatch.setattr(
        gui_main_window.MainWindow,
        "_original_check_author",
        original,
        raising=False,
    )
    monkeypatch.setattr(gui_main_window.MainWindow, "check_author", lambda _self: None)
