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


def test_get_pptx_renderer_choice_normalises_values():
    assert cfg.get_pptx_renderer_choice({}) == "auto"
    assert cfg.get_pptx_renderer_choice({"pptx_renderer": "MS_OFFICE"}) == "ms_office"
    assert (
        cfg.get_pptx_renderer_choice({"pptx_renderer": "HTTP_OFFICE"}) == "http_office"
    )
    assert cfg.get_pptx_renderer_choice({"pptx_renderer": " none "}) == "none"
    assert cfg.get_pptx_renderer_choice({"pptx_renderer": None}) == "none"
    assert cfg.get_pptx_renderer_choice({"pptx_renderer": "unknown"}) == "unknown"


def test_save_config_normalises_renderer(tmp_path):
    path = tmp_path / "pdf_toolbox_config.json"
    cfg.save_config_at(path, {"pptx_renderer": None})
    stored = json.loads(path.read_text())
    assert stored["pptx_renderer"] == "none"
    loaded = cfg.load_config_at(path)
    assert loaded["pptx_renderer"] == "none"
