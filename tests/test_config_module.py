from __future__ import annotations
from __future__ import annotations

import json

import pdf_toolbox.config as cfg


def test_load_config_default(tmp_path, monkeypatch):
    path = tmp_path / "pdf_toolbox_config.json"
    monkeypatch.setattr(cfg, "CONFIG_PATH", path)
    data = cfg.load_config()
    assert data["language"] == "system"


def test_save_and_load_config(tmp_path, monkeypatch):
    path = tmp_path / "pdf_toolbox_config.json"
    monkeypatch.setattr(cfg, "CONFIG_PATH", path)
    cfg.save_config({"pptx_renderer": "ms_office"})
    loaded = cfg.load_config()
    assert loaded["pptx_renderer"] == "ms_office"
    raw = json.loads(path.read_text())
    assert raw["pptx_renderer"] == "ms_office"
