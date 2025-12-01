from __future__ import annotations

from dataclasses import dataclass

import pytest

import pdf_toolbox.gui.main_window as mw
from pdf_toolbox import actions, gui
from pdf_toolbox.gui.worker import Worker

pytest_plugins = ("tests.gui.conftest_qt",)

pytestmark = [
    pytest.mark.gui,
    pytest.mark.usefixtures("force_lang_en", "temp_config_dir", "no_file_dialogs"),
]


@dataclass
class _TestOptions:
    quality: int = 80
    format: str = "PNG"


def _make_window(qtbot) -> gui.MainWindow:
    window = gui.MainWindow()
    qtbot.addWidget(window)
    return window


def test_action_settings_are_saved(monkeypatch: pytest.MonkeyPatch, qtbot) -> None:
    """Action settings are saved to config when running."""

    def sample(quality: int = 80, name: str = "default") -> None:
        pass

    act = actions.build_action(sample, name="Sample")
    monkeypatch.setattr(gui, "list_actions", lambda: [act])

    saved_cfg = {}

    def mock_save_config(cfg):
        saved_cfg.update(cfg)

    monkeypatch.setattr(mw, "save_config", mock_save_config)

    window = _make_window(qtbot)
    try:
        window.current_action = act
        window.build_form(act)

        # quality is LineEdit by default for unknown int params
        window.current_widgets["quality"].setText("90")
        window.current_widgets["name"].setText("custom")

        # Mock worker to avoid actual execution
        monkeypatch.setattr(Worker, "start", lambda _: None)

        window.on_run()

        assert saved_cfg.get("quality") == "90"
        assert saved_cfg.get("name") == "custom"

    finally:
        window.close()


def test_paths_are_not_saved(monkeypatch: pytest.MonkeyPatch, qtbot) -> None:
    """Path arguments are not saved to config."""

    def sample(input_pdf: str, output_dir: str) -> None:
        pass

    act = actions.build_action(sample, name="Sample")
    monkeypatch.setattr(gui, "list_actions", lambda: [act])

    saved_cfg = {}

    def mock_save_config(cfg):
        saved_cfg.update(cfg)

    monkeypatch.setattr(mw, "save_config", mock_save_config)

    window = _make_window(qtbot)
    try:
        window.current_action = act
        window.build_form(act)

        window.current_widgets["input_pdf"].setText("/tmp/input.pdf")  # noqa: S108  # pdf-toolbox: test fixture path only | issue:-
        window.current_widgets["output_dir"].setText("/tmp/output")  # noqa: S108  # pdf-toolbox: test fixture path only | issue:-

        # Mock worker
        monkeypatch.setattr(Worker, "start", lambda _: None)

        window.on_run()

        assert "input_pdf" not in saved_cfg
        assert "output_dir" not in saved_cfg

    finally:
        window.close()


def test_settings_are_restored(monkeypatch: pytest.MonkeyPatch, qtbot) -> None:
    """Settings are restored from config when building form."""

    def sample(quality: int = 80, name: str = "default") -> None:
        pass

    act = actions.build_action(sample, name="Sample")
    monkeypatch.setattr(gui, "list_actions", lambda: [act])

    # Pre-populate config
    cfg = gui.DEFAULT_CONFIG.copy()
    cfg.update({"quality": "75", "name": "restored"})
    monkeypatch.setattr(mw, "load_config", lambda: cfg)

    window = _make_window(qtbot)
    try:
        window.current_action = act
        window.build_form(act)

        assert window.current_widgets["quality"].text() == "75"
        assert window.current_widgets["name"].text() == "restored"

    finally:
        window.close()


def test_nested_dataclass_settings_are_saved(monkeypatch: pytest.MonkeyPatch, qtbot) -> None:
    """Nested dataclass settings like options.quality are saved correctly."""

    def sample(options: _TestOptions | None = None) -> None:
        pass

    act = actions.build_action(sample, name="Sample")
    monkeypatch.setattr(gui, "list_actions", lambda: [act])

    saved_cfg = {}

    def mock_save_config(cfg):
        saved_cfg.update(cfg)

    monkeypatch.setattr(mw, "save_config", mock_save_config)

    window = _make_window(qtbot)
    try:
        window.current_action = act
        window.build_form(act)

        # Nested params should be saved with dotted names
        window.current_widgets["options.quality"].setText("95")
        window.current_widgets["options.format"].setText("JPEG")

        monkeypatch.setattr(Worker, "start", lambda _: None)

        window.on_run()

        # Should save with nested keys
        assert saved_cfg.get("options.quality") == "95"
        assert saved_cfg.get("options.format") == "JPEG"

    finally:
        window.close()


def test_nested_dataclass_settings_are_restored(monkeypatch: pytest.MonkeyPatch, qtbot) -> None:
    """Nested dataclass settings are restored from config."""

    def sample(options: _TestOptions | None = None) -> None:
        pass

    act = actions.build_action(sample, name="Sample")
    monkeypatch.setattr(gui, "list_actions", lambda: [act])

    # Pre-populate config with nested keys
    cfg = gui.DEFAULT_CONFIG.copy()
    cfg.update({"options.quality": "90", "options.format": "WEBP"})
    monkeypatch.setattr(mw, "load_config", lambda: cfg)

    window = _make_window(qtbot)
    try:
        window.current_action = act
        window.build_form(act)

        # Should restore from nested keys
        assert window.current_widgets["options.quality"].text() == "90"
        assert window.current_widgets["options.format"].text() == "WEBP"

    finally:
        window.close()
