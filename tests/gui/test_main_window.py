"""Comprehensive Qt GUI tests that exercise MainWindow behaviour."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import pytest

pytest.importorskip("PySide6.QtWidgets")
from PySide6.QtWidgets import QApplication

from pdf_toolbox import actions, gui

pytest_plugins = ("tests.gui.conftest_qt",)

pytestmark = [
    pytest.mark.gui,
    pytest.mark.usefixtures("force_lang_en", "temp_config_dir", "no_file_dialogs"),
]


def test_load_config_default(temp_config_dir: Path) -> None:
    """Loading config without an existing file returns the defaults."""
    config_path = temp_config_dir / "pdf_toolbox_config.json"
    assert not config_path.exists()
    assert gui.load_config() == gui.DEFAULT_CONFIG


def test_save_config_roundtrip(temp_config_dir: Path) -> None:
    """Saving config writes JSON that round-trips cleanly."""
    config_path = temp_config_dir / "pdf_toolbox_config.json"
    payload = {"a": 1}
    gui.save_config(payload)
    assert json.loads(config_path.read_text()) == payload


def _make_window(qtbot) -> gui.MainWindow:
    """Helper that instantiates a main window for use in tests."""
    window = gui.MainWindow()
    qtbot.addWidget(window)
    return window


def test_mainwindow_populates_actions(monkeypatch: pytest.MonkeyPatch, qtbot) -> None:
    """The action tree populates with registered actions."""

    def _sample() -> None:
        pass

    act = actions.build_action(_sample, name="Sample", category="demo")
    monkeypatch.setattr(gui, "list_actions", lambda: [act])
    window = _make_window(qtbot)
    try:
        assert window.tree.topLevelItemCount() > 0
    finally:
        window.close()


def test_mainwindow_collect_args(monkeypatch: pytest.MonkeyPatch, qtbot) -> None:
    """Collected arguments mirror the widgets' state."""

    def sample(name: str, flag: bool = False) -> None:
        del name, flag

    act = actions.build_action(sample, name="Sample")
    monkeypatch.setattr(gui, "list_actions", lambda: [act])
    window = _make_window(qtbot)
    try:
        window.current_action = act
        window.build_form(act)
        window.current_widgets["name"].setText("foo")
        window.current_widgets["flag"].setChecked(True)
        assert window.collect_args() == {"name": "foo", "flag": True}
    finally:
        window.close()


def test_main_raises_without_qt(monkeypatch: pytest.MonkeyPatch) -> None:
    """`gui.main()` surfaces the import error when Qt is unavailable."""
    monkeypatch.setattr(gui, "QT_AVAILABLE", False)
    monkeypatch.setattr(gui, "QT_IMPORT_ERROR", RuntimeError("missing"))
    with pytest.raises(RuntimeError):
        gui.main()


def test_build_form_handles_pep604_union(
    monkeypatch: pytest.MonkeyPatch, qtbot
) -> None:
    """Union fields expose both combo box and spin box with toggling."""

    def sample(dpi: int | Literal["Low", "High"] = "High") -> None:
        del dpi

    act = actions.build_action(sample, name="Sample")
    monkeypatch.setattr(gui, "list_actions", lambda: [act])
    window = _make_window(qtbot)
    try:
        window.build_form(act)
        window.show()
        combo, spin = window.current_widgets["dpi"]
        assert combo.currentText() == "High"
        assert not spin.isVisible()
        combo.setCurrentText("Custom")
        QApplication.processEvents()
        assert spin.isVisible()
    finally:
        window.close()


def test_build_form_union_int_default(monkeypatch: pytest.MonkeyPatch, qtbot) -> None:
    """Integer defaults propagate into the custom spin box path."""

    def sample(dpi: int | Literal["Low", "High"] = 150) -> None:
        del dpi

    act = actions.build_action(sample, name="Sample")
    monkeypatch.setattr(gui, "list_actions", lambda: [act])
    window = _make_window(qtbot)
    try:
        window.build_form(act)
        window.show()
        QApplication.processEvents()
        combo, spin = window.current_widgets["dpi"]
        assert combo.currentText() == "Custom"
        assert spin.isVisible()
        assert spin.value() == 150
    finally:
        window.close()


def test_float_none_spinbox_range(monkeypatch: pytest.MonkeyPatch, qtbot) -> None:
    """Float-or-none parameters allow large upper bounds."""

    def sample(max_size_mb: float | None = None) -> None:
        del max_size_mb

    act = actions.build_action(sample, name="Sample")
    monkeypatch.setattr(gui, "list_actions", lambda: [act])
    window = _make_window(qtbot)
    try:
        window.build_form(act)
        spin = window.current_widgets["max_size_mb"]
        assert spin.maximum() > 99
    finally:
        window.close()


