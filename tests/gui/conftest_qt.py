"""Shared Qt fixtures for GUI tests."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
os.environ.setdefault("QT_OPENGL", "software")

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtWidgets import QFileDialog

from pdf_toolbox import config, gui, i18n, utils
from pdf_toolbox.gui import main_window as gui_main_window


class _DialogStubs:
    """Deterministic responses for :mod:`PySide6.QtWidgets.QFileDialog`."""

    def __init__(self, base: Path) -> None:
        self._base = base
        self._base.mkdir(parents=True, exist_ok=True)
        self.directory = self._base / "chosen-dir"
        self.directory.mkdir(exist_ok=True)
        self.file = self._base / "chosen.pdf"
        self.file.write_text("dummy")
        self.files: list[Path] = [self.file]
        self._cancel_next: set[str] = set()

    def cancel_next(self, dialog: str) -> None:
        """Mark *dialog* to return a cancelled selection on the next call."""
        valid = {"existing_directory", "open_file_name", "open_file_names"}
        if dialog not in valid:
            raise ValueError(dialog)
        self._cancel_next.add(dialog)

    def get_existing_directory(self, *_args, **_kwargs) -> str:
        """Return the deterministic directory selection."""
        if "existing_directory" in self._cancel_next:
            self._cancel_next.remove("existing_directory")
            return ""
        return str(self.directory)

    def get_open_file_name(self, *_args, **_kwargs) -> tuple[str, str]:
        """Return the deterministic single-file selection."""
        if "open_file_name" in self._cancel_next:
            self._cancel_next.remove("open_file_name")
            return "", ""
        return str(self.file), ""

    def get_open_file_names(self, *_args, **_kwargs) -> tuple[list[str], str]:
        """Return the deterministic multi-file selection."""
        if "open_file_names" in self._cancel_next:
            self._cancel_next.remove("open_file_names")
            return ([], "")
        return ([str(path) for path in self.files], "")


@pytest.fixture(scope="session", autouse=True)
def _session_qapp(qapp):
    """Ensure pytest-qt initialises a single :class:`QApplication`."""
    return qapp


@pytest.fixture
def force_lang_en() -> Iterator[None]:
    """Force the GUI language to English for deterministic assertions."""
    previous = getattr(i18n, "_STATE", {}).get("lang")
    i18n.set_language("en")
    try:
        yield
    finally:
        i18n.set_language(previous)


@pytest.fixture
def temp_config_dir(monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Redirect configuration reads and writes to a temporary directory."""
    with TemporaryDirectory() as tmp:
        base = Path(tmp)
        cfg_path = base / "pdf_toolbox_config.json"
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(config, "CONFIG_PATH", cfg_path)
        monkeypatch.setattr(gui, "CONFIG_PATH", cfg_path)
        monkeypatch.setattr(gui_main_window, "CONFIG_PATH", cfg_path)
        monkeypatch.setattr(utils, "CONFIG_FILE", cfg_path)
        yield base


@pytest.fixture
def no_file_dialogs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> _DialogStubs:
    """Make file dialogs deterministic so tests avoid native UI prompts."""
    stubs = _DialogStubs(tmp_path / "dialog-selection")
    monkeypatch.setattr(
        QFileDialog, "getExistingDirectory", stubs.get_existing_directory
    )
    monkeypatch.setattr(QFileDialog, "getOpenFileName", stubs.get_open_file_name)
    monkeypatch.setattr(QFileDialog, "getOpenFileNames", stubs.get_open_file_names)
    return stubs


@pytest.fixture(autouse=True)
def _disable_author_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Skip the author metadata prompt during GUI initialisation."""
    monkeypatch.setattr(gui_main_window.MainWindow, "check_author", lambda _self: None)
