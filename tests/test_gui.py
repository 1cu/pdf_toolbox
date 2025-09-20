import json
import os

import pytest

pytest.importorskip("PySide6.QtWidgets")
from PySide6.QtWidgets import QApplication

from pdf_toolbox import actions, gui


@pytest.fixture(scope="module")
def app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    patcher = pytest.MonkeyPatch()
    patcher.setattr(gui.MainWindow, "check_author", lambda _: None)
    app = QApplication.instance() or QApplication([])
    yield app
    app.quit()
    patcher.undo()


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


def test_mainwindow_populates_actions(app, monkeypatch):
    _ = app

    def _sample() -> None:
        pass

    act = actions.build_action(_sample, name="Sample", category="demo")
    monkeypatch.setattr(gui, "list_actions", lambda: [act])
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
        win.current_action = act
        win.build_form(act)
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


def test_build_form_union_int_default(app, monkeypatch):
    _ = app
    from typing import Literal

    def sample(dpi: int | Literal["Low", "High"] = 150) -> None:
        pass

    act = actions.build_action(sample, name="Sample")
    monkeypatch.setattr(gui, "list_actions", lambda: [act])
    win = gui.MainWindow()
    try:
        win.build_form(act)
        win.show()
        QApplication.processEvents()
        combo, spin = win.current_widgets["dpi"]
        assert combo.currentText() == "Custom"
        assert spin.isVisible()
        assert spin.value() == 150
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


def test_miro_profile_toggles_fields(app, monkeypatch):
    _ = app
    import pdf_toolbox.gui.main_window as mw
    from pdf_toolbox.actions.miro import miro_export

    act = actions.build_action(miro_export, name="miro_export")
    monkeypatch.setattr(gui, "list_actions", lambda: [act])
    monkeypatch.setattr(mw, "load_config", lambda: {"last_export_profile": "standard"})
    saved: dict[str, object] = {}
    monkeypatch.setattr(mw, "save_config", lambda cfg: saved.update(cfg))

    win = gui.MainWindow()
    try:
        item = win.tree.topLevelItem(0).child(0)
        win.on_item_clicked(item)
        combo = win.profile_combo
        assert combo is not None
        assert combo.currentData() == "standard"
        for name in ("image_format", "dpi", "quality"):
            widget = win.field_rows.get(name)
            assert widget is not None
            assert widget.isVisible()
        combo.setCurrentIndex(combo.findData("miro"))
        QApplication.processEvents()
        assert combo.currentData() == "miro"
        for name in ("image_format", "dpi", "quality"):
            widget = win.field_rows.get(name)
            assert widget is not None
            assert not widget.isVisible()
        assert win.profile_help_label is not None
        assert win.profile_help_label.isVisible()
        assert win.cfg["last_export_profile"] == "miro"
        assert saved.get("last_export_profile") == "miro"
    finally:
        win.close()


def test_pptx_error_messages_use_translations(app, monkeypatch):
    _ = app
    import pdf_toolbox.gui.main_window as mw
    from pdf_toolbox.i18n import tr
    from pdf_toolbox.renderers.pptx import (
        PptxProviderUnavailableError,
        PptxRenderingError,
    )

    monkeypatch.setattr(gui, "list_actions", lambda: [])

    cfg = gui.DEFAULT_CONFIG.copy()
    cfg.update({"language": "en"})
    monkeypatch.setattr(mw, "load_config", lambda: cfg.copy())
    monkeypatch.setattr(mw, "save_config", lambda _cfg: None)

    win = gui.MainWindow()
    try:
        win.on_error(PptxRenderingError("invalid_range", code="invalid_range"))
        text = win.log.toPlainText()
        assert "invalid_range" not in text
        assert tr("pptx_invalid_range") in text

        win.log.clear()
        win.on_error(PptxProviderUnavailableError())
        assert tr("pptx.no_provider") in win.log.toPlainText()
    finally:
        win.close()


def test_on_run_fails_fast_without_pptx_provider(app, monkeypatch):
    _ = app
    import pdf_toolbox.gui.main_window as mw
    from pdf_toolbox.i18n import tr

    def sample(input_pptx: str) -> None:
        del input_pptx

    act = actions.build_action(sample, name="Sample", requires_pptx_renderer=True)
    monkeypatch.setattr(gui, "list_actions", lambda: [act])

    cfg = gui.DEFAULT_CONFIG.copy()
    cfg.update({"language": "en"})
    monkeypatch.setattr(mw, "load_config", lambda: cfg.copy())
    monkeypatch.setattr(mw, "save_config", lambda _cfg: None)
    monkeypatch.setattr(mw.pptx_registry, "select", lambda _choice: None)

    warnings: list[tuple[str, str]] = []

    def fake_warning(_parent, title, text):
        warnings.append((title, text))
        return mw.QMessageBox.StandardButton.Ok

    monkeypatch.setattr(mw.QMessageBox, "warning", fake_warning)

    win = gui.MainWindow()
    try:
        win.current_action = act
        win.build_form(act)
        widget = win.current_widgets["input_pptx"]
        widget.setText("deck.pptx")
        win.on_run()
        assert warnings
        title, text = warnings[-1]
        assert title == tr("warning")
        assert text == tr("pptx.no_provider")
        assert win.worker is None
        assert win.banner.isVisible()
    finally:
        win.close()