def test_build_form_hides_cancel(monkeypatch: pytest.MonkeyPatch, qtbot) -> None:
    """The cancel parameter is not exposed in the form."""

    def sample(path: str, cancel=None) -> None:
        del path, cancel

    act = actions.build_action(sample, name="Sample")
    monkeypatch.setattr(gui, "list_actions", lambda: [act])
    window = _make_window(qtbot)
    try:
        window.build_form(act)
        assert "cancel" not in window.current_widgets
    finally:
        window.close()


def test_miro_profile_toggles_fields(monkeypatch: pytest.MonkeyPatch, qtbot) -> None:
    """Selecting the Miro profile hides fields and shows help text."""
    import pdf_toolbox.gui.main_window as mw
    from pdf_toolbox.actions.miro import miro_export

    act = actions.build_action(miro_export, name="miro_export")
    monkeypatch.setattr(gui, "list_actions", lambda: [act])
    monkeypatch.setattr(mw, "load_config", lambda: {"last_export_profile": "standard"})
    saved: dict[str, object] = {}
    monkeypatch.setattr(mw, "save_config", lambda cfg: saved.update(cfg))

    window = _make_window(qtbot)
    try:
        top_item = window.tree.topLevelItem(0)
        assert top_item is not None
        item = top_item.child(0)
        assert item is not None
        window.on_item_clicked(item)
        combo = window.profile_combo
        assert combo is not None
        assert combo.currentData() == "standard"
        for name in ("image_format", "dpi", "quality"):
            widget = window.field_rows.get(name)
            assert widget is not None
            assert widget.isVisible()
        combo.setCurrentIndex(combo.findData("miro"))
        QApplication.processEvents()
        assert combo.currentData() == "miro"
        for name in ("image_format", "dpi", "quality"):
            widget = window.field_rows.get(name)
            assert widget is not None
            assert not widget.isVisible()
        assert window.profile_help_label is not None
        assert window.profile_help_label.isVisible()
        assert window.cfg["last_export_profile"] == "miro"
        assert saved.get("last_export_profile") == "miro"
    finally:
        window.close()


def test_pptx_error_messages_use_translations(
    monkeypatch: pytest.MonkeyPatch, qtbot
) -> None:
    """Renderer errors surface translated strings in the log dock."""
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

    window = _make_window(qtbot)
    try:
        window.on_error(PptxRenderingError("invalid_range", code="invalid_range"))
        text = window.log.toPlainText()
        assert "invalid_range" not in text
        assert tr("pptx_invalid_range") in text

        window.log.clear()
        window.on_error(PptxProviderUnavailableError())
        assert tr("pptx.no_provider") in window.log.toPlainText()
    finally:
        window.close()


def test_on_run_fails_fast_without_pptx_provider(
    monkeypatch: pytest.MonkeyPatch, qtbot
) -> None:
    """Running a PPTX action without a provider warns the user immediately."""
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
    calls: list[str] = []

    def fake_select(choice: str) -> None:
        calls.append(choice)

    monkeypatch.setattr(mw.pptx_registry, "select", fake_select)

    warnings: list[tuple[str, str]] = []

    def fake_warning(_parent, title, text):
        warnings.append((title, text))
        return mw.QMessageBox.StandardButton.Ok

    monkeypatch.setattr(mw.QMessageBox, "warning", fake_warning)

    window = _make_window(qtbot)
    try:
        window.current_action = act
        window.build_form(act)
        widget = window.current_widgets["input_pptx"]
        widget.setText("deck.pptx")
        baseline_calls = len(calls)
        window.on_run()
        assert warnings
        title, text = warnings[-1]
        assert title == tr("warning")
        assert text == tr("pptx.no_provider")
        assert window.worker is None
        assert window.banner.isVisible()
        assert len(calls) == baseline_calls + 1
    finally:
        window.close()


def test_select_pptx_provider_handles_truthy_non_string(
    monkeypatch: pytest.MonkeyPatch, qtbot
) -> None:
    """Truthy non-string config entries are coerced before selection."""
    import pdf_toolbox.gui.main_window as mw

    monkeypatch.setattr(gui, "list_actions", lambda: [])

    cfg = gui.DEFAULT_CONFIG.copy()
    cfg.update({"language": "en", "pptx_renderer": True})
    monkeypatch.setattr(mw, "load_config", lambda: cfg.copy())
    monkeypatch.setattr(mw, "save_config", lambda _cfg: None)

    calls: list[str] = []

    def fake_select(choice: str) -> None:
        calls.append(choice)

    monkeypatch.setattr(mw.pptx_registry, "select", fake_select)

    window = _make_window(qtbot)
    try:
        window.cfg["pptx_renderer"] = True
        provider = window._select_pptx_provider()
        assert provider is None
        assert calls == ["True"]
    finally:
        window.close()
