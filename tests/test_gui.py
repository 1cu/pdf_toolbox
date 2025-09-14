import json
import os

import pytest

pytest.importorskip("PySide6.QtWidgets")
from PySide6.QtWidgets import QApplication

from pdf_toolbox import actions, gui


@pytest.fixture(scope="module")
def app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    yield app
    app.quit()


def test_load_config_default(tmp_path, monkeypatch):
    cfg_path = tmp_path / "config.json"
    monkeypatch.setattr(gui, "CONFIG_PATH", cfg_path)
    cfg = gui.load_config()
    assert cfg == gui.DEFAULT_CONFIG


def test_save_config_roundtrip(tmp_path, monkeypatch):
    cfg_path = tmp_path / "config.json"
    monkeypatch.setattr(gui, "CONFIG_PATH", cfg_path)
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    data = {"a": 1}
    gui.save_config(data)
    loaded = json.loads(cfg_path.read_text())
    assert loaded == data


def test_mainwindow_populates_actions(app):
    _ = app
    win = gui.MainWindow()
    try:
        assert win.tree.topLevelItemCount() > 0
    finally:
        win.close()


def test_mainwindow_collect_args(app, monkeypatch):
    _ = app

    def sample(name: str, flag: bool = False) -> None:
        pass

    act = actions.build_action(sample, name="Sample")
    monkeypatch.setattr(gui, "list_actions", lambda: [act])
    win = gui.MainWindow()
    try:
        item = win.tree.topLevelItem(0).child(0)
        win.on_item_clicked(item)
        win.current_widgets["name"].setText("foo")
        win.current_widgets["flag"].setChecked(True)
        kwargs = win.collect_args()
        assert kwargs == {"name": "foo", "flag": True}
    finally:
        win.close()


def test_main_raises_without_qt(monkeypatch):
    monkeypatch.setattr(gui, "QT_AVAILABLE", False)
    monkeypatch.setattr(gui, "QT_IMPORT_ERROR", RuntimeError("missing"))
    with pytest.raises(RuntimeError):
        gui.main()


def test_build_form_handles_pep604_union(app, monkeypatch):
    _ = app
    from typing import Literal

    def sample(dpi: int | Literal["Low", "High"] = "High") -> None:
        pass

    act = actions.build_action(sample, name="Sample")
    monkeypatch.setattr(gui, "list_actions", lambda: [act])
    win = gui.MainWindow()
    try:
        win.build_form(act)
        win.show()
        combo, spin = win.current_widgets["dpi"]
        assert combo.currentText() == "High"
        assert not spin.isVisible()
        combo.setCurrentText("Custom")
        QApplication.processEvents()
        assert spin.isVisible()
    finally:
        win.close()


def test_float_none_spinbox_range(app, monkeypatch):
    _ = app

    def sample(max_size_mb: float | None = None) -> None:
        pass

    act = actions.build_action(sample, name="Sample")
    monkeypatch.setattr(gui, "list_actions", lambda: [act])
    win = gui.MainWindow()
    try:
        win.build_form(act)
        spin = win.current_widgets["max_size_mb"]
        assert spin.maximum() > 99
    finally:
        win.close()


def test_build_form_hides_cancel(app, monkeypatch):
    _ = app

    def sample(path: str, cancel=None) -> None:
        pass

    act = actions.build_action(sample, name="Sample")
    monkeypatch.setattr(gui, "list_actions", lambda: [act])
    win = gui.MainWindow()
    try:
        win.build_form(act)
        assert "cancel" not in win.current_widgets
    finally:
        win.close()
