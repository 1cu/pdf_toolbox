"""Comprehensive Qt GUI tests that exercise MainWindow behaviour."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Literal, cast

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialogButtonBox,
    QDoubleSpinBox,
    QLabel,
    QLineEdit,
    QSpinBox,
)

from pdf_toolbox import actions, gui
from pdf_toolbox.gui.main_window import ComboBoxWithSpin
from pdf_toolbox.gui.widgets import FileEdit

pytest_plugins = ("tests.gui.conftest_qt",)

pytestmark = [
    pytest.mark.gui,
    pytest.mark.usefixtures("force_lang_en", "temp_config_dir", "no_file_dialogs"),
]


def _expect_widget[TWidget](
    window: gui.MainWindow, key: str, expected_type: type[TWidget]
) -> TWidget:
    widget = window.current_widgets[key]
    assert isinstance(widget, expected_type)
    return cast(TWidget, widget)


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
        name_edit = _expect_widget(window, "name", QLineEdit)
        name_edit.setText("foo")
        flag_box = _expect_widget(window, "flag", QCheckBox)
        flag_box.setChecked(True)
        assert window.collect_args() == {"name": "foo", "flag": True}
    finally:
        window.close()


def test_main_raises_without_qt(monkeypatch: pytest.MonkeyPatch) -> None:
    """`gui.main()` surfaces the import error when Qt is unavailable."""
    monkeypatch.setattr(gui, "QT_AVAILABLE", False)
    monkeypatch.setattr(gui, "QT_IMPORT_ERROR", RuntimeError("missing"))
    with pytest.raises(RuntimeError):
        gui.main()


def test_build_form_handles_pep604_union(monkeypatch: pytest.MonkeyPatch, qtbot) -> None:
    """Union fields expose both combo box and spin box with toggling."""

    def sample(dpi: int | Literal["Low", "High"] = "High") -> None:
        del dpi

    act = actions.build_action(sample, name="Sample")
    monkeypatch.setattr(gui, "list_actions", lambda: [act])
    window = _make_window(qtbot)
    try:
        window.build_form(act)
        window.show()
        widget = window.current_widgets["dpi"]
        assert isinstance(widget, ComboBoxWithSpin)
        assert widget.combo_box.currentText() == "High"
        assert not widget.spin_box.isVisible()
        idx = widget.combo_box.findData("__custom__")
        widget.combo_box.setCurrentIndex(max(idx, 0))
        QApplication.processEvents()
        assert widget.spin_box.isVisible()
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
        widget = window.current_widgets["dpi"]
        assert isinstance(widget, ComboBoxWithSpin)
        assert widget.combo_box.currentData() == "__custom__"
        assert widget.spin_box.isVisible()
        assert widget.spin_box.value() == 150
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
        spin = _expect_widget(window, "max_size_mb", QDoubleSpinBox)
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


def test_build_form_skips_pptx_probe_for_unrelated_actions(
    monkeypatch: pytest.MonkeyPatch, qtbot
) -> None:
    """Actions without PPTX requirements avoid renderer probes."""

    def sample(flag: bool = False) -> None:
        del flag

    act = actions.build_action(sample, name="Sample", requires_pptx_renderer=False)
    monkeypatch.setattr(gui, "list_actions", lambda: [act])
    window = _make_window(qtbot)
    try:
        window.current_action = act

        def _fail() -> None:
            pytest.fail("should not probe PPTX providers")

        monkeypatch.setattr(window, "_select_pptx_provider", _fail)
        window.build_form(act)
    finally:
        window.close()


def test_build_form_resets_form_between_actions(monkeypatch: pytest.MonkeyPatch, qtbot) -> None:
    """Subsequent form builds clear previously added rows."""

    def action_one(path: str) -> None:
        del path

    def action_two(name: str) -> None:
        del name

    act_one = actions.build_action(action_one, name="One")
    act_two = actions.build_action(action_two, name="Two")
    monkeypatch.setattr(gui, "list_actions", lambda: [act_one, act_two])
    window = _make_window(qtbot)
    try:
        window.build_form(act_one)
        assert "path" in window.current_widgets
        window.build_form(act_two)
        assert "path" not in window.current_widgets
        assert "name" in window.current_widgets
    finally:
        window.close()


def test_build_form_unknown_saved_profile_defaults_to_miro(
    monkeypatch: pytest.MonkeyPatch, qtbot
) -> None:
    """Invalid saved profile values fall back to the default Miro option."""
    import pdf_toolbox.gui.main_window as mw
    from pdf_toolbox.actions.miro import miro_export

    act = actions.build_action(miro_export, name="miro_export")
    monkeypatch.setattr(gui, "list_actions", lambda: [act])
    monkeypatch.setattr(mw, "load_config", lambda: {"last_export_profile": "mystery"})
    monkeypatch.setattr(mw, "save_config", lambda _cfg: None)

    window = _make_window(qtbot)
    try:
        top_item = window.tree.topLevelItem(0)
        assert top_item is not None
        item = top_item.child(0)
        assert item is not None
        window.on_item_clicked(item)
        combo = window.profile_combo
        assert combo is not None
        assert combo.currentData() == "miro"
    finally:
        window.close()


def test_build_form_union_without_literal(monkeypatch: pytest.MonkeyPatch, qtbot) -> None:
    """Union parameters without literals fall back to a spin box."""

    def sample(level: int | float = 2.5) -> None:
        del level

    act = actions.build_action(sample, name="Sample")
    monkeypatch.setattr(gui, "list_actions", lambda: [act])
    window = _make_window(qtbot)
    try:
        window.build_form(act)
        widget = window.current_widgets["level"]
        assert isinstance(widget, QSpinBox)
        assert widget.minimum() == 0
    finally:
        window.close()


def test_build_form_creates_multi_file_field(monkeypatch: pytest.MonkeyPatch, qtbot) -> None:
    """Parameters named ``paths`` enable the multi-file widget."""
    import pdf_toolbox.gui.main_window as mw

    def sample(paths: list[str] | None = None) -> None:
        del paths

    act = actions.build_action(sample, name="Sample")
    monkeypatch.setattr(gui, "list_actions", lambda: [act])
    window = _make_window(qtbot)
    try:
        window.build_form(act)
        widget = window.current_widgets["paths"]
        assert isinstance(widget, mw.FileEdit)
        assert widget.multi is True
    finally:
        window.close()


def test_miro_profile_toggles_fields(monkeypatch: pytest.MonkeyPatch, qtbot) -> None:
    """Selecting the Miro profile hides fields and shows help text."""
    import pdf_toolbox.gui.main_window as mw
    from pdf_toolbox.actions.miro import miro_export

    act = actions.build_action(miro_export, name="miro_export")
    monkeypatch.setattr(gui, "list_actions", lambda: [act])
    monkeypatch.setattr(mw, "load_config", lambda: {"last_export_profile": "custom"})
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
        assert combo.currentData() == "custom"
        for name in (
            "options.image_format",
            "options.dpi",
            "options.quality",
        ):
            widget = window.field_rows.get(name)
            assert widget is not None
            assert widget.isVisible()
        assert saved == {}
        combo.setCurrentIndex(combo.findData("miro"))
        QApplication.processEvents()
        assert combo.currentData() == "miro"
        for name in (
            "options.image_format",
            "options.dpi",
            "options.quality",
        ):
            widget = window.field_rows.get(name)
            assert widget is not None
            assert not widget.isVisible()
        assert window.profile_help_label is not None
        assert window.profile_help_label.isVisible()
        assert window.cfg["last_export_profile"] == "miro"
        assert saved.get("last_export_profile") == "miro"
    finally:
        window.close()


def test_pptx_error_messages_use_translations(monkeypatch: pytest.MonkeyPatch, qtbot) -> None:
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


def test_on_run_fails_fast_without_pptx_provider(monkeypatch: pytest.MonkeyPatch, qtbot) -> None:
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
        widget = _expect_widget(window, "input_pptx", FileEdit)
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


def test_set_row_visible_ignores_missing_field(monkeypatch: pytest.MonkeyPatch, qtbot) -> None:
    """Calling ``_set_row_visible`` on unknown keys is a no-op."""
    monkeypatch.setattr(gui, "list_actions", lambda: [])
    window = _make_window(qtbot)
    try:
        window._set_row_visible("missing", False)
    finally:
        window.close()


def test_on_info_without_action_shows_nothing(
    monkeypatch: pytest.MonkeyPatch, qtbot, messagebox_stubs
) -> None:
    """Info dialog is skipped when no action is selected."""
    monkeypatch.setattr(gui, "list_actions", lambda: [])
    window = _make_window(qtbot)
    try:
        window.current_action = None
        window.on_info()
        assert not messagebox_stubs.calls["instances"]
    finally:
        window.close()


def test_on_run_without_action(monkeypatch: pytest.MonkeyPatch, qtbot) -> None:
    """Attempting to run without an action leaves the UI unchanged."""
    monkeypatch.setattr(gui, "list_actions", lambda: [])
    window = _make_window(qtbot)
    try:
        window.current_action = None
        window.on_run()
        assert window.worker is None
    finally:
        window.close()


def test_on_run_cancel_wait_timeout(monkeypatch: pytest.MonkeyPatch, qtbot) -> None:
    """Workers that fail to stop cleanly are terminated."""
    from pdf_toolbox.i18n import tr

    def sample(path: str) -> None:
        del path

    act = actions.build_action(sample, name="Sample")
    monkeypatch.setattr(gui, "list_actions", lambda: [act])
    window = _make_window(qtbot)
    try:
        window.current_action = act
        window.build_form(act)
        file_edit = _expect_widget(window, "path", FileEdit)
        file_edit.setText("file.pdf")

        class BlockingWorker:
            def __init__(self) -> None:
                self.cancelled = False
                self.wait_calls: list[object] = []
                self.terminated = False

            def isRunning(self) -> bool:  # noqa: N802  # pdf-toolbox: mimic Qt worker API naming | issue:-
                return True

            def cancel(self) -> None:
                self.cancelled = True

            def wait(self, timeout: int | None = None) -> bool:
                self.wait_calls.append(timeout)
                return timeout is None

            def terminate(self) -> None:
                self.terminated = True

        worker = BlockingWorker()
        window.worker = worker  # type: ignore[assignment]  # pdf-toolbox: stub worker lacks QObject base class | issue:-
        window.on_run()
        assert worker.cancelled is True
        assert worker.wait_calls == [100, None]
        assert worker.terminated is True
        assert window.run_btn.text() == tr("start")
        assert window.status_key == "cancelled"
    finally:
        window.close()


def test_update_status_reflects_log_state(qtbot) -> None:
    """Status text reflects whether the log widget is visible."""
    window = _make_window(qtbot)
    try:
        window.log.setVisible(True)
        window.update_status("Working", "working")
        assert window.status.text().endswith("▼")
        window.log.setVisible(False)
        window.update_status("Idle")
        assert window.status.text().endswith("▶")
        assert window.status_key == "Idle"
    finally:
        window.close()


def test_collect_args_handles_composite_widgets(
    monkeypatch: pytest.MonkeyPatch, qtbot, tmp_path: Path
) -> None:
    """Collecting arguments normalises values from complex widgets."""

    def sample(
        dpi: int | Literal["Low", "High"] = "High",
        paths: list[str] | None = None,
        max_size_mb: float | None = None,
        mode: Literal["A", "B"] = "A",
        count: int | None = None,
    ) -> None:
        del dpi, paths, max_size_mb, mode, count

    act = actions.build_action(sample, name="Sample")
    monkeypatch.setattr(gui, "list_actions", lambda: [act])
    window = _make_window(qtbot)
    try:
        window.current_action = act
        window.build_form(act)
        assert "dpi" in window.current_widgets
        widget = window.current_widgets["dpi"]
        assert isinstance(widget, ComboBoxWithSpin)
        idx = widget.combo_box.findData("__custom__")
        widget.combo_box.setCurrentIndex(max(idx, 0))
        widget.spin_box.setValue(300)
        file_one = tmp_path / "a.pdf"
        file_two = tmp_path / "b.pdf"
        file_one.write_text("dummy")
        file_two.write_text("dummy")
        file_edit = _expect_widget(window, "paths", FileEdit)
        file_edit.setText(f"{file_one};{file_two}")
        double_spin = _expect_widget(window, "max_size_mb", QDoubleSpinBox)
        double_spin.setValue(0)
        mode_combo = _expect_widget(window, "mode", QComboBox)
        mode_combo.setCurrentText("B")
        count_spin = _expect_widget(window, "count", QSpinBox)
        count_spin.setValue(0)
        result = window.collect_args()
        assert result["dpi"] == 300
        assert result["paths"] == [str(file_one), str(file_two)]
        assert result["max_size_mb"] is None
        assert result["mode"] == "B"
        assert result["count"] is None
    finally:
        window.close()


@pytest.mark.slow
def test_collect_args_multi_file_requires_value(monkeypatch: pytest.MonkeyPatch, qtbot) -> None:
    """Empty multi-file inputs raise a validation error."""

    def sample(paths: list[str]) -> None:
        del paths

    act = actions.build_action(sample, name="Sample")
    monkeypatch.setattr(gui, "list_actions", lambda: [act])
    window = _make_window(qtbot)
    try:
        window.current_action = act
        window.build_form(act)
        file_edit = _expect_widget(window, "paths", FileEdit)
        file_edit.setText("")
        with pytest.raises(ValueError, match="cannot be empty"):
            window.collect_args()
    finally:
        window.close()


def test_on_language_preserves_stop_text_when_running(
    monkeypatch: pytest.MonkeyPatch, qtbot, dialog_exec_stub
) -> None:
    """Changing language keeps the stop label when a worker is active."""
    from pdf_toolbox.i18n import tr

    monkeypatch.setattr(gui, "list_actions", lambda: [])
    window = _make_window(qtbot)
    try:

        class ActiveWorker:
            def __init__(self) -> None:
                self.cancelled = False

            def isRunning(self) -> bool:  # noqa: N802  # pdf-toolbox: mimic Qt worker API naming | issue:-
                return True

            def cancel(self) -> None:
                self.cancelled = True

            def wait(self, timeout: int | None = None) -> bool:
                self.waited = timeout
                return True

        window.worker = ActiveWorker()  # type: ignore[assignment]  # pdf-toolbox: stub worker lacks QObject base class | issue:-

        def configure(dialog) -> None:
            combo = dialog.findChildren(QComboBox)[0]
            combo.setCurrentText(tr("english"))

        dialog_exec_stub.set_callback(configure)
        window.on_language()
        assert window.run_btn.text() == tr("stop") + " ❌"
    finally:
        window.close()


def test_on_pptx_renderer_reports_renderer_name(
    monkeypatch: pytest.MonkeyPatch, qtbot, dialog_exec_stub
) -> None:
    """The renderer dialog shows the effective renderer name when available."""

    class DummyRenderer:
        pass

    monkeypatch.setattr(gui, "list_actions", lambda: [])
    window = _make_window(qtbot)
    try:
        monkeypatch.setattr(window, "_select_pptx_provider", lambda: DummyRenderer())

        def accept(dialog) -> None:
            dialog.findChildren(QDialogButtonBox)[0].accepted.emit()

        dialog_exec_stub.set_callback(accept)
        window.on_pptx_renderer()
        dialog = dialog_exec_stub.calls[-1]
        labels = [lbl.text() for lbl in dialog.findChildren(QLabel)]
        assert "DummyRenderer" in labels
    finally:
        window.close()


def test_set_row_visible_toggles_label_visibility(monkeypatch: pytest.MonkeyPatch, qtbot) -> None:
    """Toggling a row hides both the widget and its label."""

    def sample(path: str) -> None:
        del path

    act = actions.build_action(sample, name="Sample")
    monkeypatch.setattr(gui, "list_actions", lambda: [act])
    window = _make_window(qtbot)
    try:
        window.build_form(act)
        widget = window.field_rows["path"]
        label = window.form_layout.labelForField(widget)
        assert label is not None
        window._set_row_visible("path", False)
        assert not widget.isVisible()
        assert not label.isVisible()
        window._set_row_visible("path", True)
        QApplication.processEvents()
        assert widget.isVisible()
        assert label.isVisible()
    finally:
        window.close()


def test_update_pptx_banner_hides_with_provider(monkeypatch: pytest.MonkeyPatch, qtbot) -> None:
    """The PPTX banner disappears once a provider is available."""

    def sample(input_pptx: str) -> None:
        del input_pptx

    act = actions.build_action(sample, name="Sample", requires_pptx_renderer=True)
    monkeypatch.setattr(gui, "list_actions", lambda: [act])
    window = _make_window(qtbot)
    try:
        from pdf_toolbox.renderers.pptx_base import BasePptxRenderer

        class DummyProvider(BasePptxRenderer):
            name = "dummy"

            def to_images(self, *args, **kwargs) -> str:  # type: ignore[override]  # pdf-toolbox: stub implements abstract renderer for tests | issue:-
                del args, kwargs
                return "images"

            def to_pdf(self, *args, **kwargs) -> str:  # type: ignore[override]  # pdf-toolbox: stub implements abstract renderer for tests | issue:-
                del args, kwargs
                return "pdf"

        window.current_action = act
        window._update_pptx_banner(None)
        assert window.banner.isVisible()
        window._update_pptx_banner(DummyProvider())
        assert not window.banner.isVisible()
    finally:
        window.close()


def test_open_pptx_docs_uses_desktop_services(monkeypatch: pytest.MonkeyPatch, qtbot) -> None:
    """Opening the PPTX docs delegates to QDesktopServices."""
    import pdf_toolbox.gui.main_window as mw

    window = _make_window(qtbot)
    urls: list[QUrl] = []

    def fake_open(url: QUrl) -> bool:
        urls.append(url)
        return True

    monkeypatch.setattr(mw.QDesktopServices, "openUrl", fake_open)
    try:
        window._open_pptx_docs()
    finally:
        window.close()

    assert urls
    assert urls[0].toString() == QUrl(mw.PPTX_PROVIDER_DOCS_URL).toString()


def test_info_dialog_renders_help_html(
    monkeypatch: pytest.MonkeyPatch, qtbot, messagebox_stubs
) -> None:
    """The help dialog formats descriptions as rich text."""

    def sample() -> None:
        """Line1."""

    sample.__doc__ = "Line1\nLine2."

    act = actions.build_action(sample, name="Sample")
    monkeypatch.setattr(gui, "list_actions", lambda: [act])
    window = _make_window(qtbot)
    try:
        window.current_action = act
        window.on_info()
        instance = messagebox_stubs.calls["instances"][-1]
        assert "Line1" in instance.text
        assert "<br>" in instance.text
        assert instance.text_format is not None
    finally:
        window.close()


def test_on_run_collects_validation_errors(
    monkeypatch: pytest.MonkeyPatch, qtbot, messagebox_stubs
) -> None:
    """Validation failures surface via a critical message box."""

    def sample(path: str) -> None:
        del path

    act = actions.build_action(sample, name="Sample")
    monkeypatch.setattr(gui, "list_actions", lambda: [act])
    window = _make_window(qtbot)
    try:
        window.current_action = act
        window.build_form(act)
        widget = _expect_widget(window, "path", FileEdit)
        widget.clear()
        window.on_run()
        assert messagebox_stubs.calls["critical"]
        _parent, title, text = messagebox_stubs.calls["critical"][-1]
        assert title == "Error"
        assert "cannot" in text.lower()
        assert window.worker is None
    finally:
        window.close()


def test_on_run_success_triggers_worker_lifecycle(
    monkeypatch: pytest.MonkeyPatch, qtbot, stub_worker
) -> None:
    """Successful runs update progress, status, and the log view."""

    def sample(input_pdf: str) -> str:
        return input_pdf.upper()

    act = actions.build_action(sample, name="Sample")
    monkeypatch.setattr(gui, "list_actions", lambda: [act])
    window = _make_window(qtbot)
    try:
        window.current_action = act
        window.build_form(act)
        file_edit = _expect_widget(window, "input_pdf", FileEdit)
        file_edit.setText("report.pdf")
        window.on_run()
        qtbot.waitUntil(lambda: window.worker is None)
        assert stub_worker.starts
        assert window.worker is None
        assert window.progress.maximum() == 1
        assert window.progress.value() == 1
        assert window.status_key == "done"
        assert window.log.isVisible()
        assert "REPORT.PDF" in window.log.toPlainText()
    finally:
        window.close()


def test_on_run_handles_worker_error(monkeypatch: pytest.MonkeyPatch, qtbot, stub_worker) -> None:
    """Worker exceptions populate the log and reset the UI."""

    def sample() -> None:
        raise RuntimeError("boom")

    act = actions.build_action(sample, name="Sample")
    monkeypatch.setattr(gui, "list_actions", lambda: [act])
    window = _make_window(qtbot)
    try:
        window.current_action = act
        window.build_form(act)
        window.on_run()
        assert window.status_key == "error"
        assert window.log.isVisible()
        assert "boom" in window.log.toPlainText()
        assert stub_worker.starts
    finally:
        window.close()


def test_on_run_cancel_running_worker(monkeypatch: pytest.MonkeyPatch, qtbot, stub_worker) -> None:
    """Cancelling a running worker resets progress and status."""
    from pdf_toolbox.i18n import tr

    def sample(path: str) -> None:
        del path

    act = actions.build_action(sample, name="Sample")
    monkeypatch.setattr(gui, "list_actions", lambda: [act])
    window = _make_window(qtbot)
    try:
        window.current_action = act
        window.build_form(act)
        file_edit = _expect_widget(window, "path", FileEdit)
        file_edit.setText("file.pdf")
        running = stub_worker.cls(sample, {"path": "file.pdf"})
        running._running = True
        assert running.isRunning() is True
        window.worker = running
        window.on_run()
        assert stub_worker.cancels
        assert stub_worker.waits
        assert stub_worker.waits[-1] == 100
        assert window.worker is None
        assert running.isRunning() is False
        assert window.status_key == "cancelled"
        assert window.progress.value() == 0
        assert window.run_btn.text() == tr("start")
    finally:
        window.close()


def test_on_finished_handles_iterable_results(qtbot) -> None:
    """Lists are rendered line-by-line in the log panel."""
    window = _make_window(qtbot)
    try:
        window.log.clear()
        window.on_finished(["one", "two"])
        assert window.log.entries()
        assert window.log.entries()[-1].message == "one\ntwo"
        assert window.status_key == "done"
    finally:
        window.close()


def test_on_finished_appends_existing_log(qtbot) -> None:
    """Existing log text is preserved when new results arrive."""
    window = _make_window(qtbot)
    try:
        window.log.add_entry("baseline", level="INFO", source="test")
        window.on_finished("extra")
        messages = [entry.message for entry in window.log.entries()]
        assert "baseline" in messages[0]
        assert messages[-1] == "extra"
    finally:
        window.close()


def test_on_finished_shows_open_output_button(
    monkeypatch: pytest.MonkeyPatch, qtbot, tmp_path: Path
) -> None:
    """Successful runs expose a shortcut to the output directory."""
    import pdf_toolbox.gui.main_window as mw

    output_file = tmp_path / "result.pdf"
    output_file.write_text("content")

    urls: list[QUrl] = []

    def fake_open(url: QUrl) -> bool:
        urls.append(url)
        return True

    monkeypatch.setattr(mw.QDesktopServices, "openUrl", fake_open)

    window = _make_window(qtbot)
    try:
        window.on_finished(str(output_file))
        assert window.open_output_btn.isVisible()
        assert window.open_output_btn.isEnabled()
        window.on_open_output()
    finally:
        window.close()

    assert urls
    assert urls[0].toLocalFile() == str(output_file.parent.resolve())


def test_on_finished_hides_output_button_for_missing_files(qtbot) -> None:
    """Non-existent outputs do not surface the quick access button."""
    window = _make_window(qtbot)
    try:
        window.on_finished("/nonexistent/path/file.txt")
        assert not window.open_output_btn.isVisible()
    finally:
        window.close()


def test_on_error_clears_output_targets(qtbot, tmp_path: Path) -> None:
    """Errors reset any previously collected output locations."""
    window = _make_window(qtbot)
    try:
        existing = tmp_path / "file.txt"
        existing.write_text("x")
        window.on_finished(str(existing))
        assert window.open_output_btn.isVisible()
        window.on_error("boom")
        assert not window.open_output_btn.isVisible()
    finally:
        window.close()


def test_on_error_appends_existing_log(qtbot) -> None:
    """Error messages append when log output already exists."""
    window = _make_window(qtbot)
    try:
        window.log.add_entry("baseline", level="INFO", source="test")
        window.on_error("failure")
        assert window.log.isVisible()
        messages = [entry.message for entry in window.log.entries()]
        assert messages[-2] == "baseline"
        assert messages[-1] == "failure"
    finally:
        window.close()


def test_toggle_log_updates_status_arrow(qtbot) -> None:
    """The log toggle keeps status arrows in sync."""
    window = _make_window(qtbot)
    try:
        window.log.setVisible(False)
        window.update_status("Ready", "ready")
        window.toggle_log()
        assert window.log.isVisible()
        assert window.status.text().endswith("▼")
        window.toggle_log()
        assert not window.log.isVisible()
        assert window.status.text().endswith("▶")
    finally:
        window.close()


@pytest.mark.slow
def test_on_author_saves_new_values(
    monkeypatch: pytest.MonkeyPatch, qtbot, dialog_exec_stub
) -> None:
    """Accepted author edits persist to the configuration file."""
    import pdf_toolbox.gui.main_window as mw

    saved: list[dict[str, str]] = []
    monkeypatch.setattr(mw, "save_config", lambda cfg: saved.append(cfg.copy()))

    def fill(dialog) -> None:
        edits = dialog.findChildren(QLineEdit)
        assert len(edits) == 2
        edits[0].setText("Alice")
        edits[1].setText("alice@example.com")

    dialog_exec_stub.set_callback(fill)
    window = _make_window(qtbot)
    try:
        window.on_author()
        assert window.cfg["author"] == "Alice"
        assert window.cfg["email"] == "alice@example.com"
        assert saved
        assert saved[-1]["author"] == "Alice"
    finally:
        window.close()


def test_on_log_level_updates_configuration(
    monkeypatch: pytest.MonkeyPatch, qtbot, dialog_exec_stub
) -> None:
    """Changing the log level stores the choice and reconfigures logging."""
    import pdf_toolbox.gui.main_window as mw

    saved: list[dict[str, str]] = []
    monkeypatch.setattr(mw, "save_config", lambda cfg: saved.append(cfg.copy()))
    reconfigured: list[tuple[str, object]] = []
    monkeypatch.setattr(
        mw,
        "configure_logging",
        lambda level, handler: reconfigured.append((level, handler)),
    )

    def fill(dialog) -> None:
        combo = dialog.findChildren(QComboBox)[0]
        combo.setCurrentText("DEBUG")

    dialog_exec_stub.set_callback(fill)
    window = _make_window(qtbot)
    try:
        window.on_log_level()
        assert window.cfg["log_level"] == "DEBUG"
        assert saved
        assert saved[-1]["log_level"] == "DEBUG"
        assert reconfigured
        assert reconfigured[-1][0] == "DEBUG"
    finally:
        window.close()


def test_on_language_updates_configuration(
    monkeypatch: pytest.MonkeyPatch, qtbot, dialog_exec_stub
) -> None:
    """Language changes persist and refresh visible translations."""
    import pdf_toolbox.gui.main_window as mw
    from pdf_toolbox.i18n import tr

    saved: list[dict[str, str]] = []
    monkeypatch.setattr(mw, "save_config", lambda cfg: saved.append(cfg.copy()))
    chosen: list[str | None] = []
    monkeypatch.setattr(mw, "set_language", lambda lang: chosen.append(lang))

    def fill(dialog) -> None:
        combo = dialog.findChildren(QComboBox)[0]
        combo.setCurrentText(tr("german"))

    dialog_exec_stub.set_callback(fill)
    window = _make_window(qtbot)
    try:
        window.on_language()
        assert window.cfg["language"] == "de"
        assert saved
        assert saved[-1]["language"] == "de"
        assert chosen
        assert chosen[-1] == "de"
        assert window.lbl_actions.text() == tr("actions")
    finally:
        window.close()


@pytest.mark.slow
def test_on_pptx_renderer_updates_configuration(
    monkeypatch: pytest.MonkeyPatch, qtbot, dialog_exec_stub
) -> None:
    """Selecting a PPTX renderer stores the choice."""
    import pdf_toolbox.gui.main_window as mw

    saved: list[dict[str, object]] = []
    monkeypatch.setattr(mw, "save_config", lambda cfg: saved.append(cfg.copy()))

    def fill(dialog) -> None:
        combo = dialog.findChildren(QComboBox)[0]
        index = combo.findData("http_office")
        combo.setCurrentIndex(index)
        http_type = dialog.findChild(QComboBox, "pptx_http_type")
        assert http_type is not None
        http_type_index = http_type.findData("stirling")
        http_type.setCurrentIndex(max(http_type_index, 0))
        http_endpoint = dialog.findChild(QLineEdit, "pptx_http_endpoint")
        assert http_endpoint is not None
        http_endpoint.setText("https://stirling.example/api/pptx")
        http_timeout = dialog.findChild(QDoubleSpinBox, "pptx_http_timeout")
        assert http_timeout is not None
        http_timeout.setValue(45.0)
        http_verify = dialog.findChild(QCheckBox, "pptx_http_verify_tls")
        assert http_verify is not None
        http_verify.setChecked(False)
        header_name = dialog.findChild(QLineEdit, "pptx_http_header_name")
        header_value = dialog.findChild(QLineEdit, "pptx_http_header_value")
        assert header_name is not None
        assert header_value is not None
        header_name.setText("X-API-Key")
        header_value.setText("secret-token")

    dialog_exec_stub.set_callback(fill)
    window = _make_window(qtbot)
    try:
        window.cfg["http_office"] = {
            "mode": "auto",
            "endpoint": "https://existing.example/convert",
            "timeout_s": 30.0,
            "verify_tls": True,
            "headers": {
                "Authorization": "Bearer old-token",
                "X-Trace-ID": "42",
            },
        }
        window.on_pptx_renderer()
        assert window.cfg["pptx_renderer"] == "http_office"
        assert saved
        assert saved[-1]["pptx_renderer"] == "http_office"
        http_saved = saved[-1]["http_office"]
        assert isinstance(http_saved, dict)
        assert http_saved["mode"] == "stirling"
        assert http_saved["endpoint"] == "https://stirling.example/api/pptx"
        assert http_saved["verify_tls"] is False
        assert http_saved["headers"] == {
            "X-Trace-ID": "42",
            "X-API-Key": "secret-token",
        }
        assert http_saved["timeout_s"] == pytest.approx(45.0)
        assert window.cfg["http_office"] == http_saved
    finally:
        window.close()


def test_on_about_displays_version(
    monkeypatch: pytest.MonkeyPatch, qtbot, messagebox_stubs
) -> None:
    """About dialog shows the package version."""
    import pdf_toolbox.gui.main_window as mw

    monkeypatch.setattr(mw.metadata, "version", lambda _pkg: "1.2.3")
    window = _make_window(qtbot)
    try:
        window.on_about()
        instance = messagebox_stubs.calls["instances"][-1]
        assert "1.2.3" in instance.text
        assert messagebox_stubs.calls["exec"][-1] is instance
    finally:
        window.close()


def test_format_exception_message_deduplicates_details(qtbot) -> None:
    """Renderer errors include detail without duplication."""
    from pdf_toolbox.i18n import tr
    from pdf_toolbox.renderers.pptx import PptxRenderingError

    window = _make_window(qtbot)
    try:
        err = PptxRenderingError("Extra info", code="invalid_range", detail="Detail")
        message = window._format_exception_message(err)
        lines = message.splitlines()
        assert lines[0] == tr("pptx_invalid_range")
        assert "Detail" in lines[1]
        assert lines[2] == "Extra info: Detail"
    finally:
        window.close()


def test_format_error_message_plain_string(qtbot) -> None:
    """Plain objects are stringified when formatting errors."""
    window = _make_window(qtbot)
    try:
        window.on_error("plain failure")
        assert window.log.entries()
        assert window.log.entries()[-1].message == "plain failure"
    finally:
        window.close()


def test_close_event_waits_for_worker(qtbot, stub_worker) -> None:
    """Closing the window cancels and waits for running workers."""
    window = _make_window(qtbot)
    try:

        def noop(cancel):  # type: ignore[no-untyped-def]  # pdf-toolbox: Worker injects Event parameter dynamically | issue:-
            cancel.is_set()

        worker = stub_worker.cls(noop, {})
        worker._running = True
        window.worker = worker
        window.closeEvent(QCloseEvent())
        assert stub_worker.cancels
        assert stub_worker.waits
        assert stub_worker.waits[-1] == 1000
    finally:
        window.close()


def test_check_author_prompts_when_missing(
    monkeypatch: pytest.MonkeyPatch, qtbot, messagebox_stubs
) -> None:
    """Missing author metadata triggers a warning and dialog."""
    import pdf_toolbox.gui.main_window as mw

    monkeypatch.setattr(mw, "_load_author_info", lambda: ("", ""))
    window = _make_window(qtbot)
    try:
        invoked: list[str] = []
        monkeypatch.setattr(window, "on_author", lambda: invoked.append("on_author"))
        original_attr = getattr(mw.MainWindow, "_original_check_author", None)
        assert original_attr is not None
        original = cast(Callable[[gui.MainWindow], None], original_attr)
        original(window)
        assert messagebox_stubs.calls["warning"]
        assert invoked == ["on_author"]
    finally:
        window.close()
