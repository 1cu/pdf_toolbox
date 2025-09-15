from __future__ import annotations

import json

from pdf_toolbox import config
from pdf_toolbox.renderers.ms_office import PptxMsOfficeRenderer
from pdf_toolbox.renderers.pptx import NullRenderer, get_pptx_renderer


def test_default_renderer(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "cfg.json")
    assert isinstance(get_pptx_renderer(), NullRenderer)


def test_ms_office_renderer(tmp_path, monkeypatch):
    path = tmp_path / "cfg.json"
    path.write_text(json.dumps({"pptx_renderer": "ms_office"}))
    monkeypatch.setattr(config, "CONFIG_PATH", path)
    assert isinstance(get_pptx_renderer(), PptxMsOfficeRenderer)


def test_unknown_renderer(tmp_path, monkeypatch):
    path = tmp_path / "cfg.json"
    path.write_text(json.dumps({"pptx_renderer": "unknown"}))
    monkeypatch.setattr(config, "CONFIG_PATH", path)
    assert isinstance(get_pptx_renderer(), NullRenderer)
