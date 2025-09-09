import json

from pdf_toolbox import gui


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
