"""Shared Qt fixtures for GUI smoke tests."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

os.environ.setdefault("QT_OPENGL", "software")

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtWidgets import QFileDialog

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


@pytest.fixture(autouse=True)
def _disable_author_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Skip the author metadata prompt during GUI initialisation."""
    monkeypatch.setattr(gui_main_window.MainWindow, "check_author", lambda _self: None)
