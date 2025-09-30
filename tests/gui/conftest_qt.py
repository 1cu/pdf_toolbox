"""Shared Qt fixtures for GUI smoke tests."""

from __future__ import annotations

import inspect
import os
import tempfile
from collections.abc import Callable, Iterator
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from typing import ClassVar

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox

os.environ.setdefault("QT_OPENGL", "software")

from pdf_toolbox import config, gui, i18n, utils
from pdf_toolbox.gui import main_window as gui_main_window


@pytest.fixture(name="force_lang_en")
def _force_lang_en() -> Iterator[None]:
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


@pytest.fixture(name="no_file_dialogs")
def _no_file_dialogs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
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

    monkeypatch.setattr(QFileDialog, "getExistingDirectory", fake_get_existing_directory)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", fake_get_open_file_name)
    monkeypatch.setattr(QFileDialog, "getOpenFileNames", fake_get_open_file_names)


@pytest.fixture
def messagebox_stubs(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Replace ``QMessageBox`` with a controllable stub."""
    real_message_box = QMessageBox
    calls = _initial_messagebox_calls()
    responses = _initial_messagebox_responses(real_message_box)
    stub_class = _make_messagebox_stub(real_message_box, calls, responses)

    monkeypatch.setattr(gui_main_window, "QMessageBox", stub_class)
    return SimpleNamespace(
        calls=calls,
        set_response=_make_messagebox_response_setter(responses),
        responses=responses,
    )


@pytest.fixture
def dialog_exec_stub(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Stub ``QDialog.exec`` so tests can control dialog outcomes."""
    callbacks: list[Callable[[QDialog], None]] = []
    results: dict[str, QDialog.DialogCode | int] = {"return": QDialog.DialogCode.Accepted}
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
    return SimpleNamespace(calls=calls, set_result=set_result, set_callback=set_callback)


@pytest.fixture
def stub_worker(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Patch the GUI worker with a deterministic, synchronous variant."""
    state = _WorkerState()
    worker_cls = _create_immediate_worker(state)

    monkeypatch.setattr(gui_main_window, "Worker", worker_cls)
    return SimpleNamespace(
        cls=worker_cls,
        created=state.created,
        cancels=state.cancels,
        waits=state.waits,
        terminates=state.terminates,
        starts=state.starts,
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


def _initial_messagebox_calls() -> dict[str, list[object]]:
    """Return a dictionary collecting message box interactions."""
    return {
        "critical": [],
        "warning": [],
        "information": [],
        "question": [],
        "exec": [],
        "instances": [],
    }


def _initial_messagebox_responses(real_message_box: type[QMessageBox]) -> dict[str, object]:
    """Return the default responses for stubbed message boxes."""
    default = real_message_box.StandardButton.Ok
    return {
        "critical": default,
        "warning": default,
        "information": default,
        "question": default,
        "exec": default,
    }


class _MessageBoxStub:
    """Simple QMessageBox replacement recording interactions for tests."""

    StandardButton = QMessageBox.StandardButton
    _camel_case_aliases: ClassVar[dict[str, str]] = {
        "setWindowTitle": "set_window_title",
        "setTextFormat": "set_text_format",
        "setText": "set_text",
        "setInformativeText": "set_informative_text",
        "setStandardButtons": "set_standard_buttons",
        "setTextInteractionFlags": "set_text_interaction_flags",
    }
    calls: ClassVar[dict[str, list[object]]] = {}
    responses: ClassVar[dict[str, object]] = {}

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.window_title = ""
        self.text = ""
        self.informative_text = ""
        self.text_format = None
        self.text_flags = None
        self.buttons = None
        type(self).calls.setdefault("instances", []).append(self)

    def __getattr__(self, name: str):
        alias = self._camel_case_aliases.get(name)
        if alias is not None:
            return getattr(self, alias)
        raise AttributeError(name)

    def set_window_title(self, title: str) -> None:
        self.window_title = title

    def set_text_format(self, fmt) -> None:  # type: ignore[override]  # pdf-toolbox: stub preserves Qt camelCase API | issue:-
        self.text_format = fmt

    def set_text(self, text: str) -> None:
        self.text = text

    def set_informative_text(self, text: str) -> None:
        self.informative_text = text

    def set_standard_buttons(self, buttons) -> None:  # type: ignore[override]  # pdf-toolbox: stub preserves Qt camelCase API | issue:-
        self.buttons = buttons

    def set_text_interaction_flags(self, flags) -> None:  # type: ignore[override]  # pdf-toolbox: stub preserves Qt camelCase API | issue:-
        self.text_flags = flags

    def exec(self) -> QMessageBox.StandardButton:
        type(self).calls.setdefault("exec", []).append(self)
        return type(self).responses.get("exec", self.StandardButton.Ok)

    @classmethod
    def critical(cls, parent, title: str, text: str) -> QMessageBox.StandardButton:
        cls.calls.setdefault("critical", []).append((parent, title, text))
        return cls.responses.get("critical", cls.StandardButton.Ok)

    @classmethod
    def warning(cls, parent, title: str, text: str) -> QMessageBox.StandardButton:
        cls.calls.setdefault("warning", []).append((parent, title, text))
        return cls.responses.get("warning", cls.StandardButton.Ok)

    @classmethod
    def information(cls, parent, title: str, text: str) -> QMessageBox.StandardButton:
        cls.calls.setdefault("information", []).append((parent, title, text))
        return cls.responses.get("information", cls.StandardButton.Ok)

    @classmethod
    def question(cls, parent, title: str, text: str) -> QMessageBox.StandardButton:
        cls.calls.setdefault("question", []).append((parent, title, text))
        return cls.responses.get("question", cls.StandardButton.Ok)

    @classmethod
    def configure(
        cls,
        real_message_box: type[QMessageBox],
        calls: dict[str, list[object]],
        responses: dict[str, object],
    ) -> None:
        cls.StandardButton = real_message_box.StandardButton
        cls.calls = calls
        cls.responses = responses


def _make_messagebox_stub(
    real_message_box: type[QMessageBox],
    calls: dict[str, list[object]],
    responses: dict[str, object],
) -> type[QMessageBox]:
    """Create a stub ``QMessageBox`` class backed by ``calls`` and ``responses``."""
    _MessageBoxStub.configure(real_message_box, calls, responses)
    return _MessageBoxStub


def _make_messagebox_response_setter(
    responses: dict[str, object],
) -> Callable[[str, QMessageBox.StandardButton], None]:
    """Return a helper that updates the stubbed message box responses."""

    def set_response(kind: str, value: QMessageBox.StandardButton) -> None:
        responses[kind] = value

    return set_response


class _WorkerState:
    """Collects worker lifecycle events for the ``stub_worker`` fixture."""

    def __init__(self) -> None:
        self.created: list[QObject] = []
        self.cancels: list[QObject] = []
        self.waits: list[int | None] = []
        self.terminates: list[QObject] = []
        self.starts: list[QObject] = []


class _ImmediateWorker(QObject):
    """Worker implementation used by the ``stub_worker`` fixture."""

    finished = Signal(object)
    error = Signal(object)
    state: ClassVar[_WorkerState | None] = None

    def __init__(self, func, kwargs: dict[str, object]):
        super().__init__()
        self.func = func
        self.kwargs = dict(kwargs)
        self._cancel = Event()
        self._running = False
        state = type(self).state
        if state is not None:
            state.created.append(self)

    def __getattr__(self, name: str):
        if name == "isRunning":
            return self.is_running
        raise AttributeError(name)

    def is_running(self) -> bool:
        return self._running

    def cancel(self) -> None:
        state = type(self).state
        if state is not None:
            state.cancels.append(self)
        self._cancel.set()
        self._running = False

    def wait(self, timeout: int | None = None) -> bool:
        state = type(self).state
        if state is not None:
            state.waits.append(timeout)
        return True

    def terminate(self) -> None:
        state = type(self).state
        if state is not None:
            state.terminates.append(self)
        self._running = False

    def start(self) -> None:
        state = type(self).state
        if state is None:
            return
        self._running = True
        state.starts.append(self)
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

    @classmethod
    def configure(cls, state: _WorkerState) -> None:
        cls.state = state


def _create_immediate_worker(state: _WorkerState) -> type[QObject]:
    """Return a worker class that executes tasks synchronously for tests."""
    _ImmediateWorker.configure(state)
    return _ImmediateWorker
